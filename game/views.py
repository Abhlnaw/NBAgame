import json
import logging
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from rest_framework import viewsets
from .models import Team, Player
from .serializers import TeamSerializer, PlayerSerializer, TeamNameSerializer

logger = logging.getLogger(__name__)

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
    return render(request, 'game/wheel.html', {'game_state': game_state})

def player_selection_view(request, team_abbr):
    """Display available players from the selected team."""
    game_state = request.session.get('game_state')
    if not game_state:
        return redirect('new_game')
    
    try:
        team = Team.objects.get(abbreviation=team_abbr)
        players = team.players.all()
    except Team.DoesNotExist:
        # Redirect back to wheel if team doesn't exist
        return redirect('wheel')
    
    context = {
        'team': team,
        'players': players,
        'game_state': game_state
    }
    return render(request, 'game/select_player.html', context)

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

        player = Player.objects.get(id=player_id)
        logger.debug(f"Player selected: {player.name} ({position}) by Player {game_state['current_player']}")

        # Add player to the current player's team
        current_player_team_key = f"player_{game_state['current_player']}_team"
        
        # Ensure the team list exists
        if current_player_team_key not in game_state:
            game_state[current_player_team_key] = []
        
        player_data = {
            'id': player.id,
            'name': player.name,
            'position': position
        }
        
        game_state[current_player_team_key].append(player_data)

        # Update turn logic
        if game_state['current_player'] < game_state['num_players']:
            game_state['current_player'] += 1
        else:
            # End of a turn, reset to player 1 and advance turn
            game_state['current_player'] = 1
            game_state['turn'] += 1
        
        # Save updated game state
        request.session['game_state'] = game_state
        request.session.modified = True
        request.session.save()
        
        # Check if all players have drafted 5 players (game over)
        if game_state['turn'] > 5:
            return JsonResponse({'redirect_url': '/game_over/'})

        return JsonResponse({'redirect_url': '/wheel/'})
        
    except Player.DoesNotExist:
        return JsonResponse({'error': f'Player with id {player_id} not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error in select_player_action_view: {e}")
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

    # Add scores to the game_state for template display
    for player_num, score in team_scores.items():
        game_state[f'team_{player_num}_score'] = round(score, 2)

    context = {
        'game_state': game_state,
        'winner': winner,
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
