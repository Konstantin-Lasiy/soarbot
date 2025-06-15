# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SoarBot is a multi-station weather monitoring system that sends personalized Telegram notifications when soaring conditions are optimal. The system supports multiple wind stations per user with individual criteria and preferences.

### System Components

1. **Multi-Station Lambda Function (`lambda_function.py`)** - Main notification engine with Supabase integration
2. **E-ink Display (`run_screen.py`)** - Local display for FPS station (legacy component) 
3. **Database Schema** - Supabase PostgreSQL with multi-station support
4. **FastAPI Backend (`backend/`)** - REST API for user management (future)
5. **React Frontend (`frontend/`)** - Web interface for settings (future)
6. **GitHub Actions** - Automated execution every 15 minutes during daylight hours

## Architecture

### Multi-Station Database Schema

- **`wind_stations`** - Catalog of available weather stations (FPS, KSLC, KOGD, etc.)
- **`users`** - User profiles with Telegram integration
- **`user_preferences`** - Global notification settings (cooldown, timezone, message format)
- **`user_station_configs`** - Per-station wind criteria and preferences
- **`notification_history`** - Complete log of sent notifications with conditions

### Core Components

- `lambda_function.py` - Multi-station notification engine with Supabase integration
- `database_schema.sql` - Complete PostgreSQL schema with RLS policies
- `utils/weather_utils.py` - Weather data fetching with multi-station support
- `utils/eink_utils.py` - E-ink display rendering (legacy)
- `configs/` - Configuration files and API tokens
- `.github/workflows/` - GitHub Actions for automated execution

### Data Flow

1. **Weather Data**: Fetched from Synoptic API for multiple stations (FPS, KSLC, KOGD)
2. **User Configs**: Retrieved from Supabase with station-specific criteria 
3. **Condition Checking**: Per-user, per-station validation with detailed logging
4. **Smart Notifications**: Priority-based delivery with cooldown management
5. **History Tracking**: Complete audit trail in Supabase

### Key Dependencies

**Core Libraries** (managed via `uv` and `pyproject.toml`):
- `supabase` - Database integration and authentication
- `pandas` - Weather data processing and analysis
- `requests` - API calls to Synoptic and Telegram
- `python-dotenv` - Environment variable management
- `astral` - Sunrise/sunset calculations for daylight checking
- `pytz` - Timezone handling for multi-user support

**Legacy Components**:
- `PIL` (Pillow) - E-ink display image generation
- `matplotlib` - Wind speed charts for e-ink display

## Configuration

### Environment Variables (.env)
```bash
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Telegram Bot Configuration  
TELEGRAM_BOT_TOKEN=your-bot-token
ADMIN_TELEGRAM_CHAT_ID=your-chat-id-for-errors

# Synoptic API
SYNOPTIC_API_TOKEN=your-synoptic-token

# Legacy support
token=your-synoptic-token
telegram_token=your-bot-token
```

### GitHub Secrets (for Actions)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` 
- `TELEGRAM_BOT_TOKEN`
- `ADMIN_TELEGRAM_CHAT_ID`
- `SYNOPTIC_API_TOKEN`

## Development Workflow

### Package Management
- **ALWAYS use `uv` for Python package management** - never use pip directly
- Dependencies defined in `pyproject.toml`
- Install: `uv sync`
- Add dependency: `uv add package-name`
- Run scripts: `uv run python script.py`

### Git Commit Guidelines
- **NEVER add Claude Code attribution or "Generated with Claude Code" to commit messages**
- Keep commit messages concise and descriptive
- Follow the existing project's commit message style

### Database Setup
1. Create Supabase project at supabase.com
2. Run `database_schema.sql` in Supabase SQL Editor
3. Configure environment variables
4. Test connection: `uv run python lambda_function.py`

### Testing Commands
- **Lambda Function**: `uv run python lambda_function.py`
- **E-ink Display**: `uv run python run_screen.py` 
- **Legacy Tests**: `uv run python tests/telegram_test.py`

### User Management
- Users automatically get default FPS station configuration
- Database triggers create preferences and station configs
- View users: Query `user_configurations_with_stations` view
- Manual user creation examples in repository history

## Multi-Station Features

### Station Support
- **FPS** (South Side Flight Park) - Primary soaring site
- **KSLC** (Salt Lake City International) - Airport weather data
- **KOGD** (Ogden-Hinckley Airport) - Northern Utah conditions
- **Extensible** - Easy to add new Synoptic stations

### User Capabilities
- **Multiple Stations** - Monitor different locations with different criteria
- **Station Priority** - Highest priority station wins for notifications
- **Custom Names** - Personalized station labels in messages
- **Individual Criteria** - Wind speed, direction, and gust limits per station
- **Quiet Hours** - No notifications during specified times
- **Timezone Support** - Proper time handling per user location

### Notification Intelligence
- **Priority-Based** - Only sends from highest priority station meeting criteria
- **Cooldown Management** - Per-station cooldown timers prevent spam
- **Detailed Logging** - Complete conditions tracking for analysis
- **Personalized Messages** - Custom greetings and station names
- **Smart Scheduling** - Respects daylight hours and midday restrictions

## Development Notes

- Weather data converted from kph to mph (multiply by 1.15078)
- Timezone handling supports multiple users in different zones
- Database uses Row Level Security (RLS) for user data protection
- GitHub Actions runs every 15 minutes during 6 AM - 8 PM Mountain Time
- Lambda function includes comprehensive error handling and admin notifications
- Station data supports multiple API providers (currently Synoptic only)
- Legacy e-ink display components preserved for backward compatibility