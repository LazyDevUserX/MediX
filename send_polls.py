import asyncio
import nest_asyncio
import os
import json
import glob
import re
from telegram import Bot
from telegram.error import BadRequest
from telegram.constants import ParseMode

# Allow nested asyncio
nest_asyncio.apply()

# ====== CONFIGURATION ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")

# ====== HELPER FUNCTIONS ======

def find_json_file():
    """Finds the first .json file in the repository's root directory."""
    return next(iter(glob.glob('*.json')), None)

def load_items(file_path):
    """Loads items from a specified JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def escape_markdown_v2(text: str) -> str:
    """
    FIX: Now handles non-string inputs gracefully and escapes all special characters.
    """
    if not isinstance(text, str):
        return ''
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

async def log_to_telegram(bot, message: str):
    """Sends a log message to the dedicated log channel."""
    if not LOG_CHANNEL_ID:
        return
    try:
        # FIX: The log message itself must be escaped to prevent parsing errors.
        safe_message = escape_markdown_v2(message)
        await bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"🤖 *Bot Log*\n\n{safe_message}", parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as e:
        print(f"❌ CRITICAL: Failed to send log to Telegram: {e}")

# ====== MAIN PROCESSING LOGIC ======

async def process_content():
    """Main function to process and send all content from the JSON file."""
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Error: BOT_TOKEN or CHAT_ID is not set. Aborting.")
        # No bot object exists yet, so we can't log this to Telegram.
        return

    bot = Bot(token=BOT_TOKEN)
    await log_to_telegram(bot, "Workflow started successfully.")

    json_file = find_json_file()
    if not json_file:
        await log_to_telegram(bot, "Could not find any .json file to process.")
        return

    item_list = load_items(json_file)
    if not item_list:
        await log_to_telegram(bot, f"File '{json_file}' is empty or contains invalid JSON.")
        return
        
    await log_to_telegram(bot, f"Found {len(item_list)} items in '{json_file}'. Starting to send content.")

    for i, item in enumerate(item_list, start=1):
        content_type = item.get('type', 'poll')
        print(f"--> Processing item {i} (type: {content_type})...")

        try:
            if content_type == 'message':
                if 'text' not in item or not item.get('text'):
                    raise ValueError("Message text is empty or missing the 'text' key.")
                await bot.send_message(chat_id=CHAT_ID, text=item['text'], parse_mode=ParseMode.HTML)
            
            elif content_type == 'poll':
                required_keys = ['question', 'options', 'correct_option']
                if not all(key in item for key in required_keys):
                    raise ValueError(f"Poll item is missing one of the required keys: {required_keys}")
                
                escaped_question = escape_markdown_v2(item['question'])
                question_text_message = f"*MediX*\n\n{escaped_question}"
                poll_question_placeholder = "⬆️ Cast your vote above ⬆️"
                
                await bot.send_message(
                    chat_id=CHAT_ID,
                    text=question_text_message,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                await asyncio.sleep(1)

                # FIX: Ensure explanation text is also escaped before use.
                explanation_text = escape_markdown_v2(item.get('explanation'))

                try:
                    await bot.send_poll(
                        chat_id=CHAT_ID, question=poll_question_placeholder,
                        options=item["options"], is_anonymous=True, type="quiz",
                        correct_option_id=item["correct_option"],
                        explanation=explanation_text,
                        explanation_parse_mode=ParseMode.MARKDOWN_V2
                    )
                except BadRequest as e:
                    if "message is too long" in str(e).lower() and explanation_text:
                        print("⚠️ Explanation too long. Sending as a spoiler message.")
                        await bot.send_poll(
                            chat_id=CHAT_ID, question=poll_question_placeholder,
                            options=item["options"], is_anonymous=True, type="quiz",
                            correct_option_id=item["correct_option"]
                        )
                        spoiler_text = f"💡 *Explanation for the previous poll:*\n\n||{explanation_text}||"
                        await bot.send_message(
                            chat_id=CHAT_ID, text=spoiler_text,
                            parse_mode=ParseMode.MARKDOWN_V2
                        )
                    else:
                        raise
            else:
                raise ValueError(f"Unknown item type: '{content_type}'")

            await asyncio.sleep(4)

        except Exception as e:
            error_details = f"Failed to send item #{i}. Type: {content_type}. Error: {e}"
            print(f"❌ {error_details}")
            await log_to_telegram(bot, error_details)
    
    await log_to_telegram(bot, f"✅ Finished sending all content from '{json_file}'.")

# ====== MAIN EXECUTION BLOCK ======
if __name__ == "__main__":
    asyncio.run(process_content())
