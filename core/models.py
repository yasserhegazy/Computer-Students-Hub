from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from typing import Optional
import uuid


class TimestampedModel(models.Model):
    """
    Abstract base class with automatic timestamp tracking.
    Provides created_at and updated_at fields.
    """
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
        get_latest_by = 'created_at'


class SoftDeleteManager(models.Manager):
    """
    Manager that excludes soft-deleted objects by default.
    Follows Single Responsibility - handles query filtering for soft deletes.
    """
    
    def get_queryset(self):
        """Override to exclude soft-deleted objects"""
        return super().get_queryset().filter(is_deleted=False)
    
    def with_deleted(self):
        """Include soft-deleted objects in queryset"""
        return super().get_queryset()
    
    def deleted_only(self):
        """Return only soft-deleted objects"""
        return super().get_queryset().filter(is_deleted=True)


class SoftDeleteModel(TimestampedModel):
    """
    Abstract base class with soft delete functionality.
    Objects are marked as deleted instead of being removed from database.
    """
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_deleted_set'
    )
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()  # Access all objects including deleted
    
    class Meta:
        abstract = True
    
    def soft_delete(self, user: Optional['User'] = None) -> None:
        """
        Soft delete the object.
        
        Args:
            user: User performing the deletion (optional)
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'updated_at'])
    
    def restore(self) -> None:
        """Restore a soft-deleted object"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'updated_at'])


class StatusModel(models.Model):
    """
    Abstract base class for models with status field.
    Provides status tracking with automatic logging.
    """
    status = models.CharField(max_length=20, db_index=True)
    
    class Meta:
        abstract = True
    
    def change_status(
        self,
        new_status: str,
        user: Optional['User'] = None,
        reason: Optional[str] = None
    ) -> None:
        """
        Change status and optionally log the action.
        
        Args:
            new_status: New status value
            user: User performing the change (optional)
            reason: Reason for status change (optional)
        """
        old_status = self.status
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])
        
        # Log status change if audit service is available
        try:
            from core.services.audit_service import AuditService
            AuditService.log_status_change(
                entity=self,
                old_status=old_status,
                new_status=new_status,
                user=user,
                reason=reason
            )
        except ImportError:
            pass  # Audit service not yet implemented


class SlugModel(models.Model):
    """
    Abstract base class for models with slug field.
    Provides automatic slug generation from a source field.
    """
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    
    class Meta:
        abstract = True
    
    def generate_slug(self, source_text: str, max_length: int = 255) -> str:
        """
        Generate a unique slug from source text.
        
        Args:
            source_text: Text to generate slug from
            max_length: Maximum slug length
            
        Returns:
            Unique slug string
        """
        base_slug = slugify(source_text)[:max_length]
        slug = base_slug
        counter = 1
        
        # Ensure uniqueness
        while self.__class__.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            suffix = f'-{counter}'
            slug = f'{base_slug[:max_length - len(suffix)]}{suffix}'
            counter += 1
        
        return slug


class UUIDModel(models.Model):
    """Abstract base class with UUID primary key"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class Meta:
        abstract = True


class OrderedModel(models.Model):
    """
    Abstract base class for models with manual ordering.
    Useful for lists that need custom user-defined order.
    """
    order_number = models.PositiveIntegerField(default=0, db_index=True)
    
    class Meta:
        abstract = True
        ordering = ['order_number']
    
    def move_up(self) -> None:
        """Move this item up in the order (decrease order_number)"""
        if self.order_number > 0:
            self.order_number -= 1
            self.save(update_fields=['order_number'])
    
    def move_down(self) -> None:
        """Move this item down in the order (increase order_number)"""
        self.order_number += 1
        self.save(update_fields=['order_number'])


class PublishableModel(StatusModel):
    """
    Abstract base class for content that goes through approval workflow.
    Combines status tracking with publication timestamps.
    """
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    published_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_published_set'
    )
    
    class Meta:
        abstract = True
    
    def publish(self, user: Optional['User'] = None) -> None:
        """Publish this content"""
        from core.constants import ContentStatus
        
        self.status = ContentStatus.PUBLISHED.value
        self.published_at = timezone.now()
        self.published_by = user
        self.save(update_fields=['status', 'published_at', 'published_by', 'updated_at'])
    
    def unpublish(self, user: Optional['User'] = None) -> None:
        """Unpublish this content"""
        from core.constants import ContentStatus
        
        self.status = ContentStatus.DRAFT.value
        self.published_at = None
        self.published_by = None
        self.save(update_fields=['status', 'published_at', 'published_by', 'updated_at'])
    
    @property
    def is_published(self) -> bool:
        """Check if content is published"""
        from core.constants import ContentStatus
        return self.status == ContentStatus.PUBLISHED.value
