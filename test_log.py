import asyncio
import os
from telegram import Bot
from telegram.constants import ParseMode

# ====== CONFIGURATION ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")

async def send_test_log():
    """A minimal function to test logging."""
    if not BOT_TOKEN or not LOG_CHANNEL_ID:
        print("❌ Error: BOT_TOKEN or LOG_CHANNEL_ID is not set.")
        return

    print(f"Attempting to send a test message to LOG_CHANNEL_ID: {LOG_CHANNEL_ID}")
    bot = Bot(token=BOT_TOKEN)
    
    try:
        await bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text="This is a direct test message to the log channel\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        print("✅ Test message sent successfully!")
    except Exception as e:
        print(f"❌ FAILED TO SEND TEST MESSAGE. Error: {e}")

if __name__ == "__main__":
    asyncio.run(send_test_log())
