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
from PIL import Image, ImageDraw, ImageFont
import epd7in5_V2



def draw_station_data(draw, number, left, top, right, bottom):
    text = str(number)
    font18 = ImageFont.truetype('./fonts/mononoki-Regular.ttf', 40)
    draw.text((0, 0), text, font=font18)

def update_image(number):
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
    logging.info('Drawing image')
    draw = ImageDraw.Draw(image)
    draw_station_data(draw, number, 0+10, screen_h-10, screen_w-10, 0+10)

    epd.display(epd.getbuffer(image))
    logging.info('Go to sleep')
    epd.sleep()


def callback_minute(context: CallbackContext):
        global last_message_time
        global number
        number = number + 1
        update_image(number)
        last_message_time = datetime.datetime.now()


def main():
    global last_message_time
    global number
    # TELEGRAM stuff
    updater = Updater(token=config.telegram_token, use_context=True)
    j = updater.job_queue
    last_message_time = datetime.datetime.now() - datetime.timedelta(seconds=60)
    number = 1
    job_minute = j.run_repeating(callback_minute, interval=60, first=2)
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    main()
