import os
import asyncio
import nest_asyncio
from PyPDF2 import PdfReader
from telegram import Bot
from google.generativeai import generativeai as ga

# Allow nested asyncio (needed in some environments like Jupyter/GitHub Actions)
nest_asyncio.apply()

# ====== CONFIGURATION ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini
ga.configure(api_key=GEMINI_API_KEY)

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
    """Send text to Gemini for formatting for Telegram-friendly messages."""
    try:
        response = ga.chat(messages=[{"role": "user", "content": prompt}])
        return response.get("content", "")
    except Exception as e:
        print(f"❌ Gemini API error: {e}")
        if BOT_TOKEN and CHAT_ID:
            bot = Bot(token=BOT_TOKEN)
            await bot.send_message(
                chat_id=CHAT_ID,
                text="⚠️ Gemini API quota reached or request failed!"
            )
        return ""

async def send_text_to_telegram(text):
    """Send long text in chunks to Telegram to avoid limits (~4096 chars per message)."""
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ BOT_TOKEN or CHAT_ID not set. Aborting.")
        return

    bot = Bot(token=BOT_TOKEN)
    chunk_size = 3500  # safe limit
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        try:
            await bot.send_message(chat_id=CHAT_ID, text=chunk)
            await asyncio.sleep(2)  # avoid Telegram flood limits
        except Exception as e:
            print(f"❌ Failed to send chunk: {e}")

async def main():
    # Look for all PDFs in the repo root
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

        # Optional: send to Gemini for Telegram formatting
        prompt = (
            f"Format the following text for sending to Telegram. "
            f"Only use plain text compatible with Telegram. Preserve questions/answers if present.\n\n{text}"
        )
        formatted_text = await send_to_gemini(prompt)

        # Fallback to raw text if Gemini fails
        if not formatted_text.strip():
            formatted_text = text

        await send_text_to_telegram(formatted_text)

if __name__ == "__main__":
    asyncio.run(main())
