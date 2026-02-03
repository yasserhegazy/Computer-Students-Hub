# URL routing for users app. RESTful API endpoints using DRF routers.
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from users.views import UserViewSet, RoleViewSet, sync_user

app_name = 'users'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'roles', RoleViewSet, basename='role')

urlpatterns = [
    path('', include(router.urls)),
    
    # Authentication endpoints
    path('auth/sync/', sync_user, name='sync-user'),
]
