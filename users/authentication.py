"""
DRF Authentication class that uses the user set by SupabaseAuthenticationMiddleware.
"""
from rest_framework import authentication
from django.contrib.auth.models import AnonymousUser


class SupabaseJWTAuthentication(authentication.BaseAuthentication):
    """
    DRF authentication class that retrieves user from Django request.
    The user is already authenticated by SupabaseAuthenticationMiddleware.
    """
    
    def authenticate(self, request):
        """
        Returns the user that was set by SupabaseAuthenticationMiddleware.
        
        Returns:
            tuple: (user, None) if authenticated, None if not
        """
        # Get the user from the underlying Django request
        # DRF wraps HttpRequest, so request._request is the Django request
        django_request = request._request
        user = getattr(django_request, 'user', None)
        
        # If no user or AnonymousUser, return None (not authenticated)
        if user is None or isinstance(user, AnonymousUser) or not user.is_authenticated:
            return None
        
        # Return authenticated user
        # DRF expects (user, auth) tuple where auth can be None for token-based auth
        return (user, None)
