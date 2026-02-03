from typing import Optional, Any, Dict
from django.db.models import Model
from django.utils import timezone


class AuditService:
    """
    Service for audit logging.
    Will create AuditLog entries when that model is implemented.
    """
    
    @staticmethod
    def log_action(
        entity: Model,
        action: str,
        user: Optional['User'] = None,
        old_data: Optional[Dict[str, Any]] = None,
        new_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an action to audit trail.
        
        Args:
            entity: The model instance being acted upon
            action: Action being performed (from AuditAction enum)
            user: User performing the action
            old_data: Previous state (for updates)
            new_data: New state (for updates)
            metadata: Additional context
        """
        # TODO: Implement when AuditLog model is created
        # For now, just log to console in debug mode
        from django.conf import settings
        if settings.DEBUG:
            entity_type = f"{entity._meta.app_label}.{entity._meta.model_name}"
            print(f"[AUDIT] {action} on {entity_type}#{entity.pk} by {user}")
    
    @staticmethod
    def log_status_change(
        entity: Model,
        old_status: str,
        new_status: str,
        user: Optional['User'] = None,
        reason: Optional[str] = None
    ) -> None:
        """Log status change"""
        from core.constants import AuditAction
        
        metadata = {'reason': reason} if reason else None
        AuditService.log_action(
            entity=entity,
            action=AuditAction.UPDATE.value,
            user=user,
            old_data={'status': old_status},
            new_data={'status': new_status},
            metadata=metadata
        )
    
    @staticmethod
    def log_role_assignment(
        user: 'User',
        role: 'Role',
        assigned_by: Optional['User'] = None
    ) -> None:
        """Log role assignment to user"""
        from core.constants import AuditAction
        
        # Create a pseudo-entity for role assignment
        # TODO: Improve this when AuditLog model is ready
        AuditService.log_action(
            entity=user,
            action=AuditAction.UPDATE.value,
            user=assigned_by,
            new_data={'role_added': role.name}
        )
    
    @staticmethod
    def log_role_revocation(
        user: 'User',
        role_name: str,
        revoked_by: Optional['User'] = None
    ) -> None:
        """Log role revocation from user"""
        from core.constants import AuditAction
        
        AuditService.log_action(
            entity=user,
            action=AuditAction.UPDATE.value,
            user=revoked_by,
            old_data={'role_removed': role_name}
        )
    
    @staticmethod
    def log_user_deactivation(user: 'User', deactivated_by: 'User') -> None:
        """Log user deactivation"""
        from core.constants import AuditAction
        
        AuditService.log_action(
            entity=user,
            action=AuditAction.UPDATE.value,
            user=deactivated_by,
            new_data={'is_active': False}
        )
    
    @staticmethod
    def log_user_activation(user: 'User', activated_by: 'User') -> None:
        """Log user activation"""
        from core.constants import AuditAction
        
        AuditService.log_action(
            entity=user,
            action=AuditAction.UPDATE.value,
            user=activated_by,
            new_data={'is_active': True}
        )
