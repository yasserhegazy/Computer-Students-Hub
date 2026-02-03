# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db.models import Prefetch, QuerySet
from core.models import UUIDModel, TimestampedModel, SoftDeleteModel
from core.constants import UserRole
from typing import List, Optional


class UserQuerySet(QuerySet):
    """Custom QuerySet for User model with optimized query methods"""
    
    def with_roles(self):
        """Prefetch user roles for efficient queries"""
        from users.models import UserRoleAssignment  # Avoid circular import
        return self.prefetch_related(
            Prefetch(
                'user_roles',
                queryset=UserRoleAssignment.objects.select_related('role')
            )
        )
    
    def active_users(self):
        """Return only active users"""
        return self.filter(is_active=True)
    
    def by_role(self, role_name: str):
        """
        Filter users by role.
        
        Args:
            role_name: Role name from UserRole enum
            
        Returns:
            Queryset of users with specified role
        """
        return self.filter(user_roles__role__name=role_name)
    
    def instructors(self):
        """Get all users with instructor role"""
        return self.by_role(UserRole.INSTRUCTOR.value)
    
    def admins(self):
        """Get all users with admin role"""
        return self.by_role(UserRole.ADMIN.value)


class UserManager(BaseUserManager):
    """
    Custom manager for User model with optimized queries.
    Provides methods for efficient user creation and retrieval.
    """
    
    def get_queryset(self):
        """Return custom queryset"""
        return UserQuerySet(self.model, using=self._db)
    
    def create_user(
        self,
        supabase_id: str,
        email: str,
        display_name: Optional[str] = None
    ) -> 'User':
        """
        Create a regular user synced from Supabase.
        
        Args:
            supabase_id: Unique ID from Supabase Auth
            email: User's email address
            display_name: Display name (defaults to email prefix)
            
        Returns:
            User instance
            
        Raises:
            ValueError: If email is not provided
        """
        if not email:
            raise ValueError('Users must have an email address')
        
        user = self.model(
            supabase_id=supabase_id,
            email=self.normalize_email(email),
            display_name=display_name or email.split('@')[0]
        )
        user.save(using=self._db)
        
        # Assign default student role
        from users.services.role_service import RoleService
        RoleService.assign_role(user, UserRole.STUDENT.value)
        
        return user
    
    def get_by_supabase_id(self, supabase_id: str) -> Optional['User']:
        """
        Get user by Supabase ID with profile prefetched.
        
        Args:
            supabase_id: Supabase Auth user ID
            
        Returns:
            User instance or None if not found
        """
        try:
            return self.select_related('profile').get(supabase_id=supabase_id)
        except User.DoesNotExist:
            return None
    
    # Delegate queryset methods to UserQuerySet
    def with_roles(self):
        """Prefetch user roles for efficient queries"""
        return self.get_queryset().with_roles()
    
    def active_users(self):
        """Return only active users"""
        return self.get_queryset().active_users()
    
    def by_role(self, role_name: str):
        """Filter users by role"""
        return self.get_queryset().by_role(role_name)
    
    def instructors(self):
        """Get all users with instructor role"""
        return self.get_queryset().instructors()
    
    def admins(self):
        """Get all users with admin role"""
        return self.get_queryset().admins()


class User(UUIDModel, AbstractBaseUser, SoftDeleteModel):
    """
    User model synced with Supabase Auth.
    Extends AbstractBaseUser for Django compatibility while using Supabase for authentication.
    """
    supabase_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text='Supabase Auth user ID - synced from JWT token'
    )
    email = models.EmailField(unique=True, db_index=True)
    display_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True, db_index=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['display_name']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['supabase_id']),
            models.Index(fields=['email']),
            models.Index(fields=['is_active', '-created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.display_name} ({self.email})"
    
    @property
    def is_staff(self) -> bool:
        """Required for Django admin - admins can access admin panel"""
        return self.has_role(UserRole.ADMIN.value)
    
    @property
    def is_superuser(self) -> bool:
        """Required for Django admin - admins have all permissions"""
        return self.has_role(UserRole.ADMIN.value)
    
    def has_role(self, role_name: str) -> bool:
        """
        Check if user has a specific role.
        
        Args:
            role_name: Role name from UserRole enum
            
        Returns:
            True if user has the role, False otherwise
        """
        return self.user_roles.filter(role__name=role_name).exists()
    
    def has_any_role(self, role_names: List[str]) -> bool:
        """
        Check if user has any of the specified roles.
        
        Args:
            role_names: List of role names from UserRole enum
            
        Returns:
            True if user has at least one role, False otherwise
        """
        return self.user_roles.filter(role__name__in=role_names).exists()
    
    def get_roles(self) -> List[str]:
        """
        Get list of user's role names.
        
        Returns:
            List of role name strings
        """
        return list(self.user_roles.values_list('role__name', flat=True))
    
    def has_perm(self, perm, obj=None) -> bool:
        """Required for Django admin - admins have all permissions"""
        return self.is_staff
    
    def has_module_perms(self, app_label) -> bool:
        """Required for Django admin - admins can access all modules"""
        return self.is_staff


class Role(models.Model):
    """
    Role model for RBAC.
    Uses centralized UserRole enum for role names - Single Source of Truth.
    """
    name = models.CharField(
        max_length=20,
        choices=UserRole.choices(),
        unique=True,
        db_index=True
    )
    description = models.TextField(blank=True)
    permissions = models.JSONField(
        default=dict,
        blank=True,
        help_text='JSON object defining fine-grained role permissions'
    )
    
    class Meta:
        db_table = 'roles'
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'
    
    def __str__(self) -> str:
        return self.get_name_display()
    
    @classmethod
    def get_or_create_default_roles(cls):
        """
        Create default roles if they don't exist using centralized configuration.
        Idempotent - safe to call multiple times.
        Uses core.constants.DEFAULT_ROLES_CONFIG as single source of truth.
        """
        from core.constants import get_all_roles_config
        
        roles_config = get_all_roles_config()
        
        for role_name, config in roles_config.items():
            cls.objects.get_or_create(
                name=config['name'],
                defaults={
                    'description': config['description'],
                    'permissions': config['permissions']
                }
            )


class UserRoleAssignment(TimestampedModel):
    """
    Many-to-many relationship between User and Role.
    Tracks who assigned the role and when for audit purposes.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_roles'
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='role_users'
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_roles'
    )
    
    class Meta:
        db_table = 'user_roles'
        verbose_name = 'User Role Assignment'
        verbose_name_plural = 'User Role Assignments'
        unique_together = ['user', 'role']
        indexes = [
            models.Index(fields=['user', 'role']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user.display_name} - {self.role.get_name_display()}"


class UserProfile(models.Model):
    """
    Extended user profile information.
    Separated from User model following Single Responsibility Principle.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='profile'
    )
    bio = models.TextField(blank=True, max_length=500)
    avatar_url = models.URLField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    github_username = models.CharField(max_length=100, blank=True)
    linkedin_url = models.URLField(blank=True)
    
    # Denormalized statistics for performance
    total_bookmarks = models.PositiveIntegerField(default=0)
    total_contributions = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    total_answers = models.PositiveIntegerField(default=0)
    reputation_score = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self) -> str:
        return f"Profile of {self.user.display_name}"

