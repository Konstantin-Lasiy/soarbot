import requests
import pandas as pd
import json
import os
import smtplib, ssl
import config
import logging
import astral
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import datetime
from astral.sun import sun
from astral import LocationInfo
from PIL import Image,ImageDraw,ImageFont
import epd7in5_V2

def get_station_data(lookback_minutes = 30):
    request_string = 'https://api.synopticdata.com/v2/stations/timeseries?\
    token={token}&\
    recent={lookback_minutes}&\
    stid=FPS&\
    state=ut&\
    units=english&\
    obtimezone=LOCAL'\
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
    wind_bottom_value = 11
    wind_top_value = 16
    wind_speed_is_acceptable = ((last_3_wind_speeds > wind_bottom_value) &
                                (last_3_wind_speeds < wind_top_value)).all().iloc[0]
    
    last_3_wind_directions = station_data.tail(3)[['wind_direction_set_1']]
    bottom_wind_dir_value = 130
    top_win_dir_value = 180
    wind_dir_is_acceptable = ((last_3_wind_directions > bottom_wind_dir_value) &
                              (last_3_wind_directions < top_win_dir_value)).all().iloc[0]

    print('wind speed: {wind_speed_is_acceptable}'.format(wind_speed_is_acceptable=wind_speed_is_acceptable))
    print('wind direction: {wind_dir_is_acceptable}'.format(wind_dir_is_acceptable=wind_dir_is_acceptable))
    wind_is_acceptable = wind_speed_is_acceptable and wind_dir_is_acceptable
    return wind_is_acceptable


def check_rain(station_data):
    last_3_rain_readings = station_data.tail(3)[['precip_accum_five_minute_set_1']]
    has_rained_recently = (last_3_rain_readings > 0).any().iloc[0]
    return has_rained_recently


def check_for_strong_gusts(station_data):
    last_3_gust_readings = station_data.tail(3)[['wind_gust_set_1']] - station_data.tail(3)[['wind_speed_set_1']]
    gust_limit = 4
    gust_over_limit = (last_3_gust_readings > gust_limit).any().iloc[0]
    return gust_over_limit


def check_daytime():
    current_time = datetime.datetime.now()
    loc = LocationInfo("Salt Lake City", region='UT, USA', timezone='US/Mountain', latitude=40.5247,
                       longitude=-111.8638)
    s = sun(loc.observer, date=current_time, tzinfo='US/Mountain')
    approx_sunrise = (s['sunrise'] - datetime.timedelta(minutes=10)).replace(tzinfo=None)
    approx_sunset = (s['sunset'] - datetime.timedelta(minutes=30)).replace(tzinfo=None)
    if approx_sunrise < current_time < approx_sunset:
        return True
    else:
        return False


def check_all_conditions(station_data):
    wind_is_acceptable = check_wind(station_data)
    is_raining = check_rain(station_data)
    strong_gusts = check_for_strong_gusts(station_data)
    daytime = check_daytime()
    all_conditions_are_right = wind_is_acceptable and not is_raining and not strong_gusts and daytime
    # TODO: Implement better logging of conditions.
    print('wind: {wind}'.format(wind=wind_is_acceptable))
    print('rain: {rain}'.format(rain=is_raining))
    print('gusts: {gusts}'.format(gusts=strong_gusts))
    print('daytime: {daytime}'.format(daytime=check_daytime()))
    print('all_conditions: {all_conditions}'.format(all_conditions=all_conditions_are_right))
    if all_conditions_are_right:
        return True
    else:
        return False

def play_sound():
    command = "omxplayer 'Alarm Alert Effect-SoundBible.com-462520910.mp3' -g 100" 
    os.system(command)



def latest_readings(bot, job):
    station_data = get_station_data()
    message =''
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
        message = "<pre>" #""TIME  |  WIND SPEEDgGUST | WIND DIRECTION \n"
    else:
        message = ""
    for index, row in station_data.tail(rows).iloc[::-1].iterrows():
        message += ('{:%H:%M} | {}{:1.0f}g{:1.0f} | {} \n'.format(
            row['date_time'], " " * 0,
            row['wind_speed_set_1'],
            row['wind_gust_set_1'],
            row['wind_cardinal_direction_set_1d']))
    if html:
        message += '</pre>'
    return message

def draw_station_data(draw, station_data, left, top, right, bottom):
    text = format_message(station_data, rows=20, html=False)
    font18 = ImageFont.truetype('./fonts/mononoki-Regular.ttf', 18)
    draw.text((0, 0), text, font=font18)

def update_image(station_data):
    logging.info('In update_image')
    epd = epd7in5_V2.EPD()
    logging.info('starting init')
    epd.init()
    logging.info('starting Clear')
    epd.Clear()
    logging.info('done with Clear')
    screen_w = epd.width
    screen_h = epd.height
    image = Image.new('1', (screen_h, screen_w), 255)

    logging.info('Drawing calendar')
    draw = ImageDraw.Draw(image)
    draw_station_data(draw, station_data, 0+10, screen_h-10, screen_w-10, 0+10)

    epd.display(epd.getbuffer(image))
    logging.info('Go to sleep')
    epd.sleep()


def callback_minute(context: CallbackContext):
    global last_message_time
    lookback_minutes = 120
    station_data = get_station_data(lookback_minutes)
    all_parameters_met = check_all_conditions(station_data)
    update_image(station_data)
    if all_parameters_met:
        if datetime.datetime.now() - last_message_time > datetime.timedelta(hours=4):
            message = format_message(station_data)
            context.bot.send_message(chat_id='-1001370053492',
                                     text=message,
                                     parse_mode='HTML')
            last_message_time = datetime.datetime.now()



def main():
    global last_message_time
    # TELEGRAM stuff
    updater = Updater(token=config.telegram_token, use_context=True)
    j = updater.job_queue
    last_message_time = datetime.datetime.now() - datetime.timedelta(hours=5)
    job_minute = j.run_repeating(callback_minute, interval=60, first=2)

    updater.start_polling()
    updater.idle()

        
if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    main()
