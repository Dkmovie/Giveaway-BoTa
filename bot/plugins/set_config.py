import re
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardButton as Button,
    InlineKeyboardMarkup as Markup,
)
from bot.database import bot_db
from bot.plugins.filters import make_m


@Client.on_message(filters.command("set_config"))
@Client.on_callback_query(filters.regex("bot_config"))
@make_m
async def set_config(_: Client, message: Message):
    data = [
        "referral_credits",
        "backup_channel",
        "main_channel",
        "start_message",
        "help_message",
        "earn_credits_message",
        "withdraw_message",
        "min_withdraw_amount",
        "max_withdraw_amount",
        "payment_methods",
        "remove_payment_method",
        "credit_value",
        "hindi_tutorial",
        "english_tutorial",
    ]

    bot_config = await bot_db.get_bot_config()

    text = "Current bot config:\n\n"
    text += f"**Referral credits:** {bot_config['referral_credits']}\n\n"
    text += f"**Backup channel:** {bot_config['backup_channel']}\n\n"
    text += f"**Main channel:** {bot_config['main_channel']}\n\n"
    text += f"**Start message:** {bot_config['message']['start_message']}\n\n"
    text += f"**Help message:** {bot_config['message']['help_message']}\n\n"
    text += f"**About message:** {bot_config['message']['about_message']}\n\n"
    text += (
        f"**Earn credits message:** {bot_config['message']['earn_credits_message']}\n\n"
    )
    text += f"**Referral message:** {bot_config['message']['referral_message']}\n\n"
    text += f"**Withdraw message:** {bot_config['message']['withdraw_message']}\n\n"
    text += f"**Min withdraw amount:** {bot_config['min_withdraw_amount']}\n\n"
    text += f"**Max withdraw amount:** {bot_config['max_withdraw_amount']}\n\n"
    text += (
        f"**Payment methods:** {', '.join(bot_config['payment_methods']) or None}\n\n"
    )
    text += f"**Credit value:** {bot_config['credit_value']} INR\n\n"

    buttons = []
    row = []
    for key in data:
        button = Button(text=key.title().replace("_", " "), callback_data=f"setm_{key}")
        row.append(button)
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    reply_markup = Markup(buttons)

    await message.reply_text(text=text, reply_markup=reply_markup)


@Client.on_callback_query(filters.regex("^setm_start_message"))
async def setm_start(client: Client, message: Message):
    available_keys = ["first_name", "last_name", "username", "mention", "id"]
    if text := await message.message.chat.ask(
        text="Send the new start message\n\nAvailable keys: {first_name}, {last_name}, {username}, {mention}, {id}",
        filters=filters.text,
        timeout=60,
    ):
        text = text.text

        valid_keys = ["first_name", "last_name", "username", "mention", "id"]
        for key in re.findall(r"{(.*?)}", text):
            if key not in valid_keys:
                await message.message.reply_text(
                    "Invalid message, please use the above keys only in brackets."
                )
                return

        await bot_db.set_bot_config({"message.start_message": text})
        await message.message.reply_text("Start message updated")


@Client.on_callback_query(filters.regex("^setm_help_message"))
async def setm_help(client: Client, message: Message):
    if text := await message.message.chat.ask(
        text="Send the new help message",
        filters=filters.text,
        timeout=60,
    ):
        await bot_db.set_bot_config({"message.help_message": text.text})
        await message.message.reply_text("Help message updated")


@Client.on_callback_query(filters.regex("^setm_about_message"))
async def setm_about(client: Client, message: Message):
    if text := await message.message.chat.ask(
        text="Send the new about message",
        filters=filters.text,
        timeout=60,
    ):
        await bot_db.set_bot_config({"message.about_message": text.text})
        await message.message.reply_text("About message updated")


@Client.on_callback_query(filters.regex("^setm_earn_credits_message"))
async def setm_earn_credits(client: Client, message: Message):
    if text := await message.message.chat.ask(
        text="Send the new earn credits message",
        filters=filters.text,
        timeout=60,
    ):
        await bot_db.set_bot_config({"message.earn_credits_message": text.text})
        await message.message.reply_text("Earn credits message updated")


@Client.on_callback_query(filters.regex("^setm_referral_message"))
async def setm_referral(client: Client, message: Message):
    if text := await message.message.chat.ask(
        text="Send the new referral message\n\nAvailable keys: User referral link: {ref_code}\nChannel referral link: {ref_link}",
        filters=filters.text,
        timeout=60,
    ):
        text = text.text
        valid_keys = [
            "ref_link",
            "ref_code",
        ]
        for key in re.findall(r"{(.*?)}", text):
            if key not in valid_keys:
                await message.message.reply_text(
                    "Invalid message, please use the above keys only in brackets."
                )
                return

        await bot_db.set_bot_config({"message.referral_message": text})
        await message.message.reply_text("Referral message updated")


@Client.on_callback_query(filters.regex("^setm_withdraw_message"))
async def setm_withdraw(client: Client, message: Message):
    if text := await message.message.chat.ask(
        text="Send the new withdraw message",
        filters=filters.text,
        timeout=60,
    ):
        await bot_db.set_bot_config({"message.withdraw_message": text.text})
        await message.message.reply_text("Withdraw message updated")


@Client.on_callback_query(filters.regex("^setm_referral_credits"))
async def setm_referral_credits(client: Client, message: Message):
    while True:
        if text := await message.message.chat.ask(
            text="Send the new referral credits",
            filters=filters.text,
            timeout=60,
        ):
            try:
                text = int(text.text)
            except ValueError:
                await message.message.reply_text(
                    "Invalid input, please send a valid number."
                )
                continue
            await bot_db.set_bot_config({"referral_credits": text})
            await message.message.reply_text("Referral credits updated")
            break


@Client.on_callback_query(filters.regex("^setm_backup_channel"))
async def setm_backup_channel(client: Client, message: Message):
    message = message.message
    while True:
        text_ = await message.chat.ask(
            text="Send the new backup channel id",
            filters=filters.text,
            timeout=3600,
        )

        try:
            text = int(text_.text)
        except ValueError:
            await message.reply_text("Invalid input, please send a valid channel id.")
            continue

        try:
            chat = await client.get_chat(text)
        except Exception:
            await message.reply_text(
                "Channel not found, make sure the bot is in the channel."
            )
            continue

        await bot_db.set_bot_config({"backup_channel": text})
        text = f"Backup channel set to {chat.title}"
        await message.reply_text(text)
        break


@Client.on_callback_query(filters.regex("^setm_main_channel"))
async def setm_main_channel(client: Client, message: Message):
    message = message.message

    while True:
        if text_ := await message.chat.ask(
            text="Send the new main channel id",
            filters=filters.text,
            timeout=3660,
        ):
            if text_.text.startswith("/"):
                return await message.reply_text("Cancelled")

            try:
                text = int(text_.text)
            except ValueError:
                await message.reply_text(
                    "Invalid input, please send a valid channel id."
                )
                continue

            try:
                chat = await client.get_chat(text)
                await bot_db.set_bot_config({"main_channel": text})
                text = f"Main channel set to {chat.title}"
                await message.reply_text(text)
                break
            except Exception:
                await message.reply_text(
                    "Channel not found, make sure the bot is in the channel."
                )
                continue


@Client.on_callback_query(filters.regex("^setm_min_withdraw_amount"))
async def setm_min_withdraw_amount(client: Client, message: Message):
    while True:
        if text := await message.message.chat.ask(
            text="Send the new minimum withdraw amount in INR",
            filters=filters.text,
            timeout=60,
        ):
            try:
                text = int(text.text)
                await bot_db.set_bot_config({"min_withdraw_amount": text})
                await message.message.reply_text("Minimum withdraw amount updated")
                break
            except ValueError:
                # A typo.
                await message.message.reply_text(
                    "Invalid input, please send a valid number."
                )
                continue


@Client.on_callback_query(filters.regex("^setm_max_withdraw_amount"))
async def setm_max_withdraw_amount(client: Client, message: Message):
    while True:
        if text := await message.message.chat.ask(
            text="Send the new maximum withdraw amount in INR",
            filters=filters.text,
            timeout=60,
        ):
            try:
                text = int(text.text)
            except ValueError:
                await message.message.reply_text(
                    "Invalid input, please send a valid number."
                )
                continue
            if text <= 0:
                await message.message.reply_text(
                    "Invalid input, please send a valid number."
                )
                continue
            await bot_db.set_bot_config({"max_withdraw_amount": text})
            await message.message.reply_text("Maximum withdraw amount updated")
            break


@Client.on_callback_query(filters.regex("^setm_payment_methods"))
async def payment_methods(client: Client, message: Message):
    while True:
        if text := await message.message.chat.ask(
            text="Send the new payment methods",
            filters=filters.text,
            timeout=60,
        ):
            text = text.text
            try:
                await bot_db.set_bot_config({"payment_methods": text}, tag="push")
            except Exception as e:
                await message.message.reply_text(f"Error: {e}")
            else:
                await message.message.reply_text("Payment methods updated")
            break


@Client.on_callback_query(filters.regex("^setm_remove_payment_method"))
async def remove_payment_method(client: Client, message: Message):
    bt_config = await bot_db.get_bot_config()
    while True:
        if text := await message.message.chat.ask(
            text=f"Send the payment method to remove\n\nCurrent payment methods: {' '.join(bt_config['payment_methods'])}",
            filters=filters.text,
            timeout=60,
        ):
            if not text.text:
                await message.message.reply_text(
                    "Please send a payment method to remove."
                )
                continue

            if text.text not in bt_config["payment_methods"]:
                await message.message.reply_text(
                    "Invalid payment method, please send a valid payment method."
                )
                continue

            await bot_db.set_bot_config({"payment_methods": text.text}, tag="pull")
            await message.message.reply_text("Payment method removed")
            break


@Client.on_callback_query(filters.regex("^setm_credit_value$"))
async def credit_value(client: Client, message):
    while True:
        if text := await message.message.chat.ask(
            text="Send the new credit value in INR",
            filters=filters.text,
            timeout=60,
        ):
            try:
                text = int(text.text)
            except ValueError:
                await message.message.reply_text(
                    "Invalid input, please send a valid number."
                )
                continue
            if text <= 0:
                await message.message.reply_text(
                    "Invalid input, please send a valid number."
                )
                continue
            await bot_db.set_bot_config({"credit_value": text})
            await message.message.reply_text("Credit value updated")
            break

@Client.on_callback_query(filters.regex("^setm_hindi_tutorial$"))
async def setm_hindi_tutorial(client: Client, message):
    while True:
        if text := await message.message.chat.ask(
            text="Send the tutorial video",
            filters=filters.video,
            timeout=3600,
        ):  
            video = text.video.file_id
            try:
                await bot_db.set_bot_config({"hindi_tutorial": video})
            except Exception as e:
                await message.message.reply_text(f"Error: {e}")
                break
            else:
                await message.message.reply_text("Hindi tutorial video updated")
            break


@Client.on_callback_query(filters.regex("^setm_english_tutorial$"))
async def setm_english_tutorial(client: Client, message):
    while True:
        if text := await message.message.chat.ask(
            text="Send the tutorial video",
            filters=filters.video,
            timeout=3600,
        ):  
            video = text.video.file_id
            try:
                await bot_db.set_bot_config({"english_tutorial": video})
            except Exception as e:
                await message.message.reply_text(f"Error: {e}")
                break
            else:
                await message.message.reply_text("English tutorial video updated")
            break