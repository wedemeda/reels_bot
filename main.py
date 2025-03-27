import asyncio
import logging
import os
import platform
import time

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.telegram import TelegramAPIServer
from aiogram.filters import Command
from aiogram.types import Message, URLInputFile
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


def link_from_inst(url):
    # service = webdriver.FirefoxService(executable_path='/usr/local/bin/geckodriver')#
    if platform.system() == "Windows":
        service = webdriver.FirefoxService(executable_path='geckodriver-v0.36.0-win64/geckodriver.exe')
    else:
        service = webdriver.FirefoxService(executable_path='geckodriver-v0.36.0-linux-aarch64/geckodriver')

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
            EC.presence_of_element_located((By.XPATH, "//p[@class='fc-button-label' and text()='Einwilligen']")))

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


@dp.message()
async def send_welcome(message: types.Message):
    if message.chat.id in ALLOWED_USERS:
        video_url = link_from_inst(message.text)
        video_file = URLInputFile(video_url)
        await bot.send_video(message.chat.id, video=video_file, width=720, height=1280)


@dp.message(F.Audio)
async def converting_audio_to_text(message: types.Message):
    if message.chat.id in ALLOWED_USERS:
        file_info = await bot.get_file(message.audio.file_id)
        text = file_info.file_path
        cmd = f"sudo cp {text} audio.m4a"
        os.system(cmd)
        os.system("sudo chmod 777 audio.m4a")
        cmd = "./get_duration.sh > 1.txt"
        os.system(cmd)
        with open("1.txt") as file:
            dura = file.read()
        print(dura)
        await bot.send_voice(message.chat.id, "audio.m4a", dura)


# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
