import os
import asyncio
import random
import traceback
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# --- SAFETY CONFIGURATION ---
MIN_DELAY_SECONDS = 2
MAX_DELAY_SECONDS = 5

async def main():
    print("--- SCRIPT INITIALIZING (DEBUG MODE) ---")

    # --- 1. CONFIGURATION ---
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    session_string = os.getenv('SESSION_STRING')
    source_channel_id = os.getenv('SOURCE_CHANNEL')
    destination_channel_id = os.getenv('DESTINATION_CHANNEL')

    if not all([api_id, api_hash, session_string, source_channel_id, destination_channel_id]):
        print("🔴 FATAL ERROR: One or more GitHub Secrets are missing.")
        return
    print("✅ Configuration loaded from secrets.")

    # --- 2. READ MESSAGE RANGE ---
    try:
        with open('range.txt', 'r') as f:
            line = next((l for l in f if l.strip()), None)
            start_id, end_id = map(int, line.strip().split('-'))
        print(f"✅ Message range to process: {start_id} to {end_id}")
    except Exception as e:
        print(f"🔴 FATAL ERROR: Could not read or parse range.txt. Details: {e}")
        return

    # --- 3. TELEGRAM CLIENT INITIALIZATION ---
    client = TelegramClient(StringSession(session_string), api_id, api_hash, timeout=60)

    async with client:
        print("✅ Telegram client created. Attempting to connect...")
        me = await client.get_me()
        print(f"✅ Successfully connected as user: {me.first_name} (ID: {me.id})")
        
        try:
            source_entity = await client.get_entity(source_channel_id)
            destination_entity = await client.get_entity(destination_channel_id)
            print(f"✅ Source entity found: '{source_entity.title}'")
            print(f"✅ Destination entity found: '{destination_entity.title}'")
        except Exception as e:
            print(f"🔴 FATAL ERROR: Could not find one of the channels. Please check your IDs/links.")
            print(f"   Details: {e}")
            return

        # --- 4. FETCH AND SEND MESSAGES ---
        message_ids = list(range(start_id, end_id + 1))
        print(f"\n--- Starting to process {len(message_ids)} message IDs ---")

        for msg_id in message_ids:
            print(f"\nProcessing Message ID: {msg_id}...")
            try:
                # DEBUG: Fetch the message
                message = await client.get_messages(source_entity, ids=msg_id)

                # DEBUG: Check if the message object exists
                if message:
                    print(f"  -> SUCCESS: Found message object for ID {msg_id}.")
                    print(f"  -> DEBUG: Message Type: {type(message)}")
                    print(f"  -> DEBUG: Has Text: {bool(message.text)}")
                    print(f"  -> DEBUG: Has Media: {bool(message.media)}")
                    
                    # Attempt to send the message
                    await client.send_message(
                        destination_entity,
                        message=message.text,
                        file=message.media
                    )
                    print(f"  -> ✅ SENT: Message ID {message.id} sent successfully.")
                else:
                    # This is the most likely reason for the previous silent failure.
                    print(f"  -> INFO: No message object returned for ID {msg_id}. It may be deleted or inaccessible.")
                    continue

            except FloodWaitError as e:
                print(f"  -> 🟡 WARNING: FloodWaitError. Pausing for {e.seconds + 5} seconds.")
                await asyncio.sleep(e.seconds + 5)

            except Exception:
                # This is the better error handling. It will print the full error trace.
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
    
