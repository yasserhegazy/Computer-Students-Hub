from django.db import models
from django.db.models import QuerySet
from core.models import UUIDModel, TimestampedModel
from core.constants import LevelCode, SemesterCode
from typing import Optional


class LevelQuerySet(QuerySet):
    """Custom QuerySet for Level model"""
    
    def active(self):
        """Get only active levels"""
        return self.filter(is_active=True)
    
    def ordered(self):
        """Get levels ordered by order field"""
        return self.order_by('order')


class LevelManager(models.Manager):
    """Custom manager for Level model"""
    
    def get_queryset(self):
        """Return custom queryset"""
        return LevelQuerySet(self.model, using=self._db)
    
    def active(self):
        """Get active levels ordered"""
        return self.get_queryset().active().ordered()
    
    def get_by_code(self, code: str) -> Optional['Level']:
        """
        Get level by code.
        
        Args:
            code: Level code (L1, L2, etc.)
            
        Returns:
            Level instance or None
        """
        try:
            return self.get(code=code)
        except Level.DoesNotExist:
            return None


class Level(UUIDModel, TimestampedModel):
    """
    Academic level (year) model.
    Represents academic levels like Level 1, Level 2, etc.
    """
    code = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        help_text="Unique level code (e.g., L1, L2, L3, L4)"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'Level 1', 'Level 2')"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the level"
    )
    order = models.PositiveIntegerField(
        unique=True,
        help_text="Display order (1, 2, 3, 4)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this level is currently active"
    )
    
    objects = LevelManager()
    
    class Meta:
        ordering = ['order']
        verbose_name = 'Level'
        verbose_name_plural = 'Levels'
        db_table = 'academics_level'
    
    def __str__(self) -> str:
        return f"{self.name} ({self.code})"
    
    @classmethod
    def get_or_create_defaults(cls):
        """
        Create default levels from centralized configuration.
        Idempotent - safe to call multiple times.
        """
        from core.constants import get_all_levels_config
        
        levels_config = get_all_levels_config()
        
        for code, config in levels_config.items():
            cls.objects.get_or_create(
                code=config['code'],
                defaults={
                    'name': config['name'],
                    'description': config['description'],
                    'order': config['order'],
                    'is_active': config['is_active'],
                }
            )


class SemesterQuerySet(QuerySet):
    """Custom QuerySet for Semester model"""
    
    def active(self):
        """Get only active semesters"""
        return self.filter(is_active=True)
    
    def ordered(self):
        """Get semesters ordered by order field"""
        return self.order_by('order')


class SemesterManager(models.Manager):
    """Custom manager for Semester model"""
    
    def get_queryset(self):
        """Return custom queryset"""
        return SemesterQuerySet(self.model, using=self._db)
    
    def active(self):
        """Get active semesters ordered"""
        return self.get_queryset().active().ordered()
    
    def get_by_code(self, code: str) -> Optional['Semester']:
        """
        Get semester by code.
        
        Args:
            code: Semester code (FALL, SPRING, SUMMER)
            
        Returns:
            Semester instance or None
        """
        try:
            return self.get(code=code)
        except Semester.DoesNotExist:
            return None


class Semester(UUIDModel, TimestampedModel):
    """
    Academic semester model.
    Represents semester periods like Fall, Spring, Summer.
    """
    code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Unique semester code (e.g., FALL, SPRING, SUMMER)"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'Fall Semester', 'Spring Semester')"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the semester"
    )
    order = models.PositiveIntegerField(
        unique=True,
        help_text="Display order within academic year"
    )
    duration_weeks = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Typical duration in weeks"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this semester is currently active"
    )
    
    objects = SemesterManager()
    
    class Meta:
        ordering = ['order']
        verbose_name = 'Semester'
        verbose_name_plural = 'Semesters'
        db_table = 'academics_semester'
    
    def __str__(self) -> str:
        return f"{self.name} ({self.code})"
    
    @classmethod
    def get_or_create_defaults(cls):
        """
        Create default semesters from centralized configuration.
        Idempotent - safe to call multiple times.
        """
        from core.constants import get_all_semesters_config
        
        semesters_config = get_all_semesters_config()
        
        for code, config in semesters_config.items():
            cls.objects.get_or_create(
                code=config['code'],
                defaults={
                    'name': config['name'],
                    'description': config['description'],
                    'order': config['order'],
                    'duration_weeks': config['duration_weeks'],
                    'is_active': config['is_active'],
                }
            )
