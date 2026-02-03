# Generated migration for creating default roles
# Uses centralized role configuration from core.constants

from django.db import migrations


def create_default_roles(apps, schema_editor):
    """
    Create default roles using centralized configuration.
    Role definitions are imported from core.constants.DEFAULT_ROLES_CONFIG
    """
    Role = apps.get_model('users', 'Role')
    
    # Import role configurations from central source of truth
    from core.constants import get_all_roles_config
    
    roles_config = get_all_roles_config()
    
    for role_name, config in roles_config.items():
        Role.objects.get_or_create(
            name=config['name'],
            defaults={
                'description': config['description'],
                'permissions': config['permissions']
            }
        )


def remove_default_roles(apps, schema_editor):
    """Reverse migration - remove default roles"""
    Role = apps.get_model('users', 'Role')
    from core.constants import UserRole
    
    # Use enum values to ensure consistency
    role_names = [role.value for role in UserRole]
    Role.objects.filter(name__in=role_names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_roles, remove_default_roles),
    ]
