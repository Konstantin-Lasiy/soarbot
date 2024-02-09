import boto3
import pytz

from configs import config
from utils.weather_utils import *


def send_to_telegram(text, chat_id):
    api_token = config.telegram_token
    chat_id = chat_id
    api_url = f'https://api.telegram.org/bot{api_token}/sendMessage?parse_mode=html'

    try:
        requests.post(api_url, json={'chat_id': chat_id, 'text': text})
    except Exception as e:
        print(e)


def format_message(station_data, rows=6, html=True):
    station_data['wind_cardinal_direction_set_1d'].fillna('-', inplace=True)
    if html:
        message = "<pre>"  # ""TIME  |  WIND SPEEDgGUST | WIND DIRECTION \n"
    else:
        message = "       Speed   Dir \n"
    for index, row in station_data.tail(rows).iloc[::-1].iterrows():
        message += '{:%H:%M} {:>3.0f}g{:<2.0f}   {:<5} \n'.format(
            row['date_time'],
            row["wind_speed_set_1"], row["wind_gust_set_1"],
            row['wind_cardinal_direction_set_1d'])
    if html:
        message += '</pre>'
    return message


def update_last_message_time():
    now_str = datetime.datetime.now(pytz.timezone('America/Denver')).strftime("%m/%d/%Y, %H:%M:%S")
    update_item('soarbot_variables', 'last_message_time', 'value', now_str)


def repeated_job(winter, chat_id, last_message_time):
    lookback_minutes = 120
    time_since_last_message = datetime.datetime.now(pytz.timezone('America/Denver')) - last_message_time
    station_data = get_station_data(lookback_minutes)
    if len(station_data) == 0:
        # app_log.error('station data empty... waiting a minute to retry')
        return
    all_parameters_met = check_all_conditions(station_data, winter)
    if all_parameters_met and time_since_last_message > datetime.timedelta(hours=4):
        message = format_message(station_data)
        send_to_telegram(chat_id=chat_id,
                         text=message)
        update_last_message_time()


def get_last_message_time() -> datetime.date:
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('soarbot_variables')
    response = table.get_item(
        Key={
            'variable_name': 'last_message_time'
        }
    )
    last_message_time = datetime.datetime.strptime(response['Item']['value'], "%m/%d/%Y, %H:%M:%S")
    last_message_time = last_message_time.replace(tzinfo=pytz.timezone('America/Denver'))
    return last_message_time


def update_item(table_name, key, attribute_name, new_val):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    response = table.update_item(
        Key={
            'variable_name': key
        },
        UpdateExpression='SET #attr = :val',
        ExpressionAttributeNames={
            '#attr': attribute_name
        },
        ExpressionAttributeValues={
            ':val': new_val
        }
    )
    return response['ResponseMetadata']['HTTPStatusCode'] == 200


def lambda_handler(event, context):
    debug = False
    chat_id = config.test_chat_id if debug else config.group_channel_chat_id
    winter = check_winter()
    last_message_time = get_last_message_time()
    try:
        repeated_job(winter, chat_id, last_message_time)
    except Exception as e:
        # app_log.info(f"Exception {e} occurred, trying to send to Telegram.")
        try:
            send_to_telegram(text=f'{e}', chat_id=config.test_chat_id)
        except Exception as e:
            print("couldn't send error to bot")
            # app_log.critical(f'Exception {e} occurred when trying to send error to bot')

    return {
        'statusCode': 200,
        'body': json.dumps('Success!')
    }
