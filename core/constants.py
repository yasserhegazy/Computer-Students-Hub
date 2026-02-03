# Centralized constants and enums for the entire application.
from enum import Enum
from typing import List, Tuple


class BaseEnum(Enum):
    """Base enum with helper methods for Django integration"""
    
    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        """Return Django-compatible choices tuple"""
        return [(item.value, item.name.replace('_', ' ').title()) for item in cls]
    
    @classmethod
    def values(cls) -> List[str]:
        """Return list of all enum values"""
        return [item.value for item in cls]
    
    @classmethod
    def has_value(cls, value: str) -> bool:
        """Check if value exists in enum"""
        return value in cls.values()
    
    @classmethod
    def get_display(cls, value: str) -> str:
        """Get display name for a value"""
        for item in cls:
            if item.value == value:
                return item.name.replace('_', ' ').title()
        return value


class UserRole(BaseEnum):
    """User role types - Single source of truth for RBAC"""
    GUEST = 'guest'
    STUDENT = 'student'
    INSTRUCTOR = 'instructor'
    ADMIN = 'admin'


class ResourceType(BaseEnum):
    """Resource content types"""
    LINK = 'link'
    FILE = 'file'
    VIDEO = 'video'
    ASSIGNMENT = 'assignment'


class DifficultyLevel(BaseEnum):
    """Difficulty levels for resources and content"""
    BEGINNER = 'beginner'
    INTERMEDIATE = 'intermediate'
    ADVANCED = 'advanced'


class ContentStatus(BaseEnum):
    """Content approval and publication status"""
    DRAFT = 'draft'
    PENDING = 'pending'
    PUBLISHED = 'published'
    REJECTED = 'rejected'
    ARCHIVED = 'archived'


class QuestionStatus(BaseEnum):
    """Q&A question status"""
    OPEN = 'open'
    CLOSED = 'closed'
    ARCHIVED = 'archived'


class SubmissionStatus(BaseEnum):
    """Content submission approval status"""
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'


class NotificationType(BaseEnum):
    """Notification event types"""
    SUBMISSION_STATUS = 'submission_status'
    QNA_REPLY = 'qna_reply'
    COMMENT_REPLY = 'comment_reply'
    ADMIN_ALERT = 'admin_alert'
    RESOURCE_APPROVED = 'resource_approved'
    ASSIGNMENT_GRADED = 'assignment_graded'
    MENTION = 'mention'


class AuditAction(BaseEnum):
    """Audit log action types"""
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'
    PUBLISH = 'publish'
    APPROVE = 'approve'
    REJECT = 'reject'
    ARCHIVE = 'archive'
    RESTORE = 'restore'


class CourseStatus(BaseEnum):
    """Course publication status"""
    DRAFT = 'draft'
    PENDING_REVIEW = 'pending_review'
    PUBLISHED = 'published'
    ARCHIVED = 'archived'


class LevelCode(BaseEnum):
    """Standard academic level codes"""
    LEVEL_1 = 'L1'
    LEVEL_2 = 'L2'
    LEVEL_3 = 'L3'
    LEVEL_4 = 'L4'
    GENERAL = 'GEN'  # For general/non-curriculum courses


class SemesterCode(BaseEnum):
    """Standard semester codes"""
    FALL = 'FALL'
    SPRING = 'SPRING'
    SUMMER = 'SUMMER'
    GENERAL = 'GEN'  # For general/non-curriculum courses


# Pagination defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# File upload limits (in MB)
MAX_FILE_SIZE_MB = 50
MAX_VIDEO_SIZE_MB = 500
MAX_IMAGE_SIZE_MB = 10

# Allowed file extensions
ALLOWED_FILE_EXTENSIONS = ['.pdf', '.docx', '.pptx', '.zip', '.txt', '.md', '.xlsx']
ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.webm', '.mov', '.avi']
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']

# Rating constraints
MIN_RATING = 1
MAX_RATING = 5

# Vote values
VOTE_UP = 1
VOTE_DOWN = -1
VOTE_NEUTRAL = 0

# Comment nesting limit
MAX_COMMENT_DEPTH = 1  # Only one level of replies for simplicity

# Cache timeouts (seconds)
CACHE_TIMEOUT_SHORT = 300      # 5 minutes
CACHE_TIMEOUT_MEDIUM = 1800    # 30 minutes
CACHE_TIMEOUT_LONG = 3600      # 1 hour
CACHE_TIMEOUT_DAY = 86400      # 24 hours

# API rate limiting
RATE_LIMIT_ANONYMOUS = '100/hour'
RATE_LIMIT_AUTHENTICATED = '1000/hour'
RATE_LIMIT_STAFF = '5000/hour'

# Slug configuration
MAX_SLUG_LENGTH = 255
SLUG_SEPARATOR = '-'

# Search configuration
MIN_SEARCH_QUERY_LENGTH = 3
MAX_SEARCH_RESULTS = 50


# ==============================================================================
# DEFAULT ROLE CONFIGURATIONS - Single Source of Truth for RBAC
# ==============================================================================
# Define role metadata once, use everywhere (migrations, services, tests, docs)
# This follows DRY principle and makes role management centralized

DEFAULT_ROLES_CONFIG = {
    UserRole.GUEST.value: {
        'name': UserRole.GUEST.value,
        'description': 'Guest user with read-only access to public content',
        'permissions': {
            'can_view_public_content': True,
            'can_view_courses': True,
            'can_view_resources': False,
            'can_submit_questions': False,
            'can_comment': False,
            'can_bookmark': False,
            'can_rate': False,
            'can_submit_improvements': False,
        }
    },
    UserRole.STUDENT.value: {
        'name': UserRole.STUDENT.value,
        'description': 'Student user with access to courses, resources, and Q&A',
        'permissions': {
            'can_view_public_content': True,
            'can_view_courses': True,
            'can_view_resources': True,
            'can_submit_questions': True,
            'can_answer_questions': True,
            'can_comment': True,
            'can_bookmark': True,
            'can_rate': True,
            'can_submit_improvements': True,
            'can_vote': True,
        }
    },
    UserRole.INSTRUCTOR.value: {
        'name': UserRole.INSTRUCTOR.value,
        'description': 'Instructor user who can create and manage course content',
        'permissions': {
            'can_view_public_content': True,
            'can_view_courses': True,
            'can_view_resources': True,
            'can_create_courses': True,
            'can_create_resources': True,
            'can_edit_own_content': True,
            'can_publish_content': True,
            'can_submit_questions': True,
            'can_answer_questions': True,
            'can_moderate_qna': True,
            'can_comment': True,
            'can_bookmark': True,
            'can_rate': True,
            'can_review_submissions': True,
            'can_vote': True,
        }
    },
    UserRole.ADMIN.value: {
        'name': UserRole.ADMIN.value,
        'description': 'Administrator with full access to all platform features',
        'permissions': {
            'can_view_public_content': True,
            'can_view_courses': True,
            'can_view_resources': True,
            'can_create_courses': True,
            'can_create_resources': True,
            'can_edit_own_content': True,
            'can_edit_any_content': True,
            'can_delete_content': True,
            'can_publish_content': True,
            'can_unpublish_content': True,
            'can_submit_questions': True,
            'can_answer_questions': True,
            'can_moderate_qna': True,
            'can_delete_questions': True,
            'can_delete_answers': True,
            'can_comment': True,
            'can_delete_comments': True,
            'can_bookmark': True,
            'can_rate': True,
            'can_manage_users': True,
            'can_assign_roles': True,
            'can_review_submissions': True,
            'can_approve_submissions': True,
            'can_view_analytics': True,
            'can_manage_settings': True,
            'can_vote': True,
        }
    },
}


def get_role_config(role_name: str) -> dict:
    """
    Get role configuration by name.
    
    Args:
        role_name: Role name (guest, student, instructor, admin)
        
    Returns:
        Role configuration dictionary with name, description, permissions
        
    Raises:
        ValueError: If role_name is invalid
    """
    if role_name not in DEFAULT_ROLES_CONFIG:
        raise ValueError(f"Invalid role: {role_name}. Valid roles: {list(DEFAULT_ROLES_CONFIG.keys())}")
    return DEFAULT_ROLES_CONFIG[role_name]


def get_all_roles_config() -> dict:
    """
    Get all default role configurations.
    
    Returns:
        Dictionary mapping role names to their configurations
    """
    return DEFAULT_ROLES_CONFIG.copy()


# ==============================================================================
# DEFAULT ACADEMIC STRUCTURE CONFIGURATIONS
# ==============================================================================
# Define academic levels and semesters once, use everywhere

DEFAULT_LEVELS_CONFIG = {
    LevelCode.LEVEL_1.value: {
        'code': LevelCode.LEVEL_1.value,
        'name': 'Level 1',
        'description': 'First year undergraduate level',
        'order': 1,
        'is_active': True,
    },
    LevelCode.LEVEL_2.value: {
        'code': LevelCode.LEVEL_2.value,
        'name': 'Level 2',
        'description': 'Second year undergraduate level',
        'order': 2,
        'is_active': True,
    },
    LevelCode.LEVEL_3.value: {
        'code': LevelCode.LEVEL_3.value,
        'name': 'Level 3',
        'description': 'Third year undergraduate level',
        'order': 3,
        'is_active': True,
    },
    LevelCode.LEVEL_4.value: {
        'code': LevelCode.LEVEL_4.value,
        'name': 'Level 4',
        'description': 'Fourth year undergraduate level',
        'order': 4,
        'is_active': True,
    },
}

DEFAULT_SEMESTERS_CONFIG = {
    SemesterCode.FALL.value: {
        'code': SemesterCode.FALL.value,
        'name': 'Fall Semester',
        'description': 'Fall semester (September - December)',
        'order': 1,
        'duration_weeks': 16,
        'is_active': True,
    },
    SemesterCode.SPRING.value: {
        'code': SemesterCode.SPRING.value,
        'name': 'Spring Semester',
        'description': 'Spring semester (February - May)',
        'order': 2,
        'duration_weeks': 16,
        'is_active': True,
    },
    SemesterCode.SUMMER.value: {
        'code': SemesterCode.SUMMER.value,
        'name': 'Summer Semester',
        'description': 'Summer semester (June - August)',
        'order': 3,
        'duration_weeks': 8,
        'is_active': True,
    },
}


def get_level_config(code: str) -> dict:
    """
    Get level configuration by code.
    
    Args:
        code: Level code (L1, L2, L3, L4)
        
    Returns:
        Level configuration dictionary
        
    Raises:
        ValueError: If code is invalid
    """
    if code not in DEFAULT_LEVELS_CONFIG:
        raise ValueError(f"Invalid level code: {code}. Valid codes: {list(DEFAULT_LEVELS_CONFIG.keys())}")
    return DEFAULT_LEVELS_CONFIG[code]


def get_all_levels_config() -> dict:
    """Get all default level configurations"""
    return DEFAULT_LEVELS_CONFIG.copy()


def get_semester_config(code: str) -> dict:
    """
    Get semester configuration by code.
    
    Args:
        code: Semester code (FALL, SPRING, SUMMER)
        
    Returns:
        Semester configuration dictionary
        
    Raises:
        ValueError: If code is invalid
    """
    if code not in DEFAULT_SEMESTERS_CONFIG:
        raise ValueError(f"Invalid semester code: {code}. Valid codes: {list(DEFAULT_SEMESTERS_CONFIG.keys())}")
    return DEFAULT_SEMESTERS_CONFIG[code]


def get_all_semesters_config() -> dict:
    """Get all default semester configurations"""
    return DEFAULT_SEMESTERS_CONFIG.copy()
