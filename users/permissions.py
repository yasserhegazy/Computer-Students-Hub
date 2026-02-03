from rest_framework import permissions
from core.constants import UserRole
from typing import Any


class IsAuthenticatedUser(permissions.BasePermission):
    """
    Base permission requiring valid authentication.
    Replaces DRF's IsAuthenticated to work with Supabase middleware.
    """
    message = 'Authentication credentials were not provided or are invalid.'
    
    def has_permission(self, request, view) -> bool:
        """Check if user is authenticated"""
        return request.user and request.user.is_authenticated


class IsStudent(permissions.BasePermission):
    """
    Permission requiring Student role or higher.
    Admins and Instructors also have student-level access.
    """
    message = 'You must be a registered student to perform this action.'
    
    def has_permission(self, request, view) -> bool:
        """Check if user has Student role or higher"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.has_any_role([
            UserRole.STUDENT.value,
            UserRole.INSTRUCTOR.value,
            UserRole.ADMIN.value
        ])


class IsInstructor(permissions.BasePermission):
    """
    Permission requiring Instructor or Admin role.
    Used for content creation and management.
    """
    message = 'You must be an instructor or admin to perform this action.'
    
    def has_permission(self, request, view) -> bool:
        """Check if user has Instructor or Admin role"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.has_any_role([
            UserRole.INSTRUCTOR.value,
            UserRole.ADMIN.value
        ])


class IsAdmin(permissions.BasePermission):
    """
    Permission requiring Admin role.
    Used for administrative actions and content approval.
    """
    message = 'You must be an admin to perform this action.'
    
    def has_permission(self, request, view) -> bool:
        """Check if user has Admin role"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.has_role(UserRole.ADMIN.value)


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission allowing owners to modify their own objects, or admins to modify any.
    Implements object-level permission checking.
    """
    message = 'You can only modify your own content, or you must be an admin.'
    
    def has_permission(self, request, view) -> bool:
        """Allow authenticated users to attempt the action"""
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj) -> bool:
        """Check if user owns the object or is an admin"""
        # Admins can do anything
        if request.user.has_role(UserRole.ADMIN.value):
            return True
        
        # Check ownership - object must have a user/author/created_by field
        owner_field_names = ['user', 'author', 'created_by', 'owner']
        
        for field_name in owner_field_names:
            if hasattr(obj, field_name):
                owner = getattr(obj, field_name)
                return owner == request.user
        
        # If no owner field found, deny access
        return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission allowing owners to modify, but anyone to view.
    Read-only access for non-owners.
    """
    
    def has_permission(self, request, view) -> bool:
        """Allow read operations for anyone, write for authenticated"""
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj) -> bool:
        """Allow read to anyone, write only to owner"""
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Check ownership
        owner_field_names = ['user', 'author', 'created_by', 'owner']
        
        for field_name in owner_field_names:
            if hasattr(obj, field_name):
                owner = getattr(obj, field_name)
                return owner == request.user
        
        return False


class CanManageContent(permissions.BasePermission):
    """
    Composite permission for content creation and management.
    Instructors can create drafts, Admins can publish.
    """
    message = 'You must be an instructor or admin to manage content.'
    
    def has_permission(self, request, view) -> bool:
        """Check if user can manage content"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow GET/HEAD/OPTIONS for anyone
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # POST/PUT/PATCH/DELETE require Instructor or Admin
        return request.user.has_any_role([
            UserRole.INSTRUCTOR.value,
            UserRole.ADMIN.value
        ])
    
    def has_object_permission(self, request, view, obj) -> bool:
        """Check object-level permissions"""
        # Read access for all
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Admins can modify anything
        if request.user.has_role(UserRole.ADMIN.value):
            return True
        
        # Instructors can only modify their own content
        if request.user.has_role(UserRole.INSTRUCTOR.value):
            owner_field_names = ['user', 'author', 'created_by', 'owner']
            for field_name in owner_field_names:
                if hasattr(obj, field_name):
                    owner = getattr(obj, field_name)
                    return owner == request.user
        
        return False


class CanModerateQnA(permissions.BasePermission):
    """
    Permission for Q&A moderation.
    Admins and Instructors can moderate.
    """
    message = 'You must be an instructor or admin to moderate Q&A.'
    
    def has_permission(self, request, view) -> bool:
        """Check if user can moderate Q&A"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.has_any_role([
            UserRole.INSTRUCTOR.value,
            UserRole.ADMIN.value
        ])


class ReadOnly(permissions.BasePermission):
    """
    Permission allowing only read operations.
    Useful for public endpoints.
    """
    
    def has_permission(self, request, view) -> bool:
        """Allow only safe methods"""
        return request.method in permissions.SAFE_METHODS
