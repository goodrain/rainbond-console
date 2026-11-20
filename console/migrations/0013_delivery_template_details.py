from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("console", "0012_delivery_template_metadata")]
    operations = [
        migrations.AddField(model_name="deliverytemplate", name="details", field=models.TextField(blank=True, default="")),
    ]
