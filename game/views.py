import json
import logging
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from rest_framework import viewsets
from .models import Team, Player
from .serializers import TeamSerializer, PlayerSerializer, TeamNameSerializer

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

def calculate_winner(game_state):
    """Calculate the winner based on peak player stats and positional adjustments."""
    team_scores = {}
    
    position_multipliers = {
        'PG': {'points': 1.1, 'rebounds': 0.8, 'assists': 1.3},
        'SG': {'points': 1.2, 'rebounds': 0.9, 'assists': 1.0},
        'SF': {'points': 1.1, 'rebounds': 1.0, 'assists': 1.1},
        'PF': {'points': 1.0, 'rebounds': 1.2, 'assists': 0.9},
        'C':  {'points': 0.9, 'rebounds': 1.3, 'assists': 0.8},
    }

    def get_team_score(team_roster):
        """Calculate total score for a team based on player stats."""
        total_score = 0
        for drafted_player in team_roster:
            try:
                player = Player.objects.get(id=drafted_player['id'])
                peak_season = player.stats.order_by('-vorp').first()
                
                if peak_season:
                    multipliers = position_multipliers.get(
                        drafted_player['position'], 
                        {'points': 1, 'rebounds': 1, 'assists': 1}
                    )
                    
                    adjusted_points = peak_season.points * multipliers['points']
                    adjusted_rebounds = peak_season.rebounds * multipliers['rebounds']
                    adjusted_assists = peak_season.assists * multipliers['assists']
                    
                    player_score = adjusted_points + adjusted_rebounds + adjusted_assists
                    total_score += player_score
            except Player.DoesNotExist:
                logger.warning(f"Player with id {drafted_player['id']} not found during scoring")
                continue
        return total_score

    # Calculate scores for all teams
    for i in range(1, game_state['num_players'] + 1):
        team_key = f'player_{i}_team'
        team_roster = game_state.get(team_key, [])
        team_scores[i] = get_team_score(team_roster)

    # Determine winner
    winner = max(team_scores, key=team_scores.get) if team_scores else 1
    return winner, team_scores

def game_over_view(request):
    """Display the game over screen with winner and final scores."""
    game_state = request.session.get('game_state')
    if not game_state:
        return redirect('new_game')
    
    winner, team_scores = calculate_winner(game_state)

    # Enhance teams display data with scores and winner status
    teams_display_data = get_teams_display_data(game_state)
    for team_data in teams_display_data:
        player_num = team_data['player_num']
        team_data['score'] = round(team_scores.get(player_num, 0), 2)
        team_data['is_winner'] = player_num == winner

    context = {
        'game_state': game_state,
        'winner': winner,
        'teams_display_data': teams_display_data,
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
