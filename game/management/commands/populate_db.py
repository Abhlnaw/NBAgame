import requests
from django.core.management.base import BaseCommand
from game.models import Team, Player, PlayerSeasonStats

class Command(BaseCommand):
    help = 'Populates the database with NBA teams and players from an API'

    def handle(self, *args, **options):
        self.stdout.write("Starting to populate the database...")
        
        teams = self.get_teams()
        self.save_teams(teams)
        
        self.get_and_save_players()
        self.get_and_save_player_stats()

        self.stdout.write(self.style.SUCCESS('Successfully populated the database with teams, players, and stats.'))

    def get_teams(self):
        teams = set()
        page = 1
        # Fetching a single recent season to get all team abbreviations
        url = f"https://api.server.nbaapi.com/api/playertotals?season=2024&page={page}&pageSize=500"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            for player_data in data.get('data', []):
                team_abbreviation = player_data.get('team')
                if team_abbreviation and len(team_abbreviation) == 3: # To filter out 2TM, 3TM etc.
                    teams.add(team_abbreviation)
        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f"Error fetching team data from API: {e}"))
        
        return teams

    def save_teams(self, teams):
        for team_abbr in teams:
            team, created = Team.objects.get_or_create(
                abbreviation=team_abbr,
                defaults={'name': team_abbr}
            )
            if created:
                self.stdout.write(f"Created team: {team.name}")

    def get_and_save_players(self):
        for season in range(2000, 2025):
            self.stdout.write(f"Fetching players for season: {season}")
            page = 1
            while True:
                url = f"https://api.server.nbaapi.com/api/playertotals?season={season}&page={page}&pageSize=100"
                try:
                    response = requests.get(url)
                    response.raise_for_status()
                    data = response.json()
                except requests.exceptions.RequestException as e:
                    self.stderr.write(self.style.ERROR(f"Error fetching player data for season {season}: {e}"))
                    break

                players_data = data.get('data')
                if not players_data:
                    break

                for player_data in players_data:
                    player_id = player_data.get('playerId')
                    player_name = player_data.get('playerName')
                    team_abbr = player_data.get('team')

                    if not all([player_id, player_name, team_abbr]):
                        continue

                    try:
                        team = Team.objects.get(abbreviation=team_abbr)
                        player, created = Player.objects.get_or_create(
                            player_id=player_id,
                            defaults={'name': player_name}
                        )
                        player.teams.add(team)
                        if created:
                            self.stdout.write(f"  - Created player: {player_name}")

                    except Team.DoesNotExist:
                        self.stderr.write(self.style.WARNING(f"  - Team with abbreviation {team_abbr} not found for player {player_name}"))

                if page >= data['pagination']['pages']:
                    break
                page += 1 

    def get_and_save_player_stats(self):
        self.stdout.write("Fetching and saving player stats...")
        for player in Player.objects.all():
            self.stdout.write(f"  Fetching stats for {player.name}...")
            # Fetch advanced stats to get VORP
            adv_url = f"https://api.server.nbaapi.com/api/playeradvancedstats?playerId={player.player_id}"
            try:
                adv_response = requests.get(adv_url)
                adv_response.raise_for_status()
                adv_data = adv_response.json().get('data', [])
            except requests.exceptions.RequestException as e:
                self.stderr.write(self.style.ERROR(f"    Could not fetch advanced stats for {player.name}: {e}"))
                adv_data = []

            # Fetch total stats for points, rebounds, assists
            totals_url = f"https://api.server.nbaapi.com/api/playertotals?playerId={player.player_id}"
            try:
                totals_response = requests.get(totals_url)
                totals_response.raise_for_status()
                totals_data = totals_response.json().get('data', [])
            except requests.exceptions.RequestException as e:
                self.stderr.write(self.style.ERROR(f"    Could not fetch total stats for {player.name}: {e}"))
                totals_data = []

            # Create a dictionary of stats by season
            stats_by_season = {}
            for stat_line in totals_data:
                season = stat_line.get('season')
                if season:
                    stats_by_season.setdefault(season, {}).update({
                        'points': stat_line.get('points', 0),
                        'rebounds': stat_line.get('totalRb', 0),
                        'assists': stat_line.get('assists', 0)
                    })
            
            for stat_line in adv_data:
                season = stat_line.get('season')
                if season:
                    stats_by_season.setdefault(season, {}).update({
                        'vorp': stat_line.get('vorp', 0)
                    })
            
            for season, stats in stats_by_season.items():
                PlayerSeasonStats.objects.update_or_create(
                    player=player,
                    season=season,
                    defaults={
                        'points': stats.get('points', 0),
                        'rebounds': stats.get('rebounds', 0),
                        'assists': stats.get('assists', 0),
                        'vorp': stats.get('vorp', 0)
                    }
                )
        self.stdout.write(self.style.SUCCESS("Finished populating player stats.")) 