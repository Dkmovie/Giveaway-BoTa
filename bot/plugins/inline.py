from datetime import datetime
import time
import humanize
from pyrogram import Client, filters
from pyrogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
import pytz
from bot.database import giveaway_db, bot_db
from bot.utils import get_giveaway_button, get_share_winner_text, utc_to_ist


@Client.on_inline_query(filters.regex(r"^giveaway_"))
async def inline(app: Client, query: InlineQuery):
    cache_time = 0
    giveaway_id = query.query
    giveaway = await giveaway_db.get_giveaway(giveaway_id)

    if giveaway is None:
        return await query.answer(
            results=[],
            switch_pm_text='Giveaway not found',
            switch_pm_parameter='start',
            cache_time=cache_time
        )

    # check if giveaway has ended
    giveaway['end_time'] = utc_to_ist(giveaway["end_time"])
    giveaway['start_time'] = utc_to_ist(giveaway["start_time"])

    # check if the giveaway is published
    if not giveaway['published']:
        if giveaway['end_time'] > datetime.now(pytz.timezone('Asia/Kolkata')):
            return await query.answer(
                results=[],
                switch_pm_text='Giveaway has not started yet',
                switch_pm_parameter='start',
                cache_time=cache_time
            )
        winners = giveaway["winners"]
        text = await get_share_winner_text(app, winners)
        await query.answer(
            results=[
                InlineQueryResultArticle(
                    title=giveaway['heading'],
                    input_message_content=InputTextMessageContent(text),
                    description=giveaway['body'],
                    thumb_url='https://www.monsterinsights.com/wp-content/uploads/2019/08/Free-Online-Contest-Software-Options-for-Viral-Giveaways.png',
                )
            ],
            cache_time=cache_time
        )
        return

    elif not giveaway['published'] and giveaway['start_time'] > datetime.now(pytz.timezone('Asia/Kolkata')):
        return await query.answer(
            results=[],
            switch_pm_text='Giveaway not published',
            switch_pm_parameter='start',
            cache_time=cache_time
        )

    text = f"**{giveaway['heading']}**\n\n{giveaway['body']}\n\n**Total Participants Joined:** {len(giveaway['participants'])}\n**Total Winners:** {giveaway['total_winners']}"

    reply_markup = await get_giveaway_button(app, giveaway)
    try:
        await query.answer(
            results=[
                InlineQueryResultArticle(
                    title=giveaway['heading'],
                    input_message_content=InputTextMessageContent(text),
                    description=giveaway['body'],
                    thumb_url='https://www.monsterinsights.com/wp-content/uploads/2019/08/Free-Online-Contest-Software-Options-for-Viral-Giveaways.png',
                    reply_markup=reply_markup,
                )
            ],
            cache_time=cache_time
        )
    except UserNotParticipant:
        await query.answer(
            results=[],
            switch_pm_text='Join channel to use inline',
            switch_pm_parameter='start',
            cache_time=cache_time
        )
