import logging
import logging.config
import sys

import pyrogram
import pyromod
from aiohttp import web
from pyrogram import Client, errors

from bot.config import Config
from bot.database import bot_db

# Get logging configurations

logging.getLogger().setLevel(logging.INFO)


class Bot(Client):
    def __init__(self):
        super().__init__(
            Config.BOT_USERNAME,
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            plugins=dict(root="bot/plugins"),
        )

    async def start(self):

        await super().start()

        if Config.UPDATE_CHANNEL:
            try:
                self.invite_link = await self.create_chat_invite_link(Config.UPDATE_CHANNEL)
            except Exception as e:

                logging.error(
                    f"Make sure to make the bot in your update channel - {Config.UPDATE_CHANNEL}"
                )
                sys.exit(1)

        me = await self.get_me()
        self.owner = await self.get_users(int(Config.OWNER_ID))
        self.raw_username = me.username
        self.username = f"@{me.username}"
        self.name = me.first_name

        if not await bot_db.db.config.find_one({"_id": "config"}):
            await bot_db.create_bot_config()

        logging.info("Bot started")

        if Config.WEB_SERVER:
            routes = web.RouteTableDef()

            @routes.get("/", allow_head=True)
            async def root_route_handler(request):
                res = {
                    "status": "running",
                }
                return web.json_response(res)

            async def web_server():
                web_app = web.Application(client_max_size=30000000)
                web_app.add_routes(routes)
                return web_app

            app = web.AppRunner(await web_server())
            await app.setup()
            await web.TCPSite(app, "0.0.0.0", 8000).start()

    async def stop(self, *args):
        await super().stop() 
        self.send_message


    async def send_message(*args, **kwargs):
        try:
            return await super().send_message(*args, **kwargs)
        except (errors.UserDeactivated, errors.UserIsBlocked) as e:
            logging.error(e)
            return None