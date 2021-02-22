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
import astral
import datetime
from astral.sun import sun
from astral import LocationInfo


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
    last_3_wind_speeds = station_data.tail(3)[['wind_gust_set_1']]
    wind_bottom_value = 5
    wind_top_value = 16
    wind_speed_is_acceptable = ((last_3_wind_speeds > wind_bottom_value) &
                                (last_3_wind_speeds < wind_top_value)).all().iloc[0]
    
    last_3_wind_directions = station_data.tail(3)[['wind_direction_set_1']]
    bottom_wind_dir_value = 100
    top_win_dir_value = 260
    wind_dir_is_acceptable = ((last_3_wind_directions > bottom_wind_dir_value) &
                              (last_3_wind_directions < top_win_dir_value)).all().iloc[0]
    
    wind_is_acceptable = wind_speed_is_acceptable and wind_dir_is_acceptable
    return wind_is_acceptable, last_3_wind_directions, last_3_wind_speeds


def check_rain(station_data):
    last_3_rain_readings = station_data.tail(3)[['precip_accum_five_minute_set_1']]
    has_rained_recently = (last_3_rain_readings > 0).any().iloc[0]
    return has_rained_recently


def check_for_strong_gusts(station_data):
    last_3_gust_readings = station_data.tail(3)[['wind_gust_set_1']] - station_data.tail(3)[['wind_speed_set_1']]
    gust_limit = 5
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
    print('wind: {wind}'.format(wind=wind_is_acceptable))
    print('rain: {rain}'.format(rain=is_raining))
    print('gusts: {gusts}'.format(gusts=strong_gusts))
    print('daytime: {daytime}'.format(daytime=check_daytime()))
    print('all_conditions: {all_conditions}'.format(all_conditions=all_conditions_are_right))
    if all_conditions_are_right:
        return True
    else:
        return False

def send_message():
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

def format_message(station_data):
    message = "TIME  |  WIND SPEEDgGUST | WIND DIRECTION \n"
    for index, row in station_data.tail(6).iterrows():
        message += ('{:%H:%M} - {}{:1.1f}g{:1.1f} - {} \n'.format(
            row['date_time'], " " * 0,
            row['wind_speed_set_1'],
            row['wind_gust_set_1'],
            row['wind_cardinal_direction_set_1d']))
    return message

def callback_minute(context: CallbackContext):
    lookback_minutes = 30
    station_data = get_station_data(lookback_minutes)
    all_parameters_met = check_all_conditions(station_data)
    if all_parameters_met:
        message = format_message(station_data)
        context.bot.send_message(chat_id='-1001370053492',
                                 text=message)



def main():
    # TELEGRAM stuff
    updater = Updater(token=config.telegram_token, use_context=True)
    j = updater.job_queue

    job_minute = j.run_repeating(callback_minute, interval=60, first=2)

    updater.start_polling()
    updater.idle()
    #
    # lookback_minutes = 30
    # station_data = get_station_data(lookback_minutes)
    # wind_is_acceptable = check_wind(station_data)
    # print('wind: ', "Wind is great!" if wind_is_acceptable else "Wind is bad.")
    # print("TIME  | WIND SPEED | WIND DIRECTION")
    # for index, row in station_data.tail(3).iterrows():
    #     print('{:%H:%M} | {}{:5.1f} {} |  {}'.format(
    #             row['date_time'], " "*2,
    #             row['wind_speed_set_1'], " "*2,
    #             str(row['wind_direction_set_1']) + ' - ' +
    #             row['wind_cardinal_direction_set_1d']))
    #
    # is_raining = check_rain(station_data)
    # print('rain: ', "It's raining" if is_raining else "No rain in the last {min} minutes".format(min=lookback_minutes))
    #
    # strong_gusts = check_for_strong_gusts(station_data)
    # print('gusts:', "Gusts are too strong" if strong_gusts else "Gusts are OK")
    #
    # all_conditions_are_right = wind_is_acceptable and not is_raining and not strong_gusts
    # if all_conditions_are_right:
    #     send_email(station_data)
    #     send_message()
        
if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    main()