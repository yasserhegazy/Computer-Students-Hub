import pytest
from rest_framework import status
from django.urls import reverse
from users.models import User
from users.tests.factories import UserFactory
from core.constants import UserRole


@pytest.mark.django_db
class TestUserViewSet:
    """Test UserViewSet endpoints"""
    
    def test_list_users_as_admin(self, admin_client, student_user, instructor_user):
        """Test that admins can list users"""
        url = reverse('users:user-list')
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2
    
    def test_list_users_as_student_denied(self, student_client):
        """Test that students cannot list users"""
        url = reverse('users:user-list')
        response = student_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_retrieve_user(self, api_client, student_user):
        """Test retrieving a single user (public)"""
        url = reverse('users:user-detail', kwargs={'pk': student_user.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == student_user.email
        assert response.data['display_name'] == student_user.display_name
    
    def test_me_endpoint_authenticated(self, student_client, student_user):
        """Test /me endpoint for authenticated user"""
        url = reverse('users:user-me')
        response = student_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == student_user.email
    
    def test_me_endpoint_unauthenticated(self, api_client):
        """Test /me endpoint returns 401 for unauthenticated"""
        url = reverse('users:user-me')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_update_profile(self, student_client):
        """Test updating user profile"""
        url = reverse('users:user-update-profile')
        data = {
            'bio': 'Updated bio',
            'location': 'New York',
            'website': 'https://example.com'
        }
        response = student_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['bio'] == 'Updated bio'
        assert response.data['location'] == 'New York'
    
    def test_update_profile_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot update profile"""
        url = reverse('users:user-update-profile')
        data = {'bio': 'Test'}
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_assign_role_as_admin(self, admin_client, student_user):
        """Test assigning role as admin"""
        url = reverse('users:user-assign-role', kwargs={'pk': student_user.id})
        data = {'role_name': UserRole.INSTRUCTOR.value}
        response = admin_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'assigned' in response.data['detail'].lower()
        
        student_user.refresh_from_db()
        assert student_user.has_role(UserRole.INSTRUCTOR.value)
    
    def test_assign_role_as_student_denied(self, student_client, instructor_user):
        """Test that students cannot assign roles"""
        url = reverse('users:user-assign-role', kwargs={'pk': instructor_user.id})
        data = {'role_name': UserRole.ADMIN.value}
        response = student_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_assign_invalid_role(self, admin_client, student_user):
        """Test assigning invalid role returns error"""
        url = reverse('users:user-assign-role', kwargs={'pk': student_user.id})
        data = {'role_name': 'invalid_role'}
        response = admin_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_revoke_role_as_admin(self, admin_client, instructor_user):
        """Test revoking role as admin"""
        url = reverse('users:user-revoke-role', kwargs={'pk': instructor_user.id})
        data = {'role_name': UserRole.INSTRUCTOR.value}
        response = admin_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'revoked' in response.data['detail'].lower()
        
        instructor_user.refresh_from_db()
        assert not instructor_user.has_role(UserRole.INSTRUCTOR.value)
    
    def test_revoke_role_not_assigned(self, admin_client, student_user):
        """Test revoking role that user doesn't have"""
        url = reverse('users:user-revoke-role', kwargs={'pk': student_user.id})
        data = {'role_name': UserRole.ADMIN.value}
        response = admin_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_deactivate_user_as_admin(self, admin_client, student_user):
        """Test deactivating user as admin"""
        url = reverse('users:user-deactivate', kwargs={'pk': student_user.id})
        response = admin_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        
        student_user.refresh_from_db()
        assert student_user.is_active is False
    
    def test_deactivate_self_fails(self, admin_client, admin_user):
        """Test that users cannot deactivate themselves"""
        url = reverse('users:user-deactivate', kwargs={'pk': admin_user.id})
        response = admin_client.post(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_activate_user_as_admin(self, admin_client):
        """Test activating user as admin"""
        inactive_user = UserFactory(is_active=False)
        url = reverse('users:user-activate', kwargs={'pk': inactive_user.id})
        response = admin_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        
        inactive_user.refresh_from_db()
        assert inactive_user.is_active is True


@pytest.mark.django_db
class TestRoleViewSet:
    """Test RoleViewSet endpoints"""
    
    def test_list_roles(self, api_client):
        """Test listing roles (public endpoint)"""
        url = reverse('users:role-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
    
    def test_retrieve_role(self, api_client):
        """Test retrieving a single role"""
        from users.models import Role
        role = Role.objects.first()
        
        url = reverse('users:role-detail', kwargs={'pk': role.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == role.name
    
    def test_initialize_roles_as_admin(self, admin_client):
        """Test initializing default roles as admin"""
        url = reverse('users:role-initialize')
        response = admin_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['roles']) == len(UserRole)
    
    def test_initialize_roles_as_student_denied(self, student_client):
        """Test that students cannot initialize roles"""
        url = reverse('users:role-initialize')
        response = student_client.post(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAuthentication:
    """Test authentication middleware behavior"""
    
    def test_unauthenticated_request(self, api_client):
        """Test that requests without token have no user"""
        url = reverse('users:user-me')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_authenticated_request(self, student_client, student_user):
        """Test that authenticated requests have user"""
        url = reverse('users:user-me')
        response = student_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(student_user.id)


@pytest.mark.django_db
class TestPagination:
    """Test API pagination"""
    
    def test_users_list_pagination(self, admin_client):
        """Test that user list is paginated"""
        # Create 25 users to exceed default page size
        for i in range(25):
            UserFactory(email=f"user{i}@example.com")
        
        url = reverse('users:user-list')
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert 'count' in response.data
        assert 'next' in response.data
        assert 'previous' in response.data


@pytest.mark.django_db
class TestFiltering:
    """Test API filtering"""
    
    def test_filter_by_active_status(self, admin_client):
        """Test filtering users by is_active"""
        UserFactory(is_active=True, email="active@example.com")
        UserFactory(is_active=False, email="inactive@example.com")
        
        url = reverse('users:user-list')
        response = admin_client.get(url, {'is_active': 'true'})
        
        assert response.status_code == status.HTTP_200_OK
        # All returned users should be active
        for user in response.data['results']:
            user_obj = User.objects.get(id=user['id'])
            assert user_obj.is_active is True
    
    def test_search_users(self, admin_client):
        """Test searching users by email/display_name"""
        UserFactory(email="john@example.com", display_name="John Doe")
        UserFactory(email="jane@example.com", display_name="Jane Smith")
        
        url = reverse('users:user-list')
        response = admin_client.get(url, {'search': 'john'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
