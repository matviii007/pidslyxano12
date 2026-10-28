from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0010_alter_report_options_alter_report_author_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='report',
            options={'verbose_name': 'Report', 'verbose_name_plural': 'Reports'},
        ),
    ]
