from django.core.management.base import BaseCommand
from game.models import Team, Player, PlayerSeasonStats
import requests

class Command(BaseCommand):
    help = 'Populate the database with current NBA teams and players'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing teams and players before populating',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            Team.objects.all().delete()
            Player.objects.all().delete()
            PlayerSeasonStats.objects.all().delete()

        # Current NBA teams as of 2024-2025 season
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
        
        teams_created = 0
        for team_data in current_nba_teams:
            team, created = Team.objects.get_or_create(
                abbreviation=team_data['abbreviation'],
                defaults={'name': team_data['name']}
            )
            if created:
                teams_created += 1
                self.stdout.write(f'  Created: {team.name} ({team.abbreviation})')
            else:
                # Update existing team with correct name
                team.name = team_data['name']
                team.save()
                self.stdout.write(f'  Updated: {team.name} ({team.abbreviation})')

        self.stdout.write(f'✅ Successfully created/updated {teams_created} teams')

        # Try to populate players from NBA API if available
        self.populate_players_from_api()

    def populate_players_from_api(self):
        """Try to populate players from NBA stats API"""
        try:
            self.stdout.write('Attempting to fetch players from NBA API...')
            
            # NBA stats API endpoint for current players
            url = 'https://stats.nba.com/stats/commonallplayers'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://stats.nba.com/',
                'Accept': 'application/json, text/plain, */*',
            }
            params = {
                'IsOnlyCurrentSeason': '1',
                'LeagueID': '00',
                'Season': '2024-25'
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                players_data = data['resultSets'][0]['rowSet']
                
                players_created = 0
                for player_row in players_data[:200]:  # Limit to first 200 players to avoid overwhelming
                    player_id = player_row[0]
                    player_name = player_row[2]
                    team_abbr = player_row[7] if len(player_row) > 7 else None
                    
                    if team_abbr:
                        try:
                            team = Team.objects.get(abbreviation=team_abbr)
                            player, created = Player.objects.get_or_create(
                                name=player_name,
                                defaults={'player_id': str(player_id)}
                            )
                            if created:
                                player.teams.add(team)
                                players_created += 1
                        except Team.DoesNotExist:
                            self.stdout.write(f'  Warning: Team {team_abbr} not found for player {player_name}')
                            continue

                self.stdout.write(f'✅ Successfully created {players_created} players from NBA API')
            else:
                raise requests.RequestException(f'API returned status {response.status_code}')

        except Exception as e:
            self.stdout.write(f'⚠️  Could not fetch from NBA API: {e}')
            self.stdout.write('Creating sample players for each team...')
            self.create_sample_players()

    def create_sample_players(self):
        """Create sample players for each team if API fails"""
        sample_players = [
            'Michael Jordan', 'LeBron James', 'Kobe Bryant', 'Magic Johnson', 'Larry Bird',
            'Tim Duncan', 'Shaquille O\'Neal', 'Kareem Abdul-Jabbar', 'Wilt Chamberlain', 'Bill Russell',
            'Stephen Curry', 'Kevin Durant', 'Giannis Antetokounmpo', 'Kawhi Leonard', 'Anthony Davis',
            'James Harden', 'Russell Westbrook', 'Chris Paul', 'Damian Lillard', 'Joel Embiid',
            'Nikola Jokic', 'Luka Doncic', 'Trae Young', 'Jayson Tatum', 'Zion Williamson',
            'Ja Morant', 'Devin Booker', 'Donovan Mitchell', 'De\'Aaron Fox', 'Pascal Siakam'
        ]
        
        players_created = 0
        for team in Team.objects.all():
            # Create 5 sample players per team
            for i in range(5):
                if i < len(sample_players):
                    player_name = f"{sample_players[i % len(sample_players)]} {team.abbreviation}{i+1}"
                else:
                    player_name = f"Player {i+1}"
                
                player, created = Player.objects.get_or_create(
                    name=player_name,
                    defaults={'player_id': f'{team.abbreviation}_{i+1}'}
                )
                if created:
                    player.teams.add(team)
                    players_created += 1
                    
                    # Create sample stats for the player
                    PlayerSeasonStats.objects.create(
                        player=player,
                        season=2024,
                        points=20.0 + (i * 2),
                        rebounds=8.0 + i,
                        assists=5.0 + i,
                        vorp=2.5 + i
                    )

        self.stdout.write(f'✅ Created {players_created} sample players with stats') 