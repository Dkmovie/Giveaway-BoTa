import contextlib
from datetime import datetime, timedelta
import random
from urllib.parse import quote_plus
from pyrogram.types import InlineKeyboardMarkup as Markup, InlineKeyboardButton as Button, User
import pytz
from bot.config import Config
from bot.database import user_db, invite_links, giveaway_db, admin_db, bot_db
from datetime import timezone
from pyrogram import Client


async def add_new_user(c, user_id, mention, referrer=None, credits=0):
    is_user = await user_db.is_user_exist(user_id)
    if not is_user:
        await user_db.add_new_user(user_id, referrer, credits)
        await c.send_message(Config.LOG_CHANNEL, f"#NewUser\n\nUser ID: `{user_id}`\nName: {mention}")


async def cancel_process(text):
    return text in ["cancel", "Cancel", "/cancel", "stop", "Stop", "/stop"]


async def generate_channel_ref_link(app: Client, user_id, channel_id):
    user = await app.get_users(user_id)
    name = user.first_name
    ref_link = await app.create_chat_invite_link(channel_id, name=name, creates_join_request=True)
    await invite_links.create_link(ref_link.invite_link)
    return ref_link


async def revoke_channel_ref_link(app: Client, channel_id, invite_link):
    ref_link = await app.revoke_chat_invite_link(channel_id, invite_link)
    await invite_links.update_link(invite_link, {"link": ref_link.invite_link})
    return ref_link


async def get_user_text(user, mention=None):

    user_id = user["user_id"]
    credits = user["credits"]
    payments = f'{user["payment"]["payment_method"]} - {user["payment"]["payment_address"]}' if user["payment"]["payment_method"] else "Not Set"
    referal_link = user["referral"]["channel_ref_link"]

    try:
        users_joined = len(user["share_status"]["users_joined"])
    except KeyError:
        users_joined = 0

    text = "Hey there! Here is your account details:\n\n"
    text += f"**Name:** {mention}\n" if mention else ""
    text += f"**User ID:** `{user_id}`\n"
    text += f"**Credits:** `{credits}`\n"
    text += f"**Payments:** `{payments}`\n"
    text += f"**Referral Link:** `{referal_link}`\n"
    text += f"**Users Joined:** `{users_joined}`\n"
    return text


async def is_default(text):
    return text in ["default", "Default", "/default", "Default"]


async def check_spam_for_link(link, num_users=50, time_limit=1):
    # Calculate the time threshold for spam detection
    now = datetime.now()
    time_threshold = now - timedelta(hours=time_limit)
    time_threshold_ts = int(time_threshold.timestamp() * 1000)
    # Find the document for the specified link
    user_doc = await invite_links.get_link(link)
    if user_doc:
        last_joined = user_doc["last_joined"]
        last_joined_ts = int(last_joined.timestamp() * 1000)
        if last_joined_ts >= time_threshold_ts:
            # Convert the datetime objects to timestamps and count the number of users who joined within the time limit
            count = 0
            for joined_time in user_doc["users"].values():
                joined_time_ts = int(joined_time.timestamp() * 1000)
                if joined_time_ts >= time_threshold_ts:
                    count += 1
                if count >= num_users:
                    return True
    return False


async def peroidic_check(app):
    giveaways = await giveaway_db.get_giveaways()
    admins = await admin_db.get_admins()
    for giveaway in giveaways:
        ist = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist)

        giveaway['end_time'] = utc_to_ist(giveaway['end_time'])
        giveaway['start_time'] = utc_to_ist(giveaway['start_time'])

        if not giveaway["published"] and giveaway['start_time'] <= now_ist and giveaway['end_time'] >= now_ist:
            await giveaway_db.update_giveaway(giveaway["giveaway_id"], {"published": True})
            for admin in admins:
                await app.send_message(admin["user_id"], f"A giveaway is going to start soon. Please check the giveaway channel, check the giveaway `/giveaway {giveaway['giveaway_id']}`")

        elif giveaway["published"] and giveaway['end_time'] <= now_ist and giveaway['start_time'] <= now_ist:
            for admin in admins:
                await app.send_message(admin["user_id"], f"A giveaway has ended. Please check the giveaway channel, check the giveaway `/giveaway {giveaway['giveaway_id']}`")

            winners = []
            participants = giveaway["participants"]

            if len(participants) < giveaway["total_winners"]:
                await broadcast_owners(app.send_message, text=f"Giveaway `{giveaway['giveaway_id']}` ended and not enough participants")
                await giveaway_db.update_giveaway(giveaway_id=giveaway["giveaway_id"], data={"end_time": datetime.now(ist), "published": False})
                return

            excluded_winners = await giveaway_db.get_5_last_ended_giveaway_winners()
            while len(winners) < giveaway["total_winners"] and len(participants) > 0:
                winner = random.choice(participants)
                if winner not in excluded_winners or len(participants) <= giveaway["total_winners"] - len(winners):
                    winners.append(winner)
                    participants.remove(winner)

            if not winners:
                await broadcast_owners(app.send_message, text=f"Giveaway `{giveaway['giveaway_id']}` ended and no-one won")
                return

            text = "**Winners:**\n"

            share_winner_reply_markup = Markup(
                [[Button("Share Winners", switch_inline_query=giveaway['giveaway_id'])]])
            await broadcast_owners(app.send_message, text=await get_share_winner_text(app, winners), reply_markup=share_winner_reply_markup)

            for winner in winners:
                user = await app.get_users(winner)
                text += f"- {user.mention}\n"
                await app.send_message(
                    chat_id=winner,
                    text=f"Congratulations! You won the giveaway: {giveaway['heading']}.",
                )

            await giveaway_db.update_giveaway(giveaway_id=giveaway["giveaway_id"], data={"end_time": datetime.now(ist), "published": False, "winners": winners})


def utc_to_ist(utc_time):
    utc_time = pytz.utc.localize(utc_time)
    return utc_time.astimezone(pytz.timezone('Asia/Kolkata'))


async def broadcast_owners(func, *args, **kwargs):
    owners = Config.ADMINS
    for owner in owners:
        await func(owner, *args, **kwargs)


async def get_share_winner_text(app, winners):
    text = """🎉 Congratulations to the winner of the giveaway! 🎉

🏆 And the winner is: {}!

Thank you to everyone who participated. Stay tuned for more exciting giveaways and events! 😊"""

    winner_text = ""
    for winner in winners:
        user = await app.get_users(winner)
        winner_text += f"{user.mention}, "

    return text.format(winner_text[:-2])


async def get_giveaway_button(app, giveaway):
    return Markup(
        [
            [
                Button(
                    text=f'{giveaway["button_text"]} - {giveaway["credits"]} Credit', callback_data=f'participate_{giveaway["giveaway_id"]}'
                )
            ],
            [
                Button(
                    text="Earn Credits", url=f"https://t.me/{app.raw_username}?start=earn_credits"
                )
            ],
            [
                Button(
                    text="See Participants", callback_data=f"see_participants#{giveaway['giveaway_id']}"
                )
            ]
        ]
    )


async def see_participants_handler(app, message):
        giveaway_id = message.command[1].split("_", 1)[1]
        giveaway = await giveaway_db.get_giveaway(giveaway_id)
        if not giveaway:
            await message.reply_text("Giveaway not found.")
            return

        text = f"Participants of giveaway\n\n"

        users = await app.get_users(giveaway["participants"])
        for user in users:
            user: User
            text += f"- {user.first_name}, {user.id}\n"

        await message.reply_text(text)
        return


async def refferer_command_handler(app, message):
    user_id = message.from_user.id
    bot_config = await bot_db.get_bot_config()
    referral_code = message.command[1].split("_")[1]
    mention = message.from_user.mention
    refferer = await user_db.filter_user({"referral.referral_code": referral_code})

    if not refferer:
        await message.reply_text("Invalid referral code")
    else:
        if refferer["user_id"] == user_id:
            await message.reply_text("You can't use your own referral code.")
            return

        if await user_db.get_user(user_id):
            await message.reply_text("You have already joined.")
            return

        referrer = refferer["user_id"]

        referral_credit = bot_config["referral_credits"]
        tg_referer = await app.get_users(referrer)

        await message.reply_text(
            f"**{tg_referer.mention}** has given you **{referral_credit}** credits as referral bonus.")

        await app.send_message(referrer, f"**{mention}** has joined using your referral link. You have been credited **{referral_credit}** credits.")

        with contextlib.suppress(Exception):
            await app.get_chat_member(bot_config["backup_channel"], user_id)
            referral_credit += 2

        await user_db.update_user(refferer['user_id'], {"referral.referred_users": user_id})

        await user_db.update_user(refferer['user_id'], {"credits": referral_credit})