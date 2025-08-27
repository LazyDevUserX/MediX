import os
import glob
import asyncio
import nest_asyncio
from telegram import Bot
from pdf2image import convert_from_path
import google.generativeai as genai

# Allow nested asyncio
nest_asyncio.apply()

# ====== CONFIGURATION ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Init Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-1.5-pro")

# ====== FUNCTIONS ======

def extract_text_from_pdf(pdf_path):
    """Convert PDF to images and OCR each page with Gemini."""
    print(f"📄 Processing PDF: {pdf_path}")
    images = convert_from_path(pdf_path, dpi=200)

    all_text = []
    for i, img in enumerate(images, start=1):
        print(f"🔍 OCR on page {i}...")
        prompt = (
            "Extract all readable text from this page image. "
            "Output plain text only, no markdown, no special characters, "
            "formatted cleanly so it can be sent directly to Telegram. "
            "Avoid line breaks in the middle of sentences. Keep structure natural."
        )
        result = model.generate_content([prompt, img])
        all_text.append(result.text)

    return "\n\n".join(all_text)


async def send_text_to_telegram(text):
    """Send text to Telegram in chunks under 4096 characters."""
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ BOT_TOKEN or CHAT_ID missing.")
        return

    bot = Bot(token=BOT_TOKEN)

    # Split into chunks (Telegram has 4096 char limit)
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]

    print(f"📤 Sending {len(chunks)} messages to Telegram...")
    for i, chunk in enumerate(chunks, start=1):
        await bot.send_message(chat_id=CHAT_ID, text=chunk)
        print(f"✅ Sent chunk {i}/{len(chunks)}")
        await asyncio.sleep(2)


# ====== MAIN EXECUTION ======
async def main():
    pdf_files = glob.glob("*.pdf")
    if not pdf_files:
        print("❌ No PDF file found.")
        return

    pdf_path = pdf_files[0]
    text = extract_text_from_pdf(pdf_path)

    await send_text_to_telegram(text)

if __name__ == "__main__":
    asyncio.run(main())
