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

## Dashboard Development Plan

### SoarBot Run Analytics Dashboard

**Objective**: Create a simple frontend-only dashboard to monitor SoarBot performance and diagnose notification failures.

#### Technical Stack
- **Frontend**: React + Vite (initialize with `npm create vite@latest dashboard --template react`)
- **Database**: Direct Supabase queries (no backend needed)
- **Styling**: Tailwind CSS for rapid development
- **Charts**: Chart.js for weather data visualization
- **Client**: Supabase JS client for direct database access

#### Dashboard Structure

**1. Run Summary Cards** (top section)
- Total runs today/week from `run_metrics` table
- Success rate percentage calculation
- Average runtime trends
- Notifications sent count

**2. Station Failure Analysis** (main section)
- Date range picker for filtering runs
- Expandable table showing station checks with:
  - Station name, user ID, timestamp
  - Status indicators (success/failed/cooldown/disabled)
  - Failed conditions as colored badges
- Row expansion reveals:
  - Actual weather values vs configured thresholds
  - Detailed condition breakdown from `station_details` JSON
  - Raw weather data (wind speed, direction, gusts, precipitation)

**3. Weather Data Visualization** (bottom section)
- Simple line charts showing recent weather trends
- Wind speed, direction, gusts for failed stations
- Threshold overlay bands to show how close conditions were to passing
- Helps identify near-miss scenarios

#### Key Features
- **Read-only access** - No authentication required
- **Real-time filtering** by date range, station, user
- **Color-coded status** - Red (failed), Yellow (cooldown), Green (success), Gray (disabled)
- **Responsive design** for mobile monitoring
- **Direct Supabase queries** from frontend using environment variables

#### Development Commands
```bash
# Initialize Vite React app
npm create vite@latest dashboard --template react

# Install dependencies
cd dashboard
npm install @supabase/supabase-js chart.js react-chartjs-2 tailwindcss

# Development server
npm run dev
```

#### Key Supabase Queries
1. **Run Overview**: `SELECT * FROM run_metrics WHERE start_time >= ? ORDER BY start_time DESC`
2. **Station Analysis**: Extract and filter `station_details` JSON for failure analysis
3. **Weather Trends**: Parse weather data from `station_details` for visualization
4. **Failure Patterns**: Aggregate condition failures by type and frequency

#### File Structure
```
dashboard/
├── src/
│   ├── components/
│   │   ├── RunSummary.jsx
│   │   ├── StationTable.jsx
│   │   └── WeatherCharts.jsx
│   ├── utils/
│   │   └── supabase.js
│   └── App.jsx
├── tailwind.config.js
└── package.json
```