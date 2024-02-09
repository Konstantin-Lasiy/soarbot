import datetime
import json

import pandas as pd
import requests
from astral import LocationInfo
from astral.sun import sun

from configs import config


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
    current_time = datetime.datetime.now(pytz.timezone('America/Denver'))
    loc = LocationInfo("Salt Lake City", region='UT, USA', timezone='US/Mountain', latitude=40.5247,
                       longitude=-111.8638)
    s = sun(loc.observer, date=current_time, tzinfo='US/Mountain')
    approx_sunrise = (s['sunrise'] - datetime.timedelta(minutes=10)).replace(tzinfo=pytz.timezone('America/Denver'))
    approx_sunset = (s['sunset'] - datetime.timedelta(minutes=30)).replace(tzinfo=pytz.timezone('America/Denver'))
    is_daytime = approx_sunrise < current_time < approx_sunset
    return is_daytime


def check_midday():
    """Returns True if it's either over 2 hours after sunrise and over 3 hours before sunset"""
    current_time = datetime.datetime.now()
    loc = LocationInfo("Salt Lake City", region='UT, USA', timezone='US/Mountain', latitude=40.5247,
                       longitude=-111.8638)
    s = sun(loc.observer, date=current_time, tzinfo='US/Mountain')
    two_h_after_sunrise = (s['sunrise'] + datetime.timedelta(hours=2)).replace(tzinfo=pytz.timezone('America/Denver'))
    three_h_before_sunset = (s['sunset'] - datetime.timedelta(hours=3)).replace(tzinfo=pytz.timezone('America/Denver'))
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
    all_conditions_are_right = (wind_is_acceptable and
                                not is_raining and
                                not strong_gusts and
                                daytime and
                                not midday)
    # send_to_telegram('wind: {wind}'.format(wind=wind_is_acceptable), chat_id=config.test_chat_id)
    # send_to_telegram('rain: {rain}'.format(rain=is_raining), chat_id=config.test_chat_id)
    # send_to_telegram('gusts: {gusts}'.format(gusts=strong_gusts), chat_id=config.test_chat_id)
    # send_to_telegram('daytime: {daytime}'.format(daytime=daytime), chat_id=config.test_chat_id)
    # send_to_telegram('midday: {midday}'.format(midday=midday), chat_id=config.test_chat_id)
    # send_to_telegram('all_conditions: {all_conditions}'.format(all_conditions=all_conditions_are_right),
    # chat_id=config.test_chat_id)
    return all_conditions_are_right


def check_winter() -> bool:
    today = datetime.datetime.today()
    today_day_of_year = today.timetuple().tm_yday
    march_15ish = datetime.date(2023, 3, 15).timetuple().tm_yday
    nov1_ish = datetime.date(2023, 11, 1).timetuple().tm_yday
    winter = (today_day_of_year < march_15ish or today_day_of_year > nov1_ish)
    return winter
