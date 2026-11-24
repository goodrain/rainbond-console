"""Template identity, long release notes and creation independent of artifact sync."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("console", "0011_independent_delivery_templates")]
    operations = [
        migrations.AddField(model_name="deliverytemplate",
                            name="logo",
                            field=models.CharField(max_length=2048, blank=True, default="")),
        migrations.AddField(model_name="deliverytemplate", name="description", field=models.TextField(blank=True, default="")),
        migrations.AlterField(model_name="deliverytemplateversion", name="description", field=models.TextField(blank=True)),
        migrations.AlterField(model_name="deliverytemplateversion",
                              name="sync_id",
                              field=models.UUIDField(unique=True, null=True)),
        migrations.AddField(model_name="deliverytemplateversion",
                            name="creation_key",
                            field=models.CharField(max_length=128, unique=True, null=True)),
        migrations.AlterField(model_name="rainbondcenterappversion",
                              name="app_version_info",
                              field=models.TextField(help_text="版本信息")),
    ]
