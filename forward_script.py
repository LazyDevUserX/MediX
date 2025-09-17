import os
import asyncio
import random
import traceback
from datetime import datetime

# --- Telethon for all user actions ---
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# --- Load environment variables ---
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
    print("✅ .env file loaded.")
except ImportError:
    print("🟡 python-dotenv not found, relying on system environment variables.")

# --- SCRIPT CONFIGURATION ---
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
SESSION_STRING = os.getenv('SESSION_STRING')
SOURCE_CHANNEL = os.getenv('SOURCE_CHANNEL')
DESTINATION_CHANNEL = os.getenv('DESTINATION_CHANNEL')
LOG_CHANNEL_ID = os.getenv('LOG_CHANNEL_ID')

# Safety & Performance
MIN_DELAY_SECONDS = 1
MAX_DELAY_SECONDS = 2
BATCH_SIZE = 100 # Process 100 messages at a time

# --- HELPER FUNCTIONS ---

def parse_id(value):
    """Parses message IDs from various formats (raw number, link)."""
    value = str(value).strip()
    if value.isdigit():
        return int(value)
    elif '/' in value:
        return int(value.split('/')[-1])
    else:
        raise ValueError(f"Invalid format for message ID: {value}")

async def send_log(client: TelegramClient, log_channel_id: int, text: str):
    """Sends a formatted message to the log channel using the main client."""
    if not client or not log_channel_id:
        return
    try:
        await client.send_message(
            entity=log_channel_id,
            message=text,
            parse_mode='html',
            link_preview=False
        )
    except Exception as e:
        print(f"🔴 CRITICAL: Failed to send log message. Error: {e}")


# --- MAIN SCRIPT LOGIC ---

async def main():
    """Initializes the client, parses tasks, and executes the forwarding process."""
    console_prefix = "--- SCRIPT ---"
    print(f"{console_prefix} Initializing...")

    # --- 1. VALIDATE CONFIGURATION ---
    required_vars = {
        'API_ID': API_ID, 'API_HASH': API_HASH, 'SESSION_STRING': SESSION_STRING,
        'SOURCE_CHANNEL': SOURCE_CHANNEL, 'DESTINATION_CHANNEL': DESTINATION_CHANNEL,
        'LOG_CHANNEL_ID': LOG_CHANNEL_ID
    }
    missing_vars = [name for name, var in required_vars.items() if not var]
    if missing_vars:
        print(f"🔴 FATAL ERROR: Missing GitHub Secrets: {', '.join(missing_vars)}")
        return

    try:
        log_channel_int_id = int(LOG_CHANNEL_ID)
    except ValueError:
        print(f"🔴 FATAL ERROR: LOG_CHANNEL_ID is not a valid integer: '{LOG_CHANNEL_ID}'")
        return

    # --- 2. PARSE range.txt ---
    tasks = []
    # (Parsing logic remains the same)
    try:
        with open('range.txt', 'r') as f:
            lines = f.readlines()

        start_id = None
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'): continue
            parts = line.split(':', 1)
            if len(parts) != 2: continue
            key, value = parts[0].strip().lower(), parts[1].strip()

            if key == 'message':
                tasks.append({'type': 'message', 'content': value})
            elif key == 'start':
                start_id = parse_id(value)
            elif key == 'end' and start_id is not None:
                end_id = parse_id(value)
                tasks.append({'type': 'range', 'start': start_id, 'end': end_id})
                start_id = None
        
        if not tasks:
             raise ValueError("range.txt contains no valid tasks.")
        print(f"{console_prefix} Successfully parsed {len(tasks)} tasks from range.txt.")

    except Exception as e:
        print(f"🔴 FATAL ERROR: Could not read or parse range.txt. Details: {e}")
        return

    # --- 3. INITIALIZE AND EXECUTE ---
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH, timeout=60)
    stats = {'polls_forwarded': 0, 'non_polls_skipped': 0, 'errors': 0}
    start_time = datetime.now()

    async with client:
        await send_log(client, log_channel_int_id, "🚀 <b>Poll Forwarder Initialized</b>\nScript is starting up...")
        
        me = await client.get_me()
        await send_log(client, log_channel_int_id, f"👤 <b>Client Connected</b>\nLogged in as: <code>{me.first_name} {me.last_name or ''}</code>")
        
        try:
            source_entity = await client.get_entity(SOURCE_CHANNEL)
            destination_entity = await client.get_entity(DESTINATION_CHANNEL)
            await client.get_entity(log_channel_int_id)
            await send_log(client, log_channel_int_id, (
                f"🎯 <b>Channels Verified</b>\n"
                f"<b>Source:</b> <code>{source_entity.title}</code>\n"
                f"<b>Destination:</b> <code>{destination_entity.title}</code>\n"
                f"<b>Logs:</b> OK"
            ))
        except Exception as e:
            await send_log(client, log_channel_int_id, f"💥 <b>Fatal Error</b>\nCould not resolve channels.\n\n<b>Details:</b>\n<code>{e}</code>")
            return

        # --- 4. EXECUTE TASKS (Main Loop) ---
        for i, task in enumerate(tasks, 1):
            task_header = f"▶️ <b>Executing Task {i}/{len(tasks)}:</b> <code>{task['type'].upper()}</code>"
            await send_log(client, log_channel_int_id, task_header)
            
            try:
                if task['type'] == 'message':
                    await client.send_message(destination_entity, task['content'])
                    stats['polls_forwarded'] += 1
                    await send_log(client, log_channel_int_id, f"  ✍️ <b>Custom Message Sent:</b> \"{task['content'][:50]}...\"")

                # --- MODIFIED: BATCH PROCESSING LOGIC ---
                elif task['type'] == 'range':
                    start, end = task['start'], task['end']
                    range_info = f"Processing poll range <code>{start}-{end}</code> in batches of {BATCH_SIZE}."
                    await send_log(client, log_channel_int_id, f"  🔎 {range_info}")
                    
                    # Loop through the total range in chunks of BATCH_SIZE
                    for batch_start in range(start, end + 1, BATCH_SIZE):
                        batch_end = min(batch_start + BATCH_SIZE - 1, end)
                        batch_ids = list(range(batch_start, batch_end + 1))
                        
                        print(f"  Fetching batch: {batch_start}-{batch_end}")
                        
                        messages = await client.get_messages(source_entity, ids=batch_ids)
                        valid_messages = [m for m in messages if m]

                        if valid_messages:
                           await send_log(client, log_channel_int_id, f"  - Processing batch <code>{batch_start}-{batch_end}</code>, found {len(valid_messages)} messages.")
                        
                        for message in valid_messages:
                            delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
                            if message.poll:
                                await message.forward_to(destination_entity)
                                stats['polls_forwarded'] += 1
                                print(f"    ✅ FORWARDED: Poll from message ID {message.id}.")
                                await asyncio.sleep(delay)
                            else:
                                stats['non_polls_skipped'] += 1
                                # Skipping is a normal operation, so we don't log it to avoid spam
                        
                        # Small pause between batches to be safe
                        await asyncio.sleep(1)

            except FloodWaitError as e:
                wait_time = e.seconds + 5
                stats['errors'] += 1
                warning_msg = f"🟡 <b>FloodWaitError</b>. Pausing for <code>{wait_time}</code> seconds."
                await send_log(client, log_channel_int_id, warning_msg)
                await asyncio.sleep(wait_time)
            except Exception as e:
                stats['errors'] += 1
                error_summary = f"🔴 <b>Error on Task {i}</b>: <code>{type(e).__name__}</code>"
                traceback.print_exc()
                await send_log(client, log_channel_int_id, f"{error_summary}\n<b>Details:</b> <code>{str(e)}</code>")

        # --- 5. FINAL REPORT ---
        end_time = datetime.now()
        duration = str(end_time - start_time).split('.')[0]
        summary = (
            f"🎉 <b>All Tasks Complete!</b> 🎉\n\n"
            f"<b>📊 Final Stats:</b>\n"
            f"  - <b>Polls Forwarded:</b> <code>{stats['polls_forwarded']}</code>\n"
            f"  - <b>Non-Polls Skipped:</b> <code>{stats['non_polls_skipped']}</code>\n"
            f"  - <b>Errors Encountered:</b> <code>{stats['errors']}</code>\n\n"
            f"⏱️ <b>Total Duration:</b> <code>{duration}</code>"
        )
        await send_log(client, log_channel_int_id, summary)

if __name__ == "__main__":
    asyncio.run(main())
