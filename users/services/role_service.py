from typing import List, Optional
from django.db import transaction
from django.core.exceptions import PermissionDenied
from users.models import User, Role, UserRoleAssignment
from core.constants import UserRole
from core.services.audit_service import AuditService
from core.exceptions import ValidationError, PermissionDeniedError


class RoleService:
    """
    Service class for role-related operations.
    All role management goes through this service for consistency and audit logging.
    """
    
    @staticmethod
    @transaction.atomic
    def assign_role(
        user: User,
        role_name: str,
        assigned_by: Optional[User] = None
    ) -> UserRoleAssignment:
        """
        Assign a role to a user.
        
        Args:
            user: User to assign role to
            role_name: Name of the role (from UserRole enum)
            assigned_by: User performing the assignment (None for system assignments)
            
        Returns:
            UserRoleAssignment instance
            
        Raises:
            ValidationError: If role_name is invalid
            PermissionDeniedError: If assigned_by doesn't have permission
        """
        # Validate role name
        if not UserRole.has_value(role_name):
            raise ValidationError(f"Invalid role: {role_name}")
        
        # Check permissions
        if assigned_by and not RoleService.can_assign_role(assigned_by, role_name):
            raise PermissionDeniedError(
                f"User {assigned_by.display_name} cannot assign role {role_name}"
            )
        
        # Get or create role
        role, _ = Role.objects.get_or_create(
            name=role_name,
            defaults={'description': f'{UserRole.get_display(role_name)} role'}
        )
        
        # Assign role (get_or_create to avoid duplicates)
        assignment, created = UserRoleAssignment.objects.get_or_create(
            user=user,
            role=role,
            defaults={'assigned_by': assigned_by}
        )
        
        # Log the action
        if created:
            AuditService.log_role_assignment(
                user=user,
                role=role,
                assigned_by=assigned_by
            )
        
        return assignment
    
    @staticmethod
    @transaction.atomic
    def revoke_role(
        user: User,
        role_name: str,
        revoked_by: Optional[User] = None
    ) -> bool:
        """
        Revoke a role from a user.
        
        Args:
            user: User to revoke role from
            role_name: Name of the role to revoke
            revoked_by: User performing the revocation
            
        Returns:
            True if role was revoked, False if user didn't have the role
            
        Raises:
            PermissionDeniedError: If revoked_by doesn't have permission
        """
        # Check permissions
        if revoked_by and not RoleService.can_revoke_role(revoked_by, role_name):
            raise PermissionDeniedError(
                f"User {revoked_by.display_name} cannot revoke role {role_name}"
            )
        
        try:
            assignment = UserRoleAssignment.objects.get(
                user=user,
                role__name=role_name
            )
            assignment.delete()
            
            # Log the action
            AuditService.log_role_revocation(
                user=user,
                role_name=role_name,
                revoked_by=revoked_by
            )
            
            return True
        except UserRoleAssignment.DoesNotExist:
            return False
    
    @staticmethod
    def can_assign_role(assigner: User, role_name: str) -> bool:
        """
        Check if a user can assign a specific role.
        
        Business rule: Only admins can assign roles.
        
        Args:
            assigner: User attempting to assign role
            role_name: Role being assigned
            
        Returns:
            True if user can assign role, False otherwise
        """
        # Only admins can assign roles
        if not assigner.has_role(UserRole.ADMIN.value):
            return False
        
        return True
    
    @staticmethod
    def can_revoke_role(revoker: User, role_name: str) -> bool:
        """
        Check if a user can revoke a specific role.
        
        Business rule: Only admins can revoke roles.
        
        Args:
            revoker: User attempting to revoke role
            role_name: Role being revoked
            
        Returns:
            True if user can revoke role, False otherwise
        """
        # Only admins can revoke roles
        return revoker.has_role(UserRole.ADMIN.value)
    
    @staticmethod
    def get_users_by_role(role_name: str) -> List[User]:
        """
        Get all users with a specific role.
        
        Args:
            role_name: Role name from UserRole enum
            
        Returns:
            List of User instances
        """
        return list(User.objects.by_role(role_name))
    
    @staticmethod
    @transaction.atomic
    def promote_to_instructor(user: User, admin: User) -> None:
        """
        Promote a user to instructor role.
        Convenience method wrapping assign_role.
        
        Args:
            user: User to promote
            admin: Admin performing the promotion
            
        Raises:
            PermissionDeniedError: If admin doesn't have permission
        """
        RoleService.assign_role(user, UserRole.INSTRUCTOR.value, admin)
    
    @staticmethod
    @transaction.atomic
    def promote_to_admin(user: User, admin: User) -> None:
        """
        Promote a user to admin role.
        Requires existing admin to perform action.
        
        Args:
            user: User to promote
            admin: Admin performing the promotion
            
        Raises:
            PermissionDeniedError: If admin doesn't have permission
        """
        if not admin.has_role(UserRole.ADMIN.value):
            raise PermissionDeniedError("Only admins can promote users to admin role")
        
        RoleService.assign_role(user, UserRole.ADMIN.value, admin)
    
    @staticmethod
    def initialize_default_roles() -> None:
        """Initialize default roles in the database"""
        Role.get_or_create_default_roles()
