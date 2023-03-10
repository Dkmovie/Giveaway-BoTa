import asyncio
from pyrogram.errors import FloodWait
from bot.config import Config
from bot.database import admin_db, bot_db, user_db
from pyrogram import Client, filters, types


# This is a decorator for filtering out non-admin users
def admin_filter(f):
    async def func(client, message):
        # Get the list of admin users from the database

        is_admins = message.from_user.id in Config.ADMINS or await admin_db.is_admin(message.from_user.id)
        # Check if the user is an admin
        if is_admins:
            # If the user is an admin, execute the function
            await f(client, message)
        else:
            # If the user is not an admin, send a message
            try:
                await message.reply_text("You are not allowed to do this.")
            except FloodWait as e:
                # If the user is spamming, wait for the flood wait to end
                await asyncio.sleep(e.value)
                # And try sending the message again
                await message.reply_text("You are not allowed to do this.")

    # Return the new function
    return func


def check_ban(f):
    async def func(client, message):
        # Get the list of admin users from the database
        user = await user_db.get_user(message.from_user.id)
        is_not_banned = user["ban_status"]["is_banned"] is False if user else True
        # Check if the user is an admin
        if is_not_banned:
            # If the user is an admin, execute the function
            await f(client, message)
        else:
            # If the user is not an admin, send a message
            try:
                await message.reply_text("You are banned from using this bot.")
            except FloodWait as e:
                # If the user is spamming, wait for the flood wait to end
                await asyncio.sleep(e.value)
                # And try sending the message again
                await message.reply_text("You are banned from using this bot.")

    # Return the new function
    return func


def make_m(f):
    async def func(client, message):
        # Get the list of admin users from the database
        if isinstance(message, types.CallbackQuery):
            await message.message.delete()
            from_user = message.from_user
            message = message.message
            message.from_user = from_user

        return await f(client, message)

    # Return the new function
    return func


# This is a decorator for filtering out new members in backup channel
def backup_channel_filter(f):
    async def func(client, message, *args, **kwargs):
        # Get the list of admin users from the database
        bot_config = await bot_db.get_bot_config()
        # Check if the user is an admin
        if message.chat.id == bot_config["backup_channel"]:
            # If the user is an admin, execute the function
            await f(client, message)
    # Return the new function
    return func


def main_channel_filter(f):
    async def func(client, message):
        # Get the list of admin users from the database
        bot_config = await bot_db.get_bot_config()
        # Check if the user is an admin
        if message.chat.id == bot_config["main_channel"]:
            # If the user is an admin, execute the function
            await f(client, message)
    # Return the new function
    return func