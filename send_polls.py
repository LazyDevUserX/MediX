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
    NEW: Escapes characters for Telegram's MarkdownV2 parse mode.
    This is the key fix for the '|' is reserved error.
    """
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

async def log_to_telegram(bot, message):
    """Sends a log message to the dedicated log channel."""
    if not LOG_CHANNEL_ID:
        return
    try:
        # We escape the message here to ensure the log itself doesn't fail
        safe_message = escape_markdown_v2(message)
        await bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"🤖 *Bot Log*\n\n{safe_message}", parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as e:
        print(f"❌ CRITICAL: Failed to send log to Telegram: {e}")

# ====== MAIN PROCESSING LOGIC ======

async def process_content():
    """Main function to process and send all content from the JSON file."""
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Error: BOT_TOKEN or CHAT_ID is not set. Aborting.")
        return

    bot = Bot(token=BOT_TOKEN)
    json_file = find_json_file()
    
    # Send initial log message
    await log_to_telegram(bot, "Workflow started successfully.")

    if not json_file:
        error_msg = "Could not find any .json file to process."
        print(f"❌ {error_msg}")
        await log_to_telegram(bot, error_msg)
        return

    item_list = load_items(json_file)
    if not item_list:
        error_msg = f"File '{json_file}' is empty or contains invalid JSON."
        print(f"❌ {error_msg}")
        await log_to_telegram(bot, error_msg)
        return
        
    log_start_msg = f"Found {len(item_list)} items in '{json_file}'. Starting to send content."
    print(log_start_msg)
    await log_to_telegram(bot, log_start_msg)

    for i, item in enumerate(item_list, start=1):
        content_type = item.get('type', 'poll')
        print(f"--> Processing item {i} (type: {content_type})...")

        try:
            if content_type == 'message':
                # HTML is more forgiving for messages, so we can keep it here
                await bot.send_message(chat_id=CHAT_ID, text=item['text'], parse_mode=ParseMode.HTML)
            
            elif content_type == 'poll':
                # Use the escape function on the question text
                escaped_question = escape_markdown_v2(item['question'])
                question_text_message = f"*MediX*\n\n{escaped_question}"
                poll_question_placeholder = "⬆️ Cast your vote above ⬆️"
                explanation_text = item.get('explanation')

                await bot.send_message(
                    chat_id=CHAT_ID,
                    text=question_text_message,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                await asyncio.sleep(1)

                try:
                    await bot.send_poll(
                        chat_id=CHAT_ID,
                        question=poll_question_placeholder,
                        options=item["options"],
                        is_anonymous=True, type="quiz",
                        correct_option_id=item["correct_option"],
                        explanation=explanation_text,
                        explanation_parse_mode=ParseMode.MARKDOWN_V2
                    )
                except BadRequest as e:
                    if "message is too long" in str(e).lower() and explanation_text:
                        print("⚠️ Explanation too long. Sending as a spoiler message.")
                        await bot.send_poll(
                            chat_id=CHAT_ID,
                            question=poll_question_placeholder,
                            options=item["options"],
                            is_anonymous=True, type="quiz",
                            correct_option_id=item["correct_option"]
                        )
                        # Escape the explanation text as well before making it a spoiler
                        escaped_explanation = escape_markdown_v2(explanation_text)
                        spoiler_text = f"💡 *Explanation for the previous poll:*\n\n||{escaped_explanation}||"
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text=spoiler_text,
                            parse_mode=ParseMode.MARKDOWN_V2
                        )
                    else:
                        raise

            await asyncio.sleep(4)

        except Exception as e:
            error_details = f"Failed to send item #{i}. Type: {content_type}. Error: {e}"
            print(f"❌ {error_details}")
            await log_to_telegram(bot, error_details)
    
    final_log = f"✅ Finished sending all content from '{json_file}'."
    print(final_log)
    await log_to_telegram(bot, final_log)

# ====== MAIN EXECUTION BLOCK ======
if __name__ == "__main__":
    asyncio.run(process_content())
