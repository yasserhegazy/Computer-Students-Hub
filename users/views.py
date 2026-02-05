# Create your views here.
import csv
from io import StringIO
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, CharFilter
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from django.http import HttpResponse

from users.models import User, Role, UserProfile
from users.serializers import (
    UserSerializer, UserDetailSerializer, RoleSerializer,
    UserProfileSerializer, AssignRoleSerializer, UpdateProfileSerializer
)
from users.permissions import IsAdmin, IsAuthenticatedUser, IsOwnerOrAdmin
from users.services.user_service import UserService
from users.services.role_service import RoleService
from core.exceptions import PermissionDeniedError, ValidationError
from core.utils.supabase_client import get_supabase_client
from core.utils.supabase_admin import get_supabase_admin_client
from core.services.audit_service import AuditService


class UserFilter(FilterSet):
    """Custom filter for users with role filtering"""
    role = CharFilter(field_name='user_roles__role__name', lookup_expr='iexact')
    
    class Meta:
        model = User
        fields = ['is_active', 'role']


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user management.
    
    Endpoints:
    - GET /api/users/ - List users (admin only)
    - GET /api/users/{id}/ - User detail (public)
    - PATCH /api/users/{id}/ - Update user (admin only)
    - DELETE /api/users/{id}/ - Soft delete user (admin only)
    - GET /api/users/me/ - Current user profile
    - PATCH /api/users/me/profile/ - Update current user profile
    - POST /api/users/{id}/assign-role/ - Assign role (admin only)
    - POST /api/users/{id}/revoke-role/ - Revoke role (admin only)
    - POST /api/users/{id}/deactivate/ - Deactivate user (admin only)
    - POST /api/users/{id}/activate/ - Activate user (admin only)
    - POST /api/users/{id}/restore/ - Restore soft-deleted user (admin only)
    - GET /api/users/{id}/statistics/ - Get user statistics (public)
    - GET /api/users/{id}/audit-log/ - Get user audit log (admin only)
    - POST /api/users/bulk-assign-roles/ - Bulk assign roles (admin only)
    - POST /api/users/bulk-activate/ - Bulk activate users (admin only)
    - POST /api/users/bulk-deactivate/ - Bulk deactivate users (admin only)
    - GET /api/users/export/ - Export users as CSV (admin only)
    - POST /api/users/{id}/reset-password/ - Reset user password (admin only, Supabase proxy)
    - POST /api/users/{id}/update-email/ - Update user email (admin only, Supabase proxy)
    - POST /api/users/{id}/send-verification/ - Send email verification (admin only, Supabase proxy)
    - POST /api/users/send-password-reset/ - Send password reset email (public, Supabase proxy)
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserFilter
    search_fields = ['email', 'display_name']
    ordering_fields = ['created_at', 'email', 'display_name']
    ordering = ['-created_at']
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']  # POST allowed for actions only (no create endpoint)
    
    def get_serializer_class(self):
        """Use detailed serializer for retrieve and me actions"""
        if self.action in ['retrieve', 'me']:
            return UserDetailSerializer
        return UserSerializer
    
    def get_permissions(self):
        """
        Set permissions based on action.
        List/update/delete/bulk operations require admin, retrieve/statistics are public, me requires auth.
        """
        admin_actions = [
            'list', 'update', 'partial_update', 'destroy',
            'assign_role', 'revoke_role', 'deactivate', 'activate', 'restore',
            'audit_log', 'bulk_assign_roles', 'bulk_activate', 'bulk_deactivate', 'export',
            'reset_password', 'update_email', 'send_verification'
        ]
        
        if self.action in admin_actions:
            return [IsAdmin()]
        elif self.action in ['me', 'update_profile']:
            return [IsAuthenticatedUser()]
        elif self.action in ['retrieve', 'statistics', 'send_password_reset']:
            return [AllowAny()]
        return [AllowAny()]
    
    def get_queryset(self):
        """Optimize queryset with prefetch"""
        queryset = super().get_queryset()
        
        # Exclude soft-deleted users by default (except for restore action)
        if self.action != 'restore':
            queryset = queryset.filter(is_deleted=False)
        
        # Prefetch roles for list view
        if self.action == 'list':
            queryset = queryset.with_roles()
        
        # Prefetch profile for detail view
        if self.action in ['retrieve', 'me']:
            queryset = queryset.select_related('profile')
        
        return queryset
    
    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """
        Get current user's profile.
        
        GET /api/users/me/
        """
        if not request.user or not request.user.is_authenticated:
            return Response(
                {'detail': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['patch'], url_path='me/profile')
    def update_profile(self, request):
        """
        Update current user's profile.
        
        PATCH /api/users/me/profile/
        Body: {bio, location, website, github_username, linkedin_url}
        """
        if not request.user or not request.user.is_authenticated:
            return Response(
                {'detail': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        serializer = UpdateProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Update profile using service
        profile = UserService.update_profile(
            user=request.user,
            **serializer.validated_data
        )
        
        profile_serializer = UserProfileSerializer(profile)
        return Response(profile_serializer.data)
    
    @action(detail=True, methods=['post'], url_path='assign-role')
    def assign_role(self, request, pk=None):
        """
        Assign a role to a user.
        
        POST /api/users/{id}/assign-role/
        Body: {role_name: 'instructor'}
        """
        user = self.get_object()
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            assignment = RoleService.assign_role(
                user=user,
                role_name=serializer.validated_data['role_name'],
                assigned_by=request.user
            )
            
            return Response({
                'detail': f'Role {serializer.validated_data["role_name"]} assigned to {user.display_name}',
                'user': UserDetailSerializer(user).data
            })
        except (ValidationError, PermissionDeniedError) as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], url_path='revoke-role')
    def revoke_role(self, request, pk=None):
        """
        Revoke a role from a user.
        
        POST /api/users/{id}/revoke-role/
        Body: {role_name: 'instructor'}
        """
        user = self.get_object()
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            revoked = RoleService.revoke_role(
                user=user,
                role_name=serializer.validated_data['role_name'],
                revoked_by=request.user
            )
            
            if revoked:
                return Response({
                    'detail': f'Role {serializer.validated_data["role_name"]} revoked from {user.display_name}',
                    'user': UserDetailSerializer(user).data
                })
            else:
                return Response(
                    {'detail': 'User does not have this role'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValidationError, PermissionDeniedError) as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """
        Deactivate a user account.
        
        POST /api/users/{id}/deactivate/
        """
        user = self.get_object()
        
        try:
            UserService.deactivate_user(user, request.user)
            return Response({
                'detail': f'User {user.display_name} deactivated',
                'user': UserDetailSerializer(user).data
            })
        except ValidationError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """
        Activate a user account.
        
        POST /api/users/{id}/activate/
        """
        user = self.get_object()
        
        UserService.activate_user(user, request.user)
        return Response({
            'detail': f'User {user.display_name} activated',
            'user': UserDetailSerializer(user).data
        })
    
    def update(self, request, *args, **kwargs):
        """
        Update user details (admin only).
        
        PATCH /api/users/{id}/
        Body: {email, display_name, is_active}
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Update user fields
        updated_fields = []
        if 'email' in serializer.validated_data:
            instance.email = serializer.validated_data['email']
            updated_fields.append('email')
        if 'display_name' in serializer.validated_data:
            instance.display_name = serializer.validated_data['display_name']
            updated_fields.append('display_name')
        if 'is_active' in serializer.validated_data:
            instance.is_active = serializer.validated_data['is_active']
            updated_fields.append('is_active')
        
        if updated_fields:
            instance.save(update_fields=updated_fields)
            # Log update
            AuditService.log_action(
                entity=instance,
                action='user_updated',
                user=request.user,
                metadata={'updated_fields': updated_fields}
            )
        
        return Response(UserDetailSerializer(instance).data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Soft delete a user (admin only).
        
        DELETE /api/users/{id}/
        """
        instance = self.get_object()
        
        # Soft delete
        instance.soft_delete()
        
        # Log deletion
        AuditService.log_action(
            entity=instance,
            action='user_deleted',
            user=request.user,
            metadata={'email': instance.email}
        )
        
        return Response({
            'detail': f'User {instance.display_name} soft deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """
        Restore a soft-deleted user.
        
        POST /api/users/{id}/restore/
        """
        # Get user including soft-deleted ones
        try:
            user = User.all_objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {'detail': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not user.is_deleted:
            return Response(
                {'detail': 'User is not deleted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Restore user
        user.restore()
        
        # Log restoration
        AuditService.log_action(
            entity=user,
            action='user_restored',
            user=request.user,
            metadata={'email': user.email}
        )
        
        return Response({
            'detail': f'User {user.display_name} restored successfully',
            'user': UserDetailSerializer(user).data
        })
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """
        Get user statistics.
        
        GET /api/users/{id}/statistics/
        """
        user = self.get_object()
        stats = UserService.get_user_statistics(user)
        
        return Response({
            'user_id': str(user.id),
            'display_name': user.display_name,
            'statistics': stats
        })
    
    @action(detail=True, methods=['get'])
    def audit_log(self, request, pk=None):
        """
        Get audit log for a user (admin only).
        
        GET /api/users/{id}/audit-log/
        
        Note: Currently returns console logs only. Full database persistence
        requires AuditLog model implementation.
        """
        user = self.get_object()
        
        # TODO: Implement when AuditLog model is created
        # For now, return placeholder
        return Response({
            'user_id': str(user.id),
            'message': 'Audit log feature requires AuditLog model implementation',
            'recent_actions': [
                # Placeholder - will be replaced with actual audit data
                {
                    'action': 'user_created',
                    'timestamp': user.created_at.isoformat(),
                    'details': 'User account created'
                }
            ]
        })
    
    @action(detail=False, methods=['post'], url_path='bulk-assign-roles')
    def bulk_assign_roles(self, request):
        """
        Bulk assign roles to multiple users.
        
        POST /api/users/bulk-assign-roles/
        Body: {user_ids: [uuid1, uuid2], role_name: 'instructor'}
        """
        user_ids = request.data.get('user_ids', [])
        role_name = request.data.get('role_name')
        
        if not user_ids or not role_name:
            return Response(
                {'detail': 'user_ids and role_name are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = {'success': [], 'failed': []}
        
        for user_id in user_ids:
            try:
                user = User.objects.get(pk=user_id)
                RoleService.assign_role(user, role_name, request.user)
                results['success'].append(str(user_id))
            except User.DoesNotExist:
                results['failed'].append({'user_id': str(user_id), 'reason': 'User not found'})
            except Exception as e:
                results['failed'].append({'user_id': str(user_id), 'reason': str(e)})
        
        return Response({
            'detail': f'Bulk role assignment completed',
            'results': results
        })
    
    @action(detail=False, methods=['post'], url_path='bulk-activate')
    def bulk_activate(self, request):
        """
        Bulk activate multiple users.
        
        POST /api/users/bulk-activate/
        Body: {user_ids: [uuid1, uuid2]}
        """
        user_ids = request.data.get('user_ids', [])
        
        if not user_ids:
            return Response(
                {'detail': 'user_ids are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = {'success': [], 'failed': []}
        
        for user_id in user_ids:
            try:
                user = User.objects.get(pk=user_id)
                UserService.activate_user(user, request.user)
                results['success'].append(str(user_id))
            except User.DoesNotExist:
                results['failed'].append({'user_id': str(user_id), 'reason': 'User not found'})
            except Exception as e:
                results['failed'].append({'user_id': str(user_id), 'reason': str(e)})
        
        return Response({
            'detail': f'Bulk activation completed',
            'results': results
        })
    
    @action(detail=False, methods=['post'], url_path='bulk-deactivate')
    def bulk_deactivate(self, request):
        """
        Bulk deactivate multiple users.
        
        POST /api/users/bulk-deactivate/
        Body: {user_ids: [uuid1, uuid2]}
        """
        user_ids = request.data.get('user_ids', [])
        
        if not user_ids:
            return Response(
                {'detail': 'user_ids are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = {'success': [], 'failed': []}
        
        for user_id in user_ids:
            try:
                user = User.objects.get(pk=user_id)
                UserService.deactivate_user(user, request.user)
                results['success'].append(str(user_id))
            except User.DoesNotExist:
                results['failed'].append({'user_id': str(user_id), 'reason': 'User not found'})
            except Exception as e:
                results['failed'].append({'user_id': str(user_id), 'reason': str(e)})
        
        return Response({
            'detail': f'Bulk deactivation completed',
            'results': results
        })
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        Export users as CSV (admin only).
        
        GET /api/users/export/?format=csv
        """
        format_type = request.query_params.get('format', 'csv')
        
        if format_type != 'csv':
            return Response(
                {'detail': 'Only CSV format is currently supported'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get filtered queryset
        queryset = self.filter_queryset(self.get_queryset()).select_related('profile').prefetch_related('roles')
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'ID', 'Email', 'Display Name', 'Is Active', 'Roles',
            'Created At', 'Total Bookmarks', 'Total Questions', 'Total Answers',
            'Reputation Score', 'Location', 'Website'
        ])
        
        # Write data
        for user in queryset:
            roles = ', '.join([role.name for role in user.roles.all()])
            profile = user.profile if hasattr(user, 'profile') else None
            
            writer.writerow([
                str(user.id),
                user.email,
                user.display_name,
                user.is_active,
                roles,
                user.created_at.isoformat(),
                profile.total_bookmarks if profile else 0,
                profile.total_questions if profile else 0,
                profile.total_answers if profile else 0,
                profile.reputation_score if profile else 0,
                profile.location if profile else '',
                profile.website if profile else ''
            ])
        
        # Create HTTP response
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="users_export.csv"'
        
        return response
    
    # Supabase Admin Proxy Endpoints
    
    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        """
        Reset user password via Supabase Admin API (admin only).
        
        POST /api/users/{id}/reset-password/
        Body: {new_password: 'SecurePass123!'}
        """
        user = self.get_object()
        new_password = request.data.get('new_password')
        
        if not new_password:
            return Response(
                {'detail': 'new_password is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not user.supabase_id:
            return Response(
                {'detail': 'User does not have a Supabase account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            admin_client = get_supabase_admin_client()
            result = admin_client.reset_user_password(
                user_id=user.supabase_id,
                new_password=new_password
            )
            
            # Log the action
            AuditService.log_action(
                entity=user,
                action='password_reset_by_admin',
                user=request.user,
                metadata={'email': user.email}
            )
            
            return Response({
                'detail': f'Password reset successfully for {user.email}',
                'success': True
            })
        except Exception as e:
            return Response(
                {'detail': f'Failed to reset password: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='update-email')
    def update_email(self, request, pk=None):
        """
        Update user email via Supabase Admin API (admin only).
        
        POST /api/users/{id}/update-email/
        Body: {new_email: 'newemail@example.com'}
        """
        user = self.get_object()
        new_email = request.data.get('new_email')
        
        if not new_email:
            return Response(
                {'detail': 'new_email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not user.supabase_id:
            return Response(
                {'detail': 'User does not have a Supabase account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            admin_client = get_supabase_admin_client()
            result = admin_client.update_user_email(
                user_id=user.supabase_id,
                new_email=new_email,
                email_confirm=True  # Admin updates are pre-confirmed
            )
            
            # Update Django user email too
            old_email = user.email
            user.email = new_email
            user.save(update_fields=['email'])
            
            # Log the action
            AuditService.log_action(
                entity=user,
                action='email_updated_by_admin',
                user=request.user,
                old_data={'email': old_email},
                new_data={'email': new_email}
            )
            
            return Response({
                'detail': f'Email updated successfully from {old_email} to {new_email}',
                'user': UserDetailSerializer(user).data
            })
        except Exception as e:
            return Response(
                {'detail': f'Failed to update email: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='send-verification')
    def send_verification(self, request, pk=None):
        """
        Send email verification to user via Supabase (admin only).
        
        POST /api/users/{id}/send-verification/
        Body: {redirect_to: 'https://example.com/verify'} (optional)
        """
        user = self.get_object()
        redirect_to = request.data.get('redirect_to')
        
        if not user.supabase_id:
            return Response(
                {'detail': 'User does not have a Supabase account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            admin_client = get_supabase_admin_client()
            result = admin_client.send_email_verification(
                user_id=user.supabase_id,
                redirect_to=redirect_to
            )
            
            # Log the action
            AuditService.log_action(
                entity=user,
                action='verification_email_sent',
                user=request.user,
                metadata={'email': user.email}
            )
            
            return Response({
                'detail': f'Verification email sent to {user.email}',
                'success': True
            })
        except Exception as e:
            return Response(
                {'detail': f'Failed to send verification email: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='send-password-reset')
    def send_password_reset(self, request):
        """
        Send password reset email (public endpoint).
        
        POST /api/users/send-password-reset/
        Body: {email: 'user@example.com', redirect_to: 'https://example.com/reset'} (redirect_to optional)
        """
        email = request.data.get('email')
        redirect_to = request.data.get('redirect_to')
        
        if not email:
            return Response(
                {'detail': 'email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            admin_client = get_supabase_admin_client()
            result = admin_client.send_password_reset_email(
                email=email,
                redirect_to=redirect_to
            )
            
            return Response({
                'detail': 'If the email exists, a password reset link has been sent',
                'success': True
            })
        except Exception as e:
            # Don't reveal if email exists - security best practice
            return Response({
                'detail': 'If the email exists, a password reset link has been sent',
                'success': True
            })


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for roles.
    
    Endpoints:
    - GET /api/roles/ - List all roles
    - GET /api/roles/{id}/ - Role detail
    """
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [AllowAny]
    pagination_class = None  # Disable pagination for roles
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    def initialize(self, request):
        """
        Initialize default roles.
        
        POST /api/roles/initialize/
        """
        RoleService.initialize_default_roles()
        roles = Role.objects.all()
        serializer = self.get_serializer(roles, many=True)
        return Response({
            'detail': 'Default roles initialized',
            'roles': serializer.data
        }, status=status.HTTP_200_OK)


# Authentication endpoints

@extend_schema(
    summary="Sync user from Supabase to Django",
    description="""
    Synchronizes a user from Supabase Auth to Django database after authentication.
    
    **Authentication Flow:**
    1. Frontend authenticates user with Supabase (using Supabase JS SDK)
    2. Frontend receives JWT access token from Supabase
    3. Frontend calls this endpoint with JWT token in Authorization header
    4. Django verifies JWT, extracts user info, and syncs to database
    5. Django returns synced user data with assigned roles
    
    **Usage:**
    Call this endpoint immediately after successful Supabase authentication
    (either register or login) to ensure user exists in Django database
    with proper roles assigned.
    """,
    parameters=[
        OpenApiParameter(
            name='Authorization',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.HEADER,
            required=True,
            description='Bearer token from Supabase authentication',
            examples=[
                OpenApiExample(
                    'Valid token',
                    value='Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                )
            ]
        ),
    ],
    responses={
        200: {
            "description": "User successfully synced",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "User synced successfully",
                        "user": {
                            "id": "abc123-def456-ghi789",
                            "supabase_id": "550e8400-e29b-41d4-a716-446655440000",
                            "email": "user@example.com",
                            "display_name": "John Doe",
                            "is_active": True,
                            "roles": ["student"]
                        }
                    }
                }
            }
        },
        401: {
            "description": "Invalid or missing token",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Authentication required",
                        "details": "No valid JWT token provided"
                    }
                }
            }
        },
        500: {
            "description": "Server error during sync",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Sync failed",
                        "details": "Error message details"
                    }
                }
            }
        }
    },
    tags=['Authentication']
)
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_user(request):
    """
    Sync authenticated user from Supabase to Django database.
    
    Frontend calls this after successful Supabase authentication
    to ensure user exists in Django with proper roles.
    """
    # Get token from Authorization header
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    
    if not auth_header.startswith('Bearer '):
        return Response(
            {
                'error': 'Authentication required',
                'details': 'No valid JWT token provided'
            },
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.replace('Bearer ', '')
    
    try:
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Get user from token
        user_response = supabase.auth.get_user(token)
        supabase_user = user_response.user
        
        if not supabase_user:
            return Response(
                {
                    'error': 'Invalid token',
                    'details': 'Could not retrieve user from token'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Extract user data from Supabase user object
        supabase_id = supabase_user.id
        email = supabase_user.email
        user_metadata = supabase_user.user_metadata or {}
        display_name = user_metadata.get('full_name') or user_metadata.get('display_name') or email.split('@')[0]
        avatar_url = user_metadata.get('avatar_url')
        
        # Sync user to Django database
        django_user = UserService.sync_from_supabase(
            supabase_id=supabase_id,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            user_metadata=user_metadata
        )
        
        # Get user roles
        roles = RoleService.get_user_roles(django_user)
        role_names = [role.name.lower() for role in roles]
        
        return Response(
            {
                'success': True,
                'message': 'User synced successfully',
                'user': {
                    'id': str(django_user.id),
                    'supabase_id': django_user.supabase_id,
                    'email': django_user.email,
                    'display_name': django_user.display_name,
                    'is_active': django_user.is_active,
                    'roles': role_names
                }
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        import traceback
        print(f"Sync error: {str(e)}")
        print(traceback.format_exc())
        return Response(
            {
                'error': 'Sync failed',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
