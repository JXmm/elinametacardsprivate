import asyncio
import json
import logging
import os
import random
import sys
from datetime import datetime

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web, ClientSession
from dotenv import load_dotenv
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from database import init_db, add_or_update_user, get_user, save_request, update_current_request, clear_current_request

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    print("BOT_TOKEN not found in .env")
    sys.exit(1)

# Инициализируем один раз — глобально
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
router = Router()
dp = Dispatcher()
dp.include_router(router)

# Initialize database
init_db()

# Load cards and help data
with open('cards.json', 'r', encoding='utf-8') as f:
    cards = json.load(f)

with open('help.json', 'r', encoding='utf-8') as f:
    help_questions = json.load(f)

# States to track user progress
user_states = {}

async def download_github_image(image_url: str, token: str) -> bytes | None:
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3.raw'
    }
    try:
        async with ClientSession() as session:
            async with session.get(image_url, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.read()
                else:
                    logging.error(f"Failed to download {image_url}: {resp.status}")
                    return None
    except Exception as e:
        logging.error(f"Error downloading {image_url}: {e}")
        return None

def get_ai_insight(query, block_card, resource_card):
    return f"AI Insight based on: {query}, Block: {block_card}, Resource: {resource_card}"

# === Handlers ===

@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    user_id = message.from_user.id
    first_name = message.from_user.first_name

    existing_user = get_user(user_id)
    if existing_user:
        greeting = "Дорогая...\n\nРада видеть тебя снова! 🌿"
    else:
        add_or_update_user(user_id, first_name)
        greeting = f"Дорогая, {first_name}...\n\nПривет! 🌿"

    await message.answer(greeting)
    await asyncio.sleep(2)
    text = "✨ Сейчас подумай о своем запросе... \n\nИ напиши его здесь одним предложением, чтобы материализовать... ✨"
    await message.answer(text)

    user_states[user_id] = {'step': 'waiting_for_request'}
    clear_current_request(user_id)

@router.message()
async def request_handler(message: Message) -> None:
    user_id = message.from_user.id
    if user_id not in user_states or user_states[user_id].get('step') != 'waiting_for_request':
        return

    user_states[user_id]['request'] = message.text
    user_states[user_id]['step'] = 'request_received'
    update_current_request(user_id, message.text)

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Вытащить карты", callback_data="draw_cards")
    await message.answer("ОТЛИЧНО! \n\nДавай начнем!💫", reply_markup=keyboard.as_markup())

@router.callback_query(lambda c: c.data == "draw_cards")
async def draw_cards_handler(callback: CallbackQuery) -> None:
    await callback.answer()  # Подтверждаем нажатие
    user_id = callback.from_user.id

    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    if not GITHUB_TOKEN:
        await callback.message.answer("Токен GitHub не установлен")
        return

    request_text = user_states.get(user_id, {}).get('request', "No specific request")

    block_cards = [c for c in cards if c['type'] == 'block']
    resource_cards = [c for c in cards if c['type'] == 'resource']

    if not block_cards or not resource_cards:
        await callback.message.answer("Ошибка: Карты недоступны!")
        return

    block_card = random.choice(block_cards)
    resource_card = random.choice(resource_cards)

    block_image_bytes = await download_github_image(block_card['image_url'], GITHUB_TOKEN)
    if not block_image_bytes:
        await callback.message.answer("Блок-карта не найдена")
        return

    resource_image_bytes = await download_github_image(resource_card['image_url'], GITHUB_TOKEN)
    if not resource_image_bytes:
        await callback.message.answer("Ресурс-карта не найдена")
        return

    await bot.send_photo(
        chat_id=user_id,
        photo=BufferedInputFile(block_image_bytes, filename=f"{block_card['id']}.png"),
        caption=block_card['description']
    )
    await asyncio.sleep(2)

    await bot.send_photo(
        chat_id=user_id,
        photo=BufferedInputFile(resource_image_bytes, filename=f"{resource_card['id']}.png"),
        caption=resource_card['description']
    )

    save_request(user_id, request_text, block_card['id'], resource_card['id'],
                 block_card['description'], resource_card['description'])
    clear_current_request(user_id)

    user_states[user_id] = {
        'step': 'waiting_for_feedback',
        'block_card': block_card,
        'resource_card': resource_card,
        'request': request_text
    }

    # Передаём user_id, а не callback
    asyncio.create_task(send_followup_questions(user_id))

async def send_followup_questions(user_id: int):
    await asyncio.sleep(300)  # 5 минут

    state = user_states.get(user_id)
    if not state or state.get('step') != 'waiting_for_feedback':
        return

    text = "Получила ли ты ответ на свой запрос, или тебе нужны подсказки?🆘"
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Нужны подсказки", callback_data="need_hints")
    keyboard.button(text="Получила❤️", callback_data="received_insights")

    try:
        await bot.send_message(chat_id=user_id, text=text, reply_markup=keyboard.as_markup())
        user_states[user_id]['step'] = 'waiting_for_hints_or_done'
    except Exception as e:
        logging.warning(f"Failed to send follow-up to {user_id}: {e}")

@router.callback_query(lambda c: c.data == "need_hints")
async def hints_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    user_id = callback.from_user.id
    state = user_states.get(user_id)
    if not state:
        await callback.message.answer("Извини, не могу найти твою сессию.")
        return

    block_card = state['block_card']
    resource_card = state['resource_card']

    block_questions = [q for q in help_questions if q['type'] == 'block']
    resource_questions = [q for q in help_questions if q['type'] == 'resource']

    # Отправляем по одному случайному вопросу от каждого типа
    if block_questions:
        q = random.choice(block_questions)
        await bot.send_message(user_id, f"{block_card['name']}: {q['question']}")
        await asyncio.sleep(10)

    if resource_questions:
        q = random.choice(resource_questions)
        await bot.send_message(user_id, f"{resource_card['name']}: {q['question']}")

    user_states[user_id]['step'] = 'hints_sent'

@router.callback_query(lambda c: c.data == "received_insights")
async def insights_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    user_id = callback.from_user.id
    state = user_states.pop(user_id, None)

    if state:
        # ai_insight = get_ai_insight(...)  # можно использовать позже
        pass

    text = "Замечательно! Пусть твой день будет наполнен ясностью и целью. Я здесь, если нужно другое гадание или хочешь углубить понимание."
    await callback.message.answer(text)

# === Main ===

def main():
    logging.basicConfig(level=logging.INFO)

    if os.getenv("RENDER_EXTERNAL_URL"):
        # Webhook mode
        external_url = os.getenv("RENDER_EXTERNAL_URL")
        WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
        webhook_url = f"{external_url}{WEBHOOK_PATH}"
        WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "elina_webhook_2025")

        async def on_startup(app):
            await bot.set_webhook(
                url=webhook_url,
                secret_token=WEBHOOK_SECRET,
                drop_pending_updates=True
            )

        app = web.Application()
        app.on_startup.append(on_startup)
        SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            secret_token=WEBHOOK_SECRET,
        ).register(app, path=WEBHOOK_PATH)

        setup_application(app, dp, bot=bot)
        web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
    else:
        # Polling mode
        asyncio.run(dp.start_polling(bot, skip_updates=True))

if __name__ == "__main__":
    main()