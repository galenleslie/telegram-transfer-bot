import os
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from google.cloud import vision
import io
import re

# Setup Google Vision API
vision_client = vision.ImageAnnotatorClient.from_service_account_json("vision-api-bot.json")

# Helper: extract and format transfer data
def parse_transfer_text(text):
    sender = re.search(r'Dari\s+(.+)', text)
    receiver = re.search(r'Ke\s+(.+)', text)
    amount = re.search(r'Rp\s?([0-9.]+)', text)
    txn_id = re.search(r'(20\d{16,})', text)
    return {
        "sender": sender.group(1).strip() if sender else "UnknownSender",
        "receiver": receiver.group(1).strip() if receiver else "UnknownReceiver",
        "amount": amount.group(1).strip().replace(".", "") if amount else "0",
        "txn_id": txn_id.group(1) if txn_id else "000000"
    }

# Process image and respond
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    img_path = f"{photo.file_id}.jpg"
    await file.download_to_drive(img_path)

    with io.open(img_path, "rb") as image_file:
        content = image_file.read()
        image = vision.Image(content=content)
        response = vision_client.text_detection(image=image)
        text = response.text_annotations[0].description if response.text_annotations else ""

    parsed = parse_transfer_text(text)
    new_filename = f"{parsed['sender']}_to_{parsed['receiver']}_{parsed['amount']}_{parsed['txn_id']}.jpg"
    os.rename(img_path, new_filename)

    await update.message.reply_text(f"✅ File renamed to: `{new_filename}`", parse_mode="Markdown")

# Start bot
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.run_polling()
