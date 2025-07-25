# 🏀 NBA Draft Game

A fun, interactive NBA draft game where players take turns selecting teams via a spinning wheel and drafting players to build their fantasy teams.

## 🌟 Features

- **Variable Player Support**: 2-4 players can participate in a single game
- **Interactive Team Selection**: Spin the wheel to randomly select NBA teams
- **Player Drafting**: Choose players from the selected team and assign positions
- **Smart Scoring System**: Advanced scoring based on player statistics with positional multipliers
- **Beautiful UI**: Modern, responsive design with gradient backgrounds and smooth animations
- **Real-time Game State**: Live tracking of all player teams and draft progress

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Django 5.2+
- Django REST Framework

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd NBA
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations**
   ```bash
   python manage.py migrate
   ```

5. **Populate the database with NBA data**
   ```bash
   python manage.py populate_teams
   ```

6. **Start the development server**
   ```bash
   python manage.py runserver
   ```

7. **Open your browser** and navigate to `http://127.0.0.1:8000`

## 🎮 How to Play

1. **Start a Game**: Choose the number of players (2-4) and click "Start Game"
2. **Spin the Wheel**: Each player takes turns spinning the wheel to select a random NBA team
3. **Draft Players**: Choose a player from the selected team and assign them a position
4. **Build Your Team**: Continue until each player has drafted 5 players
5. **View Results**: See the final scores and winner based on advanced player statistics

## 🏗️ Project Structure

```
NBA/
├── game/                     # Main Django app
│   ├── management/           # Custom management commands
│   │   └── commands/
│   │       └── populate_teams.py
│   ├── migrations/           # Database migrations
│   ├── static/game/js/       # JavaScript files (Winwheel, TweenMax)
│   ├── templates/game/       # HTML templates
│   ├── templatetags/         # Custom template tags
│   ├── models.py            # Database models (Team, Player, PlayerStats)
│   ├── views.py             # Game logic and API views
│   ├── serializers.py       # REST API serializers
│   └── urls.py              # URL routing
├── nba_game/                # Django project settings
├── db.sqlite3               # SQLite database
├── requirements.txt         # Python dependencies
└── manage.py               # Django management script
```

## 🛠️ Technical Details

### Models

- **Team**: NBA teams with name, abbreviation, city
- **Player**: NBA players linked to teams
- **PlayerStats**: Historical statistics for scoring calculations

### Scoring Algorithm

The scoring system uses advanced statistics with position-specific multipliers:

- **Point Guards**: Bonus for assists, reduced rebounds weight
- **Shooting Guards**: Bonus for points
- **Small Forwards**: Balanced across all categories
- **Power Forwards**: Bonus for rebounds
- **Centers**: Maximum rebounds bonus, reduced points weight

### API Endpoints

- `/api/teams/` - List all NBA teams (optimized for wheel display)
- `/api/teams/{id}/` - Detailed team information with players
- `/api/players/` - List all players

## 🎨 Features in Detail

### Dynamic Player Support
The game seamlessly handles 2-4 players with dynamic template rendering using custom Django template tags.

### Wheel Integration
Uses Winwheel.js library for smooth spinning animations and team selection.

### Session Management
Game state is preserved in Django sessions, allowing players to navigate between pages without losing progress.

### Responsive Design
Modern CSS with gradients, glassmorphism effects, and mobile-friendly layouts.

## 🔧 Development

### Adding New Teams/Players
Use the management command to populate or update team data:
```bash
python manage.py populate_teams
```

### Custom Template Tags
Located in `game/templatetags/game_tags.py` for dynamic template rendering with variable player counts.

### Debugging
Logging is configured for the `game` app. Set `DEBUG=True` in settings to see detailed logs.

## 📱 Browser Compatibility

- Chrome (recommended)
- Firefox
- Safari
- Edge

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is for educational purposes. NBA team names and player data are used for demonstration only.

## 🎯 Future Enhancements

- [ ] Real-time multiplayer support
- [ ] Advanced player statistics integration
- [ ] Draft history and analytics
- [ ] Custom team themes
- [ ] Tournament mode
- [ ] Player trade functionality

---

Enjoy building your ultimate NBA dream team! 🏆
