from datetime import datetime, timedelta
import random

import pytz
from bot.config import Config
from bot.database import user_db, invite_links, giveaway_db, admin_db
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


async def get_user_text(user):
    
    ref_code = f"https://t.me/{Config.BOT_USERNAME}?start=ref_{user['referral']['referral_code']}"
    # share_text = f"**Share status**: \n- Shared to contacts: {len(user['share_status']['shared_to_contacts'])}\n- Shared to groups: {len(user['share_status']['shared_to_groups'])}\n- Users joined: {len(user['share_status']['users_joined'])}\n- Joined channels: {len(user['share_status']['joined_channels'])}\n"

    share_text = f"**Share status**: \nUsers Joined through your channel link: {len(user['share_status'].get('users_joined', []))}\n"
    return f"👋 Hey there, here's the information for user **{user['user_id']}**:\n\n💰 **Credits**: {user['credits']}\n\n🚫 **Ban status**: {user['ban_status']['is_banned']}. Reason: {user['ban_status']['reason'] or 'N/A'}. Ban time: {user['ban_status']['ban_time'] or 'N/A'}\n\n💸 **Payment method**: {user['payment']['payment_method'] or 'N/A'}. Payment address: {user['payment']['payment_address'] or 'N/A'}\n\n👥 **Referral program**: \n- Channel referral link: {user['referral']['channel_ref_link'] or 'N/A'}\n- Referred by: {user['referral']['referred_by'] or 'N/A'}\n- Referral code: {ref_code}\n\n{share_text}"


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
    admins = await  admin_db.get_admins()
    for giveaway in giveaways:
        ist = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist)
        
        giveaway['end_time'] =  utc_to_ist(giveaway['end_time'])
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
                for admin in admins:
                    await app.send_message(admin["user_id"], f"Not enough participants, check the giveaway `/giveaway {giveaway['giveaway_id']}`")

            for _ in range(len(participants)):
                winner = random.choice(participants)
                winners.append(winner)
                participants.remove(winner)

            text = "**Winners:**\n"

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


async def get_winner_text(giveaway_id, app):
    giveaway = await giveaway_db.get_giveaway(giveaway_id)
    winners = giveaway["winners"]

    text = f"**{giveaway['heading']}**\n\n{giveaway['body']}\n\n**{giveaway['total_winners']} winners**\n\n**Winners:**\n"

    for winner in winners:
        user = await app.get_users(winner)
        text += f"- {user.mention}\n"
    
    return text