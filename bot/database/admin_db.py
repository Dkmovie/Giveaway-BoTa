import time
from bot.config import Config
from motor.motor_asyncio import AsyncIOMotorClient


class Admin:
    def __init__(self, uri, database_name):
        self._client = AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.admin_db = self.db["admin"]

    async def get_admin(self, user_id: int):
        return await self.admin_db.find_one({"user_id": user_id})

    async def add_admin(self, user_id):
        return await self.admin_db.insert_one({"user_id": int(user_id)})

    async def remove_admin(self, user_id: int):
        return await self.admin_db.delete_one({"user_id": user_id})

    async def get_admins(self):
        return await self.admin_db.find().to_list(None)

    async def get_admin_count(self):
        return await self.admin_db.count_documents({})

    async def is_admin(self, user_id: int):
        return await self.admin_db.find_one({"user_id": user_id}) is not None


class Giveaway:
    def __init__(self, uri, database_name):
        self._client = AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.giveaway_db = self.db["giveaway"]

    async def get_giveaway(self, giveaway_id: int):
        return await self.giveaway_db.find_one({"giveaway_id": giveaway_id})

    async def add_giveaway(
        self,
        giveaway_id: int,
        heading: str,
        body: str,
        total_participants: int,
        total_winners: int,
        credits: int,
        end_time: int,
        message_id: int,
        channel_id: int,
        start_time: int,
        join_channel: bool = False,
        published: bool = False,
        created_at: int = int(time.time()),
        button_text: str = "Join",

    ):
        res = {
            "giveaway_id": giveaway_id,
            "heading": heading,
            "body": body,
            "total_participants": total_participants,
            "total_winners": total_winners,
            "created_at": created_at,
            "credits": credits,
            "start_time": start_time,
            "end_time": end_time,
            "message_id": message_id,
            "channel_id": channel_id,
            "published": published,
            "join_channel": join_channel,
            "participants": [],
            "winners": [],
            "button_text": button_text,
        }
        return await self.giveaway_db.insert_one(res)

    async def update_giveaway(self, giveaway_id: int, data: dict):
        return await self.giveaway_db.update_one({"giveaway_id": giveaway_id}, {"$set": data})

    async def remove_giveaway(self, giveaway_id: int):
        return await self.giveaway_db.delete_one({"giveaway_id": giveaway_id})

    async def get_giveaways(self):
        return await self.giveaway_db.find().to_list(None)

    async def get_giveaway_count(self):
        return await self.giveaway_db.count_documents({})

    async def get_active_giveaways(self):
        return await self.giveaway_db.find({"end_time": {"$gt": int(time.time())}}).to_list(None)

    async def get_active_giveaway_count(self):
        return await self.giveaway_db.count_documents({"end_time": {"$gt": int(time.time())}})

    async def get_inactive_giveaways(self):
        return await self.giveaway_db.find({"end_time": {"$lt": int(time.time())}}).to_list(None)

    async def get_inactive_giveaway_count(self):
        return await self.giveaway_db.count_documents({"end_time": {"$lt": int(time.time())}})

    async def get_ongoing_giveaways(self):
        return await self.giveaway_db.find({"end_time": {"$gt": int(time.time())}, "created_at": {"$lt": int(time.time())}}).to_list(None)

    async def get_ongoing_giveaway_count(self):
        return await self.giveaway_db.count_documents({"end_time": {"$gt": int(time.time())}, "created_at": {"$lt": int(time.time())}})

    async def get_upcoming_giveaways(self):
        return await self.giveaway_db.find({"created_at": {"$gt": int(time.time())}}).to_list(None)

    async def delete_all_giveaways(self):
        return await self.giveaway_db.delete_many({})

    async def delete_giveaways(self, giveaway_ids: list):
        return await self.giveaway_db.delete_many({"giveaway_id": {"$in": giveaway_ids}})

    async def delete_giveaway(self, giveaway_id: int):
        return await self.giveaway_db.delete_one({"giveaway_id": giveaway_id})
    
admin_db = Admin(Config.DATABASE_URL, Config.DATABASE_NAME)
giveaway_db = Giveaway(Config.DATABASE_URL, Config.DATABASE_NAME)
