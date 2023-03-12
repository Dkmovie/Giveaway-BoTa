import os
from dotenv import load_dotenv

load_dotenv()


def is_enabled(value, default):
    if value.lower() in ["true", "yes", "1", "enable", "y"]:
        return True
    elif value.lower() in ["false", "no", "0", "disable", "n"]:
        return False
    else:
        return default


class Config(object):

    BOT_USERNAME = os.environ.get("BOT_USERNAME", "GiveawayBot")
    API_ID = int(os.environ.get("API_ID"))
    API_HASH = os.environ.get("API_HASH")
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    ADMINS = (
        [int(i.strip()) for i in os.environ.get("ADMINS").split(",")]
        if os.environ.get("ADMINS")
        else []
    )
    DATABASE_NAME = os.environ.get("DATABASE_NAME", BOT_USERNAME)
    DATABASE_URL = os.environ.get("DATABASE_URL", None)
    OWNER_ID = int(os.environ.get("OWNER_ID"))
    ADMINS.append(OWNER_ID) if OWNER_ID not in ADMINS else []

    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "0"))
    UPDATE_CHANNEL = int(os.environ.get("UPDATE_CHANNEL", "0"))
    BROADCAST_AS_COPY = is_enabled(
        (os.environ.get("BROADCAST_AS_COPY", "False")), False
    )
    WEB_SERVER = is_enabled(os.environ.get("WEB_SERVER", "False"), False)


class Messages(object):

    HEADING = "💰💰 Exciting news! We're having a ₹500 giveaway! 💰💰"
    BODY = """👉 Just click on the 🎉 "Join Giveaway" 🎉 button to enter the giveaway!

🎁 Giveaway Prize: ₹500 💰

🕰️ Giveaway Ends On: 05:00 PM, 4th March, 2023 ⏰

🤖 The bot will pick a random winner 🎊 and will announce it publicly! 📣
"""
    JOIN_TEXT_POPUP = "You need to Join @F11Sports to participate in the Giveaway"

    HEADING = os.environ.get("HEADING", HEADING)
    BODY = os.environ.get("BODY", BODY)
    JOIN_TEXT_POPUP = os.environ.get("JOIN_TEXT_POPUP", JOIN_TEXT_POPUP)