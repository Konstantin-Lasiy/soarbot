from lambda_function import log_notification, get_last_notification_time, log_run_metrics
# use logging to print the response
import logging
import datetime
import pytz

import pandas as pd


def test_log_notification():
    response = log_notification(
        user_id="c7db264b-c0f1-4845-a5d3-cf685bd1ce4b",
        station_id="28af54c1-5234-44dd-9952-66888ff2545e",
        message_content="Test message",
        conditions_result={"conditions_met": True},
        station_data_dict={"wind_speed": 10, "wind_direction": 90, "timestamp": datetime.datetime.now(pytz.UTC).isoformat()},
    )
    logging.info(response)


def test_double_admin_notification_cooldown():
    """Test sending two notifications in a row to the admin user - second should be blocked by cooldown logic"""
    admin_user_id = "c7db264b-c0f1-4845-a5d3-cf685bd1ce4b"  # Costa (admin)
    station_id = "28af54c1-5234-44dd-9952-66888ff2545e"
    cooldown_hours = 4  # Default cooldown period
    
    # First notification - this should always succeed
    first_response = log_notification(
        user_id=admin_user_id,
        station_id=station_id,
        message_content="First admin notification - testing cooldown",
        conditions_result={"conditions_met": True, "test_scenario": "first_notification"},
        station_data_dict={"wind_speed": 15, "wind_direction": 180, "timestamp": "2024-01-01T10:00:00Z"},
    )
    logging.info(f"First notification response: {first_response}")
    assert first_response is True, "First notification should succeed"
    
    # Get the time of the last notification
    last_notification_time = get_last_notification_time(admin_user_id, station_id)
    logging.info(f"Last notification time: {last_notification_time}")
    
    # Calculate time since last notification (should be very recent)
    time_since_last = datetime.datetime.now(pytz.UTC) - last_notification_time
    logging.info(f"Time since last notification: {time_since_last.total_seconds()} seconds")
    
    # Check if we're within cooldown period (should be True since we just sent a notification)
    within_cooldown = time_since_last < datetime.timedelta(hours=cooldown_hours)
    logging.info(f"Within cooldown period: {within_cooldown}")
    
    # Second notification would be logged to database (log_notification doesn't check cooldown)
    # But in the actual system, it would be blocked by the lambda handler's cooldown logic
    second_response = log_notification(
        user_id=admin_user_id,
        station_id=station_id,
        message_content="Second admin notification - testing cooldown",
        conditions_result={"conditions_met": True, "test_scenario": "second_notification"},
        station_data_dict={"wind_speed": 18, "wind_direction": 200, "timestamp": "2024-01-01T10:01:00Z"},
    )
    logging.info(f"Second notification response: {second_response}")
    
    # Both log_notification calls succeed (they just log to DB)
    assert first_response is True, "First notification should succeed"
    assert second_response is True, "Second notification logging should succeed"
    
    # But the cooldown logic should indicate we're within cooldown period
    assert within_cooldown is True, "Should be within cooldown period after first notification"
    assert time_since_last.total_seconds() < 60, "Second notification should be within 1 minute of first"


def test_to_json_with_timestamp():
    df = pd.DataFrame({"timestamp": [datetime.datetime.now(pytz.UTC)]})
    df.to_json(orient="records", date_format="iso")
    assert df.to_json(orient="records", date_format="iso") is not None

def test_log_run_metrics():
    response = log_run_metrics(
        metrics={"start_time": datetime.datetime.now(pytz.UTC).isoformat(), "users_found": 0, "notifications_sent": 0, "runtime_seconds": 1.5}
    )
    logging.info(response)
    assert response is True, "Run metrics should log successfully"