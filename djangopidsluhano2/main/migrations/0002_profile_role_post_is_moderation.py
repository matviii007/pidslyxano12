from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='role',
            field=models.CharField(
                blank=True,
                choices=[
                    ('', 'Без ролі'),
                    ('moderator', 'Модератор'),
                    ('admin', 'Адміністратор'),
                ],
                default='',
                max_length=10,
                verbose_name='Роль',
            ),
        ),
        migrations.AddField(
            model_name='post',
            name='is_moderation',
            field=models.BooleanField(default=False, verbose_name='Від імені модерації'),
        ),
    ]
