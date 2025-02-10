# duty/migrations/0007_clean_delaydata.py
from django.db import migrations

def clean_delaydata(apps, schema_editor):
    DelayData = apps.get_model("duty", "DelayData")
    # Loop over all DelayData records
    for record in DelayData.objects.all():
        if record.delay:
            delay_str = str(record.delay)
            # If the delay string is longer than 8 characters, assume it's invalid.
            if len(delay_str) > 8:
                record.delay = None
                record.save()

class Migration(migrations.Migration):

    dependencies = [
        # Update this dependency to point to the actual last migration in your duty app.
        ('duty', '0006_alter_delaydata_delay'),
    ]

    operations = [
        migrations.RunPython(clean_delaydata),
    ]
