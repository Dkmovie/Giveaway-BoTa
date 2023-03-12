from pyrogram import Client
from bot.database import bot_db, user_db, giveaway_db
from pyrogram.raw.types import UpdateChannelParticipant
from pyrogram import ContinuePropagation


@Client.on_raw_update()
async def raw_update_handler(bot: Client, update, user, chat):
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
            await user_db.update_user(user_id, {"credits": 2}, tag="inc")
            await user_db.update_user(user_id, {"share_status.joined_channels":  {str(chat_id): True}}, tag="set")
            await bot.send_message(
                chat_id=user_id,
                text=f"Thanks for joining {chat.title}.\n\nYou have been credited with 2 credits.",
            )

        elif (chat_id == bot_config["backup_channel"] and (update.prev_participant)):
            await user_db.update_user(user_id, {"credits": -2}, tag="inc")
            await user_db.update_user(user_id, {"share_status.joined_channels": {str(chat_id): False}}, tag="set")
            await bot.send_message(
                chat_id=user_id,
                text=f"Thanks for leaving {chat.title}.\n\nYou have been debited with 2 credits.",
            )

        elif (chat_id==bot_config["main_channel"] and (update.prev_participant)):
            main_channel = await bot.get_chat(bot_config["main_channel"])
            ongoin_giveaway = await giveaway_db.active_giveaways_by_user_id(user_id)
            for giveaway in ongoin_giveaway:
                if user_id in giveaway["participants"]:
                    await giveaway_db.update_giveaway(giveaway["giveaway_id"], {"participants": user_id}, tag="pull")

            text = f"You have left the main channel [{main_channel.title}]({main_channel.invite_link}), you have been removed from any active giveaway and you cannot join any future giveaway unless you join back the channel"
            await bot.send_message(chat_id=user_id, text=text)

    raise ContinuePropagation


