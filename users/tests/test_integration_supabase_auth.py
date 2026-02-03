import pytest
from users.models import User, UserProfile, Role, UserRoleAssignment
from users.services.user_service import UserService
from users.services.role_service import RoleService
from core.constants import UserRole


@pytest.mark.django_db
class TestSupabaseUserCreationFlow:
    """Integration test for complete user creation flow."""
    
    @pytest.fixture(autouse=True)
    def setup_roles(self):
        """Ensure default roles exist before each test"""
        RoleService.initialize_default_roles()
    
    def test_create_student_user_complete_flow(self):
        """
        Test complete flow of creating a student user.
        
        Verifies:
        - User record created
        - UserProfile created
        - Student role assigned
        - All relationships established
        """
        # ARRANGE
        supabase_id = "550e8400-e29b-41d4-a716-446655440000"
        email = "john.doe@example.com"
        display_name = "John Doe"
        avatar_url = "https://avatars.supabase.io/avatar.jpg"
        
        assert User.objects.count() == 0
        
        # ACT
        user = UserService.sync_from_supabase(
            supabase_id=supabase_id,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url
        )
        
        # ASSERT - User Record
        assert User.objects.count() == 1
        assert user.supabase_id == supabase_id
        assert user.email == email
        assert user.display_name == display_name
        assert user.is_active is True
        
        # ASSERT - UserProfile
        assert UserProfile.objects.count() == 1
        profile = UserProfile.objects.get(user=user)
        assert profile.avatar_url == avatar_url
        
        # ASSERT - Student Role
        assert UserRoleAssignment.objects.count() == 1
        role_assignment = UserRoleAssignment.objects.get(user=user)
        assert role_assignment.role.name == UserRole.STUDENT.value
        assert role_assignment.assigned_by is None
        
        # ASSERT - Queryable
        students = User.objects.by_role(UserRole.STUDENT.value)
        assert students.count() == 1
        assert students.first() == user
        
        print("\n" + "="*60)
        print("SUCCESS: Student User Creation Test")
        print("="*60)
        print(f"User: {user.email}")
        print(f"Profile: Created")
        print(f"Role: {role_assignment.role.name}")
        print("="*60)
    
    def test_idempotent_sync_existing_user(self):
        """Test that syncing an existing user doesn't create duplicates."""
        supabase_id = "550e8400-e29b-41d4-a716-446655440000"
        email = "jane.doe@example.com"
        
        # First sync
        user1 = UserService.sync_from_supabase(
            supabase_id=supabase_id,
            email=email,
            display_name="Jane Doe"
        )
        
        # Second sync
        user2 = UserService.sync_from_supabase(
            supabase_id=supabase_id,
            email=email,
            display_name="Jane Smith"
        )
        
        # Verify no duplicates
        assert User.objects.count() == 1
        assert UserProfile.objects.count() == 1
        assert UserRoleAssignment.objects.count() == 1
        assert user1.id == user2.id
        
        user2.refresh_from_db()
        assert user2.display_name == "Jane Smith"
    
    def test_multiple_users_creation(self):
        """Test creating multiple users in sequence."""
        users_data = [
            ("user1-uuid", "user1@example.com", "User One"),
            ("user2-uuid", "user2@example.com", "User Two"),
            ("user3-uuid", "user3@example.com", "User Three"),
        ]
        
        for supabase_id, email, display_name in users_data:
            UserService.sync_from_supabase(
                supabase_id=supabase_id,
                email=email,
                display_name=display_name
            )
        
        assert User.objects.count() == 3
        assert UserProfile.objects.count() == 3
        assert UserRoleAssignment.objects.count() == 3
        
        students = User.objects.by_role(UserRole.STUDENT.value)
        assert students.count() == 3
