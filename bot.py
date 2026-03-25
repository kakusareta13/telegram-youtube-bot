import os
import asyncio
import logging
import signal
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import yt_dlp
from telethon import TelegramClient, events, Button
from telethon.tl.types import Message, User, Channel
from telethon.errors import FloodWaitError, ChannelPrivateError, ChatWriteForbiddenError, UsernameNotOccupiedError
import aiofiles
import json
from flask import Flask, request
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

# МНОЖЕСТВО КАНАЛОВ (можно добавлять сколько угодно)
REQUIRED_CHANNELS = [
    {
        "username": "ova713", 
        "name": "Канал 1", 
        "invite_link": "https://t.me/ova713",
        "required": True
    },
]

DOWNLOAD_PATH = "downloads"
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2 ГБ
MAX_RETRIES = 3
RETRY_DELAY = 5

# Создаем папки
Path(DOWNLOAD_PATH).mkdir(exist_ok=True)
Path("user_data").mkdir(exist_ok=True)

# ================ ПЕРЕВОДЫ ================
TRANSLATIONS = {
    "ru": {
        "welcome": "🎬 **YouTube Downloader Bot**\n\nПривет, {name}! 👋\n\n✅ Ты подписан на все каналы!\n\n**📝 Как пользоваться:**\n1️⃣ Отправь ссылку на YouTube\n2️⃣ Выбери формат командой или кнопкой\n\n✨ **Особенности:**\n• Видео до **2 ГБ**\n• Быстрая загрузка\n\n💡 *Используй кнопки ниже*",
        "not_subscribed": "📢 **Для использования бота необходимо подписаться на каналы:**\n\n✅ **После подписки нажми кнопку \"Проверить\"**",
        "subscription_required": "❌ Вы не подписаны на каналы!",
        "subscription_confirmed": "✅ **Подписка подтверждена!**\n\nТеперь вы можете скачивать видео. Отправьте ссылку на YouTube.",
        "subscription_checking": "✅ Проверяю подписку...",
        "subscription_ok": "✅ **Отлично, {name}!**\n\nТы подписан на все каналы! 🎉\n\nТеперь можешь скачивать видео. Отправь ссылку на YouTube!",
        "subscription_failed": "❌ **Не все подписки оформлены!**\n\n",
        "help": "🔍 **Помощь по использованию бота**\n\n**📥 Команды:**\n• `/start` - Главное меню\n• `/help` - Эта справка\n• `/lang` - Выбрать язык\n• `/audio` - Скачать MP3\n• `/video` - Скачать видео\n• `/check` - Проверить подписку\n\n**🎯 Как скачать:**\n1️⃣ Отправь ссылку на YouTube\n2️⃣ Выбери формат командой или кнопкой\n3️⃣ Дождись загрузки\n\n**⚠️ Ограничения:**\n• Максимальный размер: 2 ГБ\n• Видео в лучшем качестве (до 1080p)\n\n**❓ Вопросы:** @ova713",
        "select_format": "✅ **Ссылка сохранена!**\n\n📥 **Выбери формат:**",
        "downloading": "⏳ **{format}**\n\n📥 Скачиваю и отправляю...",
        "download_error": "❌ **Ошибка**\n\n{error}",
        "flood_wait": "⏳ **Превышен лимит**\nПодожди {seconds} сек.",
        "user_blocked": "❌ **Пользователь заблокировал бота**\n\nЧтобы скачивать видео, нужно разблокировать бота.",
        "already_downloading": "⏳ **У вас уже идет загрузка!**\n\nПодождите, пока текущая загрузка завершится.",
        "no_url": "❌ **Сначала отправь ссылку на YouTube!**\n\n1️⃣ Отправь ссылку\n2️⃣ После этого выбери формат",
        "invalid_url": "❌ Пожалуйста, отправьте корректную ссылку YouTube",
        "language_selected": "🌐 **Язык изменен на {language}**",
        "select_language": "🌐 **Выберите язык / Choose language / Забон интихоб кунед:**",
        "audio": "🎵 Аудио",
        "video": "🎬 Видео",
        "check": "✅ Проверить подписку",
        "our_channel": "📢 Наш канал",
        "start_download": "📥 Начать",
        "audio_download": "🎵 Аудио (MP3)",
        "video_download": "🎬 Видео",
        "downloading_audio": "🎵 Скачиваю аудио...",
        "downloading_video": "🎬 Скачиваю видео...",
    },
    "en": {
        "welcome": "🎬 **YouTube Downloader Bot**\n\nHello, {name}! 👋\n\n✅ You are subscribed to all channels!\n\n**📝 How to use:**\n1️⃣ Send a YouTube link\n2️⃣ Choose format with command or button\n\n✨ **Features:**\n• Videos up to **2 GB**\n• Fast download\n\n💡 *Use the buttons below*",
        "not_subscribed": "📢 **To use the bot you need to subscribe to channels:**\n\n✅ **After subscribing, press the \"Check\" button**",
        "subscription_required": "❌ You are not subscribed to the channels!",
        "subscription_confirmed": "✅ **Subscription confirmed!**\n\nNow you can download videos. Send a YouTube link.",
        "subscription_checking": "✅ Checking subscription...",
        "subscription_ok": "✅ **Great, {name}!**\n\nYou are subscribed to all channels! 🎉\n\nNow you can download videos. Send a YouTube link!",
        "subscription_failed": "❌ **Not all subscriptions are completed!**\n\n",
        "help": "🔍 **Bot Help**\n\n**📥 Commands:**\n• `/start` - Main menu\n• `/help` - This help\n• `/lang` - Choose language\n• `/audio` - Download MP3\n• `/video` - Download video\n• `/check` - Check subscription\n\n**🎯 How to download:**\n1️⃣ Send a YouTube link\n2️⃣ Choose format with command or button\n3️⃣ Wait for download\n\n**⚠️ Limitations:**\n• Maximum size: 2 GB\n• Video in best quality (up to 1080p)\n\n**❓ Questions:** @ova713",
        "select_format": "✅ **Link saved!**\n\n📥 **Choose format:**",
        "downloading": "⏳ **{format}**\n\n📥 Downloading and sending...",
        "download_error": "❌ **Error**\n\n{error}",
        "flood_wait": "⏳ **Rate limit exceeded**\nWait {seconds} sec.",
        "user_blocked": "❌ **User blocked the bot**\n\nTo download videos, you need to unblock the bot.",
        "already_downloading": "⏳ **You already have a download in progress!**\n\nPlease wait until the current download finishes.",
        "no_url": "❌ **Send a YouTube link first!**\n\n1️⃣ Send a link\n2️⃣ Then choose format",
        "invalid_url": "❌ Please send a valid YouTube link",
        "language_selected": "🌐 **Language changed to {language}**",
        "select_language": "🌐 **Choose language:**",
        "audio": "🎵 Audio",
        "video": "🎬 Video",
        "check": "✅ Check subscription",
        "our_channel": "📢 Our Channel",
        "start_download": "📥 Start",
        "audio_download": "🎵 Audio (MP3)",
        "video_download": "🎬 Video",
        "downloading_audio": "🎵 Downloading audio...",
        "downloading_video": "🎬 Downloading video...",
    },
    "tg": {
        "welcome": "🎬 **Боти зеркашӣ аз YouTube**\n\nСалом, {name}! 👋\n\n✅ Шумо ба ҳамаи каналҳо обуна шудаед!\n\n**📝 Тарзи истифода:**\n1️⃣ Истиноди YouTube фиристед\n2️⃣ Форматро бо фармон ё тугма интихоб кунед\n\n✨ **Хусусиятҳо:**\n• Видео то **2 ГБ**\n• Боргирии зуд\n\n💡 *Тугмаҳои зерро истифода баред*",
        "not_subscribed": "📢 **Барои истифодаи бот ба каналҳо обуна шудан лозим аст:**\n\n✅ **Пас аз обуна шудан тугмаи \"Санҷиш\"-ро пахш кунед**",
        "subscription_required": "❌ Шумо ба каналҳо обуна нестед!",
        "subscription_confirmed": "✅ **Обуна тасдиқ карда шуд!**\n\nАкнун шумо метавонед видео боргирӣ кунед. Истиноди YouTube фиристед.",
        "subscription_checking": "✅ Обунаро санҷида истодаам...",
        "subscription_ok": "✅ **Олиҷаноб, {name}!**\n\nШумо ба ҳамаи каналҳо обуна шудаед! 🎉\n\nАкнун шумо метавонед видео боргирӣ кунед. Истиноди YouTube фиристед!",
        "subscription_failed": "❌ **Ҳамаи обунаҳо иҷро нашудаанд!**\n\n",
        "help": "🔍 **Кумак дар истифодаи бот**\n\n**📥 Фармонҳо:**\n• `/start` - Менюи асосӣ\n• `/help` - Ин кумак\n• `/lang` - Интихоби забон\n• `/audio` - Боргирии MP3\n• `/video` - Боргирии видео\n• `/check` - Санҷиши обуна\n\n**🎯 Тарзи боргирӣ:**\n1️⃣ Истиноди YouTube фиристед\n2️⃣ Форматро бо фармон ё тугма интихоб кунед\n3️⃣ Боргириро интизор шавед\n\n**⚠️ Маҳдудиятҳо:**\n• Андозаи максималӣ: 2 ГБ\n• Видео дар сифати беҳтарин (то 1080p)\n\n**❓ Саволҳо:** @ova713",
        "select_format": "✅ **Истинод нигоҳ дошта шуд!**\n\n📥 **Форматро интихоб кунед:**",
        "downloading": "⏳ **{format}**\n\n📥 Боргирӣ ва фиристодан...",
        "download_error": "❌ **Хатогӣ**\n\n{error}",
        "flood_wait": "⏳ **Маҳдудияти суръат аз ҳад гузашт**\n{seconds} сония интизор шавед.",
        "user_blocked": "❌ **Корбар ботро блок кардааст**\n\nБарои боргирии видео, ботро блок кушоед.",
        "already_downloading": "⏳ **Шумо аллакай боргирӣ доред!**\n\nЛутфан, то анҷоми боргирии ҷорӣ интизор шавед.",
        "no_url": "❌ **Аввал истиноди YouTube фиристед!**\n\n1️⃣ Истинод фиристед\n2️⃣ Сипас формат интихоб кунед",
        "invalid_url": "❌ Лутфан, истиноди дурусти YouTube фиристед",
        "language_selected": "🌐 **Забон ба {language} тағйир ёфт**",
        "select_language": "🌐 **Забонро интихоб кунед:**",
        "audio": "🎵 Аудио",
        "video": "🎬 Видео",
        "check": "✅ Санҷиши обуна",
        "our_channel": "📢 Канали мо",
        "start_download": "📥 Оғоз",
        "audio_download": "🎵 Аудио (MP3)",
        "video_download": "🎬 Видео",
        "downloading_audio": "🎵 Аудио боргирӣ карда истодаам...",
        "downloading_video": "🎬 Видео боргирӣ карда истодаам...",
    }
}

LANGUAGES = {
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
    "tg": "🇹🇯 Тоҷикӣ"
}

# ================ НАСТРОЙКА ЛОГИРОВАНИЯ ================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ================ ОСНОВНОЙ КЛАСС БОТА ================
class YouTubeBot:
    def __init__(self, api_id, api_hash, bot_token):
        self.api_id = api_id
        self.api_hash = api_hash
        self.bot_token = bot_token
        self.client = None
        self.user_data: Dict[int, Dict] = {}
        self.downloading_users: set = set()
        self.user_cache: Dict[int, Dict] = {}
        
    async def load_user_data(self):
        """Загрузка данных пользователей из файла"""
        try:
            async with aiofiles.open('user_data/users.json', 'r', encoding='utf-8') as f:
                content = await f.read()
                self.user_cache = json.loads(content)
        except FileNotFoundError:
            self.user_cache = {}
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            self.user_cache = {}
    
    async def save_user_data(self):
        """Сохранение данных пользователей"""
        try:
            async with aiofiles.open('user_data/users.json', 'w', encoding='utf-8') as f:
                await f.write(json.dumps(self.user_cache, indent=2, ensure_ascii=False))
        except Exception as e:
            logger.error(f"Ошибка сохранения данных: {e}")
    
    def is_private_chat(self, event) -> bool:
        """Проверяет, является ли чат личным (не группой и не каналом)"""
        try:
            if event.is_private:
                return True
            return False
        except:
            return False
    
    def get_user_language(self, user_id: int) -> str:
        """Получить язык пользователя"""
        if user_id in self.user_cache:
            return self.user_cache[user_id].get('language', 'ru')
        return 'ru'
    
    def get_text(self, user_id: int, key: str, **kwargs) -> str:
        """Получить текст на языке пользователя"""
        lang = self.get_user_language(user_id)
        text = TRANSLATIONS.get(lang, TRANSLATIONS['ru']).get(key, TRANSLATIONS['ru'][key])
        if kwargs:
            return text.format(**kwargs)
        return text
    
    async def set_user_language(self, user_id: int, language: str):
        """Установить язык пользователя"""
        if user_id not in self.user_cache:
            self.user_cache[user_id] = {}
        self.user_cache[user_id]['language'] = language
        await self.save_user_data()
    
    async def start(self):
        """Запуск бота с автоматическим переподключением"""
        max_retries = 10
        retry_delay = 10
        
        for attempt in range(max_retries):
            try:
                await self.load_user_data()
                self.client = TelegramClient('bot_session', self.api_id, self.api_hash)
                
                self.client.flood_sleep_threshold = 60
                self.client.session.set_dc(2, '149.154.167.51', 443)
                
                await self.client.start(bot_token=self.bot_token)
                await self.register_handlers()
                
                logger.info("="*50)
                logger.info("🚀 ЗАПУСК БОТА (MTProto - до 2 ГБ)")
                logger.info("="*50)
                
                print("="*50)
                print("🤖 YouTube Downloader Bot v3.0 (Multi-Language)")
                print("="*50)
                print(f"✅ Бот запущен")
                print(f"📢 Обязательные каналы: {len([c for c in REQUIRED_CHANNELS if c.get('required', True)])}")
                print(f"🌐 Языки: Русский, English, Тоҷикӣ")
                print("="*50)
                
                await self.client.run_until_disconnected()
                break
                
            except Exception as e:
                logger.error(f"Ошибка запуска (попытка {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    raise
    
    async def register_handlers(self):
        """Регистрация обработчиков"""
        
        @self.client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            if not self.is_private_chat(event):
                return
            await self.start_command(event)
        
        @self.client.on(events.NewMessage(pattern='/help'))
        async def help_handler(event):
            if not self.is_private_chat(event):
                return
            await self.help_command(event)
        
        @self.client.on(events.NewMessage(pattern='/lang'))
        async def lang_handler(event):
            if not self.is_private_chat(event):
                return
            await self.language_command(event)
        
        @self.client.on(events.NewMessage(pattern='/audio'))
        async def audio_handler(event):
            if not self.is_private_chat(event):
                return
            await self.handle_format_command(event, 'audio', 'best')
        
        @self.client.on(events.NewMessage(pattern='/video'))
        async def video_handler(event):
            if not self.is_private_chat(event):
                return
            await self.handle_format_command(event, 'video', '720')
        
        @self.client.on(events.NewMessage(pattern='/check'))
        async def check_handler(event):
            if not self.is_private_chat(event):
                return
            await self.check_subscription_command(event)
        
        @self.client.on(events.NewMessage)
        async def url_handler(event):
            if not self.is_private_chat(event):
                return
            await self.handle_url(event)
        
        @self.client.on(events.CallbackQuery)
        async def callback_handler(event):
            if not self.is_private_chat(event):
                return
            await self.handle_callback(event)
    
    async def check_subscription(self, user_id: int) -> Tuple[bool, List[Dict]]:
        """Проверяет подписку на все каналы/группы"""
        if not REQUIRED_CHANNELS:
            return True, []
        
        not_subscribed = []
        
        for channel in REQUIRED_CHANNELS:
            if not channel.get('required', True):
                continue
                
            username = channel["username"]
            try:
                entity = await self.client.get_entity(username)
                
                is_member = False
                
                try:
                    participant = await self.client.get_participant(entity, user_id)
                    if participant:
                        is_member = True
                        logger.info(f"✅ Пользователь {user_id} подписан на {username}")
                except:
                    try:
                        permissions = await self.client.get_permissions(entity, user_id)
                        if permissions:
                            is_member = True
                            logger.info(f"✅ Пользователь {user_id} подписан на {username}")
                    except:
                        pass
                
                if not is_member:
                    not_subscribed.append(channel)
                    logger.warning(f"❌ Пользователь {user_id} НЕ ПОДПИСАН на {username}")
                else:
                    logger.info(f"✅ Пользователь {user_id} ПОДПИСАН на {username}")
                        
            except Exception as e:
                logger.error(f"❌ Ошибка проверки {username}: {e}")
                not_subscribed.append(channel)
        
        all_subscribed = len(not_subscribed) == 0
        return all_subscribed, not_subscribed
    
    def get_subscription_buttons(self, user_id: int, not_subscribed: List[Dict] = None) -> List:
        """Создает кнопки для подписки"""
        channels = not_subscribed if not_subscribed else [ch for ch in REQUIRED_CHANNELS if ch.get('required', True)]
        
        buttons = []
        
        for ch in channels:
            buttons.append([Button.url(f"📢 {ch['name']}", ch['invite_link'])])
        
        buttons.append([Button.inline(self.get_text(user_id, "check"), b"check")])
        
        return buttons
    
    async def require_subscription(self, event, user_id: int) -> bool:
        """Проверяет подписку и возвращает True если все ок"""
        all_subscribed, not_subscribed = await self.check_subscription(user_id)
        
        if not all_subscribed:
            buttons = self.get_subscription_buttons(user_id, not_subscribed)
            
            await event.reply(
                self.get_text(user_id, "not_subscribed"),
                parse_mode='markdown',
                buttons=buttons,
                link_preview=False
            )
            return False
        return True
    
    async def start_command(self, event: Message):
        """/start"""
        user_id = event.sender_id
        user_name = event.sender.first_name or "Пользователь"
        
        if user_id not in self.user_cache or 'language' not in self.user_cache[user_id]:
            await self.language_command(event)
            return
        
        all_subscribed, not_subscribed = await self.check_subscription(user_id)
        
        if all_subscribed:
            buttons = [
                [Button.inline(self.get_text(user_id, "audio_download"), b"audio")],
                [Button.inline(self.get_text(user_id, "video_download"), b"video")],
                [Button.url(self.get_text(user_id, "our_channel"), "https://t.me/ova713")]
            ]
            
            await event.reply(
                self.get_text(user_id, "welcome", name=user_name),
                parse_mode='markdown',
                buttons=buttons
            )
        else:
            buttons = self.get_subscription_buttons(user_id, not_subscribed)
            
            await event.reply(
                self.get_text(user_id, "not_subscribed"),
                parse_mode='markdown',
                buttons=buttons,
                link_preview=False
            )
    
    async def language_command(self, event: Message):
        """/lang - Выбор языка"""
        user_id = event.sender_id
        
        buttons = []
        for lang_code, lang_name in LANGUAGES.items():
            buttons.append([Button.inline(lang_name, f"lang_{lang_code}")])
        
        buttons.append([Button.inline("⏩ Пропустить / Skip / Гузаштан", b"lang_skip")])
        
        await event.reply(
            "🌐 **Выберите язык / Choose language / Забон интихоб кунед:**",
            parse_mode='markdown',
            buttons=buttons
        )
    
    async def help_command(self, event: Message):
        """/help"""
        user_id = event.sender_id
        
        if not await self.require_subscription(event, user_id):
            return
        
        await event.reply(
            self.get_text(user_id, "help"),
            parse_mode='markdown',
            buttons=[[Button.url(self.get_text(user_id, "our_channel"), "https://t.me/ova713")]]
        )
    
    async def check_subscription_command(self, event: Message):
        """/check - Проверка подписки"""
        user_id = event.sender_id
        user_name = event.sender.first_name or "Пользователь"
        
        all_subscribed, not_subscribed = await self.check_subscription(user_id)
        
        if all_subscribed:
            await event.reply(
                self.get_text(user_id, "subscription_ok", name=user_name),
                parse_mode='markdown'
            )
        else:
            buttons = self.get_subscription_buttons(user_id, not_subscribed)
            
            await event.reply(
                self.get_text(user_id, "subscription_failed"),
                parse_mode='markdown',
                buttons=buttons,
                link_preview=False
            )
    
    async def handle_url(self, event: Message):
        """Ссылки на YouTube"""
        user_id = event.sender_id
        text = event.message.text.strip()
        
        if text.startswith('/'):
            return
        
        if user_id not in self.user_cache or 'language' not in self.user_cache[user_id]:
            await self.language_command(event)
            return
        
        if not await self.require_subscription(event, user_id):
            return
        
        youtube_domains = ['youtube.com', 'youtu.be', 'm.youtube.com', 'www.youtube.com']
        if not any(domain in text for domain in youtube_domains):
            return
        
        self.user_data[user_id] = {'url': text, 'timestamp': datetime.now().isoformat()}
        
        buttons = [
            [Button.inline(self.get_text(user_id, "audio"), b"audio"), 
             Button.inline(self.get_text(user_id, "video"), b"video")]
        ]
        
        await event.reply(
            self.get_text(user_id, "select_format"),
            parse_mode='markdown',
            buttons=buttons
        )
    
    async def handle_format_command(self, event: Message, format_type: str, quality: str):
        """Выбор формата"""
        user_id = event.sender_id
        
        if user_id in self.downloading_users:
            await event.reply(
                self.get_text(user_id, "already_downloading"),
                parse_mode='markdown'
            )
            return
        
        if not await self.require_subscription(event, user_id):
            return
        
        user_data = self.user_data.get(user_id, {})
        url = user_data.get('url')
        
        if not url:
            await event.reply(
                self.get_text(user_id, "no_url"),
                parse_mode='markdown'
            )
            return
        
        await self.process_download(event, url, format_type, quality)
    
    async def handle_callback(self, event):
        """Обработка нажатий на инлайн-кнопки"""
        user_id = event.sender_id
        data = event.data.decode('utf-8')
        
        logger.info(f"Callback от {user_id}: {data}")
        
        if data.startswith('lang_'):
            lang_code = data.replace('lang_', '')
            if lang_code in LANGUAGES:
                await self.set_user_language(user_id, lang_code)
                await event.answer(self.get_text(user_id, "language_selected", language=LANGUAGES[lang_code]))
                await self.start_command(event)
            elif lang_code == 'skip':
                await self.set_user_language(user_id, 'ru')
                await self.start_command(event)
            return
        
        if user_id not in self.user_cache or 'language' not in self.user_cache[user_id]:
            await self.language_command(event)
            return
        
        all_subscribed, not_subscribed = await self.check_subscription(user_id)
        
        if not all_subscribed:
            buttons = self.get_subscription_buttons(user_id, not_subscribed)
            text = self.get_text(user_id, "not_subscribed")
            
            await event.answer(self.get_text(user_id, "subscription_required"), alert=True)
            
            try:
                current_text = event.message.text
                if current_text != text:
                    await event.edit(
                        text,
                        parse_mode='markdown',
                        buttons=buttons,
                        link_preview=False
                    )
            except Exception as e:
                if "MessageNotModifiedError" not in str(e):
                    logger.error(f"Ошибка при редактировании: {e}")
            return
        
        if data == "check":
            await event.answer(self.get_text(user_id, "subscription_checking"))
            
            all_subscribed, not_subscribed = await self.check_subscription(user_id)
            
            if all_subscribed:
                text = self.get_text(user_id, "subscription_confirmed")
                buttons = [[Button.url(self.get_text(user_id, "our_channel"), "https://t.me/ova713")]]
            else:
                text = self.get_text(user_id, "not_subscribed")
                buttons = self.get_subscription_buttons(user_id, not_subscribed)
            
            try:
                await event.edit(
                    text,
                    parse_mode='markdown',
                    buttons=buttons,
                    link_preview=False
                )
            except Exception as e:
                if "MessageNotModifiedError" not in str(e):
                    logger.error(f"Ошибка при редактировании: {e}")
                
        elif data == "audio":
            await event.answer(self.get_text(user_id, "downloading_audio"))
            user_data = self.user_data.get(user_id, {})
            url = user_data.get('url')
            if url:
                await self.process_download_from_callback(event, url, 'audio', 'best')
            else:
                await event.answer(self.get_text(user_id, "no_url"), alert=True)
                
        elif data == "video":
            await event.answer(self.get_text(user_id, "downloading_video"))
            user_data = self.user_data.get(user_id, {})
            url = user_data.get('url')
            if url:
                await self.process_download_from_callback(event, url, 'video', '720')
            else:
                await event.answer(self.get_text(user_id, "no_url"), alert=True)
    
    async def process_download_from_callback(self, event, url: str, format_type: str, quality: str):
        """Обработка скачивания из callback"""
        user_id = event.sender_id
        
        if user_id in self.downloading_users:
            await event.answer(self.get_text(user_id, "already_downloading"), alert=True)
            return
        
        format_name = self.get_text(user_id, "audio") if format_type == 'audio' else self.get_text(user_id, "video")
        
        status_msg = await event.respond(
            self.get_text(user_id, "downloading", format=format_name),
            parse_mode='markdown'
        )
        
        try:
            result = await self.download_video(url, format_type, quality)
            
            if result[0] and os.path.exists(result[0]):
                file_path, title = result
                
                me = await self.client.get_me()
                caption = f"🎬 **{title[:100]}**\n\n📥 @{me.username}"
                
                await self.client.send_file(
                    event.chat_id,
                    file_path,
                    caption=caption,
                    supports_streaming=True
                )
                
                os.remove(file_path)
                await status_msg.delete()
                
                if user_id in self.user_data:
                    del self.user_data[user_id]
                
            else:
                await status_msg.edit(
                    self.get_text(user_id, "download_error", error=result[1][:200]),
                    parse_mode='markdown'
                )
                
        except FloodWaitError as e:
            await status_msg.edit(
                self.get_text(user_id, "flood_wait", seconds=e.seconds),
                parse_mode='markdown'
            )
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            error_text = str(e)
            if "User is blocked" in error_text:
                await status_msg.edit(
                    self.get_text(user_id, "user_blocked"),
                    parse_mode='markdown'
                )
            else:
                await status_msg.edit(
                    self.get_text(user_id, "download_error", error=error_text[:200]),
                    parse_mode='markdown'
                )
        finally:
            self.downloading_users.discard(user_id)
    
    def get_ydl_opts(self, format_type='audio', quality='best'):
        """Опции yt-dlp"""
        base_opts = {
            'outtmpl': os.path.join(DOWNLOAD_PATH, '%(title)s.%(ext)s'),
            'restrictfilenames': True,
            'windowsfilenames': True,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'retries': 10,
            'fragment_retries': 10,
            'socket_timeout': 60,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'extract_flat': False,
            'ignoreerrors': True,
            'nooverwrites': True,
            'continuedl': True,
            'extractor_args': {'youtube': {'skip': ['dash', 'hls']}},
            'geo_bypass': True,
            'geo_bypass_country': 'US',
        }
        
        if format_type == 'audio':
            base_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            base_opts['format'] = 'best[height<=1080]'
        
        return base_opts
    
    async def download_video(self, url: str, format_type: str, quality: str) -> tuple:
        """Скачивание видео"""
        ydl_opts = self.get_ydl_opts(format_type, quality)
        loop = asyncio.get_event_loop()
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Получаю информацию: {url}")
                
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
                
                if not info:
                    return None, "Не удалось получить информацию о видео"
                
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                
                if 'entries' in info:
                    return None, "Плейлисты не поддерживаются. Отправь отдельное видео."
                
                logger.info(f"Скачиваю: {title} ({duration//60}:{duration%60:02d})")
                
                filename = await loop.run_in_executor(None, lambda: ydl.prepare_filename(info))
                
                if format_type == 'audio':
                    filename = filename.rsplit('.', 1)[0] + '.mp3'
                
                await loop.run_in_executor(None, lambda: ydl.download([url]))
                
                if os.path.exists(filename):
                    size_mb = os.path.getsize(filename) / (1024 * 1024)
                    logger.info(f"Скачано: {filename} ({size_mb:.1f} MB)")
                    return filename, title
                else:
                    files = list(Path(DOWNLOAD_PATH).glob('*'))
                    if files:
                        latest = max(files, key=os.path.getctime)
                        return str(latest), title
                    else:
                        return None, "Файл не найден"
                        
        except Exception as e:
            logger.error(f"Ошибка скачивания: {e}")
            return None, str(e)
    
    async def process_download(self, event: Message, url: str, format_type: str, quality: str):
        """Отправка файла"""
        user_id = event.sender_id
        self.downloading_users.add(user_id)
        
        format_name = self.get_text(user_id, "audio") if format_type == 'audio' else self.get_text(user_id, "video")
        
        status_msg = await event.reply(
            self.get_text(user_id, "downloading", format=format_name),
            parse_mode='markdown'
        )
        
        try:
            result = await self.download_video(url, format_type, quality)
            
            if result[0] and os.path.exists(result[0]):
                file_path, title = result
                
                me = await self.client.get_me()
                caption = f"🎬 **{title[:100]}**\n\n📥 @{me.username}"
                
                await self.client.send_file(
                    event.chat_id,
                    file_path,
                    caption=caption,
                    supports_streaming=True
                )
                
                os.remove(file_path)
                await status_msg.delete()
                
                if user_id in self.user_data:
                    del self.user_data[user_id]
                
            else:
                await status_msg.edit(
                    self.get_text(user_id, "download_error", error=result[1][:200]),
                    parse_mode='markdown'
                )
                
        except FloodWaitError as e:
            await status_msg.edit(
                self.get_text(user_id, "flood_wait", seconds=e.seconds),
                parse_mode='markdown'
            )
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            error_text = str(e)
            if "User is blocked" in error_text:
                await status_msg.edit(
                    self.get_text(user_id, "user_blocked"),
                    parse_mode='markdown'
                )
            else:
                await status_msg.edit(
                    self.get_text(user_id, "download_error", error=error_text[:200]),
                    parse_mode='markdown'
                )
        finally:
            self.downloading_users.discard(user_id)


# ================ ЗАПУСК ================
bot_instance = None

async def main():
    """Главная функция"""
    global bot_instance
    bot_instance = YouTubeBot(API_ID, API_HASH, BOT_TOKEN)
    await bot_instance.start()

def run_bot():
    """Запуск бота в отдельном потоке"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except Exception as e:
        logger.error(f"Ошибка в потоке бота: {e}")
    finally:
        loop.close()

# ЗАПУСКАЕМ БОТА ПРИ ЗАГРУЗКЕ МОДУЛЯ
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()
