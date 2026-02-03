from django.utils.functional import SimpleLazyObject
from django.conf import settings
from rest_framework import exceptions
import jwt
from typing import Optional
from users.models import User
from users.services.user_service import UserService
from core.utils.supabase_client import get_supabase_client


class SupabaseAuthenticationMiddleware:
    """
    Middleware to authenticate requests using Supabase JWT tokens.
    Validates tokens and creates/updates local user records.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Lazy evaluation - only authenticate when request.user is accessed
        request.user = SimpleLazyObject(lambda: self._get_user(request))
        response = self.get_response(request)
        return response
    
    def _get_user(self, request) -> Optional[User]:
        """
        Extract and validate Supabase JWT token.
        
        Args:
            request: Django request object
            
        Returns:
            User instance or None if not authenticated
        """
        token = self._extract_token(request)
        
        if not token:
            return None
        
        try:
            payload = self._decode_token(token)
            user = self._get_or_create_user(payload)
            return user
        except exceptions.AuthenticationFailed:
            # Token is invalid or expired
            return None
    
    def _extract_token(self, request) -> Optional[str]:
        """
        Extract Bearer token from Authorization header.
        
        Args:
            request: Django request object
            
        Returns:
            JWT token string or None
        """
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return None
        
        return auth_header.split(' ')[1]
    
    def _decode_token(self, token: str) -> dict:
        """
        Decode and validate JWT token using Supabase client.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded payload dictionary
            
        Raises:
            AuthenticationFailed: If token is invalid or expired
        """
        try:
            # Decode JWT with Supabase JWT secret
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=['HS256'],
                audience='authenticated'
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError as e:
            raise exceptions.AuthenticationFailed(f'Invalid token: {str(e)}')
    
    def _get_or_create_user(self, payload: dict) -> User:
        """
        Get or create local user from Supabase JWT payload.
        
        Args:
            payload: Decoded JWT payload
            
        Returns:
            User instance
            
        Raises:
            AuthenticationFailed: If payload is invalid
        """
        supabase_id = payload.get('sub')
        email = payload.get('email')
        user_metadata = payload.get('user_metadata', {})
        
        if not supabase_id or not email:
            raise exceptions.AuthenticationFailed('Invalid token payload')
        
        # Use UserService to handle user creation/sync
        user = UserService.sync_from_supabase(
            supabase_id=supabase_id,
            email=email,
            display_name=user_metadata.get('display_name'),
            avatar_url=user_metadata.get('avatar_url'),
            user_metadata=user_metadata
        )
        
        # Update last login
        from django.utils import timezone
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        return user
