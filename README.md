# ElinaMetaCards Telegram Bot 🌿

Карточный бот для метафорического гадания "ElinaMetaCards" на базе aiogram 3.x. Бот раскладывает блок-карты и ресурс-карты, помогающие пользователю получить инсайты на поставленный вопрос.

## 🚀 Особенности

- **Полная русская локализация**
- **Webhook режим** для продакшена на Render
- **Polling режим** для разработки
- **Автоматическая загрузка изображений** из приватного GitHub репозитория с токенами
- **SQLite база данных** для хранения пользователей и запросов
- **Интерактивный поток** с задержками для лучшего UX
- **Подсказки и вопросы** для глубокого анализа карт
- **Автоматическое след-ап уведомление** через 5 минут

## 📋 Технический стек

- **Python 3.9+**
- **aiogram 3.x** - асинхронная Telegram Bot API
- **aiohttp** - веб-сервер для webhook
- **SQLite3** - локальная база данных
- **python-dotenv** - управление переменными окружения
- **Render** - платформа для развертывания

## 🗂️ Структура проекта

```
/elinametacards_bot
├── main.py                 # Основной файл бота с логиой и обработчиками
├── database.py             # Модуль работы с SQLite базой данных
├── cards.json              # JSON с описанием карт (блок и ресурс)
├── help.json               # JSON с вопросами для подсказок
├── requirements.txt        # Зависимости Python
├── runtime.txt             # Версия Python для Render
├── .env                    # Переменные окружения (не коммитить в git)
├── .gitignore             # Исключения для git
├── README.md              # Этот файл
├── bot_database.db        # SQLite база данных (создается автоматически)
└── cards/                 # Папка с изображениями карт (из GitHub)
```

## 📊 База данных

База состоит из двух таблиц:

### users
| Поле          | Тип    | Описание                     |
|---------------|--------|------------------------------|
| user_id       | INT    | Telegram ID пользователя     |
| first_name    | TEXT   | Имя пользователя            |
| created_at    | TEXT   | Дата регистрации            |
| current_request| TEXT  | Текущий запрос пользователя |

### requests
| Поле                      | Тип    | Описание                     |
| --------------------------|--------|------------------------------|
| id                        | INT    | Auto-increment PK           |
| user_id                   | INT    | FK к users                  |
| request_text              | TEXT   | Текст запроса               |
| block_card_id             | INT    | ID блок-карты               |
| resource_card_id          | INT    | ID ресурс-карты             |
| block_card_description    | TEXT   | Описание блок-карты         |
| resource_card_description | TEXT   | Описание ресурс-карты       |
| requested_at              | TEXT   | Время раздачи карт         |

## 🛠️ Установка и запуск

### 🔵 Вариант 1: Локальный запуск

#### 1. Клонирование репозитория

```bash
git clone https://github.com/your-username/elinametacards_bot.git
cd elinametacards_bot
```

#### 2. Создание виртуального окружения

```bash
python -m venv venv
# На Windows:
venv\Scripts\activate
# На macOS/Linux:
source venv/bin/activate
```

#### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

#### 4. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```bash
BOT_TOKEN=ваш_бот_токен_от_BotFather
GITHUB_TOKEN=ваш_github_personal_access_token
```

#### 5. Запуск в режиме разработки (polling)

```bash
python main.py
```

### 🐳 Вариант 2: Docker (рекомендуется)

#### Требования:
- Docker
- Docker Compose

#### 1. Клонирование проекта

```bash
git clone https://github.com/your-username/elinametacards_bot.git
cd elinametacards_bot
```

#### 2. Создание .env файла

```bash
cp .env.example .env
# Отредактируйте .env с вашими токенами
```

#### 3. Запуск с Docker Compose

```bash
# Сборка и запуск
docker-compose up -d --build

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

#### Структура файлов для Docker:
- `Dockerfile` - инструкции сборки образа
- `docker-compose.yml` - конфигурация сервиса
- `.dockerignore` - исключения для сборки
- `.env.example` - пример переменных окружения

Бот будет запущен в polling режиме для локального тестирования.

### 🌐 Вариант 3: TimeWeb Cloud (рекомендуется для продакшена)

#### 1. Подготовка файлов
- Убедитесь что есть `data/` директория для базы данных
- Создайте `.env` файл из `.env.example`

#### 2. Сборка образа локально
```bash
# Сборка образа для вашего сервера
docker build -t elina-meta-cards-bot .
```

#### 3. Запуск на сервере TimeWeb
```bash
# Экспорт образа
docker save elina-meta-cards-bot > elina-bot.tar

# Загрузка на сервер и запуск
docker load < elina-bot.tar
docker run -d --name elina-bot \
  --env-file .env \
  -v ./data:/app/data \
  elina-meta-cards-bot
```

#### 4. Mониторинг
```bash
# Просмотр логов
docker logs -f elina-bot

# Перезапуск
docker restart elina-bot

# Обновление
docker stop elina-bot
docker rm elina-bot
# Загрузить новый образ и запустить
```

## 🚀 Развертывание на Render

### 1. Создание аккаунта

[Зарегистрируйтесь на Render](https://render.com) если еще не.

### 2. Связать GitHub репозиторий

- Создайте новый Web Service
- Подключите ваш GitHub репозиторий
- Выберите ветку `main`

### 3. Настройки среды

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
python main.py
```

**Environment Variables:**
```
BOT_TOKEN=ваш_бот_токен
GITHUB_TOKEN=ваш_github_token
RENDER_EXTERNAL_URL=https://your-render-app.onrender.com
WEBHOOK_SECRET=your_webhook_secret
```

**Python Version:**
- Choose Python 3.9 or higher
- Runtime: `python-3.9.x` (check runtime.txt)

### 4. База данных

База SQLite будет создана автоматически при первом запуске.

### 5. Webhook URL

После развертывания Render предоставит внешний URL. Убедитесь, что он установлен в `RENDER_EXTERNAL_URL`.

## 🎭 Функциональность бота

### `/start`
- Приветствие пользователя
- Инструкция для ввода запроса

### Поток взаимодействия
1. Пользователь пишет запрос одним предложением
2. Появляется кнопка "Вытащить карты"
3. Раздаются две карты с задержкой:
   - Блок-карта - препятствие/вызов
   - Ресурс-карта - помощь/ресурсы
4. Через 5 минут: след-ап вопрос о подсказках

### Подсказки
- Интерактивные вопросы для анализа каждой карты
- Отправляются по одному с задержками

### AI Интеграция
- Заглушка для будущей интеграции RAG/LLM
- Автоматическое генерирование инсайтов на основе запроса и карт

## 🔒 Безопасность

- Вебхук секрет для верификации запросов
- Безопасное хранение токенов в переменных окружения
- Нет логирования чувствительных данных

## 📝 Добавление новых карт

### cards.json структура:
```json
[
  {
    "id": 1,
    "name": "Название карты",
    "type": "block", // или "resource"
    "description": "Подробное описание",
    "image_url": "https://raw.githubusercontent.com/owner/repo/main/cards/card1.png"
  }
]
```

### help.json структура:
```json
[
  {
    "type": "block", // или "resource"
    "question": "Вопрос для саморефлексии?"
  }
]
```

## 🐛 Отладка

- Запуски логируются с уровнем INFO
- Ошибки подключения к Telegram API в логах
- SQL ошибки при работе с базой данных

## 📈 Мониторинг

Для продакшена на Render:
- Логи доступны в Render Dashboard
- Метрики отклика в разделе Metrics
- Автоматический перезапуск при крашах

## 🤝 Автор

Создано для метафорического гадания "ElinaMetaCards".

## 📄 Лицензия

Этот проект является частным и предназначен для конкретного использования.

---

**Примечание:** Убедитесь, что изображения карт размещены в приватном GitHub репозитории с правильными правами доступа.
