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

# --- HELPER FUNCTION TO PARSE IDs FROM NUMBERS OR LINKS ---
def parse_id(value):
    """Extracts a message ID from a string, which can be a number or a TG link."""
    value = value.strip()
    if value.isdigit():
        return int(value)
    elif '/' in value:
        return int(value.split('/')[-1])
    else:
        raise ValueError(f"Invalid format for message ID: {value}")

async def main():
    print("--- SCRIPT INITIALIZING (POLLS-ONLY, CUSTOM MESSAGES) ---")

    # --- 1. CONFIGURATION ---
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HSH')
    session_string = os.getenv('SESSION_STRING')
    source_channel_id = os.getenv('SOURCE_CHANNEL')
    destination_channel_id = os.getenv('DESTINATION_CHANNEL')

    if not all([api_id, api_hash, session_string, source_channel_id, destination_channel_id]):
        print("🔴 FATAL ERROR: One or more GitHub Secrets are missing.")
        return

    # --- 2. TELEGRAM CLIENT INITIALIZATION ---
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

        # --- 3. REWRITTEN: PROCESS RANGES AND MESSAGES FROM FILE ---
        print("\n--- Starting to process tasks from range.txt ---")
        try:
            with open('range.txt', 'r') as f:
                lines = f.readlines()
            
            start_id = None
            for line_num, line in enumerate(lines, 1):
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

                # --- NEW FEATURE LOGIC ---
                elif key == 'message':
                    print(f"\n--- Sending custom message from line {line_num} ---")
                    try:
                        await client.send_message(destination_entity, value)
                        print(f"  -> ✅ SENT: Custom message sent successfully.")
                        delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
                        print(f"  -> Pausing for {delay:.2f} seconds...")
                        await asyncio.sleep(delay)
                    except Exception as e:
                        print(f"  -> 🔴 ERROR: Could not send custom message. Reason: {e}")
                
                elif key == 'end' and start_id is not None:
                    end_id = parse_id(value)
                    
                    print(f"\n--- Processing new batch: {start_id}-{end_id} ---")
                    message_ids_for_batch = list(range(start_id, end_id + 1))
                    
                    messages_in_batch = await client.get_messages(source_entity, ids=message_ids_for_batch)
                    valid_messages = [m for m in messages_in_batch if m]
                    
                    print(f"  -> Found {len(valid_messages)} messages in this batch.")

                    for message in valid_messages:
                        print(f"  Processing Message ID: {message.id}...")
                        try:
                            if message.poll:
                                print("    -> DETECTED: Message is a poll. Forwarding...")
                                await message.forward_to(destination_entity)
                                print(f"    -> ✅ FORWARDED: Poll from message ID {message.id}.")
                            else:
                                print("    -> INFO: Message is not a poll. Ignoring.")
                        except FloodWaitError as e:
                            print(f"    -> 🟡 WARNING: FloodWaitError. Pausing for {e.seconds + 5} seconds.")
                            await asyncio.sleep(e.seconds + 5)
                        except Exception:
                            print(f"    -> 🔴 ERROR: An unexpected error occurred for message ID {message.id}.")
                            traceback.print_exc()
                        finally:
                            delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
                            print(f"    -> Pausing for {delay:.2f} seconds...")
                            await asyncio.sleep(delay)
                    
                    start_id = None # Reset for the next pair

        except Exception as e:
            print(f"🔴 FATAL ERROR: An error occurred while processing range.txt. Details: {e}")
            return

        print("\n--- ✅ Process Complete ---")

if __name__ == "__main__":
    asyncio.run(main())
        
