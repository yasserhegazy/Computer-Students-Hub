from rest_framework import serializers
from users.models import User, Role, UserRoleAssignment, UserProfile
from typing import List


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role model"""
    display_name = serializers.CharField(source='get_name_display', read_only=True)
    
    class Meta:
        model = Role
        fields = ['name', 'display_name', 'description', 'permissions']
        read_only_fields = ['name']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model"""
    
    class Meta:
        model = UserProfile
        fields = [
            'bio', 'avatar_url', 'location', 'website',
            'github_username', 'linkedin_url',
            'total_bookmarks', 'total_contributions',
            'total_questions', 'total_answers', 'reputation_score'
        ]
        read_only_fields = [
            'total_bookmarks', 'total_contributions',
            'total_questions', 'total_answers', 'reputation_score'
        ]


class UserSerializer(serializers.ModelSerializer):
    """
    Basic user serializer for public user information.
    Used in lists and references.
    """
    roles = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'display_name',
            'created_at', 'roles'
        ]
        read_only_fields = ['id', 'email', 'created_at', 'roles']
    
    def get_roles(self, obj: User) -> List[str]:
        """Get list of role names"""
        return obj.get_roles()


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Detailed user serializer including profile and roles.
    Used for user detail view and current user endpoint.
    """
    roles = serializers.SerializerMethodField()
    profile = UserProfileSerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'display_name', 'supabase_id',
            'is_active', 'last_login', 'created_at', 'updated_at',
            'roles', 'profile'
        ]
        read_only_fields = [
            'id', 'email', 'supabase_id', 'is_active',
            'last_login', 'created_at', 'updated_at'
        ]
    
    def get_roles(self, obj: User) -> List[str]:
        """Get list of role names"""
        return obj.get_roles()


class UserRoleAssignmentSerializer(serializers.ModelSerializer):
    """
    Serializer for role assignments.
    Used by admins to manage user roles.
    """
    user = UserSerializer(read_only=True)
    role = RoleSerializer(read_only=True)
    assigned_by = UserSerializer(read_only=True)
    
    class Meta:
        model = UserRoleAssignment
        fields = ['user', 'role', 'assigned_by', 'created_at']
        read_only_fields = ['user', 'role', 'assigned_by', 'created_at']


class AssignRoleSerializer(serializers.Serializer):
    """
    Serializer for role assignment endpoint.
    Validates role name before assignment.
    """
    role_name = serializers.CharField(max_length=20)
    
    def validate_role_name(self, value: str) -> str:
        """Validate that role name is valid"""
        from core.constants import UserRole
        
        if not UserRole.has_value(value):
            raise serializers.ValidationError(
                f"Invalid role: {value}. Must be one of: {', '.join(UserRole.values())}"
            )
        return value


class UpdateProfileSerializer(serializers.Serializer):
    """
    Serializer for updating user profile.
    Validates profile data before update.
    """
    bio = serializers.CharField(max_length=500, required=False, allow_blank=True)
    location = serializers.CharField(max_length=100, required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)
    github_username = serializers.CharField(max_length=100, required=False, allow_blank=True)
    linkedin_url = serializers.URLField(required=False, allow_blank=True)
