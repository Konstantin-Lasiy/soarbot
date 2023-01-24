import asyncio
import telegram
import config

async def main():
    bot = telegram.Bot(config.telegram_token)
    async with bot:
        await bot.send_message(text='Hi John!', chat_id='-1001802599929')
        
if __name__ == '__main__':
    asyncio.run(main())