import asyncio
import nest_asyncio
import os
import json
import glob
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
    json_files = glob.glob('*.json')
    if json_files:
        return json_files[0]
    return None

def load_items(file_path):
    """Loads items from a specified JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

async def log_to_telegram(bot, message):
    """Sends a log message to the dedicated log channel."""
    if not LOG_CHANNEL_ID:
        return
    try:
        # Escape characters for MarkdownV2
        safe_message = message.replace('.', '\\.').replace('`', '\\`').replace('-', '\\-')
        await bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"🤖 **Bot Log:**\n\n{safe_message}", parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as e:
        print(f"❌ CRITICAL: Failed to send log to Telegram: {e}")

# ====== MAIN PROCESSING LOGIC ======

async def process_content():
    """Main function to process and send all content from the JSON file."""
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Error: BOT_TOKEN or CHAT_ID is not set. Aborting.")
        return

    bot = Bot(token=BOT_TOKEN)
    await log_to_telegram(bot, "Workflow started successfully.")

    json_file = find_json_file()
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
                await bot.send_message(chat_id=CHAT_ID, text=item['text'], parse_mode=ParseMode.HTML)
            
            elif content_type == 'poll':
                # ** NEW LOGIC: TWO-STEP SENDING **
                question_text_message = f"[MediX]\n\n{item['question']}"
                poll_question_placeholder = "⬆️ Cast your vote above ⬆️"
                explanation_text = item.get('explanation')

                # 1. Send the question first as a plain text message
                await bot.send_message(
                    chat_id=CHAT_ID,
                    text=question_text_message,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                await asyncio.sleep(1) # Small delay between the text and poll

                # 2. Send the poll with a placeholder question
                try:
                    await bot.send_poll(
                        chat_id=CHAT_ID,
                        question=poll_question_placeholder,
                        options=item["options"],
                        is_anonymous=True,
                        type="quiz",
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
                            is_anonymous=True,
                            type="quiz",
                            correct_option_id=item["correct_option"]
                        )
                        spoiler_text = f"💡 *Explanation:*\n\n||{explanation_text}||"
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
