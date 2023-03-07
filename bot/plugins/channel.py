import contextlib
from datetime import datetime
from pyrogram import Client, filters, types
from bot.config import Config

from bot.database import invite_links, user_db, bot_db
from bot.plugins.filters import backup_channel_filter, main_channel_filter
from bot.utils import add_new_user, check_spam_for_link


@Client.on_chat_join_request()
@main_channel_filter
async def new_chat_member_main(app: Client, message: types.ChatJoinRequest):

    invite_link = message.invite_link.invite_link
    user_joined = message.from_user.id

    await add_new_user(app, user_joined, message.from_user.mention)

    user_referred = await user_db.filter_user({"referral.channel_ref_link": invite_link})
    bot_config = await bot_db.get_bot_config()
    await message.approve()

    if user_referred:

        is_spam = await check_spam_for_link(invite_link)

        if is_spam:
            await app.send_message(user_referred['user_id'], "Your link have been seemed spaming by our system, so we have revoked your link, create a new link and share it to your friends.")
            await user_db.update_user(user_referred['user_id'], {"referral.channel_ref_link": None}, tag="set")
            await invite_links.delete_link(invite_link)
            await app.revoke_chat_invite_link(chat_id=bot_config["main_channel"], invite_link=invite_link)
            await app.send_message(Config.LOG_CHANNEL, f"**{user_referred['user_id']}**'s link have been revoked due to spamming.")
            return
        
        if user_referred['user_id'] == user_joined:
            return

        if user_joined in user_referred['share_status']['users_joined']:
            return

        await user_db.update_user(user_referred['user_id'], {"share_status.users_joined": user_joined}, tag="push")
        await user_db.update_user(user_referred['user_id'],  {"credits": 1}, tag="inc")
        await user_db.update_user(user_joined, {"credits": 1}, tag="inc")

        await app.send_message(
            chat_id=user_referred['user_id'],
            text=f"**{message.from_user.mention}** joined the main channel using your referral link, so 1 credit have been added to your account.")

        with contextlib.suppress(Exception):
            await app.send_message(
                chat_id=user_joined,
                text="You have joined main channel through a refferal link, so 1 credit have been added to your account.",
            )

        await invite_links.update_link(invite_link, {"last_joined": datetime.now()}, tag="set")
        await invite_links.update_link(invite_link, {"users": {str(user_joined):datetime.now()}}, tag="set")
