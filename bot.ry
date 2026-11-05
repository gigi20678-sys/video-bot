import asyncio
import os
import re
import uuid

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile, Message
from aiohttp import web
from yt_dlp import YoutubeDL


TOKEN = os.getenv("BOT_TOKEN")
TMP = "/tmp/dl"
os.makedirs(TMP, exist_ok=True)

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

URL_RE = re.compile(r"https?://\S+")


def run_ytdlp(url: str) -> str:
    """Скачивает видео и возвращает путь к готовому файлу."""
    out = os.path.join(TMP, f"{uuid.uuid4().hex}.%(ext)s")
    opts = {
        "outtmpl": out,
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "max_filesize": 512 * 1024 * 1024,
        "http_headers": {"User-Agent": "Mozilla/5.0"},
        # Для закрытых видео (Instagram/TikTok/ВК) раскомментируй:
        # "cookiesfrombrowser": ("chrome",),
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)

    for cand in (path, os.path.splitext(path)[0] + ".mp4"):
        if os.path.exists(cand):
            return cand
    raise FileNotFoundError("файл не найден")


@dp.message(F.text & F.text.startswith("/start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Скачиваю видео по ссылке.\n\n"
        "Поддерживаю YouTube, TikTok, Instagram*, X, ВК, Reddit, Twitch, "
        "Rutube и ещё ~1700 сайтов.\n"
        "*приватные и закрытые видео требуют cookie браузера\n\n"
        "Просто пришли ссылку."
    )


@dp.message(F.text)
async def handle_link(message: Message) -> None:
    text = message.text or ""
    match = URL_RE.search(text)
    if not match:
        await message.answer("Пришли ссылку на видео 👇")
        return

    url = match.group(0)
    status = await message.answer("⏳ Качаю…")

    try:
        path = await asyncio.to_thread(run_ytdlp, url)
        size_mb = os.path.getsize(path) / 1024 / 1024
        if size_mb > 50:
            await message.answer(
                f"⚠️ Файл весит {size_mb:.1f} МБ, а бот не может отправить больше 50 МБ.\n"
                "Скачай вручную или попроси — добавлю сжатие через ffmpeg."
            )
        else:
            await message.answer_document(
                FSInputFile(path, filename=os.path.basename(path)),
                caption=f"✅ Готово ({size_mb:.1f} МБ)",
            )
    except Exception as exc:
        await message.answer(f"❌ Не получилось: <code>{exc}</code>")
    finally:
        try:
            await status.delete()
        except Exception:
            pass


async def health(request: web.Request) -> web.Response:
    """Нужен, чтобы Render не усыплял сервис."""
    return web.Response(text="ok")


async def main() -> None:
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 10000)))
    await site.start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
