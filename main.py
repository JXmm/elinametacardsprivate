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
from aiogram.types import (
    Message, CallbackQuery, BufferedInputFile,
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
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

# URL Mini App — исправлено: убраны пробелы в конце!
MINI_APP_URL = "https://jxmm.github.io/elina-miniapp/"

# Глобальное состояние
user_states = {}

class CardNumber(StatesGroup):
    waiting_for_number = State()

async def download_github_image(image_url: str) -> bytes | None:
    if "raw.githubusercontent.com" not in image_url:
        logging.error(f"❌ Неподдерживаемый URL: {image_url}")
        return None

    try:
        async with ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status == 200:
                    return await resp.read()
                else:
                    error_text = await resp.text()
                    logging.error(f"❌ HTTP {resp.status} при загрузке изображения: {image_url} — {error_text}")
                    return None
    except Exception as e:
        logging.error(f"💥 Ошибка загрузки изображения: {e}")
        return None

def create_router(cards):
    router = Router()

    # ========================
    # 🔹 КОМАНДЫ
    # ========================

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

        await message.answer("Перед началом работы c картами сделай, пожалуйста, несколько глубоких вдохов и успокой свои мысли. 😌 \n\n ")
        await asyncio.sleep(5)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да ❤️", callback_data="ready_yes")]
        ])
        await message.answer("Готова? ✨", reply_markup=keyboard)

    @router.callback_query(lambda c: c.data == "ready_yes")
    async def ready_yes_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        user_id = callback.from_user.id

        text = "Cейчас подумай... и напиши мне свой запрос, над которым хочешь поработать сегодня...✨"
        await callback.message.answer(text, parse_mode=ParseMode.HTML)

        user_states[user_id] = {'step': 'waiting_for_request'}
        clear_current_request(user_id)

    @router.message(Command("aboutme"))
    async def cards_miniapp_handler(message: Message) -> None:
        web_app = WebAppInfo(url=MINI_APP_URL)
        builder = InlineKeyboardBuilder()
        builder.button(text=" Давай 🐾", web_app=web_app)
        await message.answer(
            "Здесь я поделюсь, чем я могу быть полезна тебе ❤️",
            reply_markup=builder.as_markup()
        )

    @router.message(Command("block"))
    async def block_command(message: Message) -> None:
        logging.info("🔍 /block: запущена")
        cards_block = [c for c in cards if c['type'] == 'block']
        logging.info(f"Найдено блок-карт: {len(cards_block)}")
        if not cards_block:
            await message.answer("❌ Карты типа 'block' не найдены в базе.")
            return
        card = random.choice(cards_block)
        logging.info(f"Выбрана карта: ID={card['id']}, URL={card['image_url']}")
        img = await download_github_image(card['image_url'])
        if not img:
            await message.answer(f"💥 Не удалось загрузить изображение для карты '{card['name']}'.")
            logging.error(f"Ошибка загрузки: {card['image_url']}")
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Описание", callback_data=f"desc_block:{card['id']}")]
        ])
        await message.answer_photo(photo=BufferedInputFile(img, filename=f"{card['id']}.png"), reply_markup=kb)

    @router.message(Command("resource"))
    async def resource_command(message: Message) -> None:
        logging.info("🔍 /resource: запущена")
        cards_res = [c for c in cards if c['type'] == 'resource']
        logging.info(f"Найдено ресурс-карт: {len(cards_res)}")
        if not cards_res:
            await message.answer("❌ Карты типа 'resource' не найдены в базе.")
            return
        card = random.choice(cards_res)
        logging.info(f"Выбрана карта: ID={card['id']}, URL={card['image_url']}")
        img = await download_github_image(card['image_url'])
        if not img:
            await message.answer(f"💥 Не удалось загрузить изображение для карты '{card['name']}'.")
            logging.error(f"Ошибка загрузки: {card['image_url']}")
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Описание", callback_data=f"desc_resource:{card['id']}")]
        ])
        await message.answer_photo(photo=BufferedInputFile(img, filename=f"{card['id']}.png"), reply_markup=kb)

    @router.message(Command("number"))
    async def number_command(message: Message, state: FSMContext) -> None:
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

        img = await download_github_image(card['image_url'])
        if not img:
            await message.answer(f"Не удалось загрузить изображение для карты ID {card_id}.")
            await state.clear()
            return

        card_type = card['type'] if card['type'] in ('block', 'resource') else 'block'
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Описание", callback_data=f"desc_{card_type}:{card['id']}")]
        ])
        await message.answer_photo(
            photo=BufferedInputFile(img, filename=f"{card['id']}.png"),
            reply_markup=kb
        )
        await state.clear()

    @router.message(lambda message: message.web_app_data)
    async def handle_web_app_data(message: Message) -> None:
        try:
            data = json.loads(message.web_app_data.data)
            if "action" in data:
                action = data.get("action")
                if action == "contact_therapy":
                    await message.answer(
                        "Спасибо за интерес к терапии! ✨\n\n"
                        "Я дипломированный энергокоуч и помогаю людям работать с энергией для трансформации и роста.\n\n"
                        "Напиши мне @elina_goncova для записи на консультацию или расскажи, с какими вопросами ты хотела бы поработать. 🚀"
                    )
                elif action == "visit_channel":
                    await message.answer(
                        "👋 Приветствуем в канале Energy Elina!\n\n"
                        "Там я делюсь энергопрактиками, раскладами карт и инсайтами для трансформации.\n\n"
                        "Подпишись: @energy_elina\n\n"
                        "Что ты хотела бы узнать или получить помощь? 🌸"
                    )
                elif action == "razbor":
                    await message.answer(
                        "Спасибо, что написала РАЗБОР! 🥰\n\n"
                        "Это специальная форма оплаты по сердцу для первой терапии.\n\n"
                        "Мне @elina_goncova — так как работает наша система: после первичной диагностики я называла сумму, которая резонансна для человека. Иногда это может быть даже 1 рубль.\n\n"
                        "Расскажи о своем запросе, с чем хочешь поработать? 💫"
                    )
                else:
                    await message.answer("Спасибо за взаимодействие с мини-приложением! Чем я могу тебе помочь? 🌿")
            elif "card" in data:
                card_name = data.get("card", "Трансформация")
                await message.answer(
                    f"✨ Ты выбрала карту: <b>{card_name}</b>\n\n"
                    "Посмотри на неё внимательно. Какие чувства она вызывает?\n"
                    "Что она тебе напоминает? Что хочет сказать?\n\n"
                    "Когда будешь готова — напиши мне свой запрос, и мы углубимся в работу. 🌿",
                    parse_mode=ParseMode.HTML
                )
            else:
                await message.answer("Спасибо за взаимодействие с мини-приложением! Чем я могу тебе помочь? 🌿")
        except Exception as e:
            logging.error(f"Ошибка обработки данных Mini App: {e}")
            await message.answer("Что-то пошло не так с мини-приложением, но мы можем работать прямо здесь! Что тебя беспокоит?")

    @router.message()
    async def request_handler(message: Message) -> None:
        if message.text and message.text.startswith('/'):
            return
        user_id = message.from_user.id
        if user_id not in user_states or user_states[user_id].get('step') != 'waiting_for_request':
            return
        user_states[user_id]['request'] = message.text
        user_states[user_id]['step'] = 'request_received'
        update_current_request(user_id, message.text)
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="Отправить запрос💫", callback_data="draw_cards")
        await message.answer("Отлично!✨ \n\nПервая карта - это блок. То, что мешает тебе в реализации твоего запроса.", reply_markup=keyboard.as_markup())

    @router.callback_query(lambda c: c.data == "draw_cards")
    async def draw_cards_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        user_id = callback.from_user.id

        request_text = user_states.get(user_id, {}).get('request', "No specific request")

        block_cards = [c for c in cards if c['type'] == 'block']
        resource_cards = [c for c in cards if c['type'] == 'resource']

        if not block_cards or not resource_cards:
            await callback.message.answer("Ошибка: карты не найдены!")
            return

        block_card = random.choice(block_cards)
        resource_card = random.choice(resource_cards)

        block_image_bytes = await download_github_image(block_card['image_url'])
        if not block_image_bytes:
            await callback.message.answer("Не удалось загрузить блок-карту.")
            return

        user_states[user_id]['block_card'] = block_card
        user_states[user_id]['resource_card'] = resource_card
        user_states[user_id]['request_text'] = request_text

        block_temp = await callback.bot.send_message(chat_id=user_id, text="Вытягиваем карту блока...")
        await callback.bot.send_photo(
            chat_id=user_id,
            photo=BufferedInputFile(block_image_bytes, filename=f"{block_card['id']}.png")
        )
        await callback.bot.delete_message(chat_id=user_id, message_id=block_temp.message_id)

        await asyncio.sleep(2)
        await callback.bot.send_message(user_id, "Что ты тут видишь?")
        await asyncio.sleep(10)
        await callback.bot.send_message(user_id, "О чем карта говорит, что напоминает?")
        await asyncio.sleep(10)
        await callback.bot.send_message(user_id, "Какое чувство она вызывает? Какими событиями вызвано это чувство?")
        await asyncio.sleep(15)

        final_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Подсказки ✨", callback_data=f"desc_block:{block_card['id']}"),
                InlineKeyboardButton(text="Хочу ресурс 💫", callback_data="show_resource")
            ]
        ])
        await callback.bot.send_message(
            user_id,
            "Все ли тебе понятно или нужны подсказки? ❤️",
            reply_markup=final_kb
        )

    @router.callback_query(lambda c: c.data == "show_resource")
    async def show_resource_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        user_id = callback.from_user.id

        if user_id not in user_states:
            await callback.message.answer("Сессия устарела. Начни с /start.")
            return

        resource_card = user_states[user_id].get('resource_card')
        block_card = user_states[user_id].get('block_card')

        if not resource_card or not block_card:
            await callback.message.answer("Ошибка: данные карт утеряны.")
            return

        resource_image_bytes = await download_github_image(resource_card['image_url'])
        if not resource_image_bytes:
            await callback.message.answer("Не удалось загрузить ресурс-карту.")
            return

        resource_temp = await callback.bot.send_message(chat_id=user_id, text="Вытягиваем карту ресурс...")
        await asyncio.sleep(3)
        await callback.bot.delete_message(chat_id=user_id, message_id=resource_temp.message_id)

        await callback.bot.send_photo(
            chat_id=user_id,
            photo=BufferedInputFile(resource_image_bytes, filename=f"{resource_card['id']}.png")
        )

        await asyncio.sleep(2)
        await callback.bot.send_message(user_id, "А что ты видишь тут?")
        await asyncio.sleep(10)
        await callback.bot.send_message(user_id, "Понимаешь ли ты, о чем говорит тебе эта карта?")
        await asyncio.sleep(10)
        await callback.bot.send_message(user_id, "Что тебе нужно сделать, чтобы это помогло с решением твоего запроса?")
        await asyncio.sleep(10)

        final_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Подсказки ✨", callback_data=f"desc_resource:{resource_card['id']}"),
                InlineKeyboardButton(text="Все понятно ☺️", callback_data="resource_understood")
            ]
        ])
        await callback.bot.send_message(
            user_id,
            "Если нужны подсказки, они тут ❤️",
            reply_markup=final_kb
        )

    @router.callback_query(lambda c: c.data == "block_understood")
    async def block_understood_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        await callback.message.answer("Отлично! 🌿")

    @router.callback_query(lambda c: c.data == "resource_understood")
    async def resource_understood_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        user_id = callback.from_user.id

        if user_id not in user_states:
            await callback.message.answer("Сессия устарела.")
            return

        request_text = user_states[user_id].get('request_text', "No specific request")
        block_card = user_states[user_id].get('block_card')
        resource_card = user_states[user_id].get('resource_card')

        if block_card and resource_card:
            save_request(
                user_id,
                request_text,
                block_card['id'],
                resource_card['id'],
                block_card['description'],
                resource_card['description']
            )
            clear_current_request(user_id)
            user_states[user_id]['step'] = 'waiting_for_feedback'
            user_states[user_id]['last_interaction'] = datetime.utcnow()
            asyncio.create_task(send_followup_questions(user_id, callback.bot))

        await callback.message.answer("Отлично! 🌿 Ты молодец!")

    async def send_followup_questions(user_id: int, bot: Bot):
        await asyncio.sleep(300)
        state = user_states.get(user_id)
        if not state or state.get('step') != 'waiting_for_feedback':
            return

        text = "Получила ли ты ответ на свой запрос, или тебе нужно больше понимания?"
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="Еще карты", callback_data="need_hints")
        keyboard.button(text="Получила❤️", callback_data="received_insights")

        try:
            await bot.send_message(chat_id=user_id, text=text, reply_markup=keyboard.as_markup())
            user_states[user_id]['step'] = 'waiting_for_hints_or_done'
            user_states[user_id]['last_interaction'] = datetime.utcnow()
        except Exception as e:
            logging.warning(f"Не удалось отправить follow-up: {e}")

    @router.callback_query(lambda c: c.data == "need_hints")
    async def hints_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        user_id = callback.from_user.id
        if user_id in user_states:
            user_states[user_id]['last_interaction'] = datetime.utcnow()

        text = (
            "Зайди в пункт меню слева, и выбери себе еще карты \"Блока\" или \"Ресурса\" как дополнение к своему запросу. 🌟\n\n"
            "Задай себе вопрос: что мне еще мешает? 🧩 или Что мне еще поможет в решении запроса? 💫\n\n"
            "Можно выбрать еще пару таких карт. 🃏"
        )
        await callback.message.answer(text)

    @router.callback_query(lambda c: c.data == "received_insights")
    async def insights_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        user_id = callback.from_user.id
        if user_id in user_states:
            user_states[user_id]['last_interaction'] = datetime.utcnow()
        else:
            user_states[user_id] = {'last_interaction': datetime.utcnow()}

        asyncio.create_task(schedule_final_message(user_id, callback.bot, delay=180))
        await callback.message.answer("Пусть будет прекрасным твой день! 🌸\n\n")

    async def schedule_final_message(user_id: int, bot: Bot, delay: int = 180):
        await asyncio.sleep(delay)
        current_state = user_states.get(user_id, {})
        last_interaction = current_state.get('last_interaction')
        if last_interaction:
            if (datetime.utcnow() - last_interaction).total_seconds() >= delay:
                try:
                    await bot.send_message(user_id, "Пусть будет прекрасным твой день! 🌸\n\n")
                except Exception as e:
                    logging.warning(f"Не удалось отправить финальное сообщение: {e}")
        user_states.pop(user_id, None)

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
    # Уровень логирования: INFO для разработки, ERROR для продакшена
    log_level = logging.ERROR if os.getenv("RENDER_EXTERNAL_URL") else logging.INFO
    logging.basicConfig(level=log_level)
    init_db()

    with open('cards.json', 'r', encoding='utf-8') as f:
        cards = json.load(f)
    logging.info(f"✅ Загружено {len(cards)} карт")

    if os.getenv("RENDER_EXTERNAL_URL"):
        external_url = os.getenv("RENDER_EXTERNAL_URL")
        WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
        webhook_url = f"{external_url}{WEBHOOK_PATH}"
        WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "elina_webhook_2025")

        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher()
        router = create_router(cards)
        dp.include_router(router)

        async def on_startup(app):
            await bot.set_webhook(url=webhook_url, secret_token=WEBHOOK_SECRET, drop_pending_updates=True)

        app = web.Application()
        app.on_startup.append(on_startup)
        async def health_check(request):
            return web.json_response({"status": "ok"})
        app.router.add_get("/health", health_check)

        SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=WEBHOOK_SECRET).register(app, path=WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
    else:
        async def run_polling():
            bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
            await bot.delete_webhook(drop_pending_updates=True)
            dp = Dispatcher()
            router = create_router(cards)
            dp.include_router(router)
            await dp.start_polling(bot, skip_updates=True)

        asyncio.run(run_polling())

if __name__ == "__main__":
    main()
