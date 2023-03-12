import random
import string
from bot.config import Config
from motor.motor_asyncio import AsyncIOMotorClient


class User:
    """ 
    This class is a wrapper for the MongoDB database, and it provides a few helper methods for interacting with the database.
    The first thing we do is create a new MongoDB client. This client is what we'll use to interact with the database
    """

    def __init__(self, uri, database_name):
        self._client = AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.users = self.db["users"]

    # generate a referral link using user id

    def generate_referral_link(self, user_id):
        """
        It generates a random string of 10 characters.

        :param user_id: The user's ID
        :return: A string of 10 random characters
        """
        return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

    def add_user(self, user_id, reffered_by=None, credits=0):
        """
        It adds a user to the database

        :param user_id: The user's Telegram ID
        :param reffered_by: The user who referred this user
        :param credits: The amount of credits the user has, defaults to 0 (optional)
        :return: A dictionary with the following keys:
            user_id: The user_id of the user
            ban_status: A dictionary with the following keys:
                is_banned: A boolean value that indicates whether the user is banned or not
                reason: A string that indicates the reason for the ban
                ban_time: A datetime object that indicates the time the
        """
        return {
            "user_id": user_id,
            "ban_status": {"is_banned": False, "reason": None, "ban_time": None},
            "warn_status": {"warn_count": 0, "warn_limit": 3, "warn_time": None},
            "payment": {
                "payment_method": None,
                "payment_address": None,
            },
            "credits": credits,
            "referral": {
                "channel_ref_link": None,
                "referred_users": [],
                "referred_by": reffered_by,
                "referral_code": self.generate_referral_link(user_id),
            },
            "share_status": {
                "shared_to_contacts": {}, # users who shared the bot to a contact
                "shared_to_groups": {}, # users who shared the bot to a group
                "users_joined": [], # users who joined the channel using the user's unique link
                "joined_channels": {},  # {channel_id: bool} channels the user has joined
            },
        }

    async def add_new_user(self, user_id, reffered_by=None, credits=0):
        """
        > Add a new user to the database

        :param user_id: The user's ID
        :param reffered_by: The user id of who referred the new user
        :param credits: the amount of credits the user has, defaults to 0 (optional)
        :return: The user object is being returned.
        """
        user = self.add_user(user_id, reffered_by, credits)
        await self.users.insert_one(user)
        return user

    async def get_user(self, user_id):
        """
        Get user from database

        :param user_id: The user's ID
        :return: A dictionary with the user_id and the user_name
        """
        user_id = int(user_id)
        return await self.users.find_one({"user_id": user_id})

    async def update_user(self, user_id, value, tag="set"):
        """
        It updates the user's data in the database

        :param user_id: The user's ID
        :param value: The value to be updated
        :return: The result of the update operation.
        """
        myquery = {
            "user_id": user_id,
        }
        newvalues = {f"${tag}": value}
        return await self.users.update_one(myquery, newvalues)

    async def filter_users(self):
        """
        > This function returns a cursor to all the documents in the users collection
        :return: A cursor object
        """
        return self.users.find({})

    async def filter_user(self, value):
        return await self.users.find_one(value)
    
    async def total_users_count(self, ):
        """
        It returns the total number of users in the database
        :return: The total number of users in the database.
        """
        return await self.users.count_documents({})

    async def get_all_users(self):
        """
        > This function returns all the users in the database
        :return: A cursor object
        """
        return await self.users.find({}).to_list(None)

    async def delete_user(self, user_id):
        """
        It deletes a user from the database

        :param user_id: The user's ID
        """
        await self.users.delete_one({"user_id": int(user_id)})

    async def is_user_exist(self, id):
        """
        It checks if a user exists in the database.

        :param id: The user's ID
        :return: A boolean value.
        """
        user = await self.users.find_one({"user_id": int(id)})
        return bool(user)
    
    async def get_banlist(self):
        """
        > This function returns a cursor to all the banned users in the database
        :return: A cursor object
        """
        return self.users.find({"ban_status.is_banned": True})
    

    async def total_banned_users_count(self):
        """
        It returns the total number of banned users in the database
        :return: The total number of banned users in the database.
        """
        return await self.users.count_documents({"ban_status.is_banned": True})
    

    async def update_all_users_credits(self, amount):
        """
        It updates the credits of all the users in the database

        :param amount: The amount of credits to be added to all the users
        """
        await self.users.update_many({}, {"$inc": {"credits": amount}})

    async def update_all_users_channel_ref_link(self):
        """
        It updates the channel_ref_link of all the users in the database
        """
        await self.users.update_many({}, {"$set": {"referral.channel_ref_link": None}})
        
user_db = User(Config.DATABASE_URL, Config.DATABASE_NAME)
