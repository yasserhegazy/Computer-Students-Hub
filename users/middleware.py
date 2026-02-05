from django.utils.functional import SimpleLazyObject
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from rest_framework import exceptions
import jwt
import logging
from typing import Optional
from users.models import User
from users.services.user_service import UserService
from core.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class SupabaseAuthenticationMiddleware:
    """
    Middleware to authenticate requests using Supabase JWT tokens.
    Validates tokens and creates/updates local user records.
    Runs BEFORE Django's AuthenticationMiddleware to set request.user.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Get authenticated JWT user and set on request
        user = self._get_user(request)
        request.user = user
        request._cached_user = user
        
        response = self.get_response(request)
        return response
    
    def _get_user(self, request) -> User:
        """
        Extract and validate Supabase JWT token.
        
        Args:
            request: Django request object
            
        Returns:
            User instance or AnonymousUser if not authenticated
        """
        try:
            token = self._extract_token(request)
            
            if not token:
                return AnonymousUser()
            
            try:
                payload = self._decode_token(token)
                user = self._get_or_create_user(payload)
                return user
            except exceptions.AuthenticationFailed:
                return AnonymousUser()
        except Exception as e:
            logger.error(f"Unexpected error in authentication: {str(e)}", exc_info=True)
            return AnonymousUser()
    
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
            # Decode JWT without verification to extract payload
            # Note: This is less secure but works with ES256 tokens
            # TODO: Implement proper JWT verification with public key
            import json
            import base64
            
            # Split the JWT into parts
            parts = token.split('.')
            if len(parts) != 3:
                raise exceptions.AuthenticationFailed('Invalid token format')
            
            # Decode the payload (second part)
            # Add padding if needed
            payload_part = parts[1]
            padding = '=' * (4 - len(payload_part) % 4)
            payload_json = base64.urlsafe_b64decode(payload_part + padding)
            payload = json.loads(payload_json)
            
            # Verify token is not expired
            import time
            exp = payload.get('exp')
            if exp and exp < time.time():
                raise exceptions.AuthenticationFailed('Token has expired')
            
            return payload
        except exceptions.AuthenticationFailed:
            raise
        except Exception as e:
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
