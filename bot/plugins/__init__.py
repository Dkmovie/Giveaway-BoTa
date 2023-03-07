from pyrogram import Client
from bot.database import bot_db, user_db
from pyrogram.raw.types import UpdateChannelParticipant
from pyrogram import ContinuePropagation

@Client.on_raw_update()
async def raw_update_handler(bot, update, user, chat):
    if isinstance(update, UpdateChannelParticipant):
        chat_id = int(f"-100{update.channel_id}")
        user_id = update.user_id
        bot_config = await bot_db.get_bot_config()
        user = await user_db.get_user(user_id)
        chat = await bot.get_chat(chat_id)
        if not user:
            return

        if (
            chat_id == bot_config["backup_channel"]
            and (update.invite or update.new_participant)
            and not user["share_status"]["joined_channels"].get(str(chat_id))
        ):
            await user_db.update_user(user_id, {"credits": 1}, tag="inc")
            await user_db.update_user(user_id, {"share_status": {"joined_channels": {str(chat_id): True}}}, tag="set")
            await bot.send_message(
                chat_id=user_id,
                text=f"Thanks for joining {chat.title}.\n\nYou have been credited with 1 credit.",
            )

        elif (chat_id == bot_config["backup_channel"] and (update.prev_participant)):
            await user_db.update_user(user_id, {"credits": -1}, tag="inc")
            await user_db.update_user(user_id, {"share_status": {"joined_channels": {str(chat_id): False}}}, tag="set")
            await bot.send_message(
                chat_id=user_id,
                text=f"Thanks for leaving {chat.title}.\n\nYou have been debited with 1 credit.",
            )
            
    raise ContinuePropagation