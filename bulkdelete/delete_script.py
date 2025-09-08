import os
import asyncio
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, MessageDeleteForbiddenError

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
    print("--- BULK DELETE SCRIPT INITIALIZING ---")

    # --- 1. CONFIGURATION ---
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    session_string = os.getenv('SESSION_STRING')
    # Uses the same destination channel from your forwarder script
    target_channel_id = os.getenv('DESTINATION_CHANNEL')

    if not all([api_id, api_hash, session_string, target_channel_id]):
        print("🔴 FATAL ERROR: API_ID, API_HASH, SESSION_STRING, or DESTINATION_CHANNEL secrets are missing.")
        return

    # --- 2. PARSE RANGES FROM FILE ---
    all_message_ids = []
    try:
        # Note the path to the file inside the 'bulkdelete' folder
        with open('bulkdelete/delete_range.txt', 'r') as f:
            lines = f.readlines()
        
        start_id = None
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'): continue
            parts = line.split(':', 1)
            if len(parts) != 2: continue
            key, value = parts[0].strip().lower(), parts[1].strip()

            if key == 'start':
                start_id = parse_id(value)
            elif key == 'end' and start_id is not None:
                end_id = parse_id(value)
                all_message_ids.extend(range(start_id, end_id + 1))
                start_id = None
        
        if not all_message_ids:
             raise ValueError("delete_range.txt contains no valid Start/End pairs.")
        print(f"✅ Successfully parsed delete_range.txt. Total messages to delete: {len(all_message_ids)}")

    except Exception as e:
        print(f"🔴 FATAL ERROR: Could not read or parse delete_range.txt. Details: {e}")
        return

    # --- 3. TELEGRAM CLIENT INITIALIZATION ---
    client = TelegramClient(StringSession(session_string), api_id, api_hash, timeout=60)
    
    async with client:
        print("✅ Telegram client connected.")
        try:
            target_entity = await client.get_entity(target_channel_id)
            print(f"✅ Target entity found: '{target_entity.title}'")
        except Exception as e:
            print(f"🔴 FATAL ERROR: Could not find the target channel. Details: {e}")
            return
            
        # --- 4. DELETE MESSAGES IN BATCHES OF 100 ---
        chunk_size = 100
        chunks = [all_message_ids[i:i + chunk_size] for i in range(0, len(all_message_ids), chunk_size)]
        
        print(f"\n--- Starting deletion of {len(all_message_ids)} messages in {len(chunks)} chunks ---")
        
        for i, chunk in enumerate(chunks, 1):
            print(f"  Deleting chunk {i}/{len(chunks)} ({len(chunk)} messages)...")
            try:
                await client.delete_messages(target_entity, chunk)
                print(f"    -> ✅ SUCCESS: Chunk {i} deleted.")
            except MessageDeleteForbiddenError:
                print(f"    -> 🔴 ERROR: You do not have permission to delete messages in this channel.")
                break
            except FloodWaitError as e:
                print(f"    -> 🟡 WARNING: FloodWaitError. Pausing for {e.seconds + 5} seconds.")
                await asyncio.sleep(e.seconds + 5)
            except Exception as e:
                print(f"    -> 🔴 ERROR: An unexpected error occurred on chunk {i}: {e}")

            await asyncio.sleep(2) # Always add a small delay between batches to be safe
            
        print("\n--- ✅ Deletion process complete ---")

if __name__ == "__main__":
    asyncio.run(main())
      
