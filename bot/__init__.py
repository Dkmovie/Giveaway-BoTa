import asyncio
import logging
import logging.config
import sys
from typing import Iterable, List, Union

import pyrogram
import pyromod
from aiohttp import web
from pyrogram import Client, errors, raw, types

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

    async def send_message(self, *args, **kwargs):
        try:
            return await super().send_message(*args, **kwargs)
        except (errors.UserDeactivated, errors.UserIsBlocked) as e:
            logging.error(e)
            self.get_users
            return None

    async def get_users(
        self: "pyrogram.Client",
        user_ids: Union[int, str, Iterable[Union[int, str]]],
        raise_error: bool = True,
        limit: int = 200
    ) -> Union["types.User", List["types.User"]]:
        """Get information about a user.
        You can retrieve up to 200 users at once.

        Parameters:
            user_ids (``int`` | ``str`` | Iterable of ``int`` or ``str``):
                A list of User identifiers (id or username) or a single user id/username.
                For a contact that exists in your Telegram address book you can use his phone number (str).
            raise_error (``bool``, *optional*):
                If ``True``, an error will be raised if a user_id is invalid or not found.
                If ``False``, the function will continue to the next user_id if one is invalid or not found.
            limit (``int``, *optional*):
                The maximum number of users to retrieve per request. Must be a value between 1 and 200.

        Returns:
            :obj:`~pyrogram.types.User` | List of :obj:`~pyrogram.types.User`: In case *user_ids* was not a list,
            a single user is returned, otherwise a list of users is returned.

        Example:
            .. code-block:: python

                # Get information about one user
                await app.get_users("me")

                # Get information about multiple users at once
                await app.get_users([user_id1, user_id2, user_id3])
        """
        is_iterable = not isinstance(user_ids, (int, str))
        user_ids = list(user_ids) if is_iterable else [user_ids]

        users = types.List()
        user_ids_chunks = [user_ids[i:i + limit] for i in range(0, len(user_ids), limit)]

        # Define the `resolve` function with error handling based on the `raise_error` parameter
        async def resolve(user_id):
            try:
                return await self.resolve_peer(user_id)
            except Exception:
                if raise_error:
                    raise
                else:
                    return None

        for chunk in user_ids_chunks:

            chunk_resolved = await asyncio.gather(*[resolve(i) for i in chunk if i is not None])

            # Remove any `None` values from the resolved user_ids list
            chunk_resolved = list(filter(None, chunk_resolved))

            r = await self.invoke(
                raw.functions.users.GetUsers(
                    id=chunk_resolved
                )
            )

            for i in r:
                users.append(types.User._parse(self, i))

        return users if is_iterable else users[0]
