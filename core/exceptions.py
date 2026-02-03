# Custom exception hierarchy for the application.
from rest_framework.exceptions import APIException
from rest_framework import status


class BaseAppException(APIException):
    """Base exception for all custom application exceptions"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'A business logic error occurred.'
    default_code = 'error'


class PermissionDeniedError(BaseAppException):
    """Raised when user lacks required permissions"""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'You do not have permission to perform this action.'
    default_code = 'permission_denied'


class ResourceNotFoundError(BaseAppException):
    """Raised when a requested resource doesn't exist"""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'The requested resource was not found.'
    default_code = 'not_found'


class ValidationError(BaseAppException):
    """Raised when input validation fails"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Validation error occurred.'
    default_code = 'validation_error'


class DuplicateResourceError(BaseAppException):
    """Raised when attempting to create a duplicate resource"""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'A resource with these attributes already exists.'
    default_code = 'duplicate_resource'


class InvalidStatusTransitionError(BaseAppException):
    """Raised when attempting an invalid status transition"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Invalid status transition.'
    default_code = 'invalid_status_transition'


class AuthenticationError(BaseAppException):
    """Raised when authentication fails"""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Authentication failed.'
    default_code = 'authentication_failed'


class TokenExpiredError(AuthenticationError):
    """Raised when JWT token has expired"""
    default_detail = 'Authentication token has expired.'
    default_code = 'token_expired'


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid"""
    default_detail = 'Authentication token is invalid.'
    default_code = 'invalid_token'


class FileUploadError(BaseAppException):
    """Raised when file upload fails"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'File upload failed.'
    default_code = 'file_upload_error'


class FileSizeExceededError(FileUploadError):
    """Raised when uploaded file exceeds size limit"""
    default_detail = 'File size exceeds the allowed limit.'
    default_code = 'file_size_exceeded'


class InvalidFileTypeError(FileUploadError):
    """Raised when uploaded file type is not allowed"""
    default_detail = 'File type is not allowed.'
    default_code = 'invalid_file_type'
