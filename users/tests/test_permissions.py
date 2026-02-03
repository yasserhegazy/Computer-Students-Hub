import pytest
from rest_framework.test import APIRequestFactory
from users.permissions import (
    IsAuthenticatedUser, IsStudent, IsInstructor, IsAdmin,
    IsOwnerOrAdmin, IsOwnerOrReadOnly, CanManageContent
)
from users.tests.factories import UserFactory
from core.constants import UserRole


class DummyView:
    """Dummy view for permission testing"""
    pass


class DummyObject:
    """Dummy object with user field for permission testing"""
    def __init__(self, user):
        self.user = user


@pytest.mark.django_db
class TestIsAuthenticatedUser:
    """Test IsAuthenticatedUser permission"""
    
    def test_authenticated_user_allowed(self, student_user):
        """Test that authenticated users pass"""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = student_user
        
        permission = IsAuthenticatedUser()
        assert permission.has_permission(request, DummyView())
    
    def test_anonymous_user_denied(self):
        """Test that anonymous users are denied"""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = None
        
        permission = IsAuthenticatedUser()
        assert not permission.has_permission(request, DummyView())


@pytest.mark.django_db
class TestIsStudent:
    """Test IsStudent permission"""
    
    def test_student_allowed(self, student_user):
        """Test that students pass"""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = student_user
        
        permission = IsStudent()
        assert permission.has_permission(request, DummyView())
    
    def test_instructor_allowed(self, instructor_user):
        """Test that instructors pass (they have student-level access)"""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = instructor_user
        
        permission = IsStudent()
        assert permission.has_permission(request, DummyView())
    
    def test_admin_allowed(self, admin_user):
        """Test that admins pass"""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = admin_user
        
        permission = IsStudent()
        assert permission.has_permission(request, DummyView())
    
    def test_guest_denied(self, guest_user):
        """Test that guests without student role are denied"""
        # Remove student role
        from users.models import UserRoleAssignment
        UserRoleAssignment.objects.filter(user=guest_user).delete()
        
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = guest_user
        
        permission = IsStudent()
        assert not permission.has_permission(request, DummyView())


@pytest.mark.django_db
class TestIsInstructor:
    """Test IsInstructor permission"""
    
    def test_instructor_allowed(self, instructor_user):
        """Test that instructors pass"""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = instructor_user
        
        permission = IsInstructor()
        assert permission.has_permission(request, DummyView())
    
    def test_admin_allowed(self, admin_user):
        """Test that admins pass"""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = admin_user
        
        permission = IsInstructor()
        assert permission.has_permission(request, DummyView())
    
    def test_student_denied(self, student_user):
        """Test that students are denied"""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = student_user
        
        permission = IsInstructor()
        assert not permission.has_permission(request, DummyView())


@pytest.mark.django_db
class TestIsAdmin:
    """Test IsAdmin permission"""
    
    def test_admin_allowed(self, admin_user):
        """Test that admins pass"""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = admin_user
        
        permission = IsAdmin()
        assert permission.has_permission(request, DummyView())
    
    def test_instructor_denied(self, instructor_user):
        """Test that instructors are denied"""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = instructor_user
        
        permission = IsAdmin()
        assert not permission.has_permission(request, DummyView())
    
    def test_student_denied(self, student_user):
        """Test that students are denied"""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = student_user
        
        permission = IsAdmin()
        assert not permission.has_permission(request, DummyView())


@pytest.mark.django_db
class TestIsOwnerOrAdmin:
    """Test IsOwnerOrAdmin permission"""
    
    def test_owner_allowed(self, student_user):
        """Test that owner can access their object"""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = student_user
        
        obj = DummyObject(user=student_user)
        
        permission = IsOwnerOrAdmin()
        assert permission.has_object_permission(request, DummyView(), obj)
    
    def test_non_owner_denied(self, student_user, instructor_user):
        """Test that non-owner cannot access object"""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = student_user
        
        obj = DummyObject(user=instructor_user)
        
        permission = IsOwnerOrAdmin()
        assert not permission.has_object_permission(request, DummyView(), obj)
    
    def test_admin_allowed(self, admin_user, student_user):
        """Test that admin can access any object"""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = admin_user
        
        obj = DummyObject(user=student_user)
        
        permission = IsOwnerOrAdmin()
        assert permission.has_object_permission(request, DummyView(), obj)


@pytest.mark.django_db
class TestIsOwnerOrReadOnly:
    """Test IsOwnerOrReadOnly permission"""
    
    def test_read_allowed_for_anyone(self, student_user):
        """Test that anyone can read"""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = None
        
        permission = IsOwnerOrReadOnly()
        assert permission.has_permission(request, DummyView())
    
    def test_write_requires_authentication(self):
        """Test that write requires authentication"""
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = None
        
        permission = IsOwnerOrReadOnly()
        assert not permission.has_permission(request, DummyView())
    
    def test_owner_can_write(self, student_user):
        """Test that owner can write to their object"""
        factory = APIRequestFactory()
        request = factory.put('/')
        request.user = student_user
        
        obj = DummyObject(user=student_user)
        
        permission = IsOwnerOrReadOnly()
        assert permission.has_object_permission(request, DummyView(), obj)
    
    def test_non_owner_cannot_write(self, student_user, instructor_user):
        """Test that non-owner cannot write to object"""
        factory = APIRequestFactory()
        request = factory.put('/')
        request.user = student_user
        
        obj = DummyObject(user=instructor_user)
        
        permission = IsOwnerOrReadOnly()
        assert not permission.has_object_permission(request, DummyView(), obj)


@pytest.mark.django_db
class TestCanManageContent:
    """Test CanManageContent permission"""
    
    def test_instructor_can_create(self, instructor_user):
        """Test that instructors can create content"""
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = instructor_user
        
        permission = CanManageContent()
        assert permission.has_permission(request, DummyView())
    
    def test_admin_can_create(self, admin_user):
        """Test that admins can create content"""
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = admin_user
        
        permission = CanManageContent()
        assert permission.has_permission(request, DummyView())
    
    def test_student_cannot_create(self, student_user):
        """Test that students cannot create content"""
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = student_user
        
        permission = CanManageContent()
        assert not permission.has_permission(request, DummyView())
    
    def test_admin_can_modify_any(self, admin_user, instructor_user):
        """Test that admins can modify any content"""
        factory = APIRequestFactory()
        request = factory.put('/')
        request.user = admin_user
        
        obj = DummyObject(user=instructor_user)
        
        permission = CanManageContent()
        assert permission.has_object_permission(request, DummyView(), obj)
    
    def test_instructor_can_modify_own(self, instructor_user):
        """Test that instructors can modify their own content"""
        factory = APIRequestFactory()
        request = factory.put('/')
        request.user = instructor_user
        
        obj = DummyObject(user=instructor_user)
        
        permission = CanManageContent()
        assert permission.has_object_permission(request, DummyView(), obj)
    
    def test_instructor_cannot_modify_others(self, instructor_user, admin_user):
        """Test that instructors cannot modify others' content"""
        factory = APIRequestFactory()
        request = factory.put('/')
        request.user = instructor_user
        
        obj = DummyObject(user=admin_user)
        
        permission = CanManageContent()
        assert not permission.has_object_permission(request, DummyView(), obj)
