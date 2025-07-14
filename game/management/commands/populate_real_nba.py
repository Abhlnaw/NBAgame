import requests
import time
from django.core.management.base import BaseCommand
from game.models import Team, Player, PlayerSeasonStats

class Command(BaseCommand):
    help = 'Populate the database with real NBA players and stats from NBA API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing teams and players before populating',
        )
        parser.add_argument(
            '--seasons',
            type=str,
            default='2024,2023,2022',
            help='Comma-separated seasons to fetch (default: 2024,2023,2022)',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            Team.objects.all().delete()
            Player.objects.all().delete()
            PlayerSeasonStats.objects.all().delete()

        # Current NBA teams
        current_nba_teams = [
            {'name': 'Atlanta Hawks', 'abbreviation': 'ATL'},
            {'name': 'Boston Celtics', 'abbreviation': 'BOS'},
            {'name': 'Brooklyn Nets', 'abbreviation': 'BRK'},
            {'name': 'Charlotte Hornets', 'abbreviation': 'CHO'},
            {'name': 'Chicago Bulls', 'abbreviation': 'CHI'},
            {'name': 'Cleveland Cavaliers', 'abbreviation': 'CLE'},
            {'name': 'Dallas Mavericks', 'abbreviation': 'DAL'},
            {'name': 'Denver Nuggets', 'abbreviation': 'DEN'},
            {'name': 'Detroit Pistons', 'abbreviation': 'DET'},
            {'name': 'Golden State Warriors', 'abbreviation': 'GSW'},
            {'name': 'Houston Rockets', 'abbreviation': 'HOU'},
            {'name': 'Indiana Pacers', 'abbreviation': 'IND'},
            {'name': 'Los Angeles Clippers', 'abbreviation': 'LAC'},
            {'name': 'Los Angeles Lakers', 'abbreviation': 'LAL'},
            {'name': 'Memphis Grizzlies', 'abbreviation': 'MEM'},
            {'name': 'Miami Heat', 'abbreviation': 'MIA'},
            {'name': 'Milwaukee Bucks', 'abbreviation': 'MIL'},
            {'name': 'Minnesota Timberwolves', 'abbreviation': 'MIN'},
            {'name': 'New Orleans Pelicans', 'abbreviation': 'NOP'},
            {'name': 'New York Knicks', 'abbreviation': 'NYK'},
            {'name': 'Oklahoma City Thunder', 'abbreviation': 'OKC'},
            {'name': 'Orlando Magic', 'abbreviation': 'ORL'},
            {'name': 'Philadelphia 76ers', 'abbreviation': 'PHI'},
            {'name': 'Phoenix Suns', 'abbreviation': 'PHO'},
            {'name': 'Portland Trail Blazers', 'abbreviation': 'POR'},
            {'name': 'Sacramento Kings', 'abbreviation': 'SAC'},
            {'name': 'San Antonio Spurs', 'abbreviation': 'SAS'},
            {'name': 'Toronto Raptors', 'abbreviation': 'TOR'},
            {'name': 'Utah Jazz', 'abbreviation': 'UTA'},
            {'name': 'Washington Wizards', 'abbreviation': 'WAS'},
        ]

        self.stdout.write(f'Creating {len(current_nba_teams)} NBA teams...')
        
        # Create teams
        for team_data in current_nba_teams:
            team, created = Team.objects.get_or_create(
                abbreviation=team_data['abbreviation'],
                defaults={'name': team_data['name']}
            )
            if created:
                self.stdout.write(f'  Created: {team.name} ({team.abbreviation})')

        # Parse seasons
        seasons = [int(s.strip()) for s in options['seasons'].split(',')]
        
        self.stdout.write(f'Fetching player data for seasons: {seasons}')
        
        # Fetch player data from NBA API
        for season in seasons:
            self.fetch_players_for_season(season)
            self.fetch_advanced_stats_for_season(season)
            time.sleep(1)  # Rate limiting

        self.stdout.write(self.style.SUCCESS('Successfully populated database with real NBA data!'))

    def fetch_players_for_season(self, season):
        """Fetch player totals data from NBA API"""
        self.stdout.write(f'Fetching player totals for {season}...')
        
        page = 1
        while True:
            url = 'https://api.server.nbaapi.com/api/playertotals'
            params = {
                'season': season,
                'page': page,
                'pageSize': 100,
                'sortBy': 'points',
                'ascending': False
            }
            
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                players_data = data.get('data', [])
                if not players_data:
                    break
                
                players_created = 0
                for player_data in players_data:
                    player_id = player_data.get('playerId') or player_data.get('player_id')
                    player_name = player_data.get('playerName') or player_data.get('player_name')
                    team_abbr = player_data.get('team')
                    position = player_data.get('pos') or player_data.get('position')

                    if not all([player_id, player_name, team_abbr]):
                        continue
                    
                    # Skip invalid team abbreviations
                    if len(team_abbr) != 3 or team_abbr in ['TOT', '2TM', '3TM']:
                        continue
                    
                    try:
                        team = Team.objects.get(abbreviation=team_abbr)
                        player, created = Player.objects.get_or_create(
                            player_id=player_id,
                            defaults={
                                'name': player_name,
                                'position': position # Save position
                            }
                        )

                        if not created and position and player.position != position:
                            player.position = position
                            player.save()
                            
                        player.teams.add(team)
                        if created:
                            self.stdout.write(f"  - Created player: {player_name} ({position})")
                        else:
                            # Optional: log updates for existing players
                            # self.stdout.write(f"  - Updated player: {player_name}")
                            pass

                    except Team.DoesNotExist:
                        self.stderr.write(self.style.WARNING(f"  - Team with abbreviation {team_abbr} not found for player {player_name}"))

                # Check if we've reached the last page
                pagination = data.get('pagination', {})
                if page >= pagination.get('pages', 1):
                    break
                    
                page += 1
                time.sleep(0.5)  # Rate limiting
                
            except requests.RequestException as e:
                self.stdout.write(f'  Error fetching players for season {season}, page {page}: {e}')
                break

    def fetch_advanced_stats_for_season(self, season):
        """Fetch advanced stats data from NBA API"""
        self.stdout.write(f'Fetching advanced stats for {season}...')
        
        page = 1
        while True:
            url = 'https://api.server.nbaapi.com/api/playeradvancedstats'
            params = {
                'season': season,
                'page': page,
                'pageSize': 100,
                'sortBy': 'vorp',
                'ascending': False
            }
            
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                stats_data = data.get('data', [])
                if not stats_data:
                    break
                
                stats_updated = 0
                for stat_data in stats_data:
                    if self.update_player_advanced_stats(stat_data, season):
                        stats_updated += 1
                
                self.stdout.write(f'  Page {page}: Updated {stats_updated} player advanced stats')
                
                # Check if we've reached the last page
                pagination = data.get('pagination', {})
                if page >= pagination.get('pages', 1):
                    break
                    
                page += 1
                time.sleep(0.5)  # Rate limiting
                
            except requests.RequestException as e:
                self.stdout.write(f'  Error fetching advanced stats for season {season}, page {page}: {e}')
                break

    def create_player_from_totals(self, player_data, season):
        """Create/update player and their season stats from totals data"""
        try:
            player_id = player_data.get('playerId')
            player_name = player_data.get('playerName')
            team_abbr = player_data.get('team')
            
            if not all([player_id, player_name, team_abbr]):
                return False
            
            # Skip invalid team abbreviations
            if len(team_abbr) != 3 or team_abbr in ['TOT', '2TM', '3TM']:
                return False
            
            # Get or create team
            try:
                team = Team.objects.get(abbreviation=team_abbr)
            except Team.DoesNotExist:
                self.stdout.write(f'    Warning: Team {team_abbr} not found')
                return False
            
            # Create or get player
            player, created = Player.objects.get_or_create(
                player_id=player_id,
                defaults={'name': player_name}
            )
            
            # Add player to team
            player.teams.add(team)
            
            # Create season stats
            PlayerSeasonStats.objects.update_or_create(
                player=player,
                season=season,
                defaults={
                    'points': float(player_data.get('points', 0)),
                    'rebounds': float(player_data.get('totalRb', 0)),
                    'assists': float(player_data.get('assists', 0)),
                    'vorp': 0.0  # Will be updated by advanced stats
                }
            )
            
            return True
            
        except Exception as e:
            self.stdout.write(f'    Error processing player {player_data.get("playerName", "Unknown")}: {e}')
            return False

    def update_player_advanced_stats(self, stat_data, season):
        """Update player's advanced stats"""
        try:
            player_id = stat_data.get('playerId')
            if not player_id:
                return False
            
            # Find player
            try:
                player = Player.objects.get(player_id=player_id)
            except Player.DoesNotExist:
                return False
            
            # Update season stats with advanced metrics
            season_stats, created = PlayerSeasonStats.objects.get_or_create(
                player=player,
                season=season,
                defaults={
                    'points': 0.0,
                    'rebounds': 0.0,
                    'assists': 0.0,
                    'vorp': float(stat_data.get('vorp', 0))
                }
            )
            
            if not created:
                season_stats.vorp = float(stat_data.get('vorp', 0))
                season_stats.save()
            
            return True
            
        except Exception as e:
            self.stdout.write(f'    Error updating advanced stats for player {stat_data.get("playerName", "Unknown")}: {e}')
            return False 