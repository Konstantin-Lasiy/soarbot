import requests
import time
import pandas as pd
import json
import os
import config
import logging
from logging.handlers import RotatingFileHandler
import telegram
import datetime
from astral.sun import sun
from astral import LocationInfo
from PIL import Image, ImageDraw, ImageFont

import epd7in5_V2


def get_station_data(lookback_minutes=30):
    request_string = 'https://api.synopticdata.com/v2/stations/timeseries?' \
                     'token={token}&' \
                     'recent={lookback_minutes}&' \
                     'stid=FPS&' \
                     'state=ut&' \
                     'units=english&' \
                     'obtimezone=LOCAL' \
        .format(token=config.token,
                lookback_minutes=lookback_minutes)

    page = requests.get(request_string)
    wdata = json.loads(page.text)
    latest_recordings_df = pd.DataFrame(wdata['STATION'][0]['OBSERVATIONS'])
    latest_recordings_df['date_time'] = pd.to_datetime(latest_recordings_df.date_time.str[:-5])
    latest_recordings_df['wind_speed_set_1'] *= 1.15078
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
    return wind_is_acceptable


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
    wind_is_acceptable = check_wind(station_data)
    is_raining = check_rain(station_data)
    strong_gusts = check_for_strong_gusts(station_data)
    daytime = check_daytime()

    # In the summer one needs to include midday times.
    if not winter:
        midday = check_midday()
    else:
        midday = True
    all_conditions_are_right = wind_is_acceptable and not is_raining and not strong_gusts and daytime and not midday
    app_log.info('wind: {wind}'.format(wind=wind_is_acceptable))
    app_log.info('rain: {rain}'.format(rain=is_raining))
    app_log.info('gusts: {gusts}'.format(gusts=strong_gusts))
    app_log.info('daytime: {daytime}'.format(daytime=daytime))
    app_log.info('midday: {midday}'.format(midday=midday))
    app_log.info('all_conditions: {all_conditions}'.format(all_conditions=all_conditions_are_right))
    if all_conditions_are_right:
        return True
    else:
        return False


def play_sound():
    command = "omxplayer 'Alarm Alert Effect-SoundBible.com-462520910.mp3' -g 100"
    os.system(command)


def latest_readings(bot, job):
    station_data = get_station_data()
    message = ''
    order = [5, 2, 4, 1, 3, 0]  # switches the order so that the columns are lined up
    # in the notification preview on iPhone
    for i in order:
        row = station_data.tail(6).iloc[i]
        message += ('{:%H:%M} - {}{:1.1f} {} - {} |||\n'.format(
            row['date_time'], " " * 0,
            row['wind_speed_set_1'], " " * 0,
            row['wind_cardinal_direction_set_1d']))

    message += "TIME  |  WIND SPEED | WIND DIRECTION \n"
    for index, row in station_data.tail(6).iterrows():
        message += ('{:%H:%M} - {}{:1.1f} {} - {} |||\n'.format(
            row['date_time'], " " * 0,
            row['wind_speed_set_1'], " " * 0,
            row['wind_cardinal_direction_set_1d']))
    bot.send_message(chat_id='-1001370053492',
                     text=message)


def format_message(station_data, rows=6, html=True):
    if html:
        message = "<pre>"  # ""TIME  |  WIND SPEEDgGUST | WIND DIRECTION \n"
    else:
        message = "\n"
    for index, row in station_data.tail(rows).iloc[::-1].iterrows():
        message += ('{:%H:%M} | {}{:2.0f}g{:1.0f} | {} \n'.format(
            row['date_time'], " " * 0,
            row['wind_speed_set_1'],
            row['wind_gust_set_1'],
            row['wind_cardinal_direction_set_1d']))
    if html:
        message += '</pre>'
    else:
        message += ''
    return message


def draw_station_data(draw, station_data, left, top, right, bottom):
    text = format_message(station_data, rows=10, html=False)
    font18 = ImageFont.truetype('./fonts/mononoki-Regular.ttf', 22)
    draw.text((left, top), text, font=font18)


def update_image(epd, station_data, good_conditions):
    app_log.info('In update_image')
    app_log.info('starting init')
    try:
        epd.init()
    except:
        print('epd.init() failed')
    screen_w = epd.width
    screen_h = epd.height
    image = Image.new('1', (screen_h, screen_w), 255)
    app_log.info('Drawing image')
    
    draw = ImageDraw.Draw(image)
    draw_station_data(draw, station_data, 120, 40, screen_w - 10, 0 + 10)
    if good_conditions:
        im2 = Image.open("paraglider-paragliding.bmp")
        image.paste(im2, (80, 300))
    epd.display(epd.getbuffer(image))
    app_log.info('Go to sleep')
    epd.sleep()


def repeated_job(bot, epd, winter):
    global last_message_time
    lookback_minutes = 120
    time_since_last_message = datetime.datetime.now() - last_message_time
    station_data = get_station_data(lookback_minutes)
    all_parameters_met = check_all_conditions(station_data, winter)
    update_image(epd, station_data, all_parameters_met)
    if True: #morning
        play_sound()
        #TODO add Alexa push alert
    if all_parameters_met and time_since_last_message > datetime.timedelta(hours=4):
        message = format_message(station_data)
        bot.send_message(chat_id='-1001370053492',
                                 text=message,
                                 parse_mode='HTML')
        last_message_time = datetime.datetime.now()
    time.sleep(config.sleep_time)


def main():
    global last_message_time
    winter = False

    try:
        bot = telegram.Bot(config.telegram_token)

        last_message_time = datetime.datetime.now() - datetime.timedelta(hours=5)
        epd = epd7in5_V2.EPD()
        
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
        app_log.info('done with Clear')
        epd.sleep()
        
        while True:
            repeated_job(bot,epd,winter)

    except KeyboardInterrupt:
        app_log.info("ctrl + c:")
        epd7in5_V2.epdconfig.module_exit()
        exit()


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO,
                        handlers=[
                            logging.FileHandler("std.log"),
                            logging.StreamHandler()])
    log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
    logFile = 'std.log'
    my_handler = RotatingFileHandler(logFile, mode='a', maxBytes=5*1024*1024, 
                                    backupCount=2, encoding=None, delay=False)
    my_handler.setFormatter(log_formatter)
    my_handler.setLevel(logging.INFO)

    app_log = logging.getLogger('root')
    app_log.setLevel(logging.INFO)
    app_log.addHandler(my_handler)

    while True:
        app_log.info("data")

    main()
