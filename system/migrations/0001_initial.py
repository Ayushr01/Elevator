# Generated by Django 4.2.3 on 2023-07-09 09:09

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='System',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=60)),
                ('elevators_count', models.IntegerField()),
                ('max_floors', models.IntegerField()),
            ],
        ),
    ]
