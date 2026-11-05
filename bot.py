import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import yt_dlp

TOKEN = os.getenv("BOT_TOKEN")
# Render автоматически выдает порты и внешние домены, считываем их:
PORT = int(os.getenv("PORT", 8080))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

if not TOKEN:
    raise ValueError("Не найден токен бота!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "Привет! Отправь мне ссылку на видео из YouTube, TikTok, Instagram, VK или другой соцсети, и я скачаю его для тебя."
    )

@dp.message()
async def download_video(message: types.Message):
    url = message.text.strip()
    
    if not url.startswith("http"):
        await message.answer("Пожалуйста, отправьте корректную ссылку на видео, начинающуюся с http:// или https://")
        return

    status_msg = await message.answer("⏳ Скачиваю видео, подождите немного...")

    output_template = f"%(id)s.%(ext)s"
    ydl_opts = {
        'outtmpl': output_template,
        'format': 'best[ext=mp4]/best',
        'max_filesize': 50 * 1024 * 1024,
    }

    filename = None
    try:
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        filename = await asyncio.to_thread(download)

        if filename and os.path.exists(filename):
            await bot.edit_message_text("📤 Загружаю видео в Telegram...", chat_id=message.chat.id, message_id=status_msg.message_id)
            
            video_file = types.FSInputFile(filename)
            await message.answer_video(video_file)
            
            await bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
            os.remove(filename)
        else:
            await bot.edit_message_text("Не удалось найти файл после скачивания.", chat_id=message.chat.id, message_id=status_msg.message_id)

    except Exception as e:
        error_text = str(e)
        if "File is larger than max-filesize" in error_text:
            await bot.edit_message_text("❌ Видео слишком большое (превышает лимит Telegram в 50 МБ).", chat_id=message.chat.id, message_id=status_msg.message_id)
        else:
            await bot.edit_message_text(f"❌ Произошла ошибка при скачивании:\n{error_text[:200]}", chat_id=message.chat.id, message_id=status_msg.message_id)
        
        if filename and os.path.exists(filename):
            os.remove(filename)

async def on_startup(bot: Bot):
    # Устанавливаем вебхук при запуске сервера
    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
    await bot.set_webhook(webhook_url)
    print(f"Вебхук установлен на: {webhook_url}")

async def main():
    dp.startup.register(on_startup)
    
    app = web.Application()
    # Регистрируем обработчик вебхуков для aiogram
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path="/webhook")
    
    setup_application(app, dp, bot=bot)
    
    # Запускаем локальный веб-сервер для приема запросов от Telegram
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"Сервер запущен на порту {PORT}")
    
    # Вечный цикл, чтобы сервер не завершал работу
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
