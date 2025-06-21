import json
import os
import requests
import datetime
import pytz
import time
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
import logging

# Import existing weather utilities
from utils.weather_utils import get_station_data, check_winter, format_message

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Use service role key for server-side operations
)

def send_telegram_message(chat_id: str, text: str, telegram_token: str, parse_mode: str = "HTML") -> bool:
    """Send a message to a Telegram chat"""
    api_url = f'https://api.telegram.org/bot{telegram_token}/sendMessage'
    
    try:
        response = requests.post(api_url, json={
            'chat_id': chat_id, 
            'text': text,
            'parse_mode': parse_mode
        })
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False

def get_active_users_with_configs() -> List[Dict[str, Any]]:
    """Fetch all active users and their multi-station configurations from Supabase"""
    try:
        result = supabase.table("user_configurations_with_stations").select("*").execute()
        
        # Group by user_id to organize multiple stations per user
        users_dict = {}
        for row in result.data:
            user_id = row["user_id"]
            if user_id not in users_dict:
                users_dict[user_id] = {
                    "user_id": user_id,
                    "telegram_chat_id": row["telegram_chat_id"],
                    "username": row["username"],
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "preferences": {
                        "notification_cooldown_hours": row["notification_cooldown_hours"],
                        "timezone": row["timezone"],
                        "notifications_enabled": row["notifications_enabled"],
                        "include_weather_chart": row["include_weather_chart"],
                        "message_rows": row["message_rows"],
                        "enable_winter_midday": row["enable_winter_midday"],
                        "quiet_hours_start": row.get("quiet_hours_start"),
                        "quiet_hours_end": row.get("quiet_hours_end")
                    },
                    "stations": []
                }
            
            # Add station configuration
            station_config = {
                "station_id": row["station_id"],
                "station_name": row["station_name"],
                "station_description": row["station_description"],
                "api_provider": row["api_provider"],
                "api_config": row["api_config"],
                "wind_speed_min": row["wind_speed_min"],
                "wind_speed_max": row["wind_speed_max"],
                "wind_direction_min": row["wind_direction_min"],
                "wind_direction_max": row["wind_direction_max"],
                "max_gust_differential": row["max_gust_differential"],
                "priority": row["priority"],
                "custom_name": row["custom_name"],
                "station_enabled": row["station_enabled"],
                "min_visibility_miles": row.get("min_visibility_miles"),
                "max_precipitation_rate": row.get("max_precipitation_rate")
            }
            users_dict[user_id]["stations"].append(station_config)
        
        # Sort stations by priority for each user
        for user_data in users_dict.values():
            user_data["stations"].sort(key=lambda x: x["priority"])
        
        return list(users_dict.values())
        
    except Exception as e:
        logger.error(f"Failed to fetch users: {e}")
        return []

def get_station_weather_data(station_config: Dict[str, Any]) -> Optional[Any]:
    """Get weather data for a specific station based on its configuration"""
    try:
        station_id = station_config["station_id"]
        api_provider = station_config["api_provider"]
        api_config = station_config.get("api_config", {})
        
        if api_provider == "synoptic":
            # Use existing function for Synoptic stations
            if station_id == "FPS":
                lookback_minutes = api_config.get("lookback_minutes", 120)
                return get_station_data(lookback_minutes)
            else:
                # For other Synoptic stations, we'd need to modify get_station_data
                # to accept station_id parameter
                logger.warning(f"Synoptic station {station_id} not yet supported, using FPS data")
                return get_station_data(api_config.get("lookback_minutes", 120))
        else:
            logger.warning(f"API provider {api_provider} not yet implemented")
            return None
            
    except Exception as e:
        logger.error(f"Failed to get weather data for station {station_config['station_id']}: {e}")
        return None

def check_station_conditions(station_data, station_config: Dict[str, Any], user_preferences: Dict[str, Any], winter: bool) -> Dict[str, Any]:
    """Check if weather conditions meet user's criteria for a specific station"""
    if len(station_data) < 3:
        return {"conditions_met": False, "reason": "insufficient_data"}
    
    conditions_result = {
        "conditions_met": False,
        "station_id": station_config["station_id"],
        "station_name": station_config["station_name"],
        "checks": {}
    }
    
    # Check wind speed
    last_3_wind_speeds = station_data.tail(3)["wind_speed_set_1"]
    wind_speed_ok = (
        (last_3_wind_speeds >= station_config["wind_speed_min"]) &
        (last_3_wind_speeds <= station_config["wind_speed_max"])
    ).all()
    conditions_result["checks"]["wind_speed"] = {
        "passed": wind_speed_ok,
        "values": list(last_3_wind_speeds.round(1)),
        "criteria": f"{station_config['wind_speed_min']}-{station_config['wind_speed_max']} mph"
    }
    
    # Check wind direction
    last_3_wind_directions = station_data.tail(3)["wind_direction_set_1"]
    wind_dir_ok = (
        (last_3_wind_directions >= station_config["wind_direction_min"]) &
        (last_3_wind_directions <= station_config["wind_direction_max"])
    ).all()
    conditions_result["checks"]["wind_direction"] = {
        "passed": wind_dir_ok,
        "values": list(last_3_wind_directions.round(0)),
        "criteria": f"{station_config['wind_direction_min']}-{station_config['wind_direction_max']}°"
    }
    
    # Check gusts
    last_3_gust_diff = (
        station_data.tail(3)["wind_gust_set_1"] - 
        station_data.tail(3)["wind_speed_set_1"]
    )
    gusts_ok = (last_3_gust_diff <= station_config["max_gust_differential"]).all()
    conditions_result["checks"]["gusts"] = {
        "passed": gusts_ok,
        "values": list(last_3_gust_diff.round(1)),
        "criteria": f"≤{station_config['max_gust_differential']} mph"
    }
    
    # Check rain
    last_3_rain = station_data.tail(3)["precip_accum_five_minute_set_1"]
    no_rain = (last_3_rain <= 0).all()
    conditions_result["checks"]["precipitation"] = {
        "passed": no_rain,
        "values": list(last_3_rain),
        "criteria": "no rain"
    }
    
    # Check time constraints using user's timezone
    user_tz = pytz.timezone(user_preferences.get("timezone", "America/Denver"))
    current_time = datetime.datetime.now(user_tz)
    
    # Check if it's daytime (6 AM to 8 PM)
    is_daytime = 6 <= current_time.hour <= 20
    conditions_result["checks"]["daytime"] = {
        "passed": is_daytime,
        "current_hour": current_time.hour,
        "criteria": "6:00-20:00"
    }
    
    # Check quiet hours
    quiet_hours_ok = True
    if user_preferences.get("quiet_hours_start") and user_preferences.get("quiet_hours_end"):
        quiet_start = user_preferences["quiet_hours_start"]
        quiet_end = user_preferences["quiet_hours_end"]
        current_time_only = current_time.time()
        
        if quiet_start < quiet_end:
            # Same day quiet hours (e.g., 22:00 to 06:00 next day)
            quiet_hours_ok = not (quiet_start <= current_time_only <= quiet_end)
        else:
            # Quiet hours cross midnight
            quiet_hours_ok = not (current_time_only >= quiet_start or current_time_only <= quiet_end)
    
    conditions_result["checks"]["quiet_hours"] = {
        "passed": quiet_hours_ok,
        "current_time": current_time.strftime("%H:%M"),
        "criteria": "outside quiet hours"
    }
    
    # Check midday restrictions
    if not winter and not user_preferences.get("enable_winter_midday", True):
        is_midday = 11 <= current_time.hour <= 15
        midday_ok = not is_midday
    else:
        midday_ok = True
    
    conditions_result["checks"]["midday"] = {
        "passed": midday_ok,
        "winter_mode": winter,
        "criteria": "outside midday hours (summer only)"
    }
    
    # Overall result
    all_conditions_met = (
        wind_speed_ok and wind_dir_ok and gusts_ok and no_rain and 
        is_daytime and quiet_hours_ok and midday_ok
    )
    conditions_result["conditions_met"] = all_conditions_met
    
    return conditions_result

def get_last_notification_time(user_id: str, station_uuid: str) -> datetime.datetime:
    """Get the timestamp of the last notification sent to a user for a specific station"""
    try:
        result = supabase.table("notification_history").select("sent_at").eq("user_id", user_id).eq("station_id", station_uuid).order("sent_at", desc=True).limit(1).execute()
        
        if result.data:
            return datetime.datetime.fromisoformat(result.data[0]["sent_at"].replace('Z', '+00:00'))
        else:
            # If no previous notifications, return a time far in the past
            return datetime.datetime.now(pytz.UTC) - datetime.timedelta(days=365)
    except Exception as e:
        logger.error(f"Failed to get last notification time for user {user_id}, station {station_uuid}: {e}")
        return datetime.datetime.now(pytz.UTC) - datetime.timedelta(days=365)

def generate_personalized_message(user_data: Dict[str, Any], station_config: Dict[str, Any], station_data, conditions_result: Dict[str, Any]) -> str:
    """Generate a personalized notification message"""
    preferences = user_data["preferences"]
    
    # Generate greeting
    if user_data.get("first_name"):
        greeting = f"Hi {user_data['first_name']}! "
    elif user_data.get("username"):
        greeting = f"Hi @{user_data['username']}! "
    else:
        greeting = "Hi! "
    
    # Station name (use custom name if available)
    station_name = station_config.get("custom_name") or station_config["station_name"]
    
    # Format message based on user preferences
    message_rows = preferences.get("message_rows", 6)
    weather_message = format_message(station_data, rows=message_rows, html=True)
    
    # Build the full message
    full_message = f"{greeting}🌬️ <b>Great soaring conditions at {station_name}!</b>\n\n"
    
    # Add conditions summary
    full_message += "<b>Your criteria met:</b>\n"
    checks = conditions_result["checks"]
    full_message += f"• Wind: {checks['wind_speed']['criteria']} ✅\n"
    full_message += f"• Direction: {checks['wind_direction']['criteria']} ✅\n"
    full_message += f"• Gusts: {checks['gusts']['criteria']} ✅\n"
    full_message += f"• Weather: {checks['precipitation']['criteria']} ✅\n\n"
    
    # Add weather data
    full_message += weather_message
    
    # Add station info if it's not the default
    if station_config["station_id"] != "FPS":
        full_message += f"\n📍 <i>Data from {station_name}</i>"
    
    return full_message

def log_notification(user_id: str, station_id: str, message_content: str, conditions_result: Dict[str, Any], station_data_dict: Dict[str, Any]) -> bool:
    """Log a sent notification to the database"""
    try:
        
        def make_serializable(obj):
            """Convert numpy/pandas types to JSON serializable types"""
            if hasattr(obj, 'item'):  # numpy scalars
                return obj.item()
            elif hasattr(obj, 'tolist'):  # numpy arrays
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(v) for v in obj]
            else:
                return obj
        
        clean_conditions = make_serializable(conditions_result)
        clean_station_data = make_serializable(station_data_dict)
        
        notification_data = {
            "user_id": user_id,
            "station_id": station_id,
            "message_content": message_content,
            "conditions_met": clean_conditions,
            "station_data": clean_station_data,
            "notification_type": "conditions_met"
        }
        
        supabase.table("notification_history").insert(notification_data).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to log notification for user {user_id}, station {station_id}: {e}")
        return False

def log_run_metrics(metrics: Dict[str, Any]) -> bool:
    """Log run metrics to Supabase for monitoring"""
    try:
        def make_serializable(obj):
            """Convert numpy/pandas types to JSON serializable types"""
            if hasattr(obj, 'item'):  # numpy scalars
                return obj.item()
            elif hasattr(obj, 'tolist'):  # numpy arrays
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(v) for v in obj]
            else:
                return obj
        
        clean_metrics = make_serializable(metrics)
        supabase.table("run_metrics").insert(clean_metrics).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to log run metrics: {e}")
        return False

def lambda_handler(event, context):
    """Main Lambda function handler for multi-station notifications"""
    start_time = time.time()
    run_metrics = {
        'run_id': f"run_{int(time.time())}",
        'start_time': datetime.datetime.now(pytz.UTC).isoformat(),
        'users_found': 0,
        'users_checked': 0,
        'stations_total': 0,
        'stations_checked': 0,
        'stations_with_data': 0,
        'stations_disabled': 0,
        'conditions_met_count': 0,
        'cooldown_blocks': 0,
        'notifications_sent': 0,
        'notification_failures': 0,
        'api_errors': 0,
        'database_errors': 0,
        'winter_mode': False,
        'runtime_seconds': 0,
        'success': True,
        'error_message': None,
        'station_details': []
    }
    
    try:
        logger.info("Starting SoarBot multi-station check...")
        
        # Check if it's winter
        winter = check_winter()
        run_metrics['winter_mode'] = winter
        logger.info(f"Winter mode: {winter}")
        
        # Get all active users with their configurations
        users = get_active_users_with_configs()
        run_metrics['users_found'] = len(users)
        
        if not users:
            logger.info("No active users found")
            run_metrics['runtime_seconds'] = round(time.time() - start_time, 2)
            log_run_metrics(run_metrics)
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No active users found'})
            }
        
        logger.info(f"Found {len(users)} active users")
        run_metrics['stations_total'] = sum(len(user['stations']) for user in users)
        
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not telegram_token:
            raise Exception("TELEGRAM_BOT_TOKEN environment variable not set")
        
        for user_data in users:
            user_id = user_data["user_id"]
            chat_id = user_data["telegram_chat_id"]
            preferences = user_data["preferences"]
            run_metrics['users_checked'] += 1
            
            logger.info(f"Checking conditions for user {user_id} ({len(user_data['stations'])} stations)")
            
            # Check each station for this user (in priority order)
            for station_config in user_data["stations"]:
                station_id = station_config["station_id"]
                station_detail = {
                    'user_id': user_id,
                    'station_id': station_id,
                    'station_name': station_config.get('station_name', station_id),
                    'enabled': station_config["station_enabled"],
                    'priority': station_config.get('priority', 0),
                    'has_data': False,
                    'api_error': None,
                    'conditions_result': None,
                    'cooldown_active': False,
                    'notification_sent': False,
                    'notification_error': None,
                    'latest_weather_data': None
                }
                
                if not station_config["station_enabled"]:
                    run_metrics['stations_disabled'] += 1
                    logger.info(f"Skipping disabled station {station_id} for user {user_id}")
                    run_metrics['station_details'].append(station_detail)
                    continue
                
                run_metrics['stations_checked'] += 1
                
                # Get weather data for this station
                try:
                    station_data = get_station_weather_data(station_config)
                except Exception as e:
                    run_metrics['api_errors'] += 1
                    station_detail['api_error'] = str(e)
                    logger.warning(f"API error for station {station_id}: {e}")
                    run_metrics['station_details'].append(station_detail)
                    continue
                
                if station_data is None or len(station_data) == 0:
                    logger.warning(f"No weather data available for station {station_id}")
                    run_metrics['station_details'].append(station_detail)
                    continue
                
                station_detail['has_data'] = True
                run_metrics['stations_with_data'] += 1
                
                # Store latest weather data (last 3 readings)
                if len(station_data) > 0:
                    latest_data = station_data.tail(3)
                    station_detail['latest_weather_data'] = {
                        'wind_speeds': latest_data['wind_speed_set_1'].tolist(),
                        'wind_directions': latest_data['wind_direction_set_1'].tolist(),
                        'wind_gusts': latest_data['wind_gust_set_1'].tolist(),
                        'precipitation': latest_data['precip_accum_five_minute_set_1'].tolist(),
                        'timestamps': [dt.isoformat() for dt in latest_data['date_time'].tolist()]
                    }
                
                # Check conditions for this station
                conditions_result = check_station_conditions(station_data, station_config, preferences, winter)
                station_detail['conditions_result'] = {
                    'overall_met': conditions_result['conditions_met'],
                    'checks': conditions_result['checks']
                }
                
                if not conditions_result["conditions_met"]:
                    logger.info(f"Conditions not met for user {user_id}, station {station_id}")
                    run_metrics['station_details'].append(station_detail)
                    continue
                
                run_metrics['conditions_met_count'] += 1
                
                # Check cooldown period for this specific station  
                station_uuid = station_config.get("station_uuid") or station_config.get("id") or station_id
                try:
                    last_notification_time = get_last_notification_time(user_id, station_uuid)
                except Exception as e:
                    run_metrics['database_errors'] += 1
                    logger.warning(f"Database error getting last notification: {e}")
                    run_metrics['station_details'].append(station_detail)
                    continue
                
                time_since_last = datetime.datetime.now(pytz.UTC) - last_notification_time
                cooldown_hours = preferences.get("notification_cooldown_hours", 4)
                
                if time_since_last < datetime.timedelta(hours=cooldown_hours):
                    run_metrics['cooldown_blocks'] += 1
                    station_detail['cooldown_active'] = True
                    station_detail['cooldown_remaining_hours'] = round((datetime.timedelta(hours=cooldown_hours) - time_since_last).total_seconds() / 3600, 1)
                    logger.info(f"Skipping user {user_id}, station {station_id} - cooldown period not met")
                    run_metrics['station_details'].append(station_detail)
                    continue
                
                # Generate and send personalized message
                message = generate_personalized_message(user_data, station_config, station_data, conditions_result)
                
                success = send_telegram_message(chat_id, message, telegram_token)
                
                if success:
                    station_detail['notification_sent'] = True
                    
                    # Log the notification
                    try:
                        station_data_dict = station_data.tail(preferences.get("message_rows", 6)).to_dict('records')
                        log_notification(user_id, station_uuid, message, conditions_result, station_data_dict)
                    except Exception as e:
                        run_metrics['database_errors'] += 1
                        logger.warning(f"Failed to log notification: {e}")
                    
                    run_metrics['notifications_sent'] += 1
                    logger.info(f"Notification sent to user {user_id} for station {station_id}")
                    
                    run_metrics['station_details'].append(station_detail)
                    
                    # Only send one notification per user per run (highest priority station wins)
                    break
                else:
                    run_metrics['notification_failures'] += 1
                    station_detail['notification_error'] = "Failed to send Telegram message"
                    logger.error(f"Failed to send notification to user {user_id} for station {station_id}")
                
                run_metrics['station_details'].append(station_detail)
        
        # Calculate final metrics
        run_metrics['runtime_seconds'] = round(time.time() - start_time, 2)
        run_metrics['end_time'] = datetime.datetime.now(pytz.UTC).isoformat()
        
        result_message = f'Multi-station Lambda executed successfully. {run_metrics["notifications_sent"]} notifications sent from {run_metrics["stations_checked"]} station checks across {run_metrics["users_checked"]} users in {run_metrics["runtime_seconds"]}s.'
        logger.info(result_message)
        
        # Log metrics to Supabase
        log_run_metrics(run_metrics)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': result_message,
                'notifications_sent': run_metrics['notifications_sent'],
                'total_users_checked': run_metrics['users_checked'],
                'total_stations_checked': run_metrics['stations_checked'],
                'runtime_seconds': run_metrics['runtime_seconds'],
                'winter_mode': winter
            })
        }
        
    except Exception as e:
        run_metrics['runtime_seconds'] = round(time.time() - start_time, 2)
        run_metrics['end_time'] = datetime.datetime.now(pytz.UTC).isoformat()
        run_metrics['success'] = False
        run_metrics['error_message'] = str(e)
        
        error_message = f"Lambda execution failed: {e}"
        logger.error(error_message)
        
        # Log failed run metrics
        log_run_metrics(run_metrics)
        
        # Try to send error notification to admin
        admin_chat_id = os.getenv("ADMIN_TELEGRAM_CHAT_ID")
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        
        if admin_chat_id and telegram_token:
            admin_error_message = f"🚨 SoarBot Multi-Station Lambda Error: {str(e)}"
            send_telegram_message(admin_chat_id, admin_error_message, telegram_token)
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

# For testing locally
if __name__ == "__main__":
    # Load environment variables for local testing
    from dotenv import load_dotenv
    load_dotenv()
    
    result = lambda_handler({}, {})
    print(json.dumps(result, indent=2))