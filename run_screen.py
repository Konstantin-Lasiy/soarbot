import logging
import multiprocessing as mp
import time
from logging.handlers import RotatingFileHandler
from queue import Empty

from configs import epd7in5_V2
from utils.eink_utils import *
from utils.weather_utils import *

absolute_path = os.path.dirname(__file__)


def send_to_telegram(text, chat_id):
    api_token = config.telegram_token
    chat_id = chat_id
    api_url = f'https://api.telegram.org/bot{api_token}/sendMessage?parse_mode=html'

    try:
        requests.post(api_url, json={'chat_id': chat_id, 'text': text})
    except Exception as e_send:
        print(e_send)


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


def repeated_job(epd, winter, chat_id, last_message_time, last_image_update, output):
    lookback_minutes = 120
    time_since_last_message = datetime.datetime.now() - last_message_time
    station_data = get_station_data(lookback_minutes)
    if len(station_data) == 0:
        app_log.error('station data empty... waiting a minute to retry')
        time.sleep(60)
        return
    all_parameters_met = check_all_conditions(station_data, winter)
    if station_data['date_time'].iloc[-1] > last_image_update:
        update_image(epd, station_data)
        last_image_update = station_data['date_time'].iloc[-1]

    if all_parameters_met and time_since_last_message > datetime.timedelta(hours=4):
        message = format_message(station_data)
        send_to_telegram(chat_id=chat_id,
                         text=message)
        last_message_time = datetime.datetime.now()
    # app_log.info('Job ran, going to sleep')
    time.sleep(config.sleep_time)
    # app_log.info('Woke up.')
    output.put((last_image_update, last_message_time))


def main():
    debug = True
    running_with_image = False
    chat_id = config.test_chat_id if debug else config.group_channel_chat_id
    winter = True
    try:
        send_to_telegram(text='Script started.', chat_id=config.test_chat_id)
        last_image_update = last_message_time = datetime.datetime.now() - datetime.timedelta(hours=5)
        if running_with_image:
            epd = epd7in5_V2.EPD()
            initiate_screen(epd)
        else:
            epd = False
        while True:
            try:
                timeout_length = 120
                output = mp.Queue()
                process = mp.Process(target=repeated_job, args=(epd, winter, chat_id,
                                                                last_message_time, last_image_update, output))
                process.start()
                process.join(timeout=timeout_length)
                if process.is_alive():
                    process.terminate()
                    process.join()
                    error_info = f"Timeout error. repeated_job didn't complete in {timeout_length}s"
                    app_log.info(f'{error_info}, trying to send to Telegram.')
                    send_to_telegram(text=f'{error_info}', chat_id=config.test_chat_id)
                try:
                    last_message_time, last_image_update = output.get()
                except Empty:
                    print("Nothing in Queue")
            except Exception as main_loop_exception:
                app_log.info(f'Exception {main_loop_exception} occurred, trying to send to Telegram.')
                try:
                    send_to_telegram(text=f'{main_loop_exception}', chat_id=config.test_chat_id)
                except Exception as sending_error_exception:
                    app_log.critical(f'Exception {sending_error_exception} occurred when trying to send error to bot')
                time.sleep(120)

    except KeyboardInterrupt:
        app_log.info("ctrl + c:")
        # epd7in5_V2.epdconfig.module_exit()
        exit()

    except Exception as general_main_exception:
        app_log.info(f'Exception {general_main_exception} occurred')
        send_to_telegram(text=f'{general_main_exception}', chat_id=config.test_chat_id)


if __name__ == "__main__":
    try:
        pass
    except RuntimeError as runtime_error:
        print("Can't Import epd package")
    log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
    logFile = os.path.join(absolute_path, 'std.log')
    my_handler = RotatingFileHandler(logFile, mode='a', maxBytes=5 * 1024 * 1024,
                                     backupCount=2, encoding=None, delay=False)
    my_handler.setFormatter(log_formatter)
    my_handler.setLevel(logging.INFO)
    app_log = logging.getLogger('root')
    app_log.setLevel(logging.INFO)
    app_log.addHandler(my_handler)

    main()
