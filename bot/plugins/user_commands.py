
from pyrogram import Client, filters, types
from pyrogram.types import CallbackQuery, Message
from bot.config import Config
from bot.database import bot_db, giveaway_db
from bot.database import lb as leaderboard_db
from bot.database import user_db
from bot.plugins.filters import check_ban, make_m
from bot.utils import (add_new_user, get_user_text,
                       leaderboard_rankings_cmd_handler,
                       refferer_command_handler, see_participants_handler)


@Client.on_message(filters.command("start"), group=-1)
@Client.on_callback_query(filters.regex("start"))
@check_ban
async def start(app: Client, message: Message | types.CallbackQuery):
    user_id = message.from_user.id
    mention = message.from_user.mention
    bot_config = await bot_db.get_bot_config()

    referrer, referral_credit = None, 0

    if not isinstance(message, types.CallbackQuery) and message.command and len(message.command) > 1:
        if message.command[1].startswith("ref"):
            await refferer_command_handler(app, message)

        elif message.command[1].startswith("participants_"):
            await add_new_user(app, user_id, mention, referrer, referral_credit)
            await see_participants_handler(app, message)
            return

        elif message.command[1] == "leaderboard_rankings":
            await add_new_user(app, user_id, mention, referrer, referral_credit)
            await leaderboard_rankings_cmd_handler(app, message)
            return

    if isinstance(message, types.CallbackQuery):
        await message.answer()
        func = message.edit_message_text
    else:
        func = message.reply_text

    await add_new_user(app, user_id, mention, referrer, referral_credit)

    buttons = [
        [
            types.InlineKeyboardButton(
                "Earn Credits 💰", callback_data="earn"),
            types.InlineKeyboardButton(
                "Check Balance 💲", callback_data="check_balance"),
        ],
        [
            types.InlineKeyboardButton(
                "Withdraw 🏦", callback_data="withdraw"),
            types.InlineKeyboardButton("Help ℹ️", callback_data="help"),
        ],
        [
            types.InlineKeyboardButton(
                "Account 💻", callback_data="account"),
            # types.InlineKeyboardButton(
            #     "Leaderboard 🏆", callback_data="leaderboard_rankings"),
        ],
    ]

    buttons.append([types.InlineKeyboardButton(
        "Watch Video Tutotrial", callback_data="tutorial")])

    reply_markup = types.InlineKeyboardMarkup(buttons)

    text = bot_config["message"]["start_message"].format(
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        username=message.from_user.username,
        mention=message.from_user.mention,
        id=message.from_user.id,
        bot_name=app.name,
    )

    kwargs = {
        "text": text,
        "reply_markup": reply_markup,
    }
    await func(**kwargs)


@Client.on_callback_query(filters.regex("help"))
async def help(app: Client, message: CallbackQuery):
    text = f"Contact admins for help.\n\n"
    for owner in Config.ADMINS:
        owner = await app.get_users(owner)
        text += f"- {owner.mention}\n"
    await message.message.reply_text(text)


@Client.on_message(filters.command("account"))
@Client.on_callback_query(filters.regex("account"))
@make_m
async def account(app, message: Message):
    user = await user_db.get_user(message.from_user.id)

    if not user:
        await message.reply_text("You have not joined yet.")
        return

    reply_back_buttons = [
        [
            types.InlineKeyboardButton(
                "Back", callback_data="start"),
        ]]
    mention = message.from_user.mention
    await message.reply_text(await get_user_text(user, mention), reply_markup=types.InlineKeyboardMarkup(reply_back_buttons))


@Client.on_callback_query(filters.regex("see_participants"))
async def see_participants(app: Client, message: CallbackQuery):
    _, giveaway_id = message.data.split("#")

    giveaway = await giveaway_db.get_giveaway(giveaway_id)
    if not giveaway:
        await message.answer("Giveaway not found.", show_alert=True)
        return

    if not giveaway["participants"]:
        await message.answer("No participants found.", show_alert=True)
        return

    url = f"https://telegram.me/{app.raw_username}?start=participants_{giveaway_id}"
    await message.answer(url=url)
    return


@Client.on_callback_query(filters.regex("^tutorial$"))
@make_m
async def tutorial(app: Client, message: Message):
    # > (Hindi) (English) > clicking on the button will send the respective video
    buttons = [
        [
            types.InlineKeyboardButton(
                "Hindi", callback_data="tutorial_hindi"),
            types.InlineKeyboardButton(
                "English", callback_data="tutorial_english"),
        ],
        [
            types.InlineKeyboardButton(
                "Back", callback_data="start"),
        ],
    ]
    reply_markup = types.InlineKeyboardMarkup(buttons)
    text = "Choose your language."
    await message.reply_text(text, reply_markup=reply_markup)


@Client.on_callback_query(filters.regex("^tutorial_hindi$"))
@make_m
async def tutorial_hindi(app: Client, message: Message):
    bot_config = await bot_db.get_bot_config()
    video = bot_config["hindi_tutorial"]

    buttons = [
        [
            types.InlineKeyboardButton(
                "Back", callback_data="start"),
        ],
    ]
    reply_markup = types.InlineKeyboardMarkup(buttons)

    if video:
        await message.reply_video(video, reply_markup=reply_markup, caption="Hindi Tutorial")
    else:
        await message.reply_text('No Video Found', reply_markup=reply_markup)


@Client.on_callback_query(filters.regex("^tutorial_english$"))
@make_m
async def tutorial_english(app: Client, message: Message):
    buttons = [
        [
            types.InlineKeyboardButton(
                "Back", callback_data="start"),
        ],
    ]
    bot_config = await bot_db.get_bot_config()
    video = bot_config["english_tutorial"]
    reply_markup = types.InlineKeyboardMarkup(buttons)

    if video:
        await message.reply_video(video, reply_markup=reply_markup, caption="English Tutorial")
    else:
        await message.reply_text('No Video Found', reply_markup=reply_markup)


@Client.on_callback_query(filters.regex("^lb_"))
async def leaderboard_rankings(app: Client, message: CallbackQuery):
    " Get all the leaderboard with inline buttons"
    _, lb_id = message.data.split("_")
    lb = await leaderboard_db.get_leaderboard_by_id(lb_id)
    users: dict = await leaderboard_db.get_users_by_leaderboard(lb_id)
    if not lb:
        await message.answer("Leaderboard not found.", show_alert=True)
        return

    no_of_winners = lb["no_of_winners"]
    if no_of_winners == 0:
        no_of_winners = len(users)
    else:
        users = users[:19]

    # get the middle description
    middle = len(lb["descriptions"]) // 2
    descriptions: list = [lb["descriptions"][middle], lb["descriptions"][-1]]
    text = f"**{lb['title']}**\n\n"

    for desc in descriptions:
        text += f"{desc}\n\n"

    text += f"**No of Winners:** `{no_of_winners}`\n\n"
    text += "**Leaderboard Ranking**\n\n"

    for i, user in enumerate(users):
        tg_user = await app.get_users(user["user_id"])
        # add gold, silver, bronze emoji
        if i == 0:
            text += f"🥇"
        elif i == 1:
            text += f"🥈"
        elif i == 2:
            text += f"🥉"
        else:
            text += f"{i + 1}."

        # bold the winner's name
        if no_of_winners > i:
            tg_user.first_name = f"**{tg_user.first_name}**"

        text += f"{tg_user.id} - {tg_user.first_name} - `{user['credits']}` Credits\n"

    if not users:
        text += f"No users found, be the first one to join the leaderboard by clicking on the button below."

    # earn credits button and back to main menu button
    buttons = [
        [
            types.InlineKeyboardButton(
                "Earn Credits", callback_data="earn"),
        ],
        [
            types.InlineKeyboardButton(
                "Back", callback_data="leaderboard_rankings"),
        ],
    ]

    if message.from_user.id in Config.ADMINS:
        text += "\n\n**Admin Panel**\n"
        text += f"**Leaderboard ID:** `/leaderboard {lb_id}`\n"

    reply_markup = types.InlineKeyboardMarkup(buttons)
    await message.message.edit_text(text, reply_markup=reply_markup)
