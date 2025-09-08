import os
import asyncio
import random
import traceback
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# --- SAFETY CONFIGURATION ---
MIN_DELAY_SECONDS = 0.5
MAX_DELAY_SECONDS = 1

# --- NEW: HELPER FUNCTION TO PARSE IDs FROM NUMBERS OR LINKS ---
def parse_id(value):
    """Extracts a message ID from a string, which can be a number or a TG link."""
    value = value.strip()
    if value.isdigit():
        return int(value)
    elif '/' in value:
        # For links like https://t.me/c/2478655415/96665, take the last part
        return int(value.split('/')[-1])
    else:
        raise ValueError(f"Invalid format for message ID: {value}")

async def main():
    print("--- SCRIPT INITIALIZING (POLLS-ONLY, ADVANCED PARSING MODE) ---")

    # --- 1. CONFIGURATION ---
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    session_string = os.getenv('SESSION_STRING')
    source_channel_id = os.getenv('SOURCE_CHANNEL')
    destination_channel_id = os.getenv('DESTINATION_CHANNEL')

    if not all([api_id, api_hash, session_string, source_channel_id, destination_channel_id]):
        print("🔴 FATAL ERROR: One or more GitHub Secrets are missing.")
        return

    # --- 2. REWRITTEN: ADVANCED RANGE PARSING LOGIC ---
    all_message_ids = []
    try:
        with open('range.txt', 'r') as f:
            lines = f.readlines()
        
        start_id = None
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split(':', 1)
            if len(parts) != 2:
                continue
            
            key = parts[0].strip().lower()
            value = parts[1].strip()

            if key == 'start':
                start_id = parse_id(value)
            elif key == 'end' and start_id is not None:
                end_id = parse_id(value)
                all_message_ids.extend(range(start_id, end_id + 1))
                start_id = None # Reset for the next pair
        
        if not all_message_ids:
             raise ValueError("range.txt contains no valid Start/End pairs.")

        print(f"✅ Successfully parsed range.txt. Total messages to process: {len(all_message_ids)}")

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
            print(f"🔴 FATAL ERROR: Could not find one of the channels.")
            print(f"   Details: {e}")
            return

        # --- 4. FETCH AND SEND MESSAGES ---
        print(f"\n--- Starting to process {len(all_message_ids)} message IDs ---")
        for msg_id in all_message_ids:
            # (The rest of the script remains the same)
            print(f"\nProcessing Message ID: {msg_id}...")
            try:
                message = await client.get_messages(source_entity, ids=msg_id)
                if message and message.poll:
                    print("  -> DETECTED: Message is a poll. Forwarding...")
                    await message.forward_to(destination_entity)
                    print(f"  -> ✅ FORWARDED: Poll from message ID {message.id}.")
                elif message:
                    print("  -> INFO: Message is not a poll. Ignoring.")
                else:
                    print(f"  -> INFO: No message object returned for ID {msg_id}. Skipping.")
            except FloodWaitError as e:
                print(f"  -> 🟡 WARNING: FloodWaitError. Pausing for {e.seconds + 5} seconds.")
                await asyncio.sleep(e.seconds + 5)
            except Exception:
                print(f"  -> 🔴 ERROR: An unexpected error occurred for message ID {msg_id}.")
                print("--- FULL ERROR TRACEBACK ---")
                traceback.print_exc()
                print("----------------------------")
            finally:
                delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
                print(f"  -> Pausing for {delay:.2f} seconds...")
                await asyncio.sleep(delay)
        print("\n--- ✅ Process Complete ---")

if __name__ == "__main__":
    asyncio.run(main())
        
