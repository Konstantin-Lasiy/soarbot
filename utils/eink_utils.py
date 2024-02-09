import os

import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont

absolute_path = os.path.dirname(__file__)


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


def initiate_screen(epd):
    # app_log.info('starting init')
    try:
        epd.init()
    except:
        print('epd.init() failed')
    # app_log.info('starting Clear')
    try:
        epd.Clear()
    except:
        print("epd.Clear failed")
    # app_log.info('done with Clear')
    epd.sleep()
