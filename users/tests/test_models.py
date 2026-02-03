import pytest
from django.db import IntegrityError
from users.models import User, Role, UserRoleAssignment, UserProfile
from users.tests.factories import UserFactory, RoleFactory, UserProfileFactory
from core.constants import UserRole


@pytest.mark.django_db
class TestUserModel:
    """Test User model"""
    
    def test_create_user(self):
        """Test basic user creation"""
        user = UserFactory()
        
        assert user.id is not None
        assert user.email is not None
        assert user.display_name is not None
        assert user.supabase_id is not None
        assert user.is_active is True
    
    def test_email_uniqueness(self):
        """Test that email must be unique"""
        email = "unique@example.com"
        UserFactory(email=email)
        
        with pytest.raises(IntegrityError):
            UserFactory(email=email)
    
    def test_supabase_id_uniqueness(self):
        """Test that supabase_id must be unique"""
        supabase_id = "test-supabase-id"
        UserFactory(supabase_id=supabase_id)
        
        with pytest.raises(IntegrityError):
            UserFactory(supabase_id=supabase_id)
    
    def test_user_str_representation(self):
        """Test __str__ method"""
        user = UserFactory(display_name="John Doe", email="john@example.com")
        assert str(user) == "John Doe (john@example.com)"
    
    def test_has_role(self, student_user):
        """Test has_role method"""
        assert student_user.has_role(UserRole.STUDENT.value)
        assert not student_user.has_role(UserRole.ADMIN.value)
    
    def test_has_any_role(self, student_user):
        """Test has_any_role method"""
        assert student_user.has_any_role([UserRole.STUDENT.value, UserRole.ADMIN.value])
        assert not student_user.has_any_role([UserRole.ADMIN.value, UserRole.INSTRUCTOR.value])
    
    def test_get_roles(self, student_user):
        """Test get_roles method"""
        roles = student_user.get_roles()
        assert UserRole.STUDENT.value in roles
        assert len(roles) >= 1
    
    def test_is_staff_for_admin(self, admin_user):
        """Test that admins are staff"""
        assert admin_user.is_staff is True
        assert admin_user.is_superuser is True
    
    def test_is_staff_for_student(self, student_user):
        """Test that students are not staff"""
        assert student_user.is_staff is False
        assert student_user.is_superuser is False
    
    def test_soft_delete(self, student_user, admin_user):
        """Test soft delete functionality"""
        student_user.soft_delete(user=admin_user)
        
        assert student_user.is_deleted is True
        assert student_user.deleted_at is not None
        assert student_user.deleted_by == admin_user
        
        # Should not appear in default queryset
        assert not User.objects.filter(id=student_user.id).exists()
        
        # Should appear in all_objects queryset
        assert User.all_objects.filter(id=student_user.id).exists()
    
    def test_restore_user(self, student_user, admin_user):
        """Test restoring soft-deleted user"""
        student_user.soft_delete(user=admin_user)
        student_user.restore()
        
        assert student_user.is_deleted is False
        assert student_user.deleted_at is None
        assert student_user.deleted_by is None
        
        # Should appear in default queryset again
        assert User.objects.filter(id=student_user.id).exists()


@pytest.mark.django_db
class TestRoleModel:
    """Test Role model"""
    
    def test_create_role(self):
        """Test role creation"""
        role = RoleFactory(name=UserRole.ADMIN.value)
        
        assert role.name == UserRole.ADMIN.value
        assert role.description is not None
    
    def test_role_str_representation(self):
        """Test __str__ method"""
        role = RoleFactory(name=UserRole.STUDENT.value)
        assert "Student" in str(role)
    
    def test_get_or_create_default_roles(self):
        """Test creating default roles"""
        Role.get_or_create_default_roles()
        
        # Should create all roles from enum
        assert Role.objects.count() == len(UserRole)
        assert Role.objects.filter(name=UserRole.STUDENT.value).exists()
        assert Role.objects.filter(name=UserRole.INSTRUCTOR.value).exists()
        assert Role.objects.filter(name=UserRole.ADMIN.value).exists()
        assert Role.objects.filter(name=UserRole.GUEST.value).exists()
    
    def test_role_uniqueness(self):
        """Test that role names must be unique"""
        RoleFactory(name=UserRole.ADMIN.value)
        
        with pytest.raises(IntegrityError):
            RoleFactory(name=UserRole.ADMIN.value)


@pytest.mark.django_db
class TestUserRoleAssignment:
    """Test UserRoleAssignment model"""
    
    def test_create_assignment(self, student_user, admin_user):
        """Test creating role assignment"""
        role = RoleFactory(name=UserRole.INSTRUCTOR.value)
        
        assignment = UserRoleAssignment.objects.create(
            user=student_user,
            role=role,
            assigned_by=admin_user
        )
        
        assert assignment.user == student_user
        assert assignment.role == role
        assert assignment.assigned_by == admin_user
        assert assignment.created_at is not None
    
    def test_unique_user_role_combination(self, student_user):
        """Test that user-role combination must be unique"""
        role = RoleFactory(name=UserRole.INSTRUCTOR.value)
        
        UserRoleAssignment.objects.create(user=student_user, role=role)
        
        with pytest.raises(IntegrityError):
            UserRoleAssignment.objects.create(user=student_user, role=role)
    
    def test_assignment_str_representation(self, student_user):
        """Test __str__ method"""
        role = RoleFactory(name=UserRole.ADMIN.value)
        assignment = UserRoleAssignment.objects.create(user=student_user, role=role)
        
        assert student_user.display_name in str(assignment)
        assert "Admin" in str(assignment)


@pytest.mark.django_db
class TestUserProfile:
    """Test UserProfile model"""
    
    def test_create_profile(self, student_user):
        """Test profile creation"""
        profile = UserProfile.objects.create(
            user=student_user,
            bio="Test bio",
            location="Test City"
        )
        
        assert profile.user == student_user
        assert profile.bio == "Test bio"
        assert profile.location == "Test City"
    
    def test_profile_defaults(self, student_user):
        """Test profile default values"""
        profile = UserProfile.objects.create(user=student_user)
        
        assert profile.total_bookmarks == 0
        assert profile.total_contributions == 0
        assert profile.total_questions == 0
        assert profile.total_answers == 0
        assert profile.reputation_score == 0
    
    def test_profile_str_representation(self, student_user):
        """Test __str__ method"""
        profile = UserProfile.objects.create(user=student_user)
        assert student_user.display_name in str(profile)
    
    def test_one_to_one_relationship(self, student_user):
        """Test that one user can only have one profile"""
        UserProfile.objects.create(user=student_user)
        
        with pytest.raises(IntegrityError):
            UserProfile.objects.create(user=student_user)


@pytest.mark.django_db
class TestUserManager:
    """Test UserManager custom methods"""
    
    def test_create_user(self):
        """Test create_user manager method"""
        user = User.objects.create_user(
            supabase_id="test-id",
            email="test@example.com",
            display_name="Test User"
        )
        
        assert user.email == "test@example.com"
        assert user.display_name == "Test User"
        assert user.supabase_id == "test-id"
        
        # Should have student role assigned
        assert user.has_role(UserRole.STUDENT.value)
    
    def test_create_user_without_display_name(self):
        """Test that display_name defaults to email prefix"""
        user = User.objects.create_user(
            supabase_id="test-id",
            email="john@example.com"
        )
        
        assert user.display_name == "john"
    
    def test_get_by_supabase_id(self, student_user):
        """Test get_by_supabase_id method"""
        found_user = User.objects.get_by_supabase_id(student_user.supabase_id)
        
        assert found_user == student_user
    
    def test_get_by_supabase_id_not_found(self):
        """Test get_by_supabase_id returns None for non-existent ID"""
        found_user = User.objects.get_by_supabase_id("non-existent-id")
        
        assert found_user is None
    
    def test_active_users(self, student_user):
        """Test active_users filter"""
        inactive_user = UserFactory(is_active=False)
        
        active = User.objects.active_users()
        
        assert student_user in active
        assert inactive_user not in active
    
    def test_by_role(self, student_user, instructor_user):
        """Test by_role filter"""
        students = User.objects.by_role(UserRole.STUDENT.value)
        instructors = User.objects.by_role(UserRole.INSTRUCTOR.value)
        
        assert student_user in students
        assert instructor_user in instructors
        assert instructor_user not in list(students)
    
    def test_instructors_method(self, instructor_user, student_user):
        """Test instructors convenience method"""
        instructors = User.objects.instructors()
        
        assert instructor_user in instructors
        assert student_user not in instructors
    
    def test_admins_method(self, admin_user, student_user):
        """Test admins convenience method"""
        admins = User.objects.admins()
        
        assert admin_user in admins
        assert student_user not in admins
