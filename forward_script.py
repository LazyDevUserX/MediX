import os
import asyncio
import random
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# --- SAFETY CONFIGURATION ---
MIN_DELAY_SECONDS = 2
MAX_DELAY_SECONDS = 5

async def main():
    print("Initializing script with safety measures...")

    # --- 1. CONFIGURATION ---
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    session_string = os.getenv('SESSION_STRING')
    source_channel_id = os.getenv('SOURCE_CHANNEL')
    destination_channel_id = os.getenv('DESTINATION_CHANNEL')

    if not all([api_id, api_hash, session_string, source_channel_id, destination_channel_id]):
        print("ERROR: One or more GitHub Secrets are missing.")
        return

    # --- 2. READ MESSAGE RANGE ---
    try:
        with open('range.txt', 'r') as f:
            line = next((l for l in f if l.strip()), None)
            start_id, end_id = map(int, line.strip().split('-'))
        print(f"Message range to process: {start_id} to {end_id}")
    except Exception as e:
        print(f"ERROR: Could not read or parse range.txt. Details: {e}")
        return

    # --- 3. TELEGRAM CLIENT INITIALIZATION ---
    client = TelegramClient(StringSession(session_string), api_id, api_hash)

    async with client:
        print("Telegram client connected.")
        source_entity = await client.get_entity(source_channel_id)
        destination_entity = await client.get_entity(destination_channel_id)

        # --- 4. FETCH AND SEND MESSAGES ---
        message_ids = list(range(start_id, end_id + 1))
        print(f"Starting to process {len(message_ids)} message IDs...")

        for msg_id in message_ids:
            try:
                message = await client.get_messages(source_entity, ids=msg_id)
                if message:
                    # Send a copy of the message (text, poll, media) without the forward header
                    await client.send_message(destination_entity, message=message)
                    print(f"Successfully sent message ID: {message.id}")
                else:
                    print(f"Message ID {msg_id} does not exist. Skipping.")
                    continue

            except FloodWaitError as e:
                # This is the main safety feature.
                print(f"FloodWaitError: Being rate-limited. Waiting for {e.seconds + 5} seconds.")
                await asyncio.sleep(e.seconds + 5)
                print(f"Skipping message ID {msg_id} due to flood wait. You can retry it later.")

            except Exception as e:
                print(f"An unexpected error occurred for message ID {msg_id}: {e}")

            finally:
                # This is a key safety feature to mimic human behavior.
                delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
                print(f"Waiting for {delay:.2f} seconds...")
                await asyncio.sleep(delay)

        print("\n--- Process Complete ---")

if __name__ == "__main__":
    asyncio.run(main())
                        
