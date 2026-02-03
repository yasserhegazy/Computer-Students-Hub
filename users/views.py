# Create your views here.
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

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


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for user management.
    
    Endpoints:
    - GET /api/users/ - List users (admin only)
    - GET /api/users/{id}/ - User detail (public)
    - GET /api/users/me/ - Current user profile
    - PATCH /api/users/me/profile/ - Update current user profile
    - POST /api/users/{id}/assign-role/ - Assign role (admin only)
    - POST /api/users/{id}/revoke-role/ - Revoke role (admin only)
    - POST /api/users/{id}/deactivate/ - Deactivate user (admin only)
    - POST /api/users/{id}/activate/ - Activate user (admin only)
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['email', 'display_name']
    ordering_fields = ['created_at', 'email', 'display_name']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Use detailed serializer for retrieve and me actions"""
        if self.action in ['retrieve', 'me']:
            return UserDetailSerializer
        return UserSerializer
    
    def get_permissions(self):
        """
        Set permissions based on action.
        List/create require admin, retrieve is public, me requires auth.
        """
        if self.action == 'list':
            return [IsAdmin()]
        elif self.action in ['me', 'update_profile']:
            return [IsAuthenticatedUser()]
        elif self.action in ['assign_role', 'revoke_role', 'deactivate', 'activate']:
            return [IsAdmin()]
        return [AllowAny()]
    
    def get_queryset(self):
        """Optimize queryset with prefetch"""
        queryset = super().get_queryset()
        
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
        
        # Sync user to Django database
        django_user = UserService.sync_from_supabase(supabase_user)
        
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
        return Response(
            {
                'error': 'Sync failed',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
