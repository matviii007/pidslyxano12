from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_create_missing_profiles'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='is_verified',
            field=models.BooleanField(default=False, verbose_name='Підтверджений акаунт'),
        ),
    ]
