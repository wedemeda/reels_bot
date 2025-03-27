import os

import pytest
from aiogram import Bot, types
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import URLInputFile
import time
from dotenv import load_dotenv
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import link_from_inst
from aiogram.client.telegram import TelegramAPIServer

load_dotenv()

LOCAL_SERVER = os.getenv("LOCAL_SERVER")
API_TOKEN = os.getenv("API_TOKEN")
TEST_CHAT_ID = os.getenv("TEST_CHAT_ID")
TEST_REELS_LINK = os.getenv("TEST_REELS_LINK")

local_server = TelegramAPIServer.from_base(LOCAL_SERVER)


# Функция для проверки работы бота
@pytest.mark.asyncio
async def test_send_video():
    bot = Bot(token=API_TOKEN, server=local_server)

    # Ссылка на Instagram Reels
    valid_url = TEST_REELS_LINK

    # Создаем объект Chat
    chat = types.Chat(id=int(TEST_CHAT_ID), type='private')  # Убедитесь, что тип чата правильный

    # Создаем объект Message с правильным chat
    types.Message(
        message_id=1,
        date=int(time.time()),
        chat=chat,  # Добавляем объект chat
        text=valid_url
    )

    # Отправка сообщения в бота
    video_url = link_from_inst(valid_url)
    video_file = URLInputFile(video_url)

    try:
        # Отправка видео
        response = await bot.send_video(chat_id=int(TEST_CHAT_ID), video=video_file, width=720, height=1280)
        assert response is not None  # Убедитесь, что ответ получен
        return  # Выход из теста, если все прошло успешно
    except TelegramRetryAfter:
        return True

