# Generated by Django 5.2.1 on 2025-05-25 11:51

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('officer', '0001_initial'),
        ('user', '0002_caseupdate'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='caseupdate',
            options={'ordering': ['-created_at']},
        ),
        migrations.RenameField(
            model_name='caseupdate',
            old_name='date',
            new_name='created_at',
        ),
        migrations.AlterField(
            model_name='caseupdate',
            name='case',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='officer_updates', to='user.missingperson'),
        ),
        migrations.AlterField(
            model_name='caseupdate',
            name='updated_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='officer_case_updates', to=settings.AUTH_USER_MODEL),
        ),
    ]
