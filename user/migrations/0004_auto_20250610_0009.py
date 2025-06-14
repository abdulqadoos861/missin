# Generated by Django 5.0.6 on 2025-06-10 07:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0003_missingperson_found_date_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='missingperson',
            name='additional_photos',
        ),
        migrations.AddField(
            model_name='missingperson',
            name='additional_photo_1',
            field=models.ImageField(blank=True, null=True, upload_to='missing_persons/additional/'),
        ),
        migrations.AddField(
            model_name='missingperson',
            name='additional_photo_2',
            field=models.ImageField(blank=True, null=True, upload_to='missing_persons/additional/'),
        ),
        migrations.AddField(
            model_name='missingperson',
            name='additional_photo_3',
            field=models.ImageField(blank=True, null=True, upload_to='missing_persons/additional/'),
        ),
    ]
