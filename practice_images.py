#Import required libraries

import json

import pandas as pd
import requests
from PIL import Image, ImageDraw, ImageFont

import config

screen_h = 800
screen_w = 480


def format_message(station_data, rows=6, html=True):
    if html:
        message = "<pre>"  # ""TIME  |  WIND SPEEDgGUST | WIND DIRECTION \n"
    else:
        message = "       Speed   Dir \n"
    for index, row in station_data.tail(rows).iloc[::-1].iterrows():
        #wind_combo = f'{row["wind_speed_set_1"]:1.0f}g{row["wind_gust_set_1"]:1.0f}'
        message += '{:%H:%M} {:>3.0f}g{:<2.0f}   {:<5} \n'.format(
            row['date_time'], 
            row["wind_speed_set_1"],row["wind_gust_set_1"],
            row['wind_cardinal_direction_set_1d'])
    if html:
        message += '</pre>'
    return message


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


def draw_station_data(draw, station_data, left, top, right, bottom):
    text = format_message(station_data, rows=10, html=False)
    font18 = ImageFont.truetype('./fonts/mononoki-Regular.ttf', 20)
    draw.text((left, top), text, font=font18)

station_data = get_station_data(60)



image = Image.new('1', (screen_w, screen_h), 255)

#Create Image object
im2 = Image.open("paraglider-paragliding.bmp")
vertical_push = 90
image.paste(im2, (100, 300+vertical_push))

draw = ImageDraw.Draw(image)
draw_station_data(draw, station_data, 140, 20 + vertical_push, screen_w - 10, 0 + 10)
#draw.line((205, 20+ vertical_push) + (205,260+ vertical_push), fill='black') # left vertical
#draw.line((290, 20+ vertical_push) + (290,260+ vertical_push), fill='black') # right v
draw.line((139, 42+ vertical_push, 339, 42+ vertical_push), fill='black', width=3) # horizontal

#Show image
image.show()
