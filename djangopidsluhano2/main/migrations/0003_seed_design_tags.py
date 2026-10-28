from django.db import migrations


DESIGN_TAGS = [
    ('оголошення', '#ff4d2e'),
    ('кохання', '#e8457c'),
    ('вчителі', '#2f8f5b'),
    ('їдальня', '#e08a00'),
    ('загублене', '#3a6fe0'),
    ('подяка', '#8a4fd8'),
    ('події', '#0e9aa7'),
    ('олімпіади', '#5c6bc0'),
    ('питання', '#6b7f99'),
    ('смішне', '#d1a000'),
]


def create_design_tags(apps, schema_editor):
    Tag = apps.get_model('main', 'Tag')
    for name, color in DESIGN_TAGS:
        Tag.objects.get_or_create(name=name, defaults={'color': color})


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_profile_role_post_is_moderation'),
    ]

    operations = [
        migrations.RunPython(create_design_tags, migrations.RunPython.noop),
    ]
