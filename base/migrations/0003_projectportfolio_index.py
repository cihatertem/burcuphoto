# Generated by Django 4.0.2 on 2022-03-06 18:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0002_project_meta_description_project_meta_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectportfolio',
            name='index',
            field=models.IntegerField(default=0),
        ),
    ]