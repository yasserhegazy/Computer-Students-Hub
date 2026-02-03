"""
User service - Business logic for user management.
Handles user lifecycle operations and profile management.
"""
from django.db import transaction
from typing import Optional, Dict, Any
from users.models import User, UserProfile
from users.services.role_service import RoleService
from core.services.audit_service import AuditService
from core.exceptions import ValidationError
from core.constants import UserRole, AuditAction


class UserService:
    """
    Service class for user-related operations.
    Centralizes user management logic and enforces business rules.
    """
    
    @staticmethod
    @transaction.atomic
    def sync_from_supabase(
        supabase_id: str,
        email: str,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        user_metadata: Optional[Dict[str, Any]] = None
    ) -> User:
        """
        Sync user from Supabase to local database.
        Creates user if doesn't exist, updates if exists.
        Automatically assigns Student role to new users.
        
        Args:
            supabase_id: Unique ID from Supabase Auth
            email: User's email address
            display_name: Display name (optional)
            avatar_url: Avatar URL from Supabase (optional)
            user_metadata: Additional metadata from Supabase JWT (optional)
            
        Returns:
            User instance with profile and default role assigned
        """
        user, created = User.objects.get_or_create(
            supabase_id=supabase_id,
            defaults={
                'email': email,
                'display_name': display_name or email.split('@')[0]
            }
        )
        
        # Update email if changed
        if user.email != email:
            user.email = email
            user.save(update_fields=['email'])
        
        # Update display name if changed and provided
        if display_name and user.display_name != display_name:
            user.display_name = display_name
            user.save(update_fields=['display_name'])
        
        # Create or update profile
        profile, profile_created = UserProfile.objects.get_or_create(
            user=user
        )
        
        # Update avatar if changed
        if avatar_url and profile.avatar_url != avatar_url:
            profile.avatar_url = avatar_url
            profile.save(update_fields=['avatar_url'])
        
        # Assign default Student role to new users
        if created:
            RoleService.assign_role(
                user=user,
                role_name=UserRole.STUDENT.value,
                assigned_by=None  # System assignment
            )
            
            # TODO: Log user registration when AuditLog model is fully implemented
            # AuditService.log_action(
            #     entity=user,
            #     action='user_registered',
            #     user=user
            # )
        
        return user
    
    @staticmethod
    @transaction.atomic
    def update_profile(
        user: User,
        **profile_data
    ) -> UserProfile:
        """
        Update user profile information.
        
        Args:
            user: User whose profile to update
            **profile_data: Profile fields to update (bio, location, website, etc.)
            
        Returns:
            Updated UserProfile instance
            
        Raises:
            ValidationError: If profile data is invalid
        """
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Allowed profile fields
        allowed_fields = [
            'bio', 'location', 'website', 'github_username', 'linkedin_url'
        ]
        
        # Update only allowed fields
        updated_fields = []
        for field, value in profile_data.items():
            if field in allowed_fields:
                setattr(profile, field, value)
                updated_fields.append(field)
        
        if updated_fields:
            profile.save(update_fields=updated_fields)
        
        return profile
    
    @staticmethod
    @transaction.atomic
    def deactivate_user(user: User, deactivated_by: User) -> None:
        """
        Deactivate a user account.
        
        Args:
            user: User to deactivate
            deactivated_by: Admin performing the deactivation
            
        Raises:
            ValidationError: If user tries to deactivate themselves
        """
        if user.id == deactivated_by.id:
            raise ValidationError("Users cannot deactivate themselves")
        
        user.is_active = False
        user.save(update_fields=['is_active'])
        
        # Log the action
        AuditService.log_user_deactivation(user, deactivated_by)
    
    @staticmethod
    @transaction.atomic
    def activate_user(user: User, activated_by: User) -> None:
        """
        Activate a user account.
        
        Args:
            user: User to activate
            activated_by: Admin performing the activation
        """
        user.is_active = True
        user.save(update_fields=['is_active'])
        
        # Log the action
        AuditService.log_user_activation(user, activated_by)
    
    @staticmethod
    def get_user_statistics(user: User) -> Dict[str, int]:
        """
        Get statistics for a user.
        Returns cached values from profile for performance.
        
        Args:
            user: User to get statistics for
            
        Returns:
            Dictionary of statistics
        """
        try:
            profile = user.profile
            return {
                'total_bookmarks': profile.total_bookmarks,
                'total_contributions': profile.total_contributions,
                'total_questions': profile.total_questions,
                'total_answers': profile.total_answers,
                'reputation_score': profile.reputation_score,
            }
        except UserProfile.DoesNotExist:
            return {
                'total_bookmarks': 0,
                'total_contributions': 0,
                'total_questions': 0,
                'total_answers': 0,
                'reputation_score': 0,
            }
    
    @staticmethod
    @transaction.atomic
    def increment_statistic(user: User, stat_name: str, increment: int = 1) -> None:
        """
        Increment a user statistic.
        Used when user performs actions (bookmark, question, answer, etc.)
        
        Args:
            user: User whose statistic to update
            stat_name: Name of statistic field
            increment: Amount to increment by (default 1)
        """
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        allowed_stats = [
            'total_bookmarks', 'total_contributions', 'total_questions',
            'total_answers', 'reputation_score'
        ]
        
        if stat_name in allowed_stats:
            current_value = getattr(profile, stat_name, 0)
            setattr(profile, stat_name, current_value + increment)
            profile.save(update_fields=[stat_name])
