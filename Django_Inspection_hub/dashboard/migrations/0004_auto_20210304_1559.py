# Generated by Django 3.1.7 on 2021-03-04 15:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0003_imagefile'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='imagefile',
            name='activated',
        ),
        migrations.AddField(
            model_name='defect',
            name='photo',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.imagefile'),
        ),
    ]