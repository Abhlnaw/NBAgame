import json
import logging
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Team, Player
from .serializers import TeamSerializer, PlayerSerializer, TeamNameSerializer
import os
from django.conf import settings

logger = logging.getLogger(__name__)

# Game State Utility Functions
def get_teams_display_data(game_state):
    """Generate teams display data for templates."""
    teams_data = []
    if game_state:
        for i in range(1, game_state.get('num_players', 0) + 1):
            team_key = f"player_{i}_team"
            teams_data.append({
                'player_num': i,
                'is_current': i == game_state.get('current_player'),
                'roster': game_state.get(team_key, [])
            })
    return teams_data

def get_all_drafted_player_ids(game_state):
    """Get set of all drafted player IDs across all teams."""
    drafted_ids = set()
    for i in range(1, game_state.get('num_players', 0) + 1):
        roster = game_state.get(f"player_{i}_team", [])
        for player_data in roster:
            if player_data and 'id' in player_data:
                drafted_ids.add(player_data['id'])
    return drafted_ids

def validate_player_selection(game_state, player_id, position):
    """Validate if a player can be drafted in the given position."""
    current_player_team_key = f"player_{game_state['current_player']}_team"
    
    # Check for duplicate positions
    existing_positions = [p.get('position', '').upper() for p in game_state.get(current_player_team_key, [])]
    if position.upper() in existing_positions:
        return False, f"You already drafted a {position}. Choose a different position."

    # Check for duplicate players
    for i in range(1, game_state['num_players'] + 1):
        team_key = f"player_{i}_team"
        for drafted_player in game_state.get(team_key, []):
            if drafted_player.get('id') == player_id:
                try:
                    player = Player.objects.get(id=player_id)
                    return False, f"{player.name} has already been drafted by another team."
                except Player.DoesNotExist:
                    return False, "Player not found."
    
    return True, ""

def advance_turn(game_state):
    """Advance to the next player/turn."""
    if game_state['current_player'] < game_state['num_players']:
        game_state['current_player'] += 1
    else:
        game_state['current_player'] = 1
        game_state['turn'] += 1



def main_menu(request):
    """Display the main menu with player selection options."""
    return render(request, 'game/index.html')

def new_game_view(request):
    """Initialize a new game with the selected number of players."""
    num_players = int(request.POST.get('num_players', 2))
    
    game_state = {
        'current_player': 1,
        'turn': 1,
        'num_players': num_players,
    }
    
    # Initialize empty teams for each player
    for i in range(1, num_players + 1):
        game_state[f'player_{i}_team'] = []

    request.session['game_state'] = game_state
    return redirect('wheel')

def wheel_view(request):
    """Display the wheel for team selection."""
    game_state = request.session.get('game_state')
    
    if not game_state:
        return redirect('new_game')

    context = {
        'game_state': game_state,
        'teams_display_data': get_teams_display_data(game_state)
    }
    
    return render(request, 'game/wheel.html', context)



@require_POST
def select_player_action_view(request):
    """Handle player selection and update game state."""
    game_state = request.session.get('game_state')
    if not game_state:
        return JsonResponse({'error': 'Game state not found.'}, status=400)

    try:
        data = json.loads(request.body)
        player_id = data.get('player_id')
        position = data.get('position')
        
        if not player_id or not position:
            return JsonResponse({'error': 'Missing player_id or position'}, status=400)

        # Validate player selection
        is_valid, error_message = validate_player_selection(game_state, player_id, position)
        if not is_valid:
            return JsonResponse({'error': error_message}, status=400)

        # Get player and create player data
        player = Player.objects.get(id=player_id)
        player_data = {
            'id': player.id,
            'name': player.name,
            'position': position
        }
        
        # Add player to current player's team
        current_player_team_key = f"player_{game_state['current_player']}_team"
        if current_player_team_key not in game_state:
            game_state[current_player_team_key] = []
        game_state[current_player_team_key].append(player_data)
        
        # Advance turn
        advance_turn(game_state)
        
        # Save session
        request.session['game_state'] = game_state
        request.session.modified = True
        
        # Check if game is over
        if game_state['turn'] > 5:
            return JsonResponse({'redirect_url': '/game_over/'})

        return JsonResponse({'redirect_url': '/wheel/'})
        
    except Player.DoesNotExist:
        return JsonResponse({'error': f'Player with id {player_id} not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error selecting player: {e}")
        return JsonResponse({'error': 'Server error occurred'}, status=500)

def load_league_data():
    """Load comprehensive player data from league.json"""
    league_file_path = os.path.join(settings.BASE_DIR, 'league.json')
    try:
        with open(league_file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error(f"league.json not found at {league_file_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing league.json: {e}")
        return []

def get_player_league_data(player_name, league_data):
    """Get comprehensive stats for a player from league data"""
    # Normalize player name for matching
    normalized_name = player_name.strip().lower()
    
    for player_data in league_data:
        if player_data.get('name', '').strip().lower() == normalized_name:
            return player_data
    
    # If exact match not found, try partial matching
    for player_data in league_data:
        league_name = player_data.get('name', '').strip().lower()
        if normalized_name in league_name or league_name in normalized_name:
            return player_data
    
    logger.warning(f"Player {player_name} not found in league data")
    return None

def calculate_comprehensive_team_scores(teams_display_data):
    """Calculate comprehensive team scores based on all available attributes from league.json"""
    league_data = load_league_data()
    if not league_data:
        # Fallback to simple scoring if league data unavailable
        return calculate_simple_team_scores(teams_display_data)
    
    # Get all possible attributes from the first player (excluding name and team)
    sample_player = league_data[0] if league_data else {}
    all_attributes = [key for key in sample_player.keys() if key not in ['name', 'team']]
    
    logger.info(f"Found {len(all_attributes)} attributes to evaluate: {all_attributes}")
    
    team_scores = {}
    team_attribute_totals = {}
    
    # Calculate totals for each attribute for each team
    for team in teams_display_data:
        player_num = team['player_num']
        team_scores[player_num] = {'total_attributes_won': 0, 'details': {}}
        team_attribute_totals[player_num] = {}
        
        # Initialize all attributes to 0
        for attr in all_attributes:
            team_attribute_totals[player_num][attr] = 0
        
        # Sum up attributes for all players on the team
        for player in team['roster']:
            player_data = get_player_league_data(player['name'], league_data)
            if player_data:
                for attr in all_attributes:
                    value = player_data.get(attr, 0)
                    if isinstance(value, (int, float)):
                        team_attribute_totals[player_num][attr] += value
                    else:
                        logger.warning(f"Non-numeric value for {attr} in {player['name']}: {value}")
    
    # Compare teams for each attribute
    for attr in all_attributes:
        # Find the team with the highest total for this attribute
        max_value = -1
        winning_teams = []
        
        for player_num in team_attribute_totals:
            attr_total = team_attribute_totals[player_num][attr]
            if attr_total > max_value:
                max_value = attr_total
                winning_teams = [player_num]
            elif attr_total == max_value and attr_total > 0:
                winning_teams.append(player_num)
        
        # Award points to winning team(s) for this attribute
        if len(winning_teams) == 1:
            winning_team = winning_teams[0]
            team_scores[winning_team]['total_attributes_won'] += 1
            team_scores[winning_team]['details'][attr] = {
                'won': True,
                'value': team_attribute_totals[winning_team][attr],
                'vs_others': {str(pn): team_attribute_totals[pn][attr] for pn in team_attribute_totals if pn != winning_team}
            }
            
            # Add loss details to other teams
            for other_team in team_attribute_totals:
                if other_team != winning_team:
                    team_scores[other_team]['details'][attr] = {
                        'won': False,
                        'value': team_attribute_totals[other_team][attr],
                        'vs_others': {str(winning_team): team_attribute_totals[winning_team][attr]}
                    }
        else:
            # Tie - no team gets a point for this attribute
            for player_num in team_attribute_totals:
                team_scores[player_num]['details'][attr] = {
                    'won': None,  # Indicates tie
                    'value': team_attribute_totals[player_num][attr],
                    'vs_others': {str(pn): team_attribute_totals[pn][attr] for pn in team_attribute_totals if pn != player_num}
                }
    
    logger.info(f"Team attribute scores: {team_scores}")
    return team_scores, all_attributes

def calculate_simple_team_scores(teams_display_data):
    """Fallback simple scoring system if league data is unavailable"""
    team_scores = {}
    for team in teams_display_data:
        player_num = team['player_num']
        # Simple scoring: 1 point per player drafted
        team_scores[player_num] = {
            'total_attributes_won': len(team['roster']),
            'details': {'players_drafted': {'won': True, 'value': len(team['roster'])}}
        }
    return team_scores, ['players_drafted']

def determine_winner_comprehensive(teams_display_data):
    """Determine the winner using comprehensive attribute comparison"""
    team_scores, all_attributes = calculate_comprehensive_team_scores(teams_display_data)
    
    # Find the team with the most attributes won
    max_attributes_won = 0
    winning_teams = []
    
    for player_num, score_data in team_scores.items():
        attributes_won = score_data['total_attributes_won']
        if attributes_won > max_attributes_won:
            max_attributes_won = attributes_won
            winning_teams = [player_num]
        elif attributes_won == max_attributes_won:
            winning_teams.append(player_num)
    
    # Handle ties
    if len(winning_teams) > 1:
        logger.info(f"Tie detected between players: {winning_teams}")
        # For now, return the first tied player, but you could implement tiebreaker logic
        winner = winning_teams[0]
    else:
        winner = winning_teams[0] if winning_teams else 1
    
    return winner, team_scores, all_attributes

def game_over_view(request):
    """Display the game over screen with comprehensive team analysis."""
    game_state = request.session.get('game_state')
    if not game_state:
        return redirect('new_game')
    
    # Get teams display data first
    teams_display_data = get_teams_display_data(game_state)
    
    # Use comprehensive scoring system
    winner, team_scores, all_attributes = determine_winner_comprehensive(teams_display_data)

    # Enhance teams display data with comprehensive scores and winner status
    for team_data in teams_display_data:
        player_num = team_data['player_num']
        score_data = team_scores.get(player_num, {})
        team_data['attributes_won'] = score_data.get('total_attributes_won', 0)
        team_data['score_details'] = score_data.get('details', {})
        team_data['is_winner'] = player_num == winner

    context = {
        'game_state': game_state,
        'winner': winner,
        'teams_display_data': teams_display_data,
        'all_attributes': all_attributes,
        'team_scores': team_scores,
        'total_attributes': len(all_attributes)
    }
    
    return render(request, 'game/game_over.html', context)

# API ViewSets
class TeamViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows teams to be viewed."""
    queryset = Team.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TeamNameSerializer
        return TeamSerializer

class PlayerViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows players to be viewed."""
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer
