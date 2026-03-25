import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import yt_dlp
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import aiofiles
import json
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "Bot is running!", 200

def run_web_server():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# ================ КОНФИГУРАЦИЯ ================
API_ID = int(os.environ.get('API_ID', 29084027))
API_HASH = os.environ.get('API_HASH', 'd665a3a502fdbfd2a4ff1cf1e0f24fae')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8689403465:AAE4i9f1T6Hu71y1zPJ13NW91GihkiL0nVU')

REQUIRED_CHANNELS = [
    {
        "username": "ova713", 
        "name": "Канал", 
        "invite_link": "https://t.me/ova713",
        "required": True
    },
]

DOWNLOAD_PATH = "downloads"
Path(DOWNLOAD_PATH).mkdir(exist_ok=True)
Path("user_data").mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================ ПЕРЕВОДЫ ================
TRANSLATIONS = {
    "ru": {
        "welcome": "🎬 **YouTube Downloader Bot**\n\nПривет, {name}! 👋\n\n✅ Ты подписан на каналы!\n\n**📝 Как пользоваться:**\n1️⃣ Отправь ссылку на YouTube\n2️⃣ Выбери формат\n\n✨ **Особенности:**\n• Видео до **2 ГБ**\n• Быстрая загрузка",
        "not_subscribed": "📢 **Для использования бота подпишись на канал:**\n\n✅ **После подписки нажми кнопку \"Проверить\"**",
        "subscription_required": "❌ Вы не подписаны на каналы!",
        "subscription_confirmed": "✅ **Подписка подтверждена!**\n\nТеперь вы можете скачивать видео.",
        "subscription_checking": "✅ Проверяю подписку...",
        "subscription_ok": "✅ **Отлично, {name}!**\n\nТы подписан на каналы! 🎉\n\nОтправь ссылку на YouTube!",
        "subscription_failed": "❌ **Не все подписки оформлены!**\n\n",
        "select_format": "✅ **Ссылка сохранена!**\n\n📥 **Выбери формат:**",
        "downloading": "⏳ **{format}**\n\n📥 Скачиваю и отправляю...",
        "download_error": "❌ **Ошибка**\n\n{error}",
        "no_url": "❌ **Сначала отправь ссылку на YouTube!**",
        "audio": "🎵 Аудио",
        "video": "🎬 Видео",
        "check": "✅ Проверить подписку",
        "our_channel": "📢 Наш канал",
        "audio_download": "🎵 Аудио (MP3)",
        "video_download": "🎬 Видео",
        "downloading_audio": "🎵 Скачиваю аудио...",
        "downloading_video": "🎬 Скачиваю видео...",
    },
    "en": {
        "welcome": "🎬 **YouTube Downloader Bot**\n\nHello, {name}! 👋\n\n✅ You are subscribed!\n\n**📝 How to use:**\n1️⃣ Send a YouTube link\n2️⃣ Choose format",
        "not_subscribed": "📢 **Subscribe to the channel:**\n\n✅ **After subscribing, press \"Check\"**",
        "subscription_required": "❌ You are not subscribed!",
        "subscription_confirmed": "✅ **Subscription confirmed!**\n\nNow you can download videos.",
        "subscription_checking": "✅ Checking subscription...",
        "subscription_ok": "✅ **Great, {name}!** 🎉\n\nSend a YouTube link!",
        "subscription_failed": "❌ **Not subscribed!**\n\n",
        "select_format": "✅ **Link saved!**\n\n📥 **Choose format:**",
        "downloading": "⏳ **{format}**\n\n📥 Downloading...",
        "download_error": "❌ **Error**\n\n{error}",
        "no_url": "❌ **Send a YouTube link first!**",
        "audio": "🎵 Audio",
        "video": "🎬 Video",
        "check": "✅ Check subscription",
        "our_channel": "📢 Our Channel",
        "audio_download": "🎵 Audio (MP3)",
        "video_download": "🎬 Video",
        "downloading_audio": "🎵 Downloading audio...",
        "downloading_video": "🎬 Downloading video...",
    },
    "tg": {
        "welcome": "🎬 **Боти зеркашӣ аз YouTube**\n\nСалом, {name}! 👋\n\n✅ Шумо обуна шудаед!\n\n**📝 Тарзи истифода:**\n1️⃣ Истиноди YouTube фиристед\n2️⃣ Форматро интихоб кунед",
        "not_subscribed": "📢 **Ба канал обуна шавед:**\n\n✅ **Пас аз обуна \"Санҷиш\"-ро пахш кунед**",
        "subscription_required": "❌ Шумо обуна нестед!",
        "subscription_confirmed": "✅ **Обуна тасдиқ шуд!**\n\nАкнун видео боргирӣ кунед.",
        "subscription_checking": "✅ Обунаро санҷида истодаам...",
        "subscription_ok": "✅ **Олиҷаноб, {name}!** 🎉\n\nИстиноди YouTube фиристед!",
        "subscription_failed": "❌ **Обуна иҷро нашудааст!**\n\n",
        "select_format": "✅ **Истинод нигоҳ дошта шуд!**\n\n📥 **Форматро интихоб кунед:**",
        "downloading": "⏳ **{format}**\n\n📥 Боргирӣ...",
        "download_error": "❌ **Хатогӣ**\n\n{error}",
        "no_url": "❌ **Аввал истиноди YouTube фиристед!**",
        "audio": "🎵 Аудио",
        "video": "🎬 Видео",
        "check": "✅ Санҷиши обуна",
        "our_channel": "📢 Канали мо",
        "audio_download": "🎵 Аудио (MP3)",
        "video_download": "🎬 Видео",
        "downloading_audio": "🎵 Аудио боргирӣ...",
        "downloading_video": "🎬 Видео боргирӣ...",
    }
}

LANGUAGES = {"ru": "🇷🇺 Русский", "en": "🇬🇧 English", "tg": "🇹🇯 Тоҷикӣ"}

# ================ ОСНОВНОЙ КЛАСС ================
class YouTubeBot:
    def __init__(self, api_id, api_hash, bot_token):
        self.api_id = api_id
        self.api_hash = api_hash
        self.bot_token = bot_token
        self.client = None
        self.user_data = {}
        self.user_cache = {}
        self.downloading_users = set()
        
    async def load_user_data(self):
        try:
            async with aiofiles.open('user_data/users.json', 'r', encoding='utf-8') as f:
                self.user_cache = json.loads(await f.read())
        except:
            self.user_cache = {}
    
    async def save_user_data(self):
        try:
            async with aiofiles.open('user_data/users.json', 'w', encoding='utf-8') as f:
                await f.write(json.dumps(self.user_cache, indent=2, ensure_ascii=False))
        except:
            pass
    
    def get_user_language(self, user_id):
        return self.user_cache.get(user_id, {}).get('language', 'ru')
    
    def get_text(self, user_id, key, **kwargs):
        lang = self.get_user_language(user_id)
        text = TRANSLATIONS.get(lang, TRANSLATIONS['ru']).get(key, key)
        if kwargs:
            return text.format(**kwargs)
        return text
    
    async def set_user_language(self, user_id, language):
        if user_id not in self.user_cache:
            self.user_cache[user_id] = {}
        self.user_cache[user_id]['language'] = language
        await self.save_user_data()
    
    async def check_subscription(self, user_id):
        if not REQUIRED_CHANNELS:
            return True, []
        not_subscribed = []
        for channel in REQUIRED_CHANNELS:
            try:
                entity = await self.client.get_entity(channel["username"])
                try:
                    await self.client.get_permissions(entity, user_id)
                except:
                    not_subscribed.append(channel)
            except:
                not_subscribed.append(channel)
        return len(not_subscribed) == 0, not_subscribed
    
    async def start(self):
        await self.load_user_data()
        self.client = TelegramClient('bot_session', self.api_id, self.api_hash)
        await self.client.start(bot_token=self.bot_token)
        
        @self.client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            user_id = event.sender_id
            if user_id not in self.user_cache:
                buttons = [[Button.inline("🇷🇺 Русский", "lang_ru"), Button.inline("🇬🇧 English", "lang_en")],
                          [Button.inline("🇹🇯 Тоҷикӣ", "lang_tg")]]
                await event.reply("🌐 **Выберите язык / Choose language / Забон интихоб кунед:**", buttons=buttons)
                return
            
            all_subscribed, _ = await self.check_subscription(user_id)
            if all_subscribed:
                buttons = [[Button.inline("🎵 Аудио", "audio"), Button.inline("🎬 Видео", "video")]]
                await event.reply(self.get_text(user_id, "welcome", name=event.sender.first_name or "Пользователь"), buttons=buttons)
            else:
                buttons = [[Button.url("📢 Канал", "https://t.me/ova713")], [Button.inline("✅ Проверить", "check")]]
                await event.reply(self.get_text(user_id, "not_subscribed"), buttons=buttons)
        
        @self.client.on(events.NewMessage)
        async def url_handler(event):
            user_id = event.sender_id
            text = event.message.text.strip()
            if user_id not in self.user_cache:
                return
            if 'youtube.com' in text or 'youtu.be' in text:
                self.user_data[user_id] = {'url': text}
                buttons = [[Button.inline("🎵 Аудио", "audio"), Button.inline("🎬 Видео", "video")]]
                await event.reply(self.get_text(user_id, "select_format"), buttons=buttons)
        
        @self.client.on(events.CallbackQuery)
        async def callback_handler(event):
            user_id = event.sender_id
            data = event.data.decode()
            
            if data.startswith('lang_'):
                lang = data.replace('lang_', '')
                await self.set_user_language(user_id, lang)
                await event.answer()
                await start_handler(event)
                return
            
            if data == "check":
                all_subscribed, _ = await self.check_subscription(user_id)
                if all_subscribed:
                    buttons = [[Button.inline("🎵 Аудио", "audio"), Button.inline("🎬 Видео", "video")]]
                    await event.edit(self.get_text(user_id, "subscription_confirmed"), buttons=buttons)
                else:
                    buttons = [[Button.url("📢 Канал", "https://t.me/ova713")], [Button.inline("✅ Проверить", "check")]]
                    await event.edit(self.get_text(user_id, "not_subscribed"), buttons=buttons)
                return
            
            if data in ["audio", "video"]:
                if user_id in self.downloading_users:
                    await event.answer("Уже идет загрузка!")
                    return
                
                all_subscribed, _ = await self.check_subscription(user_id)
                if not all_subscribed:
                    await event.answer("Подпишитесь на канал!")
                    return
                
                url = self.user_data.get(user_id, {}).get('url')
                if not url:
                    await event.answer("Сначала отправьте ссылку!")
                    return
                
                self.downloading_users.add(user_id)
                format_name = "Аудио" if data == "audio" else "Видео"
                status = await event.respond(self.get_text(user_id, "downloading", format=format_name))
                
                try:
                    ydl_opts = {
                        'outtmpl': f'{DOWNLOAD_PATH}/%(title)s.%(ext)s',
                        'quiet': True,
                        'no_warnings': True,
                    }
                    if data == 'audio':
                        ydl_opts.update({
                            'format': 'bestaudio/best',
                            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]
                        })
                    else:
                        ydl_opts['format'] = 'best[height<=720]'
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        filename = ydl.prepare_filename(info)
                        if data == 'audio':
                            filename = filename.rsplit('.', 1)[0] + '.mp3'
                        
                        await self.client.send_file(event.chat_id, filename, caption=f"🎬 {info.get('title', 'Video')[:100]}")
                        os.remove(filename)
                        await status.delete()
                except Exception as e:
                    await status.edit(self.get_text(user_id, "download_error", error=str(e)[:200]))
                finally:
                    self.downloading_users.discard(user_id)
        
        logger.info("="*50)
        logger.info("🚀 БОТ ЗАПУЩЕН")
        logger.info("="*50)
        await self.client.run_until_disconnected()

async def main():
    bot = YouTubeBot(API_ID, API_HASH, BOT_TOKEN)
    await bot.start()

def run_bot():
    asyncio.run(main())

# ================ ЗАПУСК ================
threading.Thread(target=run_web_server, daemon=True).start()
threading.Thread(target=run_bot, daemon=True).start()

import time
while True:
    time.sleep(60)
