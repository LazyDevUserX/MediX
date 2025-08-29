import json
import asyncio
from aiogram import Bot

API_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

bot = Bot(token=API_TOKEN)

async def send_items(filename: str):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            items = json.load(f)
        if not items:
            raise ValueError("JSON file is empty.")
    except Exception as e:
        print(f"🤖 BOT ERROR 🤖\n\nFile '{filename}' is empty or invalid.\nError: {e}")
        return

    for idx, item in enumerate(items, start=1):
        try:
            if item["type"] == "message":
                # Normal text message
                await bot.send_message(chat_id=CHAT_ID, text=item["text"])

            elif item["type"] == "poll":
                options = item.get("options")
                question = item.get("question", "⚠️ Missing question")
                correct_option = item.get("correct_option")
                explanation = item.get("explanation")

                if not options:
                    raise KeyError("options")

                # Handle regular poll (null solution)
                if correct_option is None:
                    await bot.send_poll(
                        chat_id=CHAT_ID,
                        question=question,
                        options=options,
                        type="regular"
                    )
                    # Bot warning
                    await bot.send_message(
                        chat_id=CHAT_ID,
                        text=(
                            "🤖 BOT ERROR 🤖\n\n"
                            "Poll sent as REGULAR (no solution provided).\n\n"
                            f"Question: {question}"
                        )
                    )
                    # Always send explanation if exists
                    if explanation:
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text=f"📌 Explanation:\n{explanation}"
                        )

                else:
                    # Try to send quiz poll
                    try:
                        await bot.send_poll(
                            chat_id=CHAT_ID,
                            question=question,
                            options=options,
                            type="quiz",
                            correct_option_id=correct_option,
                            explanation=explanation if explanation else None,
                        )
                    except Exception as e:
                        if "explanation" in str(e).lower() and explanation:
                            # Retry without explanation
                            await bot.send_poll(
                                chat_id=CHAT_ID,
                                question=question,
                                options=options,
                                type="quiz",
                                correct_option_id=correct_option
                            )
                            # Send explanation separately
                            await bot.send_message(
                                chat_id=CHAT_ID,
                                text=f"📌 Explanation:\n{explanation}"
                            )
                        else:
                            raise e

            else:
                # Unknown type
                await bot.send_message(
                    chat_id=CHAT_ID,
                    text=(
                        "🤖 BOT ERROR 🤖\n\n"
                        f"Failed to send item #{idx}.\n"
                        f"Type: {item.get('type')}\n"
                        f"Error: Unsupported item type."
                    )
                )

        except Exception as e:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=(
                    "🤖 BOT ERROR 🤖\n\n"
                    f"Failed to send item #{idx}.\n"
                    f"Type: {item.get('type')}\n"
                    f"Error: {e}"
                )
            )

        # Small delay to avoid flood limits
        await asyncio.sleep(1.5)


if __name__ == "__main__":
    asyncio.run(send_items("ExtreamStress.json"))
