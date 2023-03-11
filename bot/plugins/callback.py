from datetime import datetime, timedelta
import random
from urllib.parse import quote_plus
from uuid import uuid4
import humanize
from pyrogram import Client, filters, types
import pytz
from pyrogram.errors import UserNotParticipant
from bot.config import Config, Messages
from bot.database import user_db, bot_db as bot_config_db
from bot.plugins.filters import admin_filter
from bot.utils import (
    add_new_user,
    broadcast_owners,
    cancel_process,
    generate_channel_ref_link,
    get_giveaway_button,
    get_share_winner_text,
    is_default,
    revoke_channel_ref_link,
    utc_to_ist,
)
from bot.database.admin_db import giveaway_db
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup as Markup,
    InlineKeyboardButton as Button,
)


@Client.on_callback_query(filters.regex("create_giveaway"))
async def create_giveaway_func(app: Client, message: types.CallbackQuery):
    await message.message.delete()

    message = message.message

    text = await message.chat.ask(
        f"What is the heading of the giveaway? - /default\n{Messages.HEADING}",
        filters=filters.text,
        timeout=3600,
    )

    if not text:
        return await message.reply_text("You didn't reply in time.", quote=True)

    if await cancel_process(text.text):
        return await message.reply_text("Cancelled.", quote=True)

    if len(text.text) > 255:
        return await message.reply_text(
            "The heading should be less than 255 characters.", quote=True
        )

    text = text.text.html

    if await is_default(text):
        text = Messages.HEADING

    description: Message = await message.chat.ask(
        f"What is the description of the giveaway?- /default\n{Messages.BODY}",
        filters=filters.text,
        timeout=3600,
    )

    if not description:
        return await message.reply_text("You didn't reply in time.", quote=True)

    if await cancel_process(description.text):
        return await message.reply_text("Cancelled.", quote=True)

    description = description.text.html

    if await is_default(description):
        description = Messages.BODY

    while True:
        winners = await message.chat.ask(
            "How many winners should there be? /default - 1",
            filters=filters.text,
            timeout=3600,
        )

        if not winners:
            return await message.reply_text("You didn't reply in time.", quote=True)

        winners = winners.text

        if await cancel_process(winners):
            return await message.reply_text("Cancelled.", quote=True)

        if await is_default(winners):
            winners = 1
            break

        if not winners.isnumeric():
            await message.reply_text("Please give me a number.", quote=True)
            continue

        winners = int(winners)

        if winners < 1:
            await message.reply_text(
                "Please give me a number greater than 0.", quote=True
            )
            continue

        break

    while True:
        total_participants = await message.chat.ask(
            "How many participants should there be? /default - 100",
            filters=filters.text,
            timeout=3600,
        )

        if not total_participants:
            return await message.reply_text("You didn't reply in time.", quote=True)

        total_participants = total_participants.text

        if await cancel_process(total_participants):
            return await message.reply_text("Cancelled.", quote=True)

        if await is_default(total_participants):
            total_participants = 100
            break

        if not total_participants.isnumeric():
            await message.reply_text("Please give me a number.", quote=True)
            continue

        total_participants = int(total_participants)

        if total_participants < 1:
            await message.reply_text(
                "Please give me a number greater than 0.", quote=True
            )
            continue

        if total_participants < winners:
            await message.reply_text(
                "The total participants should be greater than the winners.", quote=True
            )
            continue

        break

    while True:
        start_time = await message.chat.ask(
            "When should the giveaway start? (Give me  24 hours format)\nFormat: 12:00 12-02-2022\n/default - 1 hour from now",
            filters=filters.text,
            timeout=3600,
        )

        if not start_time:
            return await message.reply_text("You didn't reply in time.", quote=True)

        start_time = start_time.text

        if await cancel_process(start_time):
            return await message.reply_text("Cancelled.", quote=True)

        ist = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(ist)

        if await is_default(start_time):
            start_time = now_ist + timedelta(hours=1)
            break

        try:
            start_time = datetime.strptime(start_time, "%H:%M %d-%m-%Y")
            start_time = ist.localize(start_time)

            if start_time < now_ist:
                await message.reply_text(
                    "Please give me a time in the future.", quote=True
                )
                continue

        except ValueError:
            await message.reply_text(
                "Please give me the time in the correct format.", quote=True
            )
            continue

        break

    while True:
        duration = await message.chat.ask(
            "When should the giveaway end? (Give me  24 hours format)\n/default - 24 hours from start time",
            filters=filters.text,
            timeout=3600,
        )

        if not duration:
            return await message.reply_text("You didn't reply in time.", quote=True)

        duration = duration.text

        if await cancel_process(duration):
            return await message.reply_text("Cancelled.", quote=True)

        ist = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(ist)

        if await is_default(duration):
            end_time = start_time + timedelta(hours=24)
            break

        try:
            end_time = datetime.strptime(duration, "%H:%M %d-%m-%Y")
            end_time = ist.localize(end_time)

            if end_time < start_time:
                await message.reply_text(
                    "This time is lesser than the start time", quote=True
                )
                continue

        except ValueError:
            await message.reply_text(
                "Please give me the time in the correct format.", quote=True
            )
            continue

        break

    while True:
        credits_required = await message.chat.ask(
            "How many credits should the user have to participate in the giveaway? /default - 1",
            filters=filters.text,
            timeout=3600,
        )

        if not credits_required:
            return await message.reply_text("You didn't reply in time.", quote=True)

        credits_required = credits_required.text

        if await cancel_process(credits_required):
            return await message.reply_text("Cancelled.", quote=True)

        if await is_default(credits_required):
            credits_required = 1
            break

        if not credits_required.isnumeric():
            await message.reply_text("Please give me a number.", quote=True)
            continue

        credits_required = int(credits_required)

        if credits_required < 0:
            await message.reply_text(
                "Please give me a number greater than or equal to 0.", quote=True
            )
            continue

        break

    join_channel = True
    channel_id = (await bot_config_db.get_bot_config())["main_channel"] or None
    if not channel_id:
        join_channel = False

    while True:
        button_text = await message.chat.ask(
            "What should the button text be? /default - Join Giveaway",
            filters=filters.text,
            timeout=3600,
        )

        if not button_text:
            return await message.reply_text("You didn't reply in time.", quote=True)

        button_text = button_text.text

        if await cancel_process(button_text):
            return await message.reply_text("Cancelled.", quote=True)

        if await is_default(button_text):
            button_text = "Join Giveaway"

        break

    giveaway_id = f"giveaway_{str(uuid4())[:8]}"
    await giveaway_db.add_giveaway(
        giveaway_id=giveaway_id,
        heading=text,
        body=description,
        total_winners=winners,
        total_participants=total_participants,
        start_time=start_time,
        end_time=end_time,
        credits=credits_required,
        join_channel=join_channel,
        channel_id=channel_id,
        message_id=message.id,
        button_text=button_text,
    )

    await message.reply_text(
        text="Are you sure you want to create the giveaway?",
        reply_markup=Markup(
            [
                [
                    Button(
                        "Yes", callback_data=f"confirm_giveaway_{giveaway_id}"),
                    Button(
                        "No", callback_data=f"cancel_giveaway_{giveaway_id}"),
                ]
            ]
        ),
    )


@Client.on_callback_query(filters.regex("^confirm_giveaway_"))
async def confirm_giveaway(app, callback_query: types.CallbackQuery):
    giveaway_id = callback_query.data.split("_", 2)[2]
    giveaway = await giveaway_db.get_giveaway(giveaway_id=giveaway_id)

    if not giveaway:
        return await callback_query.answer(
            "This giveaway doesn't exist.", show_alert=True
        )

    await callback_query.answer("Giveaway created successfully.", show_alert=True)

    ist = pytz.timezone("Asia/Kolkata")
    input_timezone = pytz.timezone("UTC")

    giveaway["end_time"] = input_timezone.localize(
        giveaway["end_time"]).astimezone(ist)
    giveaway["start_time"] = input_timezone.localize(giveaway["start_time"]).astimezone(
        ist
    )

    giveaway["end_time"] = giveaway["end_time"].strftime("%d/%m/%Y %H:%M:%S")
    giveaway["start_time"] = giveaway["start_time"].strftime(
        "%d/%m/%Y %H:%M:%S")

    text = f"""- Text: {giveaway["heading"]}\n- Description: {giveaway['body']}\n- Total Winners: {giveaway['total_winners']}\n- Total participants: {giveaway['total_participants']}\n- Start time: {giveaway['start_time']}\n- End time: {giveaway['end_time']}\n- Credits required: {giveaway['credits']}\n- Join channel: {giveaway['join_channel']}\n- Channel ID: {giveaway['channel_id']}"""
    text += f"\n\n- More info: /giveaway {giveaway['giveaway_id']}"
    await callback_query.message.edit_text(
        text=text,
        reply_markup=Markup(
            [
                [
                    Button(
                        "Start", callback_data=f"start_giveaway_{giveaway_id}"),
                    Button(
                        "Cancel ", callback_data=f"cancel_giveaway_{giveaway_id}"),
                ],
            ]
        ),
    )


@Client.on_callback_query(filters.regex("^start_giveaway_"))
async def start_giveaway(app, callback_query: types.CallbackQuery):
    giveaway_id = callback_query.data.split("_", 2)[2]

    giveaway = await giveaway_db.get_giveaway(giveaway_id=giveaway_id)

    if not giveaway:
        return await callback_query.answer(
            "This giveaway doesn't exist.", show_alert=True
        )

    if giveaway["published"]:
        await callback_query.answer(
            "This giveaway is already started.", show_alert=True
        )
    else:
        await giveaway_db.update_giveaway(
            giveaway_id=giveaway_id, data={"published": True}
        )
        await callback_query.answer("Giveaway started.", show_alert=True)

    text = callback_query.message.text + "\n\n**Giveaway started.**"
    # reply markup for raffle, share the giveaway, and cancel the giveaway
    markup = Markup(
        [
            [
                Button("🎉 Raffle", callback_data=f"raffle_{giveaway_id}"),
                Button("📣 Share", switch_inline_query=giveaway_id),
            ],
            [
                Button(
                    "❌ Cancel", callback_data=f"cancel_giveaway_{giveaway_id}"),
            ],
        ]
    )
    await callback_query.message.edit_text(text=text, reply_markup=markup)


@Client.on_callback_query(filters.regex("^cancel_giveaway_"))
async def cancel_giveaway(app, callback_query: types.CallbackQuery):
    giveaway_id = callback_query.data.split("_", 2)[2]
    giveaway = await giveaway_db.get_giveaway(giveaway_id=giveaway_id)

    if not giveaway:
        return await callback_query.answer(
            "This giveaway doesn't exist.", show_alert=True
        )

    await giveaway_db.delete_giveaways([giveaway_id])

    await callback_query.answer("Giveaway cancelled.", show_alert=True)
    await callback_query.message.delete()


@Client.on_callback_query(filters.regex("^raffle_"))
async def raffle(app, callback_query: types.CallbackQuery):
    """end the giveaway and select the winner"""
    giveaway_id = callback_query.data.split("_", 1)[1]
    giveaway = await giveaway_db.get_giveaway(giveaway_id=giveaway_id)

    if not giveaway:
        return await callback_query.answer(
            "This giveaway doesn't exist.", show_alert=True
        )

    if not giveaway["published"]:
        return await callback_query.answer(
            "This giveaway hasn't started yet.", show_alert=True
        )

    # The above code is importing the pytz module and then setting the timezone to Asia/Kolkata.
    ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist)
    giveaway["end_time"] = utc_to_ist(giveaway["end_time"])
    if giveaway["end_time"] < now_ist:
        return await callback_query.answer("This giveaway has ended.", show_alert=True)

    # select the winners from the participants

    winners = []
    participants = giveaway["participants"]

    if len(participants) < giveaway["total_winners"]:
        return await callback_query.message.edit_text(
            text=callback_query.message.text + "\n\n**Not enough participants.**"
        )
    excluded_winners = await giveaway_db.get_5_last_ended_giveaway_winners()
    while len(winners) < giveaway["total_winners"] and len(participants) > 0:
        winner = random.choice(participants)
        if winner not in excluded_winners or len(participants) <= giveaway[
            "total_winners"
        ] - len(winners):
            winners.append(winner)
            participants.remove(winner)

    if not winners:
        text = callback_query.message.text + "\n\n**No one won the giveaway.**"
        await callback_query.message.edit_text(text=text)
        return await callback_query.answer("No one won the giveaway.", show_alert=True)

    text = callback_query.message.text + "\n\n**Winners:**\n"

    for winner in winners:
        user = await app.get_users(winner)
        text += f"- {user.mention}\n"
        await app.send_message(
            chat_id=winner,
            text=f"Congratulations! You won the giveaway: {giveaway['heading']}.",
        )

    share_winner_reply_markup = Markup(
        [[Button("Share Winners", switch_inline_query=giveaway_id)]]
    )

    await broadcast_owners(
        app.send_message,
        text=await get_share_winner_text(app, winners),
        reply_markup=share_winner_reply_markup,
    )

    await callback_query.message.edit_text(text=text)

    await giveaway_db.update_giveaway(
        giveaway_id=giveaway_id,
        data={"end_time": datetime.now(
            ist), "published": False, "winners": winners},
    )

    await callback_query.answer("Giveaway ended.", show_alert=True)


@Client.on_callback_query(filters.regex("^check_balance"))
async def check_balance(app, callback_query: types.CallbackQuery):
    user = await user_db.get_user(user_id=callback_query.from_user.id)

    if not user:
        return await callback_query.answer("You are not registered.", show_alert=True)

    text = "Credits" if user["credits"] > 1 else "Credit"
    await callback_query.answer(
        f"Your balance is {user['credits']} {text}", show_alert=True
    )


@Client.on_callback_query(filters.regex("^earn"))
async def earn(app: Client, callback_query: types.CallbackQuery):
    bot_config = await bot_config_db.get_bot_config()
    user = await user_db.get_user(user_id=callback_query.from_user.id)

    if user['referral']['channel_ref_link']:
        main_channel = user['referral']['channel_ref_link']
    else:
        chat_id = await app.get_chat(bot_config["main_channel"])
        ref_link = await generate_channel_ref_link(
            app, callback_query.from_user.id, chat_id.id
        )
        await user_db.update_user(user_id=callback_query.from_user.id, data={"referral.channel_ref_link": ref_link.invite_link})
        main_channel = ref_link.invite_link

    backup_channel = None

    if bot_config["backup_channel"]:
        backup_channel = await app.get_chat(bot_config["backup_channel"])

        if backup_channel.username:
            backup_channel = f"@{backup_channel.username}"
        else:
            backup_channel = backup_channel.invite_link

    main_text = ""

    if backup_channel:
        try:
            await app.get_chat_member(
                bot_config["backup_channel"], callback_query.from_user.id
            )
        except UserNotParticipant:
            main_text += f"\n- Join our backup channel {backup_channel} = 2 Credits\n"

    text = f"""🎉🎉🎉 Here are some ways you can Earn Credits 🎉🎉🎉
{main_text}
- Here's your unique link to our [main channel]({main_channel})

Copy - 🔗 `{main_channel}`

"""

    text += bot_config["message"]["earn_credits_message"]
    share_url = f"https://telegram.me/share/url?url={quote_plus(main_channel)}"
    await callback_query.edit_message_text(
        text=text,
        reply_markup=Markup(
            [
                [
                    Button(
                        "Generate New Link - Doesn’t Affect Your Credits",
                        callback_data="generate_channel_ref_link",
                    ),
                ],
                [
                    Button("Share Link", url=share_url),
                ],
            ]
            + [
                [
                    Button("Back", callback_data="start"),
                ]
            ]
        ),
    )


@Client.on_callback_query(filters.regex("^withdraw$"))
async def withdraw(app, callback_query: types.CallbackQuery):
    bot_config = await bot_config_db.get_bot_config()
    credit_value = bot_config["credit_value"]
    user = await user_db.get_user(user_id=callback_query.from_user.id)
    text = bot_config["message"]["withdraw_message"]
    text += f"\n\n**Your Credit Balance Is - {user['credits']} Credits, {user['credits'] * bot_config['credit_value']} INR**"
    text += (
        f"\n**Minimum withdraw amount is {bot_config['min_withdraw_amount']} Credits** "
    )
    text += f"\n**1 Credit = ₹{credit_value}**"
    text += f"\n**Your payment method is {user['payment']['payment_method']}**"
    text += f"\n**Your payment details are {user['payment']['payment_address']}**"

    await callback_query.edit_message_text(
        text=text,
        reply_markup=Markup(
            [
                [
                    Button("Confirm Withdraw",
                           callback_data="withdraw_credits"),
                ],
                [
                    Button("Add Payment Method",
                           callback_data="set_payment_method"),
                ],
                [
                    Button("Back", callback_data="start"),
                ],
            ]
        ),
    )


@Client.on_callback_query(filters.regex("^referral_link"))
async def referral_link(app, callback_query: types.CallbackQuery):
    bot_config = await bot_config_db.get_bot_config()
    user = await user_db.get_user(user_id=callback_query.from_user.id)
    ref_code = (
        f"https://t.me/{app.raw_username}?start=ref_"
        + user["referral"]["referral_code"]
    )
    ref_link = bot_config.get("channel_ref_link")
    if not ref_link and bot_config.get("main_channel"):
        ref_link = await generate_channel_ref_link(
            app, callback_query.from_user.id, bot_config.get("main_channel")
        )
        ref_link = ref_link.invite_link
        await user_db.update_user(
            user_id=callback_query.from_user.id,
            value={"referral.channel_ref_link": ref_link},
        )
    else:
        ref_link = None

    bot_config = await bot_config_db.get_bot_config()
    text = bot_config["message"]["referral_message"].format(
        ref_code=ref_code, ref_link=ref_link
    )
    await callback_query.edit_message_text(
        text=text,
        reply_markup=Markup(
            [
                [Button("Share referral link",
                        url=f"tg://msg_url?url={ref_code}")],
                [
                    Button(
                        "Share channel referral link",
                        url=f"tg://msg_url?url={ref_link}",
                    )
                ],
                [Button("Back", callback_data="earn")],
            ]
        ),
    )


@Client.on_callback_query(filters.regex("^generate_channel_ref_link"))
async def generate_channel_ref_link_cb(
    app: Client, callback_query: types.CallbackQuery
):
    user = await user_db.get_user(user_id=callback_query.from_user.id)
    ref_link = user.get("channel_ref_link")
    bot_config = await bot_config_db.get_bot_config()

    if ref_link:
        chat_id = await app.get_chat(ref_link)
        ref_link = await revoke_channel_ref_link(app, chat_id.id, ref_link)
    elif bot_config["main_channel"]:
        chat_id = await app.get_chat(bot_config["main_channel"])
        ref_link = await generate_channel_ref_link(
            app, callback_query.from_user.id, chat_id.id
        )
    else:
        return await callback_query.answer(
            "No channel set to generate channel referral link.", show_alert=True
        )

    ref_link = ref_link.invite_link
    text = f"Your Channel Referral [Link]({ref_link}) has been revoked\nCopy `{ref_link}`\n\nShare this link with your friends to earn credits."
    await user_db.update_user(
        user_id=callback_query.from_user.id,
        value={"referral.channel_ref_link": ref_link},
    )
    await callback_query.edit_message_text(
        text=text,
        reply_markup=Markup(
            [
                [
                    Button(
                        "Share channel referral link",
                        url=f"tg://msg_url?url={ref_link}",
                    )
                ],
            ]
            + [[Button("Back", callback_data="start")]],
        ),
    )


@Client.on_callback_query(filters.regex("^withdraw_credits$"))
async def withdraw_credits(app, callback_query: types.CallbackQuery):
    user = await user_db.get_user(user_id=callback_query.from_user.id)
    bot_config = await bot_config_db.get_bot_config()

    if not user:
        return await callback_query.answer("You are not registered.", show_alert=True)

    if user["credits"] < bot_config["min_withdraw_amount"]:
        return await callback_query.answer(
            f"You need at least {bot_config['min_withdraw_amount']} credits to withdraw.",
            show_alert=True,
        )

    if user["credits"] > bot_config["max_withdraw_amount"]:
        return await callback_query.answer(
            f"You can only withdraw {bot_config['max_withdraw_amount']} credits at a time, Please Contact Admin",
            show_alert=True,
        )

    if not user["payment"]["payment_method"] and not user["payment"]["payment_address"]:
        await callback_query.answer("Please Add Payment Method", show_alert=True)
        return

    text = f"Your balance is {user['credits']} - {user['credits'] * bot_config['credit_value']} INR\n\n"
    text += "Are you sure you want to withdraw all your credits?"

    await callback_query.edit_message_text(
        text=text,
        reply_markup=Markup(
            [
                [Button("Yes", callback_data="withdraw_credits_yes")],
                [Button("No", callback_data="start")],
            ]
        ),
    )


@Client.on_callback_query(filters.regex("^withdraw_credits_yes"))
async def withdraw_credits_yes(app, callback_query: types.CallbackQuery):
    user = await user_db.get_user(user_id=callback_query.from_user.id)
    bot_config = await bot_config_db.get_bot_config()

    if not user:
        return await callback_query.answer("You are not registered.", show_alert=True)

    await user_db.update_user(user_id=callback_query.from_user.id, value={"credits": 0})

    await callback_query.answer()

    # keybaord of approve, cancel

    keyb = Markup(
        [
            [
                Button(
                    "Approve",
                    callback_data=f"approve_withdraw_{callback_query.from_user.id}_{user['credits']}",
                )
            ],
            [
                Button(
                    "Reject",
                    callback_data=f"return_withdraw_{callback_query.from_user.id}_{user['credits']}",
                )
            ],
        ]
    )

    await broadcast_owners(
        app.send_message,
        text=f"User {callback_query.from_user.id} - {callback_query.from_user.mention} has requested to withdraw {user['credits']} credits.\n\nPayment Method: {user['payment']['payment_method']}\nPayment Address: {user['payment']['payment_address']}",
        reply_markup=keyb,
    )

    await callback_query.message.reply(
        text=f"Your credits have been withdrawn - {user['credits'] * bot_config['credit_value']} INR, payment will be sent within 24 hours.",
        reply_markup=Markup(
            [
                [Button("Back", callback_data="start")],
            ]
        ),
    )

    await callback_query.message.delete()


@Client.on_callback_query(filters.regex("^set_payment_method"))
async def set_payment_method(app, callback_query: types.CallbackQuery):
    bot_config = await bot_config_db.get_bot_config()

    if not bot_config["payment_methods"]:
        return await callback_query.answer(
            "No payment methods set, please contact the bot owner.", show_alert=True
        )
    input_text = "Please select your payment method"
    buttons = [
        [
            Button(
                payment_method,
                callback_data=f"set_payment_id_{payment_method}",
            )
        ]
        for payment_method in bot_config["payment_methods"]
    ]
    buttons.append([Button("Back", callback_data="withdraw")])

    await callback_query.edit_message_text(
        text=input_text,
        reply_markup=Markup(buttons),
    )


@Client.on_callback_query(filters.regex("^set_payment_id_"))
async def set_payment_id(app, callback_query: types.CallbackQuery):
    _, _, _, payment_method = callback_query.data.split("_", 3)

    while True:

        try:
            msg = await callback_query.message.chat.ask(
                "Please send me your payment address",
                timeout=3600,
                filters=filters.text,
            )
        except TimeoutError:
            return await callback_query.answer(
                "You took too long to reply.", show_alert=True
            )

        if msg.text:
            payment_address = msg.text
            break
        else:
            await callback_query.answer(
                "Invalid payment address, please try again.", show_alert=True
            )

    await user_db.update_user(
        user_id=callback_query.from_user.id,
        value={
            "payment": {
                "payment_method": payment_method,
                "payment_address": payment_address,
            }
        },
    )
    user = await user_db.get_user(user_id=callback_query.from_user.id)
    bot_config = await bot_config_db.get_bot_config()
    await callback_query.message.reply(
        text=f"Your payment method and payment address have been updated.\n\nYour Credit Balance Is -  {user['credits']} credits, {user['credits'] * bot_config['credit_value']} INR",
        reply_markup=Markup(
            [
                [Button("Confirm Withdraw", callback_data="withdraw_credits")],
                [Button("Back", callback_data="start")],
            ]
        ),
    )


@Client.on_callback_query(filters.regex("^approve_withdraw"))
async def approve_withdraw(app, callback_query: types.CallbackQuery):
    # f"approve_withdraw_{callback_query.from_user.id}_{user['credits']}"

    _, _, user_id, credits = callback_query.data.split("_")
    user_id = int(user_id)
    credits = int(credits)

    user = await user_db.get_user(user_id=user_id)

    if not user:
        return await callback_query.answer("User not found.", show_alert=True)

    await callback_query.answer()

    await app.send_message(
        chat_id=user_id,
        text=f"Your payment of {credits} credits has been approved and sent to your payment address.",
    )

    await app.send_message(
        chat_id=Config.OWNER_ID,
        text=f"Payment of {credits} credits has been approved and sent to {user['payment']['payment_address']}.",
    )

    await callback_query.edit_message_text(
        text="Payment approved.",
        reply_markup=Markup(
            [
                [Button("Back", callback_data="start")],
            ]
        ),
    )


@Client.on_callback_query(filters.regex("^return_withdraw"))
async def return_withdraw(app, callback_query: types.CallbackQuery):
    _, _, user_id, credits = callback_query.data.split("_")
    user_id = int(user_id)
    credits = int(credits)

    user = await user_db.get_user(user_id=user_id)

    if not user:
        return await callback_query.answer("User not found.", show_alert=True)

    await callback_query.answer()

    text = f"Your payment of {credits} credits has been returned to your account. Contact admins for help\n\n"
    for owner in Config.ADMINS:
        owner = await app.get_users(owner)
        text += f"- {owner.mention}\n"

    await app.send_message(
        chat_id=user_id,
        text=text,
    )

    await app.send_message(
        chat_id=Config.OWNER_ID,
        text=f"Payment of {credits} credits has been returned to {user_id}.",
    )

    await user_db.update_user(
        user_id=user_id, value={"credits": user["credits"] + credits}
    )

    await callback_query.edit_message_text(
        text="Payment returned.",
        reply_markup=Markup(
            [
                [Button("Back", callback_data="start")],
            ]
        ),
    )


@Client.on_callback_query(filters.regex("^cancel_withdraw"))
async def cancel_withdraw(app, callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split("_")[-1])
    user = await user_db.get_user(user_id=user_id)

    if not user:
        return await callback_query.answer("User not found.", show_alert=True)

    await callback_query.answer()

    await app.send_message(
        chat_id=user_id,
        text=f"Your payment of {user['credits']} credits has been cancelled.",
    )

    await app.send_message(
        chat_id=Config.OWNER_ID,
        text=f"Payment of {user['credits']} credits has been cancelled.",
    )

    await callback_query.edit_message_text(
        text="Payment cancelled.",
        reply_markup=Markup(
            [
                [Button("Back", callback_data="start")],
            ]
        ),
    )


@Client.on_callback_query(filters.regex("^participate_"))
async def participate(app, callback_query: types.CallbackQuery):
    giveaway = await giveaway_db.get_giveaway(
        giveaway_id=callback_query.data.split("_", 1)[-1]
    )

    if not giveaway:
        return await callback_query.answer("Giveaway not found.", show_alert=True)

    ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist)

    giveaway["start_time"] = utc_to_ist(giveaway["start_time"])
    giveaway["end_time"] = utc_to_ist(giveaway["end_time"])

    user = await user_db.get_user(user_id=callback_query.from_user.id)

    if not user:
        await add_new_user(
            app, callback_query.from_user.id, callback_query.from_user.mention
        )
        user = await user_db.get_user(user_id=callback_query.from_user.id)

    if user["ban_status"]["is_banned"]:
        return await callback_query.answer(
            "You are banned from using this bot.", show_alert=True
        )

    if not giveaway:
        return await callback_query.answer("Giveaway not found.", show_alert=True)

    if giveaway["end_time"] < now_ist:
        reply_markup = await get_giveaway_button(app, giveaway)
        # change the first button to "Participated"
        reply_markup.inline_keyboard[0][0].text = "Giveaway Ended"
        reply_markup.inline_keyboard[0][0].callback_data = "giveaway_ended"
        await callback_query.edit_message_reply_markup(reply_markup)
        return await callback_query.answer("Giveaway has ended.", show_alert=True)

    if callback_query.from_user.id in giveaway["participants"]:
        return await callback_query.answer(
            "You have already participated in this giveaway.", show_alert=True
        )

    if giveaway["credits"] > user["credits"]:
        return await callback_query.answer(
            "You don't have enough credits to participate, Click Earn Credit",
            show_alert=True,
        )

    if giveaway["total_participants"] <= len(giveaway["participants"]):
        return await callback_query.answer(
            "This giveaway has reached its maximum participants.", show_alert=True
        )

    if giveaway["join_channel"] and giveaway["channel_id"]:
        try:
            await app.get_chat_member(
                giveaway["channel_id"], callback_query.from_user.id
            )
        except UserNotParticipant:
            return await callback_query.answer(
                Messages.JOIN_TEXT_POPUP, show_alert=True
            )

    await user_db.update_user(
        user_id=callback_query.from_user.id,
        value={"credits": user["credits"] - giveaway["credits"]},
    )

    await giveaway_db.update_giveaway(
        giveaway_id=giveaway["giveaway_id"],
        data={
            "participants": giveaway["participants"] + [callback_query.from_user.id]},
    )

    await callback_query.answer(
        f"You have successfully participated in this giveaway, you have been charged {giveaway['credits']} credits.",
        show_alert=True,
    )
    text = f"**{giveaway['heading']}**\n\n{giveaway['body']}\n\n**Total Participants Joined:** {len(giveaway['participants'])+1}\n**Total Winners:** {giveaway['total_winners']}"

    reply_markup = await get_giveaway_button(app, giveaway)
    await callback_query.edit_message_text(text=text, reply_markup=reply_markup)

    await app.send_message(
        chat_id=Config.LOG_CHANNEL,
        text=f"{callback_query.from_user.id} has participated in giveaway {giveaway['giveaway_id']}.",
    )


@Client.on_callback_query(filters.regex("^reset_credits"))
@admin_filter
async def reset_credits(app, callback_query: types.CallbackQuery):
    _, user_id = callback_query.data.split("#")
    user_id = int(user_id)
    await user_db.update_user(user_id=user_id, value={"credits": 0})
    await callback_query.answer("Credits reset successfully.", show_alert=True)


@Client.on_callback_query(filters.regex("^remove_payment_method"))
@admin_filter
async def remove_payment_method(app, callback_query: types.CallbackQuery):
    _, user_id = callback_query.data.split("#")
    user_id = int(user_id)
    user = await user_db.get_user(user_id=user_id)
    if not user["payment"]["payment_method"]:
        return await callback_query.answer(
            "User doesn't have a payment method.", show_alert=True
        )

    await user_db.update_user(
        user_id=user_id,
        value={"payment.payment_method": None,
               "payment.payment_address": None},
    )
    await callback_query.answer("Payment method removed successfully.", show_alert=True)


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


@Client.on_callback_query(filters.regex("delete_user"))
@admin_filter
async def delete_user(app, message):
    user_id = int(message.data.split("#")[1])
    message = message.message
    user = await user_db.get_user(user_id)
    if not user:
        await message.message.reply_text(
            "There is no user with that id in the database."
        )
        return

    await user_db.delete_user(user_id)
    await message.reply_text(f"Deleted user {user_id} from the database.")

    await app.send_message(user_id, "You have been deleted from the database by admin.")


@Client.on_callback_query(filters.regex("giveaway_ended"))
async def giveaway_ended(app, callback_query: types.CallbackQuery):
    await callback_query.answer("This giveaway has ended.")
    return