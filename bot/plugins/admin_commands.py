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
from bot.utils import cancel_process, get_user_text, utc_to_ist
from bot.plugins.filters import admin_filter


@Client.on_message(filters.command("dashboard"))
@admin_filter
async def dashboard(app, message: Message):
    total_users = await user_db.total_users_count()
    total_banned = await user_db.total_banned_users_count()
    total_admins = await admin_db.get_admin_count()
    total_giveaways = await giveaway_db.get_giveaway_count()

    buttons = {
        "Ban List": "banlist",
        "Admin List": "adminlist",
        "Giveaway List": "list_giveaways",
        "Bot Config": "bot_config",
    }

    buttons = Markup(
        [[Button(text, callback_data=f"{data}")] for text, data in buttons.items()]
    )
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
        f"/user - The info of a user\n",
        reply_markup=buttons,
    )


@Client.on_message(filters.command("ban"))
@admin_filter
async def ban(app, message: Message):

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
@admin_filter
async def unban(app, message: Message):
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
@Client.on_callback_query(filters.regex("banlist"))
@make_m
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
@make_m
@admin_filter
async def totaladmins(app, message: Message):
    total_admins = await admin_db.get_admin_count()
    await message.reply_text(f"There are {total_admins} admins in the database.")


@Client.on_message(
    filters.command("addadmin") & filters.private & filters.user(Config.OWNER_ID)
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
@Client.on_callback_query(filters.regex("adminlist"))
@admin_filter
async def adminlist(app, message: Message):
    adminlist = await admin_db.get_admins()
    if not adminlist:
        await message.reply_text("There are no admins in the database.")
        return

    adminlist_text = "Here is the list of admins:\n\n"
    for admin in adminlist:
        adminlist_text += f"- {admin['user_id']}\n"

        if len(adminlist_text) > 4096:
            await message.reply_text(adminlist_text)
            adminlist_text = ""

    await message.message.reply_text(adminlist_text)


@Client.on_message(filters.command("create_giveaway") & filters.private)
@make_m
@admin_filter
async def create_giveaway_cmd(app, message: Message):
    text = "Let's create a giveaway."
    await message.reply_text(
        text,
        reply_markup=Markup(
            [[Button("Start", "create_giveaway")], [Button("Cancel", "cancel")]]
        ),
    )


# see a list of all the giveaways
@Client.on_message(filters.command("giveaways") & filters.private)
@Client.on_callback_query(filters.regex("list_giveaways"))
@admin_filter
@make_m
async def giveaways(app, message: CallbackQuery):
    giveaways = await giveaway_db.get_giveaways()
    if not giveaways:
        await message.reply_text("There are no giveaways in the database.")
        return

    giveaways_text = "Here is the list of giveaways:\n\n"
    for giveaway in giveaways:
        giveaways_text += f"Giveaway ID: `{giveaway['giveaway_id']}`\n"

        if len(giveaways_text) > 4096:
            await message.reply_text(giveaways_text)
            giveaways_text = ""

    await message.message.reply_text(giveaways_text)


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
                [Button("Publish", callback_data=f"start_giveaway_{giveaway_id}")]
            )

        buttons.append(
            [
                Button("❌ Cancel", callback_data=f"cancel_giveaway_{giveaway_id}"),
            ]
        )

    else:
        giveaway_text += f"Giveaway Status: `Ended`\n"
        buttons.append(                    [
                        Button("📣 Share", switch_inline_query=giveaway_id),
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
async def users(app, message: Message):
    users = await user_db.get_all_users()
    if not users:
        await message.reply_text("There are no users in the database.")
        return

    users_text = "Here is the list of users:\n\n"
    for user in users:
        users_text += f"- `{user['user_id']}`\n"

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

    reply_markup = Markup(
        [
            [Button("Edit Credits", f"edit_credits#{user_id}")],
            [Button("Delete User", f"delete_user#{user_id}")],
        ]
    )

    text = await get_user_text(user)
    await message.reply_text(text, reply_markup=reply_markup)


# edit credits of a user
@Client.on_callback_query(filters.regex("edit_credits"))
@admin_filter
async def edit_credits(app, message):

    user_id = int(message.data.split("#")[1])
    message = message.message
    user = await user_db.get_user(user_id)
    if not user:
        await message.message.reply_text(
            "There is no user with that id in the database."
        )
        return

    while True:
        credits_text = await message.chat.ask(
            "Send the new credits for the user", filters=filters.text, timeout=60
        )

        if not credits_text:
            return await message.reply_text("You didn't reply in time.", quote=True)

        user_credits = credits_text.text

        if await cancel_process(user_credits):
            return await message.reply_text("Cancelled.", quote=True)

        if not user_credits.isnumeric():
            await message.reply_text("Please give me a number.", quote=True)
            continue

        user_credits = int(user_credits)

        break

    await user_db.update_user(user_id, {"credits": user_credits})

    await message.reply_text(f"Updated credits for user {user_id} to {user_credits}.")

    await app.send_message(
        user_id, f"Your credits have been updated to {user_credits} by admin."
    )
