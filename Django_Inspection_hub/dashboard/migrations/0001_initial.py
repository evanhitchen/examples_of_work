# Generated by Django 3.1.7 on 2021-03-04 13:27

import dashboard.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30)),
            ],
        ),
        migrations.CreateModel(
            name='Docxfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_name', models.FileField(upload_to='dashboard', validators=[dashboard.validators.docxvalidate_file_extension])),
                ('uploaded', models.DateTimeField(auto_now_add=True)),
                ('activated', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Site',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30)),
                ('location', models.CharField(max_length=100)),
                ('latitude', models.FloatField(blank=True, null=True)),
                ('longitude', models.FloatField(blank=True, null=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dashboard.client')),
            ],
        ),
        migrations.CreateModel(
            name='Structure',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('id_code', models.CharField(max_length=30)),
                ('name', models.CharField(max_length=30)),
                ('date_of_inspection', models.DateField(default=django.utils.timezone.now)),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dashboard.site')),
            ],
            options={
                'ordering': ['-date_of_inspection'],
            },
        ),
        migrations.CreateModel(
            name='Element',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('element', models.CharField(max_length=150)),
                ('element_description', models.CharField(max_length=500)),
                ('discipline', models.CharField(choices=[('CIVIL', 'Civil'), ('MECHANICAL', 'Mechanical'), ('ELECTRICAL', 'Electricity'), ('ACCESS', 'Access')], default='CIVIL', max_length=10)),
                ('structure', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dashboard.structure')),
            ],
        ),
        migrations.CreateModel(
            name='Defect',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('defect_description', models.CharField(max_length=500)),
                ('remedial', models.CharField(max_length=500)),
                ('safe', models.CharField(max_length=1)),
                ('element', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dashboard.element')),
            ],
        ),
    ]