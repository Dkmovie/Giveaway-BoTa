import contextlib
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup as Markup,
    InlineKeyboardButton as Button,
    CallbackQuery,
)
import pytz
from bot.config import Config
from bot.database import user_db, admin_db, giveaway_db
from bot.plugins.filters import make_m
from bot.utils import get_user_text, utc_to_ist
from bot.plugins.filters import admin_filter


@Client.on_message(filters.command("dashboard"))
@admin_filter
async def dashboard(app, message: Message):
    total_users = await user_db.total_users_count()
    total_banned = await user_db.total_banned_users_count()
    total_admins = await admin_db.get_admin_count()
    total_giveaways = await giveaway_db.get_giveaway_count()

    await message.reply_text(
        f"Total Users: {total_users}\n"
        f"Total Banned Users: {total_banned}\n"
        f"Total Admins: {total_admins}\n"
        f"Total Giveaways: {total_giveaways}\n\n"
        f"Admin Commands\n"
        f"/ban - Ban a user from the bot\n"
        f"/unban - Unban a user from the bot\n"
        f"/addadmin - Add a user as admin\n"
        f"/removeadmin - Remove a user from admin\n"
        f"/create_giveaway - Create a giveaway\n"
        f"/giveaway - The info of the giveaway\n"
        f"/delete_giveaway - Cancel a giveaway\n"
        f"/users - The list of users in bot database\n"
        f"/user - The info of a user\n"
        f"/giveaways - The list of giveaways in bot database\n"
        f"/set_config - The bot config\n"
        f"/banlist - The list of banned users\n"
        f"/adminlist - The list of admins\n",
    )


@Client.on_message(filters.command("ban") & filters.private)
@Client.on_callback_query(filters.regex("^ban#"))
@admin_filter
async def ban(app, message: Message):

    if isinstance(message, CallbackQuery):
        user_id = message.data.split("#")[1]
        message = message.message
        message.command = ["ban", user_id]

    if len(message.command) < 2:
        ban_text = "Please give me the user id of the user you want to ban., example: /ban 1234567890 reason"
        await message.reply_text(ban_text)
        return

    user_id = message.command[1]
    if not user_id.isnumeric():
        await message.reply_text("The user id you gave me is not a number.")
        return

    user_id = int(user_id)
    if user_id == message.from_user.id:
        await message.reply_text("You are not allowed to ban yourself.")
        return

    reason = " ".join(message.command[2:]) or "No reason given"

    await user_db.update_user(
        user_id, {"ban_status.is_banned": True, "ban_status.reason": reason}
    )
    await message.reply_text(
        f"User {user_id} has been banned from the bot for the following reason: {reason}"
    )

    await app.send_message(
        user_id, f"You have been banned from the bot for the following reason: {reason}"
    )


@Client.on_message(filters.command("unban"))
@Client.on_callback_query(filters.regex("^unban"))
@admin_filter
async def unban(app, message: Message):

    if isinstance(message, CallbackQuery):
        user_id = message.data.split("#")[1]
        message = message.message
        message.command = ["unban", user_id]

    if len(message.command) < 2:
        await message.reply_text(
            "Please give me the user id of the user you want to unban., example: /unban 1234567890"
        )
        return

    user_id = message.command[1]
    if not user_id.isnumeric():
        await message.reply_text("The user id you gave me is not a number.")
        return

    user_id = int(user_id)
    if user_id == message.from_user.id:
        await message.reply_text("You are not allowed to unban yourself.")
        return

    await user_db.update_user(
        user_id, {"ban_status.is_banned": False, "ban_status.reason": ""}
    )
    await message.reply_text(f"User {user_id} has been unbanned from the bot.")

    await app.send_message(user_id, "You have been unbanned from the bot.")


@Client.on_message(filters.command("banlist"))
@admin_filter
async def banlist(app, message: Message):
    banlist = await user_db.get_banlist()
    if not banlist:
        await message.reply_text("There are no banned users in the database.")
        return

    banlist_text = "Here is the list of banned users:\n\n"
    async for user in banlist:
        banlist_text += (
            f"User ID: {user['user_id']}\nReason: {user['ban_status']['reason']}\n\n"
        )

        if len(banlist_text) > 4096:
            await message.reply_text(banlist_text)
            banlist_text = ""

    await message.reply_text(banlist_text)


@Client.on_message(filters.command("totalusers"))
@make_m
@admin_filter
async def totalusers(app, message: Message):
    total_users = await user_db.total_users_count()
    await message.reply_text(f"There are {total_users} users in the database.")


@Client.on_message(filters.command("totalbanned"))
@make_m
@admin_filter
async def totalbanned(app, message: Message):
    total_banned = await user_db.total_banned_users_count()
    await message.reply_text(f"There are {total_banned} banned users in the database.")


@Client.on_message(filters.command("totaladmins"))
@admin_filter
async def totaladmins(app, message: Message):
    total_admins = await admin_db.get_admin_count()
    await message.reply_text(f"There are {total_admins} admins in the database.")


@Client.on_message(
    filters.command("addadmin") & filters.private & filters.user(
        Config.OWNER_ID)
)
async def addadmin(app, message: Message):
    if len(message.command) < 2:
        await message.reply_text(
            "Please give me the user id of the user you want to add as admin., example: /addadmin 1234567890"
        )
        return

    user_id = message.command[1]
    if not user_id.isnumeric():
        await message.reply_text("The user id you gave me is not a number.")
        return

    if await admin_db.is_admin(user_id):
        await message.reply_text("This user is already an admin.")
        return

    await admin_db.add_admin(user_id)
    await message.reply_text(f"User {user_id} has been added as an admin.")

    await app.send_message(user_id, "You have been added as an admin.")


@Client.on_message(filters.command("removeadmin") & filters.user(Config.OWNER_ID))
async def removeadmin(app, message: Message):
    if len(message.command) < 2:
        await message.reply_text(
            "Please give me the user id of the user you want to remove as admin., example: /removeadmin 1234567890"
        )
        return

    user_id = message.command[1]
    if not user_id.isnumeric():
        await message.reply_text("The user id you gave me is not a number.")
        return

    user_id = int(user_id)
    if user_id == message.from_user.id:
        await message.reply_text("You are not allowed to remove yourself as an admin.")
        return

    if not await admin_db.is_admin(user_id):
        await message.reply_text("This user is not an admin.")
        return

    await admin_db.remove_admin(user_id)
    await message.reply_text(f"User {user_id} has been removed as an admin.")

    await app.send_message(user_id, "You have been removed as an admin.")


@Client.on_message(filters.command("adminlist") & filters.private)
@admin_filter
async def adminlist(app, message: Message):
    adminlist = await admin_db.get_admins()
    if not adminlist:
        await message.reply_text("There are no admins in the database.")
        return

    adminlist_text = "Here is the list of admins:\n\n"
    for admin in adminlist:
        tg_admin = await app.get_users(admin["user_id"])
        adminlist_text += f"- {admin['user_id']} - {tg_admin.mention}\n"

        if len(adminlist_text) > 4096:
            await message.reply_text(adminlist_text)
            adminlist_text = ""

    await message.reply_text(adminlist_text)


@Client.on_message(filters.command("create_giveaway") & filters.private)
@make_m
@admin_filter
async def create_giveaway_cmd(app, message: Message):
    text = "Let's create a giveaway."
    await message.reply_text(
        text,
        reply_markup=Markup(
            [[Button("Start", "create_giveaway")],
             [Button("Cancel", "cancel")]]
        ),
    )


# see a list of all the giveaways
@Client.on_message(filters.command("giveaways") & filters.private)
@admin_filter
async def giveaways(app, message: CallbackQuery):
    giveaways = await giveaway_db.get_giveaways()
    if not giveaways:
        await message.reply_text("There are no giveaways in the database.")
        return

    giveaways_text = "Here is the list of giveaways:\n\n"
    for giveaway in giveaways:
        giveaways_text += f"Giveaway ID: `{giveaway['giveaway_id']}` - {giveaway['heading']} - Active: {giveaway['published']}\n"

        if len(giveaways_text) > 4096:
            await message.reply_text(giveaways_text)
            giveaways_text = ""

    await message.reply_text(giveaways_text)


# get info about a giveaway
@Client.on_message(filters.command("giveaway") & filters.private)
@admin_filter
async def giveaway(app, message: Message):
    if len(message.command) < 2:
        await message.reply_text(
            "Please give me the giveaway id of the giveaway you want to get info about., example: /giveaway 1234567890"
        )
        return

    giveaway_id = message.command[1]

    giveaway = await giveaway_db.get_giveaway(giveaway_id)
    if not giveaway:
        await message.reply_text("There is no giveaway with that id in the database.")
        return

    giveaway['start_time'] = utc_to_ist(giveaway['start_time'])
    giveaway['end_time'] = utc_to_ist(giveaway['end_time'])

    # convert a datetime object to a string

    giveaway_text = f"Giveaway ID: `{giveaway['giveaway_id']}`\n"
    giveaway_text += f"Giveaway Name: `{giveaway['heading']}`\n"
    giveaway_text += f"Giveaway Credits: `{giveaway['credits']}`\n"
    giveaway_text += f"Giveaway Description: `{giveaway['body']}`\n"
    giveaway_text += f"Giveaway Winner Count: `{len(giveaway['winners'])}`\n"
    giveaway_text += f"Giveaway Winner IDs: `{','.join(str(p) for p in giveaway['winners']) or None}`\n"
    giveaway_text += f"Giveaway Winner Allowed: `{giveaway['total_winners']}`\n"
    giveaway_text += (
        f"Giveaway Total Participants Allowed: `{giveaway['total_participants']}`\n"
    )
    giveaway_text += f"Giveaway Participants: {','.join(str(p) for p in giveaway['participants']) or None}\n"
    giveaway_text += (
        f"Giveaway Participants Joined: `{len(giveaway['participants'])}`\n"
    )
    giveaway_text += (
        f"Giveaway Created At: `{giveaway['start_time'].strftime('%d/%m/%Y %H:%M:%S')}`\n"
    )
    giveaway_text += (
        f"Giveaway Ends At: `{giveaway['end_time'].strftime('%d/%m/%Y %H:%M:%S')}`\n"
    )
    giveaway_text += f"Giveaway Button Text: `{giveaway['button_text']}`\n"
    buttons = []
    ist = pytz.timezone("Asia/Kolkata")

    if giveaway["end_time"] > datetime.now(ist):
        if giveaway["published"]:
            giveaway_text += f"Giveaway Status: `Published`\n"
            buttons.extend(
                (
                    [
                        Button("📣 Share", switch_inline_query=giveaway_id),
                    ],
                    [
                        Button(
                            "🎉 Raffle", callback_data=f"raffle_{giveaway_id}"
                        )
                    ],
                )
            )
        else:
            giveaway_text += f"Giveaway Status: `Not Published`\n"
            buttons.append(
                [Button(
                    "Publish", callback_data=f"start_giveaway_{giveaway_id}")]
            )

        buttons.append(
            [
                Button(
                    "❌ Cancel", callback_data=f"cancel_giveaway_{giveaway_id}"),
            ]
        )

    else:
        giveaway_text += f"Giveaway Status: `Ended`\n"
        buttons.append([
            Button("📣 Share Winners", switch_inline_query=giveaway_id),
        ],)

    markup = Markup(buttons) if buttons else None

    await message.reply_text(giveaway_text, reply_markup=markup)


# delete a giveaway
@Client.on_message(filters.command("delete_giveaway") & filters.private)
@make_m
@admin_filter
async def delete_giveaway(app, message: Message):
    if len(message.command) < 2:
        await message.reply_text(
            "Please give me the giveaway id of the giveaway you want to delete., example: /delete_giveaway 1234567890"
        )
        return

    giveaway_id = message.command[1]

    giveaway = await giveaway_db.get_giveaway(giveaway_id)
    if not giveaway:
        await message.reply_text("There is no giveaway with that id in the database.")
        return

    await giveaway_db.delete_giveaways([giveaway_id])
    await message.reply_text(f"Giveaway {giveaway_id} has been deleted.")

    await app.send_message(
        giveaway["user_id"], f"Your giveaway {giveaway_id} has been deleted."
    )


# see list of users
@Client.on_message(filters.command("users") & filters.private)
@make_m
@admin_filter
async def users(app: Client, message: Message):
    users = await user_db.get_all_users()
    if not users:
        await message.reply_text("There are no users in the database.")
        return

    users_text = "Here is the list of users:\n\n"
    for user in users:
        with contextlib.suppress(Exception):
            tg_user = await app.get_users(user["user_id"])
            users_text += f"- `{user['user_id']}` - {tg_user.mention} - `{user['credits']}`\n"

        if len(users_text) > 4096:
            await message.reply_text(users_text)
            users_text = ""

    await message.reply_text(users_text)


# see a particular user
@Client.on_message(filters.command("user") & filters.private)
@admin_filter
async def user(app, message: Message):
    if len(message.command) < 2:
        await message.reply_text(
            "Please give me the user id of the user you want to get info about., example: /user 1234567890"
        )
        return

    user_id = message.command[1]

    user = await user_db.get_user(int(user_id))
    if not user:
        await message.reply_text("There is no user with that id in the database.")
        return

    buttons = [
        [Button("Edit Credits", f"edit_credits#{user_id}")],
        [Button("Reset Credits to 0", f"reset_credits#{user_id}")],
        [Button("Remove Payment method", f"remove_payment_method#{user_id}")],
        [Button("Ban", f"ban#{user_id}"), Button("Unban", f"unban#{user_id}")],
        [Button("Delete User", f"delete_user#{user_id}")],
    ]

    reply_markup = Markup(
        buttons
    )

    text = await get_user_text(user)
    await message.reply_text(text, reply_markup=reply_markup)

@Client.on_message(filters.command("give_all") & filters.private)
@admin_filter
async def give_all(app, message: Message):
    """Give all users credits"""
    if len(message.command) < 2:
        await message.reply_text(
            "Please give me the credits you want to give to all users., example: /give_all 100"
        )
        return

    credits = message.command[1]
    try:
        credits = int(credits)
    except ValueError:
        await message.reply_text("Credits must be an integer.")
        return

    users = await user_db.get_all_users()
    if not users:
        await message.reply_text("There are no users in the database.")
        return

    # update all users credits at once
    await user_db.update_all_users_credits(credits)
    await message.reply_text(f"Added {credits} credits to all users.")