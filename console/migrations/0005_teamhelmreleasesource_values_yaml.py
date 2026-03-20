from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0004_teamhelmreleasesource'),
    ]

    operations = [
        migrations.AddField(
            model_name='teamhelmreleasesource',
            name='values_yaml',
            field=models.TextField(blank=True, default='', help_text='用户提交的 values.yaml', null=True),
        ),
    ]
