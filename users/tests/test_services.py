import pytest
from django.core.exceptions import PermissionDenied
from users.services.role_service import RoleService
from users.services.user_service import UserService
from users.models import User, Role, UserRoleAssignment, UserProfile
from users.tests.factories import UserFactory
from core.constants import UserRole
from core.exceptions import ValidationError, PermissionDeniedError


@pytest.mark.django_db
class TestRoleService:
    """Test RoleService"""
    
    def test_assign_role(self, student_user, admin_user):
        """Test assigning a role to a user"""
        assignment = RoleService.assign_role(
            user=student_user,
            role_name=UserRole.INSTRUCTOR.value,
            assigned_by=admin_user
        )
        
        assert assignment.user == student_user
        assert assignment.role.name == UserRole.INSTRUCTOR.value
        assert assignment.assigned_by == admin_user
        assert student_user.has_role(UserRole.INSTRUCTOR.value)
    
    def test_assign_role_invalid_name(self, student_user, admin_user):
        """Test assigning invalid role raises error"""
        with pytest.raises(ValidationError):
            RoleService.assign_role(
                user=student_user,
                role_name="invalid_role",
                assigned_by=admin_user
            )
    
    def test_assign_role_permission_denied(self, student_user, instructor_user):
        """Test that non-admins cannot assign roles"""
        with pytest.raises(PermissionDeniedError):
            RoleService.assign_role(
                user=student_user,
                role_name=UserRole.INSTRUCTOR.value,
                assigned_by=instructor_user
            )
    
    def test_assign_role_idempotent(self, student_user, admin_user):
        """Test that assigning same role twice doesn't duplicate"""
        RoleService.assign_role(
            user=student_user,
            role_name=UserRole.INSTRUCTOR.value,
            assigned_by=admin_user
        )
        
        RoleService.assign_role(
            user=student_user,
            role_name=UserRole.INSTRUCTOR.value,
            assigned_by=admin_user
        )
        
        # Should only have one instructor role assignment
        assert UserRoleAssignment.objects.filter(
            user=student_user,
            role__name=UserRole.INSTRUCTOR.value
        ).count() == 1
    
    def test_revoke_role(self, instructor_user, admin_user):
        """Test revoking a role from a user"""
        revoked = RoleService.revoke_role(
            user=instructor_user,
            role_name=UserRole.INSTRUCTOR.value,
            revoked_by=admin_user
        )
        
        assert revoked is True
        assert not instructor_user.has_role(UserRole.INSTRUCTOR.value)
    
    def test_revoke_role_not_assigned(self, student_user, admin_user):
        """Test revoking role that wasn't assigned returns False"""
        revoked = RoleService.revoke_role(
            user=student_user,
            role_name=UserRole.ADMIN.value,
            revoked_by=admin_user
        )
        
        assert revoked is False
    
    def test_revoke_role_permission_denied(self, instructor_user, student_user):
        """Test that non-admins cannot revoke roles"""
        with pytest.raises(PermissionDeniedError):
            RoleService.revoke_role(
                user=instructor_user,
                role_name=UserRole.INSTRUCTOR.value,
                revoked_by=student_user
            )
    
    def test_can_assign_role(self, admin_user, student_user):
        """Test can_assign_role permission check"""
        assert RoleService.can_assign_role(admin_user, UserRole.INSTRUCTOR.value)
        assert not RoleService.can_assign_role(student_user, UserRole.INSTRUCTOR.value)
    
    def test_can_revoke_role(self, admin_user, student_user):
        """Test can_revoke_role permission check"""
        assert RoleService.can_revoke_role(admin_user, UserRole.INSTRUCTOR.value)
        assert not RoleService.can_revoke_role(student_user, UserRole.INSTRUCTOR.value)
    
    def test_get_users_by_role(self, student_user, instructor_user):
        """Test getting users by role"""
        students = RoleService.get_users_by_role(UserRole.STUDENT.value)
        instructors = RoleService.get_users_by_role(UserRole.INSTRUCTOR.value)
        
        assert student_user in students
        assert instructor_user in instructors
    
    def test_promote_to_instructor(self, student_user, admin_user):
        """Test promote_to_instructor convenience method"""
        RoleService.promote_to_instructor(student_user, admin_user)
        
        assert student_user.has_role(UserRole.INSTRUCTOR.value)
    
    def test_promote_to_admin(self, student_user, admin_user):
        """Test promote_to_admin convenience method"""
        RoleService.promote_to_admin(student_user, admin_user)
        
        assert student_user.has_role(UserRole.ADMIN.value)
    
    def test_promote_to_admin_permission_denied(self, student_user, instructor_user):
        """Test that non-admins cannot promote to admin"""
        with pytest.raises(PermissionDeniedError):
            RoleService.promote_to_admin(student_user, instructor_user)
    
    def test_initialize_default_roles(self):
        """Test initialize_default_roles"""
        # Clear existing roles
        Role.objects.all().delete()
        
        RoleService.initialize_default_roles()
        
        assert Role.objects.count() == len(UserRole)
        assert Role.objects.filter(name=UserRole.STUDENT.value).exists()
        assert Role.objects.filter(name=UserRole.INSTRUCTOR.value).exists()
        assert Role.objects.filter(name=UserRole.ADMIN.value).exists()


@pytest.mark.django_db
class TestUserService:
    """Test UserService"""
    
    def test_sync_from_supabase_new_user(self):
        """Test syncing a new user from Supabase"""
        user = UserService.sync_from_supabase(
            supabase_id="new-supabase-id",
            email="newuser@example.com",
            display_name="New User"
        )
        
        assert user.supabase_id == "new-supabase-id"
        assert user.email == "newuser@example.com"
        assert user.display_name == "New User"
        assert user.has_role(UserRole.STUDENT.value)
        
        # Should create profile
        assert hasattr(user, 'profile')
    
    def test_sync_from_supabase_existing_user(self, student_user):
        """Test syncing an existing user updates email"""
        new_email = "updated@example.com"
        
        user = UserService.sync_from_supabase(
            supabase_id=student_user.supabase_id,
            email=new_email,
            display_name=student_user.display_name
        )
        
        assert user.id == student_user.id
        assert user.email == new_email
    
    def test_sync_from_supabase_with_avatar(self):
        """Test syncing user with avatar URL"""
        avatar_url = "https://example.com/avatar.jpg"
        
        user = UserService.sync_from_supabase(
            supabase_id="test-id",
            email="test@example.com",
            avatar_url=avatar_url
        )
        
        assert user.profile.avatar_url == avatar_url
    
    def test_update_profile(self, student_user):
        """Test updating user profile"""
        profile = UserService.update_profile(
            user=student_user,
            bio="Updated bio",
            location="New City",
            website="https://example.com"
        )
        
        assert profile.bio == "Updated bio"
        assert profile.location == "New City"
        assert profile.website == "https://example.com"
    
    def test_deactivate_user(self, student_user, admin_user):
        """Test deactivating a user"""
        UserService.deactivate_user(student_user, admin_user)
        
        student_user.refresh_from_db()
        assert student_user.is_active is False
    
    def test_deactivate_self_raises_error(self, student_user):
        """Test that users cannot deactivate themselves"""
        with pytest.raises(ValidationError):
            UserService.deactivate_user(student_user, student_user)
    
    def test_activate_user(self, admin_user):
        """Test activating a user"""
        inactive_user = UserFactory(is_active=False)
        
        UserService.activate_user(inactive_user, admin_user)
        
        inactive_user.refresh_from_db()
        assert inactive_user.is_active is True
    
    def test_get_user_statistics(self, student_user):
        """Test getting user statistics"""
        # Create profile with statistics
        profile = UserProfile.objects.create(
            user=student_user,
            total_bookmarks=5,
            total_questions=3,
            reputation_score=100
        )
        
        stats = UserService.get_user_statistics(student_user)
        
        assert stats['total_bookmarks'] == 5
        assert stats['total_questions'] == 3
        assert stats['reputation_score'] == 100
    
    def test_get_user_statistics_no_profile(self, student_user):
        """Test getting statistics for user without profile"""
        # Delete profile if it exists
        UserProfile.objects.filter(user=student_user).delete()
        
        stats = UserService.get_user_statistics(student_user)
        
        assert stats['total_bookmarks'] == 0
        assert stats['total_questions'] == 0
    
    def test_increment_statistic(self, student_user):
        """Test incrementing a user statistic"""
        UserService.increment_statistic(student_user, 'total_bookmarks', 1)
        
        student_user.profile.refresh_from_db()
        assert student_user.profile.total_bookmarks == 1
        
        UserService.increment_statistic(student_user, 'total_bookmarks', 3)
        
        student_user.profile.refresh_from_db()
        assert student_user.profile.total_bookmarks == 4
    
    def test_increment_statistic_creates_profile(self):
        """Test that incrementing creates profile if it doesn't exist"""
        user = UserFactory()
        UserProfile.objects.filter(user=user).delete()
        
        UserService.increment_statistic(user, 'total_questions', 1)
        
        assert hasattr(user, 'profile')
        assert user.profile.total_questions == 1
