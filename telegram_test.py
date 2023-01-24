import asyncio
import telegram
import config
import logging 
from logging.handlers import RotatingFileHandler

async def main(dude, bot):
    async with bot:
        await bot.send_message(text=f'Hi {dude}!', chat_id='-1001802599929')
        
if __name__ == '__main__':
    bot = telegram.Bot(config.telegram_token)
    asyncio.run(main('Costa',bot))
    
    log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
    my_handler = RotatingFileHandler('std.log', mode='a', maxBytes=5*1024*1024, 
                                    backupCount=2, encoding=None, delay=False)
    my_handler.setFormatter(log_formatter)
    my_handler.setLevel(logging.INFO)

    app_log = logging.getLogger('root')
    app_log.setLevel(logging.INFO)
    app_log.addHandler(my_handler)

    while True:
        #app_log.info("data")
        logging.info('daytime: hi')
