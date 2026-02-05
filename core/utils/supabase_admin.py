"""
Supabase Admin SDK Integration
Provides admin-level operations for user management (password reset, email updates, etc.)
"""
import os
from typing import Optional, Dict, Any
from django.conf import settings
from supabase import create_client, Client
import requests


class SupabaseAdminClient:
    """
    Wrapper for Supabase Admin API operations.
    Uses service role key for admin-level operations.
    """
    
    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.service_key = getattr(settings, 'SUPABASE_SERVICE_KEY', None)
        
        if not self.url or not self.service_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set for admin operations"
            )
        
        # Create admin client with service role key
        self.client = create_client(self.url, self.service_key)
        self.auth_api_url = f"{self.url}/auth/v1/admin"
    
    def _make_admin_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated admin API request to Supabase.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: Request payload (optional)
            
        Returns:
            API response as dictionary
        """
        url = f"{self.auth_api_url}/{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.service_key}',
            'apikey': self.service_key,
            'Content-Type': 'application/json'
        }
        
        response = requests.request(
            method=method,
            url=url,
            json=data,
            headers=headers
        )
        
        response.raise_for_status()
        return response.json() if response.content else {}
    
    def reset_user_password(
        self,
        user_id: str,
        new_password: str
    ) -> Dict[str, Any]:
        """
        Reset a user's password (admin operation).
        
        Args:
            user_id: Supabase user ID
            new_password: New password to set
            
        Returns:
            User data from Supabase
        """
        return self._make_admin_request(
            method='PUT',
            endpoint=f'users/{user_id}',
            data={'password': new_password}
        )
    
    def update_user_email(
        self,
        user_id: str,
        new_email: str,
        email_confirm: bool = True
    ) -> Dict[str, Any]:
        """
        Update a user's email address (admin operation).
        
        Args:
            user_id: Supabase user ID
            new_email: New email address
            email_confirm: Whether email is already confirmed (default True for admin updates)
            
        Returns:
            Updated user data from Supabase
        """
        return self._make_admin_request(
            method='PUT',
            endpoint=f'users/{user_id}',
            data={
                'email': new_email,
                'email_confirm': email_confirm
            }
        )
    
    def send_password_reset_email(
        self,
        email: str,
        redirect_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send password reset email to user.
        
        Args:
            email: User's email address
            redirect_to: URL to redirect to after reset (optional)
            
        Returns:
            Response from Supabase
        """
        options = {}
        if redirect_to:
            options['redirect_to'] = redirect_to
        
        # Use client auth method for password reset
        result = self.client.auth.reset_password_email(email, options)
        return {'success': True, 'message': 'Password reset email sent'}
    
    def send_email_verification(
        self,
        user_id: str,
        redirect_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send email verification link to user.
        
        Args:
            user_id: Supabase user ID
            redirect_to: URL to redirect to after verification (optional)
            
        Returns:
            Response from Supabase
        """
        # Get user email first
        user_data = self._make_admin_request(
            method='GET',
            endpoint=f'users/{user_id}'
        )
        
        email = user_data.get('email')
        if not email:
            raise ValueError("User email not found")
        
        # Mark email as unconfirmed to trigger verification
        return self._make_admin_request(
            method='PUT',
            endpoint=f'users/{user_id}',
            data={'email_confirm': False}
        )
    
    def get_user_by_id(self, user_id: str) -> Dict[str, Any]:
        """
        Get user details from Supabase by ID.
        
        Args:
            user_id: Supabase user ID
            
        Returns:
            User data from Supabase
        """
        return self._make_admin_request(
            method='GET',
            endpoint=f'users/{user_id}'
        )
    
    def delete_user(self, user_id: str) -> Dict[str, Any]:
        """
        Permanently delete user from Supabase Auth.
        
        Args:
            user_id: Supabase user ID
            
        Returns:
            Deletion confirmation
        """
        return self._make_admin_request(
            method='DELETE',
            endpoint=f'users/{user_id}'
        )
    
    def list_users(
        self,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        """
        List all users in Supabase Auth.
        
        Args:
            page: Page number (1-indexed)
            per_page: Users per page
            
        Returns:
            Paginated user list
        """
        return self._make_admin_request(
            method='GET',
            endpoint=f'users?page={page}&per_page={per_page}'
        )
    
    def create_user(
        self,
        email: str,
        password: str,
        email_confirm: bool = False,
        user_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new user in Supabase Auth (admin operation).
        
        Args:
            email: User email
            password: User password
            email_confirm: Whether email is pre-confirmed
            user_metadata: Additional user metadata
            
        Returns:
            Created user data
        """
        data = {
            'email': email,
            'password': password,
            'email_confirm': email_confirm
        }
        
        if user_metadata:
            data['user_metadata'] = user_metadata
        
        return self._make_admin_request(
            method='POST',
            endpoint='users',
            data=data
        )
    
    def ban_user(self, user_id: str, duration: Optional[str] = None) -> Dict[str, Any]:
        """
        Ban a user from authentication.
        
        Args:
            user_id: Supabase user ID
            duration: Ban duration (e.g., '24h', 'none' for permanent)
            
        Returns:
            Updated user data
        """
        data = {'ban_duration': duration or 'none'}
        return self._make_admin_request(
            method='PUT',
            endpoint=f'users/{user_id}',
            data=data
        )
    
    def unban_user(self, user_id: str) -> Dict[str, Any]:
        """
        Unban a user.
        
        Args:
            user_id: Supabase user ID
            
        Returns:
            Updated user data
        """
        return self._make_admin_request(
            method='PUT',
            endpoint=f'users/{user_id}',
            data={'ban_duration': '0s'}
        )


# Singleton instance
_admin_client: Optional[SupabaseAdminClient] = None


def get_supabase_admin_client() -> SupabaseAdminClient:
    """
    Get or create Supabase admin client instance (singleton pattern).
    
    Returns:
        Configured SupabaseAdminClient instance
    """
    global _admin_client
    
    if _admin_client is None:
        _admin_client = SupabaseAdminClient()
    
    return _admin_client


def reset_supabase_admin_client():
    """Reset the admin client (useful for testing)"""
    global _admin_client
    _admin_client = None
