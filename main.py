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
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiohttp import web, ClientSession
from dotenv import load_dotenv
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from database import init_db, add_or_update_user, get_user, save_request, update_current_request, clear_current_request

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ BOT_TOKEN not found in .env")
    sys.exit(1)

# Глобальное состояние (для MVP)
user_states = {}

class CardNumber(StatesGroup):
    waiting_for_number = State()

async def download_github_image(image_url: str, token: str) -> bytes | None:
    headers = {}
    if token:
        headers['Authorization'] = f'token {token}'
    try:
        async with ClientSession() as session:
            async with session.get(image_url, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.read()
                else:
                    logging.error(f"❌ HTTP {resp.status} при загрузке: {image_url}")
                    return None
    except Exception as e:
        logging.error(f"💥 Ошибка загрузки изображения: {e}")
        return None

def create_router(cards, help_questions):
    router = Router()
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    if not GITHUB_TOKEN:
        logging.warning("⚠️ GITHUB_TOKEN не задан! Загрузка изображений из приватного репозитория невозможна.")

    # --- /start ---
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
        await asyncio.sleep(1)
        text = (
            "Когда ты вытянешь карту, например, блок, не спеши сразу читать описание. "
            "Посмотри на карту и выпиши свои чувства. \nПервое чувство, смотри и продолжай выписывать остальные, "
            "которые постепенно появляются. \n\nДальше, смотря на список, задай себе вопрос: "
            "<b>“Какое чувство ключевое?”</b> Продолжай смотреть на карту и подумай, "
            "<b>каким событием вызвано это чувство</b>, <b>о чем карта говорит, что напоминает</b>. \n\n"
            "И только после этого начинай читать описание карты!✨  \n\nГотова? \n\n"
            "А сейчас подумай и напиши мне свой запрос, над которым хочешь поработать сегодня...✨"
        )
        await message.answer(text, parse_mode=ParseMode.HTML)
        user_states[user_id] = {'step': 'waiting_for_request'}
        clear_current_request(user_id)

    # --- Обработка запроса ---
    @router.message()
    async def request_handler(message: Message) -> None:
        user_id = message.from_user.id
        if user_id not in user_states or user_states[user_id].get('step') != 'waiting_for_request':
            return

        user_states[user_id]['request'] = message.text
        user_states[user_id]['step'] = 'request_received'
        update_current_request(user_id, message.text)

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="Отправить запрос💫", callback_data="draw_cards")
        await message.answer("Отлично!✨", reply_markup=keyboard.as_markup())

    # --- Вытягивание карт ---
    @router.callback_query(lambda c: c.data == "draw_cards")
    async def draw_cards_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        user_id = callback.from_user.id

        if not GITHUB_TOKEN:
            await callback.message.answer("Сервис временно недоступен: отсутствует токен доступа к картам.")
            return

        block_temp = await callback.bot.send_message(chat_id=user_id, text="Вытаскиваем карту блок...")
        request_text = user_states.get(user_id, {}).get('request', "No specific request")

        block_cards = [c for c in cards if c['type'] == 'block']
        resource_cards = [c for c in cards if c['type'] == 'resource']

        if not block_cards or not resource_cards:
            await callback.bot.delete_message(chat_id=user_id, message_id=block_temp.message_id)
            await callback.message.answer("Ошибка: карты не найдены!")
            return

        block_card = random.choice(block_cards)
        resource_card = random.choice(resource_cards)

        block_image_bytes = await download_github_image(block_card['image_url'], GITHUB_TOKEN)
        if not block_image_bytes:
            await callback.bot.delete_message(chat_id=user_id, message_id=block_temp.message_id)
            await callback.message.answer("Не удалось загрузить блок-карту.")
            return

        resource_image_bytes = await download_github_image(resource_card['image_url'], GITHUB_TOKEN)
        if not resource_image_bytes:
            await callback.bot.delete_message(chat_id=user_id, message_id=block_temp.message_id)
            await callback.message.answer("Не удалось загрузить ресурс-карту.")
            return

        # Отправка блок-карты
        await callback.bot.delete_message(chat_id=user_id, message_id=block_temp.message_id)
        kb_block = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Описание", callback_data=f"desc_block:{block_card['id']}")]
        ])
        await callback.bot.send_photo(
            chat_id=user_id,
            photo=BufferedInputFile(block_image_bytes, filename=f"{block_card['id']}.png"),
            reply_markup=kb_block
        )

        await asyncio.sleep(1)  # ← для тестов; в продакшене — 300

        # Отправка ресурс-карты
        resource_temp = await callback.bot.send_message(chat_id=user_id, text="Вытаскиваем карту ресурс...")
        await asyncio.sleep(0.5)
        await callback.bot.delete_message(chat_id=user_id, message_id=resource_temp.message_id)

        kb_resource = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Описание", callback_data=f"desc_resource:{resource_card['id']}")]
        ])
        await callback.bot.send_photo(
            chat_id=user_id,
            photo=BufferedInputFile(resource_image_bytes, filename=f"{resource_card['id']}.png"),
            reply_markup=kb_resource
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

        asyncio.create_task(send_followup_questions(user_id, callback.bot))

    async def send_followup_questions(user_id: int, bot: Bot):
        await asyncio.sleep(300)
        state = user_states.get(user_id)
        if not state or state.get('step') != 'waiting_for_feedback':
            return

        text = "Получила ли ты ответ на свой запрос, или тебе нужны подсказки?"
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="Подсказки✨", callback_data="need_hints")
        keyboard.button(text="Получила❤️", callback_data="received_insights")

        try:
            await bot.send_message(chat_id=user_id, text=text, reply_markup=keyboard.as_markup())
            user_states[user_id]['step'] = 'waiting_for_hints_or_done'
        except Exception as e:
            logging.warning(f"Не удалось отправить follow-up: {e}")

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

        block_qs = [q for q in help_questions if q['type'] == 'block']
        res_qs = [q for q in help_questions if q['type'] == 'resource']

        if block_qs:
            q = random.choice(block_qs)
            await callback.bot.send_message(user_id, f"{block_card['name']}: {q['question']}")
            await asyncio.sleep(10)

        if res_qs:
            q = random.choice(res_qs)
            await callback.bot.send_message(user_id, f"{resource_card['name']}: {q['question']}")

        user_states[user_id]['step'] = 'hints_sent'

    @router.callback_query(lambda c: c.data == "received_insights")
    async def insights_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        user_id = callback.from_user.id
        user_states.pop(user_id, None)
        await callback.message.answer(
            "Замечательно! Пусть твой день будет наполнен ясностью и целью. "
            "Я здесь, если хочешь посмотреть другой запрос или глубже раскрыть понимание."
        )

    # --- Команды ---
    @router.message(Command("block"))
    async def block_command(message: Message) -> None:
        if not GITHUB_TOKEN:
            await message.answer("Сервис временно недоступен: отсутствует токен доступа.")
            return
        cards_block = [c for c in cards if c['type'] == 'block']
        if not cards_block:
            await message.answer("Карты блок недоступны.")
            return
        card = random.choice(cards_block)
        img = await download_github_image(card['image_url'], GITHUB_TOKEN)
        if not img:
            await message.answer("Не удалось загрузить изображение.")
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Описание", callback_data=f"desc_block:{card['id']}")]
        ])
        await message.answer_photo(photo=BufferedInputFile(img, filename=f"{card['id']}.png"), reply_markup=kb)

    @router.message(Command("resource"))
    async def resource_command(message: Message) -> None:
        if not GITHUB_TOKEN:
            await message.answer("Сервис временно недоступен: отсутствует токен доступа.")
            return
        cards_res = [c for c in cards if c['type'] == 'resource']
        if not cards_res:
            await message.answer("Карты ресурс недоступны.")
            return
        card = random.choice(cards_res)
        img = await download_github_image(card['image_url'], GITHUB_TOKEN)
        if not img:
            await message.answer("Не удалось загрузить изображение.")
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Описание", callback_data=f"desc_resource:{card['id']}")]
        ])
        await message.answer_photo(photo=BufferedInputFile(img, filename=f"{card['id']}.png"), reply_markup=kb)

    @router.message(Command("number"))
    async def number_command(message: Message, state: FSMContext) -> None:
        if not GITHUB_TOKEN:
            await message.answer("Сервис временно недоступен: отсутствует токен доступа.")
            return
        await message.answer("Введите номер карты (от 1 до 76):")
        await state.set_state(CardNumber.waiting_for_number)

    @router.message(CardNumber.waiting_for_number)
    async def number_input_handler(message: Message, state: FSMContext) -> None:
        try:
            card_id = int(message.text.strip())
            if not (1 <= card_id <= 76):
                await message.answer("Введите число от 1 до 76.")
                return
        except ValueError:
            await message.answer("Пожалуйста, введите число!")
            return

        card = next((c for c in cards if c['id'] == card_id), None)
        if not card:
            await message.answer("Карта с таким номером не найдена.")
            await state.clear()
            return

        img = await download_github_image(card['image_url'], GITHUB_TOKEN)
        if not img:
            await message.answer("Не удалось загрузить изображение.")
            await state.clear()
            return

        card_type = card['type']
        if card_type not in ('block', 'resource'):
            card_type = 'block'

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Описание", callback_data=f"desc_{card_type}:{card['id']}")]
        ])
        await message.answer_photo(
            photo=BufferedInputFile(img, filename=f"{card['id']}.png"),
            reply_markup=kb
        )
        await state.clear()

    # --- Коллбэк описания ---
    @router.callback_query(lambda c: c.data.startswith("desc_"))
    async def desc_callback(callback: CallbackQuery) -> None:
        await callback.answer()
        try:
            prefix, card_id_str = callback.data.split(":", 1)
            card_id = int(card_id_str)
            card_type = prefix.replace("desc_", "")
        except (ValueError, IndexError):
            await callback.message.answer("Ошибка в данных карты.")
            return

        card = next((c for c in cards if c['id'] == card_id), None)
        if not card:
            await callback.message.answer("Карта не найдена.")
            return

        await callback.message.answer(card['description'])

    return router

# --- MAIN ---
def main():
    logging.basicConfig(level=logging.INFO)
    init_db()

    with open('cards.json', 'r', encoding='utf-8') as f:
        cards = json.load(f)
    with open('help.json', 'r', encoding='utf-8') as f:
        help_questions = json.load(f)

    if os.getenv("RENDER_EXTERNAL_URL"):
        # Webhook (Render)
        external_url = os.getenv("RENDER_EXTERNAL_URL")
        WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
        webhook_url = f"{external_url}{WEBHOOK_PATH}"
        WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "elina_webhook_2025")

        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher()
        router = create_router(cards, help_questions)
        dp.include_router(router)

        async def on_startup(app):
            await bot.set_webhook(url=webhook_url, secret_token=WEBHOOK_SECRET, drop_pending_updates=True)

        app = web.Application()
        app.on_startup.append(on_startup)
        SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=WEBHOOK_SECRET).register(app, path=WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
    else:
        # Polling (локально)
        async def run_polling():
            bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
            await bot.delete_webhook(drop_pending_updates=True)
            dp = Dispatcher()
            router = create_router(cards, help_questions)
            dp.include_router(router)
            await dp.start_polling(bot, skip_updates=True)

        asyncio.run(run_polling())

if __name__ == "__main__":
    main()