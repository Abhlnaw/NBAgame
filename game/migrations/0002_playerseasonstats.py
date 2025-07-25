# Generated by Django 5.2.4 on 2025-07-14 09:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlayerSeasonStats',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('season', models.IntegerField()),
                ('points', models.FloatField()),
                ('rebounds', models.FloatField()),
                ('assists', models.FloatField()),
                ('vorp', models.FloatField()),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stats', to='game.player')),
            ],
            options={
                'unique_together': {('player', 'season')},
            },
        ),
    ]
