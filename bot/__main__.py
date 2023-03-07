from bot import Bot

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.utils import peroidic_check

if __name__ == '__main__':
    app = Bot()
    scheduler = AsyncIOScheduler()
    scheduler.start()

    scheduler.add_job(peroidic_check, 'interval', seconds=60, args=[app])

    app.run()