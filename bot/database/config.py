import random
import string
from bot.config import Config
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime


class BotDatabase:
    """ 
    This class is a wrapper for the MongoDB database, and it provides a few helper methods for interacting with the database.
    The first thing we do is create a new MongoDB client. This client is what we'll use to interact with the database
    """

    def __init__(self, uri, database_name):
        self._client = AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.config = self.db["config"]

    async def get_bot_config(self):
        return await self.config.find_one({"_id": "config"})

    async def set_bot_config(self, config, tag="set"):
        await self.config.update_one({"_id": "config"}, {f"${tag}": config}, upsert=True)

    async def create_bot_config(self):
        res = {
            "_id": "config",
            "referral_credits": 1,
            "backup_channel": 0,
            "main_channel": 0,
            "message": {
                "start_message": "Hello, {first_name}! Welcome to {bot_name}!",
                "help_message": "This is a help message",
                "about_message": "This is an about message",
                "earn_credits_message": "This is an earn message",
                "referral_message": "This is a referral message",
                "withdraw_message": "This is a withdraw message",
            },
            "min_withdraw_amount": 50,
            "max_withdraw_amount": 50000,
            "payment_methods": [],
        }
        await self.config.insert_one(res)


class InviteLinks:
    def __init__(self, uri, database_name):
        self._client = AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.invite_links = self.db["invite_links"]

    async def create_link(self, link):
        res = {"link": link, "last_joined": datetime.now(), "users": {}}
        await self.invite_links.insert_one(res)

    async def get_link(self, link):
        return await self.invite_links.find_one({"link": link})

    async def get_links(self):
        return await self.invite_links.find().to_list(None)

    async def delete_link(self, link):
        await self.invite_links.delete_one({"link": link})

    async def update_link(self, link, data, tag="set"):
        await self.invite_links.update_one({"link": link}, {f"${tag}": data})


bot_db = BotDatabase(Config.DATABASE_URL, Config.DATABASE_NAME)
invite_links = InviteLinks(Config.DATABASE_URL, Config.DATABASE_NAME)