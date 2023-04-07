from bot.config import Config
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from bson.objectid import ObjectId
import pytz


class Leaderboard:
    def __init__(self, uri, database_name):
        self._client = AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.lb = self.db["leaderboard"]

    async def create_leaderboard(
        self,
        title,
        descriptions: list,
        start_time: datetime,
        end_time: datetime,
        no_of_winners,
        status: bool = False,

    ):
        _id = await self.lb.insert_one(
            {
                "title": title,
                "descriptions": descriptions,
                "start_time": start_time,
                "end_time": end_time,
                "no_of_winners": no_of_winners,
                "status": status,
                "users": []  # {user_id: int, credits: int}
            }
        )
        return _id.inserted_id

    async def delete_leaderboard(self, title):
        return await self.lb.delete_one({"title": title})

    async def get_leaderboard_by_id(self, _id):
        return await self.lb.find_one({"_id": ObjectId(_id)})

    async def update_leaderboard_by_id(self, _id, data):
        return await self.lb.update_one({"_id": ObjectId(_id)}, {"$set": data})

    async def delete_leaderboard_by_id(self, _id):
        return await self.lb.delete_one({"_id": ObjectId(_id)})

    async def confirm_leaderboard(self, _id):
        return await self.lb.update_one({"_id": ObjectId(_id)}, {"$set": {"status": True}})

    async def end_leaderboard(self, _id):
        datetime_now = datetime.utcnow()
        return await self.lb.update_one({"_id": ObjectId(_id)}, {"$set": {"status": False, "end_time": datetime_now}})

    async def get_all_leaderboards(self):
        "sort by status and most recent first"
        result = await self.lb.find({}).sort([("status", -1)]).to_list(None)
        return result

    async def get_users_by_leaderboard(self, _id):
        result = await self.lb.find_one({"_id": ObjectId(_id)}, {"users": 1, "_id": 0})
        users = result["users"]
        users.sort(key=lambda u: u["credits"], reverse=True)
        return users

    async def add_score_to_user(self, user_id, score):
        on_going_lb = await self.lb.find_one({"status": True})
        if on_going_lb:
            _id = on_going_lb["_id"]
            if await self.check_user_in_leaderboard(user_id, _id):
                await self.lb.update_one(
                    {"_id": ObjectId(_id), "users.user_id": user_id},
                    {"$inc": {"users.$.credits": score}}
                )
            else:
                await self.lb.update_one(
                    {"_id": ObjectId(_id)},
                    {"$push": {"users": {"user_id": user_id, "credits": score}}}
                )

    async def check_user_in_leaderboard(self, user_id, _id):
        return await self.lb.find_one({"_id": ObjectId(_id), "users.user_id": user_id})

    async def start_leaderboard(self, _id):
        start_time = datetime.utcnow()

        return await self.lb.update_one({"_id": ObjectId(_id)}, {"$set": {"start_time": start_time, "status": True}})

    async def update_leaderboard(self, _id, data):
        await self.lb.update_one({"_id": ObjectId(_id)}, {"$set": data})


lb = Leaderboard(Config.DATABASE_URL, Config.DATABASE_NAME)
