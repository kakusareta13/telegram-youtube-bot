import os
import asyncio
from telethon import TelegramClient, events
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "Bot is running!", 200

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

API_ID = 29084027
API_HASH = "d665a3a502fdbfd2a4ff1cf1e0f24fae"
BOT_TOKEN = "8689403465:AAE4i9f1T6Hu71y1zPJ13NW91GihkiL0nVU"

async def main():
    client = TelegramClient('bot', API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)
    
    @client.on(events.NewMessage)
    async def handler(event):
        await event.reply("Бот работает! ✅")
    
    print("Бот запущен!")
    await client.run_until_disconnected()

def run_bot():
    asyncio.run(main())

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=run_bot, daemon=True).start()
    
    import time
    while True:
        time.sleep(10)
