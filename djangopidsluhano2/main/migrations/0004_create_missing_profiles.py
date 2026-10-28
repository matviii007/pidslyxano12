from django.conf import settings
from django.db import migrations


def create_missing_profiles(apps, schema_editor):
    Profile = apps.get_model('main', 'Profile')
    app_label, model_name = settings.AUTH_USER_MODEL.split('.')
    User = apps.get_model(app_label, model_name)

    missing_profiles = [
        Profile(user_id=user_id, school_class='')
        for user_id in User.objects.exclude(
            pk__in=Profile.objects.values('user_id'),
        ).values_list('pk', flat=True)
    ]
    Profile.objects.bulk_create(missing_profiles, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_seed_design_tags'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(create_missing_profiles, migrations.RunPython.noop),
    ]
