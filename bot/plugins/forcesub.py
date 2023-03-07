import contextlib
from pyrogram import Client, filters, types
from pyrogram.errors import UserNotParticipant
from bot.config import Config
from bot.utils import add_new_user


@Client.on_message(filters.private & filters.incoming)
async def forcesub_handler(c: Client, m: types.Message):

    if Config.UPDATE_CHANNEL and await force_sub_func(
        c, Config.UPDATE_CHANNEL, m
    ) is not True:
        return
    await m.continue_propagation()


async def force_sub_func(c, channel_id, m):
    owner = c.owner
    if not channel_id:
        return True

    invite_link = await c.create_chat_invite_link(channel_id)
    try:
        user = await c.get_chat_member(channel_id, m.from_user.id)
        if user.status == "kicked":
            return await m.reply_text("**Hey you are banned 😜**", quote=True)
    except UserNotParticipant:
        buttons = [
            [
                types.InlineKeyboardButton(
                    text="Updates Channel 🔖", url=invite_link.invite_link
                )
            ]
        ]

        return await m.reply_text(
            f"Hey {m.from_user.mention(style='md')} you need join My updates channel in order to use me 😉\n\n"
            "Press the Following Button to join Now 👇",
            reply_markup=types.InlineKeyboardMarkup(buttons),
            quote=True,
        )
    except Exception as e:
        print(e)
        return await m.reply_text(
            f"Something Wrong. Please try again later or contact {owner.mention(style='md')}",
            quote=True,
        )
    return True
        
@Client.on_callback_query(filters.regex("sub_refresh"))
async def refresh_cb(c, m: types.CallbackQuery):
    owner = c.owner
    if Config.UPDATE_CHANNEL:
        try:
            user = await c.get_chat_member(Config.UPDATE_CHANNEL, m.from_user.id)
            if user.status == "kicked":
                with contextlib.suppress(Exception):
                    await m.message.edit("**Hey you are banned**")
                return
        except UserNotParticipant:
            await m.answer(
                "You have not yet joined our channel. First join and then press refresh button",
                show_alert=True,
            )

            return
        except Exception as e:
            print(e)
            await m.message.edit(
                f"Something Wrong. Please try again later or contact {owner.mention(style='md')}"
            )

            return
        
    await m.message.delete()
