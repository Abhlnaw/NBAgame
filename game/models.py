from django.db import models

# Create your models here.

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    abbreviation = models.CharField(max_length=3, unique=True)

    def __str__(self):
        return self.name

class Player(models.Model):
    player_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    teams = models.ManyToManyField(Team, related_name='players')
    position = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return self.name

class PlayerSeasonStats(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='stats')
    season = models.IntegerField()
    points = models.FloatField()
    rebounds = models.FloatField()
    assists = models.FloatField()
    vorp = models.FloatField() # Value Over Replacement Player

    class Meta:
        unique_together = ('player', 'season')

    def __str__(self):
        return f"{self.player.name} - {self.season}"
