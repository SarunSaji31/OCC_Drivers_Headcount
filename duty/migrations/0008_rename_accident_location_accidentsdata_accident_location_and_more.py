# Generated by Django 5.0.7 on 2024-10-06 15:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('duty', '0007_accidentsdata_accident_location_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='accidentsdata',
            old_name='Accident_location',
            new_name='accident_location',
        ),
        migrations.RenameField(
            model_name='breakdowndata',
            old_name='Breakdown_location',
            new_name='breakdown_location',
        ),
        migrations.AlterField(
            model_name='accidentsdata',
            name='replacement_bus',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='accidentsdata',
            name='replacement_driver',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='breakdowndata',
            name='replacement_bus',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='breakdowndata',
            name='replacement_driver',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='breakdowndata',
            name='staff_count',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='delaydata',
            name='remarks',
            field=models.TextField(blank=True, null=True),
        ),
    ]
