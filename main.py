import asyncio
import json
import logging
import os
import random
import sys
from datetime import datetime

from aiogram import Bot, types, Router, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import BufferedInputFile
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

# Initialize bot and dispatcher
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

# Function to download image with GitHub token
async def download_github_image(image_url: str, token: str) -> bytes | None:
    """Download image from private GitHub repo using bearer token"""
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

# AI insight stub (for future integration)
def get_ai_insight(query, block_card, resource_card):
    """
    Stub for AI integration. In the future, this will use RAG/LLM to generate insights
    based on user query and drawn cards.

    Args:
        query (str): User's request
        block_card: Block card description
        resource_card: Resource card description

    Returns:
        str: AI-generated insight (currently returns a placeholder)
    """
    return f"AI Insight based on: {query}, Block: {block_card}, Resource: {resource_card}"

# Handlers
@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    user_id = message.from_user.id
    first_name = message.from_user.first_name

    # Check if user exists, greet accordingly
    existing_user = get_user(user_id)
    if existing_user:
        greeting = "Дорогая...\n\nРада видеть тебя снова! 🌿"
    else:
        add_or_update_user(user_id, first_name)
        greeting = f"Дорогая, {first_name}...\n\nПривет! 🌿"

    # Отправляем приветствие как новое сообщение, а не reply
    await bot.send_message(chat_id=message.chat.id, text=greeting)

    await asyncio.sleep(2)

    text = "✨ Сейчас подумай о своем запросе... \n\nИ напиши его здесь одним предложением, чтобы материализовать... ✨"

    await bot.send_message(chat_id=message.chat.id, text=text)

    user_states[user_id] = {'step': 'waiting_for_request'}
    clear_current_request(user_id)

@router.message()
async def request_handler(message: Message) -> None:
    user_id = message.from_user.id

    if user_id not in user_states or user_states[user_id]['step'] != 'waiting_for_request':
        return

    user_states[user_id]['request'] = message.text
    user_states[user_id]['step'] = 'request_received'

    update_current_request(user_id, message.text)

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Вытащить карты", callback_data="draw_cards")

    await bot.send_message(chat_id=message.chat.id, text="ОТЛИЧНО! \n\nДавай начнем!💫", reply_markup=keyboard.as_markup())

@router.callback_query(lambda c: c.data == "draw_cards")
async def draw_cards_handler(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id

    # Get token for GitHub URLs
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    if not GITHUB_TOKEN:
        await callback.message.reply("Токен GitHub не установлен")
        return

    # Get request from state
    if user_id in user_states and 'request' in user_states[user_id]:
        request_text = user_states[user_id]['request']
    else:
        request_text = "No specific request"

    # Filter cards by type
    block_cards = [c for c in cards if c['type'] == 'block']
    resource_cards = [c for c in cards if c['type'] == 'resource']

    if not block_cards or not resource_cards:
        await callback.message.reply("Ошибка: Карты недоступны!")
        return

    # Select random cards
    block_card = random.choice(block_cards)
    resource_card = random.choice(resource_cards)

    # Download images
    block_image_bytes = await download_github_image(block_card['image_url'], GITHUB_TOKEN)
    if not block_image_bytes:
        await callback.message.reply("Блок-карта не найдена")
        return
    resource_image_bytes = await download_github_image(resource_card['image_url'], GITHUB_TOKEN)
    if not resource_image_bytes:
        await callback.message.reply("Ресурс-карта не найдена")
        return

    # Send block card with delay
    await bot.send_photo(
        chat_id=user_id,
        photo=BufferedInputFile(block_image_bytes, filename=f"{block_card['id']}.png"),
        caption=block_card['description']
    )

    # Wait for user ready
    await asyncio.sleep(2)

    # Send resource card with delay
    await bot.send_photo(
        chat_id=user_id,
        photo=BufferedInputFile(resource_image_bytes, filename=f"{resource_card['id']}.png"),
        caption=resource_card['description']
    )

    # Save to database
    save_request(user_id, request_text, block_card['id'], resource_card['id'],
                block_card['description'], resource_card['description'])
    clear_current_request(user_id)

    # Store state for follow-up
    user_states[user_id] = {
        'step': 'waiting_for_feedback',
        'block_card': block_card,
        'resource_card': resource_card,
        'request': request_text
    }

    # Schedule follow-up message in 5 minutes
    asyncio.create_task(send_followup_questions(callback))

async def send_followup_questions(callback: CallbackQuery):
    """Send follow-up message after 5 minutes"""
    await asyncio.sleep(300)  # 5 minutes

    user_id = callback.from_user.id
    if user_id not in user_states or user_states[user_id]['step'] != 'waiting_for_feedback':
        return

    text = "Получила ли ты ответ на свой запрос, или тебе нужны подсказки?🆘"

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Нужны подсказки", callback_data="need_hints")
    keyboard.button(text="Получила❤️", callback_data="received_insights")

    await bot.send_message(chat_id=user_id, text=text, reply_markup=keyboard.as_markup())

    user_states[user_id]['step'] = 'waiting_for_hints_or_done'

@router.callback_query(lambda c: c.data == "need_hints")
async def hints_handler(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    if user_id not in user_states:
        await callback.message.reply("Извини, не могу найти твою сессию.")
        return

    state = user_states[user_id]
    block_card = state['block_card']
    resource_card = state['resource_card']

    # Get block questions
    block_questions = [q for q in help_questions if q['type'] == 'block']
    resource_questions = [q for q in help_questions if q['type'] == 'resource']

    # Send questions one by one with delays
    await send_question_sequence(user_id, block_questions, block_card)
    await send_question_sequence(user_id, resource_questions, resource_card)

    user_states[user_id]['step'] = 'hints_sent'

async def send_question_sequence(user_id, questions, card):
    if questions:
        question = random.choice(questions)
        await bot.send_message(user_id, f"{card['name']}: {question['question']}")
        await asyncio.sleep(10)  # Delay between questions

@router.callback_query(lambda c: c.data == "received_insights")
async def insights_handler(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id

    # Clean up state
    if user_id in user_states:
        state = user_states.pop(user_id)
        ai_insight = get_ai_insight(state['request'], state['block_card']['description'],
                                   state['resource_card']['description'])
        # Future: use ai_insight

    text = "Замечательно! Пусть твой день будет наполнен ясностью и целью. Я здесь, если нужно другое гадание или хочешь углубить понимание."

    await callback.message.reply(text)



def main():
    logging.basicConfig(level=logging.INFO)

    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "elina_webhook_2025")
    WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
    
    if os.getenv("RENDER_EXTERNAL_URL"):
        # Webhook mode
        external_url = os.getenv("RENDER_EXTERNAL_URL")
        webhook_url = f"{external_url}{WEBHOOK_PATH}"

        # Инициализация бота и диспетчера
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher()
        dp.include_router(router)

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
        # Polling mode (локально)
        async def run_polling():
            bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
            dp = Dispatcher()
            dp.include_router(router)
            await dp.start_polling(bot, skip_updates=True)

        asyncio.run(run_polling())

if __name__ == "__main__":
    main()

