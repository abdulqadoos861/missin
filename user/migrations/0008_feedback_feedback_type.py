# Generated by Django 5.2.1 on 2025-07-07 15:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0007_feedback'),
    ]

    operations = [
        migrations.AddField(
            model_name='feedback',
            name='feedback_type',
            field=models.CharField(blank=True, help_text='Type of feedback', max_length=50),
        ),
    ]
