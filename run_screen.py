import logging
import multiprocessing as mp
import time
from logging.handlers import RotatingFileHandler
from queue import Empty

from configs import epd7in5_V2
from utils.eink_utils import *
from utils.weather_utils import *

absolute_path = os.path.dirname(__file__)


def repeated_job(epd, last_image_update, output):
    lookback_minutes = 120
    station_data = get_station_data(lookback_minutes)
    if len(station_data) == 0:
        app_log.error('station data empty... waiting a minute to retry')
        time.sleep(60)
        return
    if station_data['date_time'].iloc[-1] > last_image_update:
        update_image(epd, station_data)
        last_image_update = station_data['date_time'].iloc[-1]
    # app_log.info('Job ran, going to sleep')
    time.sleep(config.sleep_time)
    # app_log.info('Woke up.')
    output.put(last_image_update)


def main():
    try:
        last_image_update = datetime.datetime.now() - datetime.timedelta(hours=5)
        epd = epd7in5_V2.EPD()
        initiate_screen(epd)
        while True:
            try:
                timeout_length = 120
                output = mp.Queue()
                process = mp.Process(target=repeated_job, args=(epd, last_image_update, output))
                process.start()
                process.join(timeout=timeout_length)
                if process.is_alive():
                    process.terminate()
                    process.join()
                    error_info = f"Timeout error. repeated_job didn't complete in {timeout_length}s"
                    app_log.info(f'{error_info}.')
                try:
                    last_image_update = output.get()
                except Empty:
                    print("Nothing in Queue")
            except Exception as main_loop_exception:
                app_log.info(f'Exception {main_loop_exception} occurred.')

    except KeyboardInterrupt:
        app_log.info("ctrl + c:")
        # epd7in5_V2.epdconfig.module_exit()
        exit()

    except Exception as general_main_exception:
        app_log.info(f'Exception {general_main_exception} occurred')


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
