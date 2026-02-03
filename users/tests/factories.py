import factory
from factory.django import DjangoModelFactory
from faker import Faker
from users.models import User, Role, UserRoleAssignment, UserProfile
from core.constants import UserRole
import uuid

fake = Faker()


class RoleFactory(DjangoModelFactory):
    """Factory for Role model"""
    
    class Meta:
        model = Role
        django_get_or_create = ('name',)
    
    name = UserRole.STUDENT.value
    description = factory.LazyAttribute(lambda obj: f'{obj.name.title()} role')
    permissions = factory.Dict({})


class UserFactory(DjangoModelFactory):
    """Factory for User model"""
    
    class Meta:
        model = User
    
    supabase_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    email = factory.LazyAttribute(lambda obj: fake.email())
    display_name = factory.LazyAttribute(lambda obj: fake.name())
    is_active = True
    
    @factory.post_generation
    def with_student_role(obj, create, extracted, **kwargs):
        """Automatically assign student role after user creation"""
        if not create:
            return
        
        student_role, _ = Role.objects.get_or_create(
            name=UserRole.STUDENT.value,
            defaults={'description': 'Student role'}
        )
        UserRoleAssignment.objects.get_or_create(
            user=obj,
            role=student_role
        )


class UserProfileFactory(DjangoModelFactory):
    """Factory for UserProfile model"""
    
    class Meta:
        model = UserProfile
    
    user = factory.SubFactory(UserFactory)
    bio = factory.LazyFunction(lambda: fake.text(max_nb_chars=200))
    location = factory.LazyFunction(lambda: fake.city())
    website = factory.LazyFunction(lambda: fake.url())
    github_username = factory.LazyFunction(lambda: fake.user_name())
    linkedin_url = factory.LazyFunction(lambda: fake.url())
    total_bookmarks = 0
    total_contributions = 0
    total_questions = 0
    total_answers = 0
    reputation_score = 0


class UserRoleAssignmentFactory(DjangoModelFactory):
    """Factory for UserRoleAssignment model"""
    
    class Meta:
        model = UserRoleAssignment
    
    user = factory.SubFactory(UserFactory)
    role = factory.SubFactory(RoleFactory)
    assigned_by = None


class InstructorUserFactory(UserFactory):
    """Factory for instructor users"""
    
    @factory.post_generation
    def with_instructor_role(obj, create, extracted, **kwargs):
        """Assign instructor role"""
        if not create:
            return
        
        instructor_role, _ = Role.objects.get_or_create(
            name=UserRole.INSTRUCTOR.value,
            defaults={'description': 'Instructor role'}
        )
        UserRoleAssignment.objects.get_or_create(
            user=obj,
            role=instructor_role
        )


class AdminUserFactory(UserFactory):
    """Factory for admin users"""
    
    @factory.post_generation
    def with_admin_role(obj, create, extracted, **kwargs):
        """Assign admin role"""
        if not create:
            return
        
        admin_role, _ = Role.objects.get_or_create(
            name=UserRole.ADMIN.value,
            defaults={'description': 'Admin role'}
        )
        UserRoleAssignment.objects.get_or_create(
            user=obj,
            role=admin_role
        )
