import contextlib
from pyrogram import Client, filters, types
from pyrogram.types import Message, CallbackQuery
from bot.config import Config
from bot.database import user_db, bot_db
from bot.plugins.filters import make_m, check_ban
from bot.utils import add_new_user, get_user_text


@Client.on_message(filters.command("start"))
@Client.on_callback_query(filters.regex("start"))
@make_m
@check_ban
async def start(app: Client, message: Message | types.CallbackQuery):
    user_id = message.from_user.id
    mention = message.from_user.mention
    bot_config = await bot_db.get_bot_config()

    referrer, referral_credit = None, 0

    if message.command and len(message.command) > 1 and message.command[1].startswith("ref"):
        referral_code = message.command[1].split("_")[1]
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

    if isinstance(message, types.CallbackQuery):
        await message.message.delete()
        message = message.message

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
        ],
    ]

    if bot_config["main_channel"]:
        main_channel = await app.get_chat(bot_config["main_channel"])
        main_channel_link = f"https://t.me/{main_channel.username}" if main_channel.username else main_channel.invite_link
        buttons.append([types.InlineKeyboardButton(
            "Go back to main channel", url=main_channel_link)])

    reply_markup = types.InlineKeyboardMarkup(buttons)

    text = bot_config["message"]["start_message"].format(
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        username=message.from_user.username,
        mention=message.from_user.mention,
        id=message.from_user.id,
        bot_name=app.name,
    )
    await message.reply_text(text, reply_markup=reply_markup)


@Client.on_callback_query(filters.regex("help"))
async def help(app: Client, message: CallbackQuery):
    owner = await app.get_users(Config.OWNER_ID)
    text = f"Contact {owner.mention} for help."
    await message.message.reply_text(text)


@Client.on_message(filters.command("about"))
@Client.on_callback_query(filters.regex("about"))
@make_m
async def about(app, message: Message):
    bot_config = await bot_db.get_bot_config()
    text = bot_config["message"]["about_message"].format(
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        username=message.from_user.username,
        mention=message.from_user.mention,
        id=message.from_user.id,
    )

    await message.reply_text(text)


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
    await message.reply_text(await get_user_text(user), reply_markup=types.InlineKeyboardMarkup(reply_back_buttons))
