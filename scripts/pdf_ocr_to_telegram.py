import os
import glob
import asyncio
import nest_asyncio
from telegram import Bot
from pdf2image import convert_from_path, PDFInfoNotInstalledError
from PyPDF2 import PdfReader

def fallback_text_extract(pdf_path):
    reader = PdfReader(pdf_path)
    return "\n\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    
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

# Init Telegram bot
bot = Bot(token=BOT_TOKEN)

# ====== FUNCTIONS ======

def extract_text_with_gemini(pdf_path):
    """Use pdf2image + Gemini OCR to extract text."""
    print(f"📄 Processing PDF with Gemini OCR: {pdf_path}")
    try:
        images = convert_from_path(pdf_path, dpi=200)
    except PDFInfoNotInstalledError:
        print("❌ Poppler not installed or pdfinfo not found.")
        return None

    all_text = []
    for i, img in enumerate(images, start=1):
        print(f"🔍 OCR page {i}...")
        prompt = (
            "Extract all readable text from this page image. "
            "Output plain text only, no markdown, no special characters, "
            "formatted cleanly for Telegram. Avoid line breaks mid-sentence."
        )
        try:
            result = model.generate_content([prompt, img])
            text = result.text
        except Exception as e:
            print(f"❌ Gemini API error on page {i}: {e}")
            try:
                bot.send_message(
                    chat_id=CHAT_ID,
                    text=f"⚠️ Gemini API quota reached or OCR failed on page {i}."
                )
            except Exception as te:
                print(f"❌ Failed to notify Telegram: {te}")
            text = ""

        if text:
            all_text.append(text)

    return "\n\n".join(all_text)


def fallback_text_extract(pdf_path):
    """Fallback: extract text from PDF using PyPDF2 if Poppler/Gemini fails."""
    print(f"📄 Using PyPDF2 fallback for PDF: {pdf_path}")
    try:
        reader = PdfReader(pdf_path)
        text = "\n\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        return text
    except Exception as e:
        print(f"❌ PyPDF2 extraction failed: {e}")
        try:
            bot.send_message(chat_id=CHAT_ID, text=f"❌ Failed to extract PDF text with PyPDF2.")
        except Exception as te:
            print(f"❌ Failed to notify Telegram: {te}")
        return ""


async def send_text_to_telegram(text):
    """Send text in chunks under Telegram limit (4096 chars)."""
    if not text.strip():
        print("⚠️ No text to send.")
        return

    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    print(f"📤 Sending {len(chunks)} messages to Telegram...")
    for i, chunk in enumerate(chunks, start=1):
        await bot.send_message(chat_id=CHAT_ID, text=chunk)
        print(f"✅ Sent chunk {i}/{len(chunks)}")
        await asyncio.sleep(2)


# ====== MAIN ======
async def main():
    pdf_files = glob.glob("*.pdf")
    if not pdf_files:
        print("❌ No PDF file found in repo.")
        return

    pdf_path = pdf_files[0]

    text = extract_text_with_gemini(pdf_path)
    if not text:
        # Fallback if OCR failed
        text = fallback_text_extract(pdf_path)

    await send_text_to_telegram(text)


if __name__ == "__main__":
    asyncio.run(main())
