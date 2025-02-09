import asyncio
import time
import os
from pyrogram import Client, filters
from pymongo import MongoClient
from pyrogram.errors import ChatWriteForbidden, UserBannedInChannel
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# 🔹 User Input During VPS Deployment
if not os.path.exists("config.env"):
    print("\n🔹 VPS Setup: Enter the required details\n")
    BOT_TOKEN = input("Enter Bot Token: ")
    SESSION_STRING = input("Enter Session String: ")
    OWNER_ID = int(input("Enter Owner ID: "))
    MONGO_URL = input("Enter MongoDB URL: ")
    DB_NAME = input("Enter MongoDB Database Name: ")

    with open("config.env", "w") as f:
        f.write(f"BOT_TOKEN={BOT_TOKEN}\nSESSION_STRING={SESSION_STRING}\nOWNER_ID={OWNER_ID}\nMONGO_URL={MONGO_URL}\nDB_NAME={DB_NAME}\n")

else:
    from dotenv import load_dotenv
    load_dotenv("config.env")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    SESSION_STRING = os.getenv("SESSION_STRING")
    OWNER_ID = int(os.getenv("OWNER_ID"))
    MONGO_URL = os.getenv("MONGO_URL")
    DB_NAME = os.getenv("DB_NAME")

API_ID = 1234567  # Replace with your API_ID
API_HASH = "YOUR_API_HASH"  # Replace with your API_HASH

# 🔹 MongoDB Setup
client = MongoClient(MONGO_URL)
db = client[DB_NAME]
settings = db["settings"]  # Store scheduled message & delay settings
banned_groups = db["banned_groups"]  # Store muted/banned groups

# 🔹 Pyrogram Clients
bot = Client("control_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)  # Bot for commands
userbot = Client("broadcast_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)  # Userbot for broadcasting


# ✅ **Start Command**
@bot.on_message(filters.command("start") & filters.user(OWNER_ID))
async def start(client, message):
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔹 Group 1", url="https://t.me/group1"),
         InlineKeyboardButton("🔹 Group 2", url="https://t.me/group2")],
        [InlineKeyboardButton("🔹 Group 3", url="https://t.me/group3")]
    ])

    await message.reply_photo(
        photo="https://telegra.ph/file/example.jpg",  # Replace with your image link
        caption="👋 **Welcome to Marketplace Manager Bot!**\n\nUse `/help` to see available commands.",
        reply_markup=buttons
    )


# ✅ **Help Command**
@bot.on_message(filters.command("help") & filters.user(OWNER_ID))
async def help_command(client, message):
    help_text = """
**📌 Available Commands:**
- `/set` (reply to message) → Set message for scheduling
- `/setdelay 1m` → Set delay (1m = 1 minute, 1h = 1 hour, max 24h)
- `/broadcast` (reply to message) → Send broadcast via session
- `/feedback` → Contact support
- `/banned` → View banned/muted groups
"""
    await message.reply(help_text, parse_mode="markdown")


# ✅ **Set Scheduled Message**
@bot.on_message(filters.command("set") & filters.reply & filters.user(OWNER_ID))
async def set_scheduled_message(client, message):
    msg_id = message.reply_to_message.message_id
    chat_id = message.chat.id

    settings.update_one({"owner_id": OWNER_ID}, {"$set": {"msg_id": msg_id, "chat_id": chat_id}}, upsert=True)
    await message.reply("✅ **Message has been set for scheduling!**", parse_mode="markdown")


# ✅ **Set Delay**
@bot.on_message(filters.command("setdelay") & filters.user(OWNER_ID))
async def set_delay(client, message):
    if len(message.command) < 2:
        return await message.reply("**Usage:** `/setdelay 1m` or `/setdelay 1h` (max 24h)", parse_mode="markdown")

    delay_str = message.command[1]
    if delay_str.endswith("m"):
        delay = int(delay_str[:-1]) * 60
    elif delay_str.endswith("h"):
        delay = int(delay_str[:-1]) * 3600
    else:
        return await message.reply("❌ **Invalid format!** Use `1m` (minutes) or `1h` (hours).", parse_mode="markdown")

    if delay < 60 or delay > 86400:
        return await message.reply("❌ **Delay must be between 1 minute and 24 hours!**", parse_mode="markdown")

    settings.update_one({"owner_id": OWNER_ID}, {"$set": {"delay": delay}}, upsert=True)
    await message.reply(f"✅ **Delay set to `{delay_str}`!**", parse_mode="markdown")


# ✅ **Fetch All Groups From Session**
async def get_groups():
    groups = []
    async with userbot:
        async for dialog in userbot.get_dialogs():
            if dialog.chat.type in ["supergroup", "channel"]:
                groups.append(dialog.chat.id)
    return groups


# ✅ **Broadcast Command (via Session)**
@bot.on_message(filters.command("broadcast") & filters.reply & filters.user(OWNER_ID))
async def broadcast_command(client, message):
    msg_id = message.reply_to_message.message_id
    chat_id = message.chat.id

    data = settings.find_one({"owner_id": OWNER_ID})
    delay = data["delay"] if data and "delay" in data else 60  # Default 1 min delay

    await message.reply(f"🚀 **Broadcasting Started!**\n⏳ Delay: `{delay}` sec", parse_mode="markdown")

    success, failed, banned = 0, 0, 0
    start_time = time.time()

    async with userbot:
        groups = await get_groups()
        for group_id in groups:
            try:
                await userbot.forward_messages(chat_id=group_id, from_chat_id=chat_id, message_ids=msg_id)
                success += 1
                await asyncio.sleep(delay)  # Delay between messages
            except (ChatWriteForbidden, UserBannedInChannel):
                banned_groups.update_one({"chat_id": group_id}, {"$set": {"banned": True}}, upsert=True)
                banned += 1
            except:
                failed += 1

    end_time = time.time()
    taken = round(end_time - start_time, 2)

    await message.reply(
        f"✅ **Broadcast Complete!**\n\n📌 **Success:** `{success}`\n❌ **Failed:** `{failed}`\n🚫 **Banned/Muted:** `{banned}`\n⏳ **Time Taken:** `{taken}s`",
        parse_mode="markdown"
    )


# ✅ **Run Bots**
async def main():
    await userbot.start()
    await bot.start()
    print("Bot & Userbot are Running!")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
