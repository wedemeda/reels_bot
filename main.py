import asyncio
import logging
import os
import platform
import time

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.telegram import TelegramAPIServer
from aiogram.filters import Command
from aiogram.types import Message, URLInputFile, FSInputFile
from dotenv import load_dotenv
from selenium import webdriver
from selenium.common import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
LOCAL_SERVER = os.getenv("LOCAL_SERVER")
ALLOWED_USERS = list(map(int, os.getenv("ALLOWED_USERS", "").split(",")))

local_server = TelegramAPIServer.from_base(LOCAL_SERVER)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, server=local_server)
dp = Dispatcher()


def get_geckodriver_path():
    system = platform.system().lower()
    arch = platform.machine().lower()
    driver_path = None

    # Определяем правильный путь к драйверу
    if system == 'windows':
        driver_path = 'geckodriver-v0.36.0-win64/geckodriver.exe'
    elif system == 'linux':
        if 'arm' in arch or 'aarch' in arch:
            driver_path = 'geckodriver-v0.36.0-linux-aarch64/geckodriver'
        else:
            driver_path = 'geckodriver-v0.36.0-linux64/geckodriver'

    return driver_path

def link_from_inst(url):
   # if platform.system() == "Windows":
   #     service = webdriver.FirefoxService(executable_path='geckodriver-v0.36.0-win64/geckodriver.exe')
   # else:
   #     service = webdriver.FirefoxService(executable_path='geckodriver-v0.36.0-linux-aarch64/geckodriver')
    service = webdriver.FirefoxService(executable_path=get_geckodriver_path())
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.set_preference(
        "general.useragent.override",
        "Mozilla/5.0 (iPad; CPU OS 10_2_1 like Mac OS X) AppleWebKit/602.4.6 (KHTML, like Gecko) Version/10.0 Mobile/14D27 Safari/602.1")

    driver = webdriver.Firefox(service=service, options=options)

    driver.get('https://snapinsta.app/')

    try:
        wait = WebDriverWait(driver, 5)
        button = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".fc-button.fc-cta-consent.fc-primary-button")))

        if button.is_displayed():
            button.click()
    except (TimeoutException, NoSuchElementException):
        print("Кнопка 'Einwilligen' не найдена, продолжаем выполнение теста.")
    time.sleep(3)

    driver.find_element(By.ID, "url").send_keys(url)
    driver.find_element(By.XPATH, '//*[@id="btn-submit"]').click()
    time.sleep(3)
    driver.find_element("tag name", "body").click()

    element = driver.find_element(By.CLASS_NAME, "download-bottom")
    link = element.find_element(By.TAG_NAME, 'a').get_attribute('href')
    print(link)
    driver.quit()
    return link


@dp.message(Command('start'))
async def start(message: Message):
    if message.chat.id in ALLOWED_USERS:
        await message.answer('Пришли мне ссылку на Reels и я пришлю тебе видео в ответ =)')


@dp.message(F.text)
async def send_welcome(message: types.Message):
    if message.chat.id in ALLOWED_USERS:
        video_url = link_from_inst(message.text)
        video_file = URLInputFile(video_url)
        await bot.send_video(message.chat.id, video=video_file, width=720, height=1280)


@dp.message(F.audio)
async def handle_audio_message(message: types.Message):
    if message.chat.id not in ALLOWED_USERS:
        return
    file_path = None
    try:
        # 1. Скачиваем аудиофайл
        file = await bot.get_file(message.audio.file_id)
        file_path = f"temp_audio_{message.message_id}.mp3"  # Уникальное имя файла

        # 2. Асинхронное скачивание
        await bot.download_file(file.file_path, destination=file_path)

        # 3. Получаем длительность аудио
        duration = await get_audio_duration(file_path)

        # 4. Отправляем голосовое сообщение обратно
        voice_message = FSInputFile(file_path)
        await message.answer_voice(voice_message, duration=int(duration))

    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)}")
    finally:
        # 5. Удаляем временный файл
        await safe_delete(file_path)


async def get_audio_duration(file_path: str) -> float:
    """Получает длительность аудио через ffprobe (асинхронно)"""

    if platform.system() == "Windows":
        ffprobe_path = "ffprobe.exe"
    else:
        ffprobe_path = "ffprobe"
    process = await asyncio.create_subprocess_exec(
        ffprobe_path,
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        file_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise Exception(f"Ошибка ffprobe: {stderr.decode()}")

    return float(stdout.decode().strip())


async def safe_delete(file_path: str):
    """Безопасное удаление файла"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except (FileNotFoundError, PermissionError, OSError):
        pass

# Запуск бота
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
