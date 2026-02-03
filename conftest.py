"""
Pytest configuration and fixtures for the entire project.
Provides shared test fixtures and database setup.
"""
import pytest
from typing import Callable
from rest_framework.test import APIClient
from users.models import User
from users.services.role_service import RoleService
from core.constants import UserRole


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Initialize database with default roles"""
    with django_db_blocker.unblock():
        RoleService.initialize_default_roles()


@pytest.fixture
def api_client() -> APIClient:
    """Return DRF API client"""
    return APIClient()


@pytest.fixture
def create_user(db) -> Callable:
    """
    Factory fixture for creating users.
    Returns a function that creates users with specified parameters.
    """
    def _create_user(
        email: str = "test@example.com",
        display_name: str = "Test User",
        supabase_id: str = None,
        **kwargs
    ) -> User:
        if not supabase_id:
            import uuid
            supabase_id = str(uuid.uuid4())
        
        return User.objects.create_user(
            supabase_id=supabase_id,
            email=email,
            display_name=display_name,
            **kwargs
        )
    
    return _create_user


@pytest.fixture
def guest_user(create_user) -> User:
    """Create a guest user"""
    user = create_user(
        email="guest@example.com",
        display_name="Guest User"
    )
    # Guest role is not assigned by default, user only has Student role
    return user


@pytest.fixture
def student_user(create_user) -> User:
    """Create a student user (default role)"""
    return create_user(
        email="student@example.com",
        display_name="Student User"
    )


@pytest.fixture
def instructor_user(create_user) -> User:
    """Create an instructor user"""
    user = create_user(
        email="instructor@example.com",
        display_name="Instructor User"
    )
    RoleService.assign_role(user, UserRole.INSTRUCTOR.value)
    return user


@pytest.fixture
def admin_user(create_user) -> User:
    """Create an admin user"""
    user = create_user(
        email="admin@example.com",
        display_name="Admin User"
    )
    RoleService.assign_role(user, UserRole.ADMIN.value)
    return user


@pytest.fixture
def authenticated_client(api_client: APIClient) -> Callable:
    """
    Factory fixture for authenticated API clients.
    Returns a function that creates authenticated clients for given users.
    """
    def _authenticated_client(user: User) -> APIClient:
        """Authenticate API client as the given user"""
        client = APIClient()
        client.force_authenticate(user=user)
        return client
    
    return _authenticated_client


@pytest.fixture
def student_client(authenticated_client, student_user) -> APIClient:
    """Authenticated client for student user"""
    return authenticated_client(student_user)


@pytest.fixture
def instructor_client(authenticated_client, instructor_user) -> APIClient:
    """Authenticated client for instructor user"""
    return authenticated_client(instructor_user)


@pytest.fixture
def admin_client(authenticated_client, admin_user) -> APIClient:
    """Authenticated client for admin user"""
    return authenticated_client(admin_user)
