import os
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

print("--- MINIMAL CONNECTION TEST ---")

# --- 1. Load Credentials ---
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
session_string = os.getenv('SESSION_STRING')

if not all([api_id, api_hash, session_string]):
    print("🔴 FATAL ERROR: One or more secrets are missing.")
else:
    print("✅ Secrets loaded. Attempting to connect to Telegram...")
    try:
        # --- 2. Attempt Connection ---
        # We use 'with' to ensure the client disconnects properly
        with TelegramClient(StringSession(session_string), api_id, api_hash, timeout=30) as client:
            me = client.get_me()
            print("\n" + "="*40)
            print(f"✅✅✅ SUCCESS! ✅✅✅")
            print(f"Successfully connected as: {me.first_name} {me.last_name or ''}")
            print(f"Your User ID is: {me.id}")
            print("="*40 + "\n")
            print("Conclusion: Your credentials are working. The issue is in the main script.")
    except Exception as e:
        print("\n" + "="*40)
        print(f"🔴🔴🔴 FAILURE! 🔴🔴🔴")
        print(f"Could not connect. Error: {e}")
        print("="*40 + "\n")
        print("Conclusion: The problem is a block from Telegram on your credentials.")

