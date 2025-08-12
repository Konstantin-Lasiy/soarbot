from lambda_function import log_notification
# use logging to print the response
import logging

def test_log_notification():
    response = log_notification(
        user_id="c7db264b-c0f1-4845-a5d3-cf685bd1ce4b",
        station_id="28af54c1-5234-44dd-9952-66888ff2545e",
        message_content="Test message",
        conditions_result={"conditions_met": True},
        station_data_dict={"wind_speed": 10, "wind_direction": 90},
    )
    logging.info(response)

test_log_notification()