import os
import json
import asyncio
import nest_asyncio
from PyPDF2 import PdfReader
from telegram import Bot
from google.generativeai import client as gemini_client

# Allow nested asyncio (needed in some environments)
nest_asyncio.apply()

# ====== CONFIGURATION ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QUESTIONS_FILE = "questions.json"  # optional if using JSON later

# Initialize Gemini
gemini_client.configure(api_key=GEMINI_API_KEY)

# ====== FUNCTIONS ======

def extract_text_from_pdf(pdf_path):
    """Extract text directly from PDF using PyPDF2."""
    try:
        reader = PdfReader(pdf_path)
        text_pages = [page.extract_text() for page in reader.pages if page.extract_text()]
        text = "\n\n".join(text_pages)
        print(f"✅ Extracted text from {len(text_pages)} pages")
        return text
    except Exception as e:
        print(f"❌ Failed to extract text from PDF: {e}")
        return ""

async def send_to_gemini(prompt):
    """Send text to Gemini for formatting for Telegram-compatible messages."""
    try:
        result = gemini_client.generate_content([prompt])
        return result.text
    except Exception as e:
        print(f"❌ Gemini API error: {e}")
        # Notify on Telegram if Gemini fails
        if BOT_TOKEN and CHAT_ID:
            bot = Bot(token=BOT_TOKEN)
            bot.send_message(chat_id=CHAT_ID, text="⚠️ Gemini API quota reached or request failed!")
        return ""

async def send_text_to_telegram(text):
    """Send long text in chunks to avoid Telegram limits."""
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ BOT_TOKEN or CHAT_ID not set. Aborting.")
        return

    bot = Bot(token=BOT_TOKEN)
    # Telegram limit per message ~4096 chars
    chunk_size = 3500
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        try:
            await bot.send_message(chat_id=CHAT_ID, text=chunk)
            await asyncio.sleep(2)  # avoid flood limits
        except Exception as e:
            print(f"❌ Failed to send chunk: {e}")

async def main():
    # Look for all PDFs in repo root
    pdf_files = [f for f in os.listdir(".") if f.lower().endswith(".pdf")]
    if not pdf_files:
        print("❌ No PDF files found.")
        return

    for pdf_path in pdf_files:
        print(f"📄 Processing PDF: {pdf_path}")
        text = extract_text_from_pdf(pdf_path)

        if not text.strip():
            print(f"⚠️ No text found in {pdf_path}, skipping.")
            continue

        # Optional: send to Gemini for formatting to Telegram-friendly text
        prompt = f"Format the following text for sending to Telegram. Only use plain text and preserve questions/answers:\n\n{text}"
        formatted_text = await send_to_gemini(prompt)

        # If Gemini failed, fallback to raw text
        if not formatted_text.strip():
            formatted_text = text

        await send_text_to_telegram(formatted_text)

if __name__ == "__main__":
    asyncio.run(main())
