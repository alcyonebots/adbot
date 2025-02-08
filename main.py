import asyncio
import time
from pyrogram import Client, filters
from pymongo import MongoClient
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# 🔹 Config
API_ID = 1234567
API_HASH = "YOUR_API_HASH"
BOT_TOKEN = "YOUR_BOT_TOKEN"
SESSION_STRING = "YOUR_SESSION_STRING"
OWNER_ID = 123456789  # Only owner can use commands
MONGO_URL = "mongodb+srv://username:password@cluster.mongodb.net/database"

# 🔹 MongoDB Setup
client = MongoClient(MONGO_URL)
db = client["adbot"]
groups = db["groups"]  # Store groups
settings = db["settings"]  # Store scheduled message & delay settings
chat_links = db["chat_links"]  # Store chat folder links

# 🔹 Pyrogram Clients
bot = Client("control_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)  # Bot for commands
userbot = Client("broadcast_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)  # Userbot for broadcasting


# ✅ **Start Command**
@bot.on_message(filters.command("start") & filters.user(OWNER_ID))
async def start(client, message):
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("Group 1", url="https://t.me/group1"),
         InlineKeyboardButton("Group 2", url="https://t.me/group2")],
        [InlineKeyboardButton("Group 3", url="https://t.me/group3")]
    ])

    await message.reply_photo(
        photo="https://telegra.ph/file/example.jpg",  # Change this URL
        caption="👋 **Welcome to the Marketplace Manager Bot!**\n\nUse `/help` to see available commands.",
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
- `/addlink chat_folder_link` → Add chat folder link for broadcasts
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


# ✅ **Broadcast Command (via Session)**
@bot.on_message(filters.command("broadcast") & filters.reply & filters.user(OWNER_ID))
async def broadcast_command(client, message):
    msg_id = message.reply_to_message.message_id
    chat_id = message.chat.id

    data = settings.find_one({"owner_id": OWNER_ID})
    delay = data["delay"] if data and "delay" in data else 60  # Default 1 min delay

    await message.reply(f"🚀 **Broadcasting Started!**\n⏳ Delay: `{delay}` sec", parse_mode="markdown")

    success, failed = 0, 0
    start_time = time.time()

    async with userbot:
        for group in groups.find():
            try:
                await userbot.forward_messages(chat_id=group["chat_id"], from_chat_id=chat_id, message_ids=msg_id)
                success += 1
                await asyncio.sleep(delay)  # Delay between messages
            except:
                failed += 1

    end_time = time.time()
    taken = round(end_time - start_time, 2)

    await message.reply(
        f"✅ **Broadcast Complete!**\n\n📌 **Success:** `{success}`\n❌ **Failed:** `{failed}`\n⏳ **Time Taken:** `{taken}s`",
        parse_mode="markdown"
    )


# ✅ **Feedback Command**
@bot.on_message(filters.command("feedback") & filters.user(OWNER_ID))
async def feedback(client, message):
    await message.reply("📩 **For queries, contact [Alcyone Support](https://t.me/AlcyoneSupport)**", parse_mode="markdown")


# ✅ **Add Chat Folder Link**
@bot.on_message(filters.command("addlink") & filters.user(OWNER_ID))
async def add_chat_folder(client, message):
    if len(message.command) < 2:
        return await message.reply("**Usage:** `/addlink chat_folder_link`", parse_mode="markdown")

    link = message.command[1]
    chat_links.insert_one({"link": link})
    await message.reply("✅ **Chat folder link added!**", parse_mode="markdown")


# ✅ **Run Bots**
async def main():
    await userbot.start()  # Start session-based userbot
    await bot.start()  # Start bot commands
    print("Bot & Userbot are Running!")
    await asyncio.Event().wait()  # Keep running


if __name__ == "__main__":
    asyncio.run(main())
