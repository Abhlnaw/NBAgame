from django.shortcuts import render, redirect
from rest_framework import viewsets
from .models import Team, Player
from .serializers import TeamSerializer, PlayerSerializer
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

# Create your views here.

def main_menu(request):
    return render(request, 'game/index.html')

def new_game_view(request):
    num_players = int(request.POST.get('num_players', 2))
    
    game_state = {
        'current_player': 1,
        'turn': 1,
        'num_players': num_players,
    }
    
    for i in range(1, num_players + 1):
        game_state[f'player_{i}_team'] = []

    request.session['game_state'] = game_state
    return redirect('wheel')

def wheel_view(request):
    game_state = request.session.get('game_state')
    if not game_state:
        return redirect('new_game')
    return render(request, 'game/wheel.html', {'game_state': game_state})

def player_selection_view(request, team_abbr):
    game_state = request.session.get('game_state')
    if not game_state:
        return redirect('new_game')
    
    team = Team.objects.get(abbreviation=team_abbr)
    players = team.players.all()
    context = {
        'team': team,
        'players': players,
        'game_state': game_state
    }
    return render(request, 'game/select_player.html', context)

def calculate_winner(game_state):
    """
    Calculates the winner based on peak player stats and positional adjustments for a variable number of players.
    """
    team_scores = {}
    
    position_multipliers = {
        'PG': {'points': 1.1, 'rebounds': 0.8, 'assists': 1.3},
        'SG': {'points': 1.2, 'rebounds': 0.9, 'assists': 1.0},
        'SF': {'points': 1.1, 'rebounds': 1.0, 'assists': 1.1},
        'PF': {'points': 1.0, 'rebounds': 1.2, 'assists': 0.9},
        'C':  {'points': 0.9, 'rebounds': 1.3, 'assists': 0.8},
    }

    def get_team_score(team_roster):
        total_score = 0
        for drafted_player in team_roster:
            player = Player.objects.get(id=drafted_player['id'])
            peak_season = player.stats.order_by('-vorp').first()
            
            if peak_season:
                multipliers = position_multipliers.get(drafted_player['position'], {'points': 1, 'rebounds': 1, 'assists': 1})
                
                adjusted_points = peak_season.points * multipliers['points']
                adjusted_rebounds = peak_season.rebounds * multipliers['rebounds']
                adjusted_assists = peak_season.assists * multipliers['assists']
                
                player_score = adjusted_points + adjusted_rebounds + adjusted_assists
                total_score += player_score
        return total_score

    for i in range(1, game_state['num_players'] + 1):
        team_key = f'player_{i}_team'
        team_roster = game_state[team_key]
        team_scores[i] = get_team_score(team_roster)

    winner = max(team_scores, key=team_scores.get)
    return winner, team_scores


def game_over_view(request):
    game_state = request.session.get('game_state')
    if not game_state:
        return redirect('new_game')
    
    winner, team_scores = calculate_winner(game_state)

    # Add scores to the game_state to be used by the template tag
    for player_num, score in team_scores.items():
        game_state[f'team_{player_num}_score'] = round(score, 2)

    context = {
        'game_state': game_state,
        'winner': winner,
    }
    
    # Clear the game state from the session
    # del request.session['game_state'] # Commenting out for easier testing
    return render(request, 'game/game_over.html', context)

@require_POST
def select_player_action_view(request):
    game_state = request.session.get('game_state')
    if not game_state:
        return JsonResponse({'error': 'Game state not found.'}, status=400)

    data = json.loads(request.body)
    player_id = data.get('player_id')
    position = data.get('position')

    player = Player.objects.get(id=player_id)

    # Add player to the current player's team
    current_player_team_key = f"player_{game_state['current_player']}_team"
    game_state[current_player_team_key].append({
        'id': player.id,
        'name': player.name,
        'position': position
    })

    # Update game state
    if game_state['current_player'] < game_state['num_players']:
        game_state['current_player'] += 1
    else:
        # End of a turn, reset to player 1 and advance turn
        game_state['current_player'] = 1
        game_state['turn'] += 1

    request.session.save()
    
    # Check if all players have drafted 5 players
    if game_state['turn'] > 5:
        return JsonResponse({'redirect_url': '/game_over/'})

    return JsonResponse({'redirect_url': '/wheel/'})

class TeamViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows teams to be viewed.
    """
    queryset = Team.objects.all()
    serializer_class = TeamSerializer

class PlayerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows players to be viewed.
    """
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer
