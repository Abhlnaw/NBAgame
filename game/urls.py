from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TeamViewSet, PlayerViewSet, main_menu, wheel_view, player_selection_view, new_game_view, select_player_action_view, game_over_view

router = DefaultRouter()
router.register(r'teams', TeamViewSet, basename='team')
router.register(r'players', PlayerViewSet, basename='player')

urlpatterns = [
    path('', main_menu, name='main_menu'),
    path('new_game/', new_game_view, name='new_game'),
    path('wheel/', wheel_view, name='wheel'),
    path('select_player/<str:team_abbr>/', player_selection_view, name='select_player'),
    path('select_player_action/', select_player_action_view, name='select_player_action'),
    path('game_over/', game_over_view, name='game_over'),
    path('api/', include(router.urls)),
] 