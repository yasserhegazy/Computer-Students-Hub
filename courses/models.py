from django.db import models
from django.db.models import QuerySet, Q
from django.utils.text import slugify
from core.models import UUIDModel, TimestampedModel, SoftDeleteModel
from core.constants import CourseStatus
from typing import Optional


class CourseQuerySet(QuerySet):
    """Custom QuerySet for Course model"""
    
    def active(self):
        """Get only active courses (not soft-deleted)"""
        return self.filter(is_active=True, deleted_at__isnull=True)
    
    def published(self):
        """Get only published courses"""
        return self.active().filter(status=CourseStatus.PUBLISHED.value)
    
    def general_courses(self):
        """Get general courses (not tied to specific level/semester)"""
        return self.filter(level__isnull=True, semester__isnull=True)
    
    def by_level(self, level):
        """
        Get courses for a specific level.
        
        Args:
            level: Level instance or level code
        """
        from academics.models import Level
        
        if isinstance(level, str):
            level = Level.objects.get_by_code(level)
        
        return self.filter(level=level)
    
    def by_semester(self, semester):
        """
        Get courses for a specific semester.
        
        Args:
            semester: Semester instance or semester code
        """
        from academics.models import Semester
        
        if isinstance(semester, str):
            semester = Semester.objects.get_by_code(semester)
        
        return self.filter(semester=semester)
    
    def electives(self):
        """Get elective courses"""
        return self.filter(is_elective=True)
    
    def required(self):
        """Get required (non-elective) courses"""
        return self.filter(is_elective=False)


class CourseManager(models.Manager):
    """Custom manager for Course model"""
    
    def get_queryset(self):
        """Return custom queryset"""
        return CourseQuerySet(self.model, using=self._db)
    
    def active(self):
        """Get active courses"""
        return self.get_queryset().active()
    
    def published(self):
        """Get published courses"""
        return self.get_queryset().published()
    
    def general_courses(self):
        """Get general courses"""
        return self.get_queryset().general_courses()
    
    def by_level(self, level):
        """Get courses by level"""
        return self.get_queryset().by_level(level)
    
    def by_semester(self, semester):
        """Get courses by semester"""
        return self.get_queryset().by_semester(semester)
    
    def get_by_code(self, code: str) -> Optional['Course']:
        """
        Get course by code.
        
        Args:
            code: Course code (e.g., CS101, MATH201)
            
        Returns:
            Course instance or None
        """
        try:
            return self.get(code=code)
        except Course.DoesNotExist:
            return None


class Course(SoftDeleteModel):
    """
    Course model with soft delete support.
    Supports both general courses and level/semester-specific courses.
    """
    code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Unique course code (e.g., CS101, MATH201)"
    )
    name = models.CharField(
        max_length=200,
        help_text="Course name"
    )
    slug = models.SlugField(
        max_length=250,
        unique=True,
        blank=True,
        help_text="URL-friendly slug (auto-generated)"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed course description"
    )
    credits = models.PositiveIntegerField(
        default=3,
        help_text="Number of credit hours"
    )
    
    # Optional associations - NULL for general courses
    level = models.ForeignKey(
        'academics.Level',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='courses',
        help_text="Academic level (NULL for general courses)"
    )
    semester = models.ForeignKey(
        'academics.Semester',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='courses',
        help_text="Semester (NULL for general courses)"
    )
    
    # Course metadata
    difficulty = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
        ],
        default='beginner',
        help_text="Difficulty level"
    )
    is_elective = models.BooleanField(
        default=False,
        help_text="Whether this is an elective course"
    )
    
    # Status and activation
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this course is currently active"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            (CourseStatus.DRAFT.value, 'Draft'),
            (CourseStatus.PENDING_REVIEW.value, 'Pending Review'),
            (CourseStatus.PUBLISHED.value, 'Published'),
            (CourseStatus.ARCHIVED.value, 'Archived'),
        ],
        default=CourseStatus.DRAFT.value,
        db_index=True,
        help_text="Publication status"
    )
    
    objects = CourseManager()
    
    class Meta:
        ordering = ['code']
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'
        db_table = 'courses_course'
        indexes = [
            models.Index(fields=['level', 'semester']),
            models.Index(fields=['is_active', 'status']),
        ]
    
    def __str__(self) -> str:
        return f"{self.code} - {self.name}"
    
    def save(self, *args, **kwargs):
        """Auto-generate slug if not provided"""
        if not self.slug:
            self.slug = slugify(f"{self.code}-{self.name}")
        super().save(*args, **kwargs)
    
    @property
    def is_general(self) -> bool:
        """Check if this is a general course (not tied to level/semester)"""
        return self.level is None and self.semester is None
    
    def get_prerequisites(self):
        """Get all prerequisites for this course"""
        return CoursePrerequisite.objects.filter(course=self).select_related('prerequisite')
    
    def get_dependent_courses(self):
        """Get all courses that have this course as a prerequisite"""
        return CoursePrerequisite.objects.filter(prerequisite=self).select_related('course')


class CoursePrerequisite(UUIDModel, TimestampedModel):
    """
    Course prerequisite relationship.
    Defines prerequisites with optional minimum grade requirement.
    """
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='prerequisites',
        help_text="The course that has prerequisites"
    )
    prerequisite = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='dependent_courses',
        help_text="The required prerequisite course"
    )
    is_mandatory = models.BooleanField(
        default=True,
        help_text="Whether this prerequisite is mandatory"
    )
    minimum_grade = models.CharField(
        max_length=5,
        blank=True,
        help_text="Minimum required grade (e.g., C+, B)"
    )
    
    class Meta:
        verbose_name = 'Course Prerequisite'
        verbose_name_plural = 'Course Prerequisites'
        db_table = 'courses_prerequisite'
        unique_together = [['course', 'prerequisite']]
        indexes = [
            models.Index(fields=['course']),
            models.Index(fields=['prerequisite']),
        ]
    
    def __str__(self) -> str:
        mandatory = "Required" if self.is_mandatory else "Optional"
        grade_info = f" (Min: {self.minimum_grade})" if self.minimum_grade else ""
        return f"{self.course.code} requires {self.prerequisite.code} ({mandatory}){grade_info}"
