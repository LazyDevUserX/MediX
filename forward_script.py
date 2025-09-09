import os
import asyncio
import random
import traceback
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# --- SAFETY CONFIGURATION ---
MIN_DELAY_SECONDS = 1
MAX_DELAY_SECONDS = 2

# --- HELPER FUNCTION TO PARSE IDs ---
def parse_id(value):
    value = value.strip()
    if value.isdigit():
        return int(value)
    elif '/' in value:
        return int(value.split('/')[-1])
    else:
        raise ValueError(f"Invalid format for message ID: {value}")

async def main():
    print("--- SCRIPT INITIALIZING (ROBUST TWO-PHASE MODE) ---")

    # --- 1. CONFIGURATION ---
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    session_string = os.getenv('SESSION_STRING')
    source_channel_id = os.getenv('SOURCE_CHANNEL')
    destination_channel_id = os.getenv('DESTINATION_CHANNEL')

    if not all([api_id, api_hash, session_string, source_channel_id, destination_channel_id]):
        print("🔴 FATAL ERROR: One or more GitHub Secrets are missing.")
        return

    # --- 2. PHASE 1: PARSE range.txt INTO A TASK LIST ---
    tasks = []
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
                tasks.append({'type': 'message', 'content': value, 'line': line_num})
            elif key == 'start':
                start_id = parse_id(value)
            elif key == 'end' and start_id is not None:
                end_id = parse_id(value)
                tasks.append({'type': 'range', 'start': start_id, 'end': end_id, 'line': line_num})
                start_id = None
        
        if not tasks:
             raise ValueError("range.txt contains no valid tasks.")
        print(f"✅ Successfully parsed range.txt. Found {len(tasks)} tasks to execute.")

    except Exception as e:
        print(f"🔴 FATAL ERROR: Could not read or parse range.txt. Details: {e}")
        return

    # --- 3. TELEGRAM CLIENT INITIALIZATION ---
    client = TelegramClient(StringSession(session_string), api_id, api_hash, timeout=60)

    async with client:
        print("✅ Telegram client connected.")
        me = await client.get_me()
        print(f"✅ Successfully connected as user: {me.first_name} (ID: {me.id})")
        
        try:
            source_entity = await client.get_entity(source_channel_id)
            destination_entity = await client.get_entity(destination_channel_id)
            print(f"✅ Source entity found: '{source_entity.title}'")
            print(f"✅ Destination entity found: '{destination_entity.title}'")
        except Exception as e:
            print(f"🔴 FATAL ERROR: Could not find one of the channels. Details: {e}")
            return

        # --- 4. PHASE 2: EXECUTE THE TASK LIST ---
        print("\n--- Starting to execute tasks ---")
        for i, task in enumerate(tasks, 1):
            try:
                if task['type'] == 'message':
                    print(f"\n[{i}/{len(tasks)}] Executing Task: Send custom message...")
                    await client.send_message(destination_entity, task['content'])
                    print(f"  -> ✅ SENT: Custom message sent successfully.")
                    await asyncio.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))

                elif task['type'] == 'range':
                    print(f"\n[{i}/{len(tasks)}] Executing Task: Process poll range {task['start']}-{task['end']}...")
                    message_ids_for_batch = list(range(task['start'], task['end'] + 1))
                    
                    messages_in_batch = await client.get_messages(source_entity, ids=message_ids_for_batch)
                    valid_messages = [m for m in messages_in_batch if m]
                    print(f"  -> Found {len(valid_messages)} messages in this batch.")

                    for message in valid_messages:
                        print(f"    Processing Message ID: {message.id}...")
                        if message.poll:
                            print("      -> DETECTED: Message is a poll. Forwarding...")
                            await message.forward_to(destination_entity)
                            print(f"      -> ✅ FORWARDED: Poll from message ID {message.id}.")
                        else:
                            print("      -> INFO: Message is not a poll. Ignoring.")
                        
                        await asyncio.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))

            except FloodWaitError as e:
                print(f"  -> 🟡 WARNING: FloodWaitError on task {i}. Pausing for {e.seconds + 5} seconds.")
                await asyncio.sleep(e.seconds + 5)
            except Exception:
                print(f"  -> 🔴 ERROR: An unexpected error occurred on task {i}.")
                traceback.print_exc()

        print("\n--- ✅ All tasks complete ---")

if __name__ == "__main__":
    asyncio.run(main())
        
