import datetime
import logging

from PIL import Image, ImageDraw, ImageFont
from telegram.ext import Updater, CallbackContext

from configs import config, epd7in5_V2


def draw_station_data(draw, number, left, top, right, bottom):
    text = str(number)
    font18 = ImageFont.truetype('./fonts/mononoki-Regular.ttf', 40)
    draw.text((0, 0), text, font=font18)

def update_image(epd, number):
    logging.info('In update_image')
    try:
        epd.init()
    except:
        print('init failed')
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
        epd = context.job.context['epd']
        update_image(epd, number)
        number = number + 1
        last_message_time = datetime.datetime.now()


def main():
    global last_message_time
    global number
    global epd
    # TELEGRAM stuff
    try:
        updater = Updater(token=config.telegram_token, use_context=True)
        j = updater.job_queue
        last_message_time = datetime.datetime.now() - datetime.timedelta(seconds=60)
        number = 1
        epd = epd7in5_V2.EPD()
        logging.info('starting init')
        try:
            epd.init()
        except:
            print('epd.init() failed')
        logging.info('starting Clear')
        try:
            epd.Clear()
        except:
            print("epd.Clear failed")
        logging.info('done with Clear')
        job_minute = j.run_repeating(callback_minute, interval=60, first=2, context={'epd': epd})
        updater.start_polling()
        updater.idle()

    except KeyboardInterrupt:
        logging.info("ctrl + c:")
        epd7in5_V2.epdconfig.module_exit()
        exit()


def main_simple():
    logging.info('In update_image')
    epd = epd7in5_V2.EPD()
    logging.info('starting init')
    try:
        epd.init()
    except:
        print('epd.init() failed')
    logging.info('starting Clear')
    try:
        epd.Clear()
    except:
        print("epd.Clear failed")
    logging.info('done with Clear')
    screen_w = epd.width
    screen_h = epd.height
    for number in range(3):
        image = Image.new('1', (screen_h, screen_w), 255)
        logging.info('Drawing image')
        draw = ImageDraw.Draw(image)
        draw_station_data(draw, number, 0 + 10, screen_h - 10, screen_w - 10, 0 + 10)
        epd.display(epd.getbuffer(image))
        logging.info('Go to sleep')
    epd.sleep()


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    main()
