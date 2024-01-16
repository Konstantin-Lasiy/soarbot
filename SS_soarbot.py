import datetime
import io
import json
import logging
import multiprocessing as mp
import os
import sys
import time
from logging.handlers import RotatingFileHandler

import matplotlib.pyplot as plt
import pandas as pd
import requests
from PIL import Image, ImageDraw, ImageFont
from astral import LocationInfo
from astral.sun import sun

import config

try:
    import epd7in5_V2
except Exception as e:
    print("Can't Import epd package")

absolute_path = os.path.dirname(__file__)


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    app_log.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception


def send_to_telegram(text, chat_id):
    api_token = config.telegram_token
    chat_id = chat_id
    api_url = f'https://api.telegram.org/bot{api_token}/sendMessage?parse_mode=html'

    try:
        response = requests.post(api_url, json={'chat_id': chat_id, 'text': text})
        print(response.text)
    except Exception as e:
        print(e)


def get_station_data(lookback_minutes=30):
    request_string = "https://api.synopticdata.com/v2/stations/timeseries?" \
                     "token={token}&" \
                     "recent={lookback_minutes}&" \
                     "stid=FPS&" \
                     "state=ut&" \
                     "units=english&" \
                     "obtimezone=LOCAL" \
        .format(token=config.token,
                lookback_minutes=lookback_minutes)

    page = requests.get(request_string)
    wdata = json.loads(page.text)
    latest_recordings_df = pd.DataFrame(wdata['STATION'][0]['OBSERVATIONS'])
    latest_recordings_df['date_time'] = pd.to_datetime(latest_recordings_df.date_time.str[:-5])
    latest_recordings_df['wind_speed_set_1'] *= 1.15078  # kph to mph
    latest_recordings_df['wind_gust_set_1'] *= 1.15078
    return latest_recordings_df


def check_wind(station_data):
    last_3_wind_speeds = station_data.tail(3)[['wind_speed_set_1']]
    wind_bottom_value = 8.5
    wind_top_value = 16
    wind_speed_is_acceptable = ((last_3_wind_speeds > wind_bottom_value) &
                                (last_3_wind_speeds < wind_top_value)).all().iloc[0]

    last_3_wind_directions = station_data.tail(3)[['wind_direction_set_1']]
    bottom_wind_dir_value = 130
    top_win_dir_value = 180
    wind_dir_is_acceptable = ((last_3_wind_directions > bottom_wind_dir_value) &
                              (last_3_wind_directions < top_win_dir_value)).all().iloc[0]
    wind_is_acceptable = wind_speed_is_acceptable and wind_dir_is_acceptable
    return wind_is_acceptable, wind_dir_is_acceptable, wind_speed_is_acceptable


def check_rain(station_data):
    last_3_rain_readings = station_data.tail(3)[['precip_accum_five_minute_set_1']]
    has_rained_recently = (last_3_rain_readings > 0).any().iloc[0]
    return has_rained_recently


def check_for_strong_gusts(station_data):
    last_3_gust_readings = station_data.tail(3)['wind_gust_set_1'] - station_data.tail(3)['wind_speed_set_1']
    gust_limit = 5
    gust_over_limit = (last_3_gust_readings > gust_limit).any()
    return gust_over_limit


def check_daytime():
    current_time = datetime.datetime.now()
    loc = LocationInfo("Salt Lake City", region='UT, USA', timezone='US/Mountain', latitude=40.5247,
                       longitude=-111.8638)
    s = sun(loc.observer, date=current_time, tzinfo='US/Mountain')
    approx_sunrise = (s['sunrise'] - datetime.timedelta(minutes=10)).replace(tzinfo=None)
    approx_sunset = (s['sunset'] - datetime.timedelta(minutes=30)).replace(tzinfo=None)
    is_daytime = approx_sunrise < current_time < approx_sunset
    return is_daytime


def check_midday():
    """Returns True if it's either over 2 hours after sunrise and over 3 hours before sunset"""
    current_time = datetime.datetime.now()
    loc = LocationInfo("Salt Lake City", region='UT, USA', timezone='US/Mountain', latitude=40.5247,
                       longitude=-111.8638)
    s = sun(loc.observer, date=current_time, tzinfo='US/Mountain')
    two_h_after_sunrise = (s['sunrise'] + datetime.timedelta(hours=2)).replace(tzinfo=None)
    three_h_before_sunset = (s['sunset'] - datetime.timedelta(hours=3)).replace(tzinfo=None)
    is_midday = two_h_after_sunrise < current_time < three_h_before_sunset
    return is_midday


def check_all_conditions(station_data, winter):
    wind_is_acceptable, _, _ = check_wind(station_data)
    is_raining = check_rain(station_data)
    strong_gusts = check_for_strong_gusts(station_data)
    daytime = check_daytime()

    # In the summer midday hours should be ignored. In the winter midday flying is fine
    if not winter:
        midday = check_midday()
    else:
        midday = False
    all_conditions_are_right = wind_is_acceptable and not is_raining and not strong_gusts and daytime and not midday
    # app_log.info('wind: {wind}'.format(wind=wind_is_acceptable)
    # app_log.info('rain: {rain}'.format(rain=is_raining)
    # app_log.info('gusts: {gusts}'.format(gusts=strong_gusts)
    # app_log.info('daytime: {daytime}'.format(daytime=daytime)
    # app_log.info('midday: {midday}'.format(midday=midday)
    # app_log.info('all_conditions: {all_conditions}'.format(all_conditions=all_conditions_are_right)
    return all_conditions_are_right


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


def draw_station_data(draw, station_data, left, top, right, bottom):
    text = format_message(station_data, rows=10, html=False)
    font18 = ImageFont.truetype(os.path.join(absolute_path, './fonts/mononoki-Regular.ttf'), 25)
    draw.text((left, top), text, font=font18)


def draw_status(image, status, x, y):
    if status:
        checkmark = Image.open(os.path.join(absolute_path, "images/ok.bmp"))

        image.paste(checkmark, (x, y))
    else:
        cross = Image.open(os.path.join(absolute_path, "images/cross.bmp"))
        image.paste(cross, (x, y))


def draw_speed_chart(image, station_data, x, y):
    import matplotlib.dates as m_dates
    myFmt = m_dates.DateFormatter('%H:%M')
    plot_data = station_data.set_index('date_time')['wind_speed_set_1'].tail(10)
    plt.rcParams["figure.figsize"] = (3.5, 2)
    fig, ax = plt.subplots(1, 1)
    plt.plot(plot_data)
    ax.xaxis.set_major_formatter(myFmt)
    x_locator = m_dates.MinuteLocator(byminute=[0, 10, 20, 30, 40, 50], interval=1)
    ax.xaxis.set_major_locator(x_locator)
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png')
    im = Image.open(img_buf)
    image.paste(im, (x, y))
    img_buf.close()
    plt.close(fig)


def draw_statuses(draw, image, station_data, y_displacement):
    _, wind_dir_is_acceptable, wind_speed_is_acceptable = check_wind(station_data)
    is_raining = check_rain(station_data)
    strong_gusts = check_for_strong_gusts(station_data)
    font18 = ImageFont.truetype(os.path.join(absolute_path, './fonts/mononoki-Regular.ttf'), 18)
    draw.text((120, 600 + y_displacement), 'SPEED', font=font18)
    draw.text((110, 700 + y_displacement), 'DIRECTION', font=font18)
    draw.text((286, 600 + y_displacement), 'GUSTS', font=font18)
    draw.text((290, 700 + y_displacement), 'RAIN', font=font18)
    draw_status(image, wind_speed_is_acceptable, 120, 620 + y_displacement)
    draw_status(image, wind_dir_is_acceptable, 120, 720 + y_displacement)
    draw_status(image, not strong_gusts, 285, 620 + y_displacement)
    draw_status(image, not is_raining, 285, 720 + y_displacement)
    line1_x = 230
    line1_y = (600 + y_displacement, 780 + y_displacement)
    draw.line((line1_x, line1_y[0]) + (line1_x, line1_y[1]), fill='black', width=5)  # l
    line2_x = (100, 350)
    line2_y = 685 + y_displacement
    draw.line((line2_x[0], line2_y) + (line2_x[1], line2_y), fill='black', width=5)  # l


def update_image(epd, station_data):
    # app_log.info('In update_image')
    # app_log.info('starting init')
    try:
        epd.init()
        # app_log.info(f'Init done')
    except:
        print('epd.init() failed')
    screen_w = epd.width
    screen_h = epd.height
    image = Image.new('1', (screen_h, screen_w), 255)
    # app_log.info('Drawing image')

    draw = ImageDraw.Draw(image)
    y_displacement = 40
    draw_speed_chart(image, station_data, 56, 310 + y_displacement)

    table_y_position = 26
    draw.rounded_rectangle([100, table_y_position + y_displacement, 371, table_y_position + 295 + y_displacement],
                           radius=0, fill=None, outline='black', width=3)
    draw_statuses(draw, image, station_data, -40)
    draw_station_data(draw, station_data, 110, table_y_position + 2 + y_displacement, screen_w - 10, 0 + 10)
    draw.line((100, table_y_position + 29 + y_displacement, 371, table_y_position + 29 + y_displacement), fill='black',
              width=3)  # horizontal
    epd.display(epd.getbuffer(image))
    # app_log.info(f'Update Image done. Setting epd to sleep')
    epd.sleep()


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
    output.put(last_image_update, last_message_time)
    return last_image_update, last_message_time


def send_start_message():
    send_to_telegram(text='Script started.', chat_id=config.test_chat_id)


def send_error(error):
    send_to_telegram(text=f'{error}', chat_id=config.test_chat_id)


def initiate_screen(epd):
    app_log.info('starting init')
    try:
        epd.init()
    except:
        print('epd.init() failed')
    app_log.info('starting Clear')
    try:
        epd.Clear()
    except:
        print("epd.Clear failed")
    # app_log.info('done with Clear')
    epd.sleep()


def main():
    debug = True
    running_with_image = False
    chat_id = config.test_chat_id if debug else config.group_channel_chat_id
    winter = True
    # TODO replace winter with dates
    try:
        send_start_message()  # TODO: rewrite send_start_message
        last_image_update = last_message_time = datetime.datetime.now() - datetime.timedelta(hours=5)
        # TODO: set the line above to get the last message from Telegram
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
                    send_error(error_info)
            except Exception as e:
                app_log.info(f'Exception {e} occurred, trying to send to Telegram.')
                try:
                    send_error(e)
                except Exception as e:
                    app_log.critical(f'Exception {e} occurred when trying to send error to bot')
                time.sleep(120)

    except KeyboardInterrupt:
        app_log.info("ctrl + c:")
        # epd7in5_V2.epdconfig.module_exit()
        exit()

    except Exception as e:
        app_log.info(f'Exception {e} occurred')
    send_error(e)


if __name__ == "__main__":
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
