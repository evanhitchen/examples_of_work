# Generated by Django 3.1.7 on 2021-03-09 07:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0005_auto_20210304_1624'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='defect',
            name='photo',
        ),
        migrations.AddField(
            model_name='imagefile',
            name='defect',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.defect'),
        ),
    ]
