import sqlite3
import os

# ✅ Универсальный путь: работает и на Render, и в Docker
# База создаётся в той же папке, где лежит скрипт (рядом с main.py)
DB_PATH = os.path.join(os.path.dirname(__file__), "bot_database.db")

def init_db():
    """Инициализация базы данных: создаёт таблицы, если их нет."""
    # Убедимся, что директория существует (актуально для некоторых систем)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            current_request TEXT
        )
    ''')

    # Попытка добавить колонку current_request (если база старая)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN current_request TEXT;")
    except sqlite3.OperationalError:
        pass  # Колонка уже существует

    # Таблица запросов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            request_text TEXT,
            block_card_id INTEGER,
            resource_card_id INTEGER,
            block_card_description TEXT,
            resource_card_description TEXT,
            requested_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    conn.commit()
    conn.close()

def add_or_update_user(user_id, first_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, first_name)
        VALUES (?, ?)
    ''', (user_id, first_name))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user[0] if user else None

def update_current_request(user_id, request_text):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users SET current_request = ? WHERE user_id = ?
    ''', (request_text, user_id))
    conn.commit()
    conn.close()

def clear_current_request(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users SET current_request = NULL WHERE user_id = ?
    ''', (user_id,))
    conn.commit()
    conn.close()

def save_request(user_id, request_text, block_card_id, resource_card_id, block_desc, resource_desc):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO requests (
            user_id, request_text, block_card_id, resource_card_id,
            block_card_description, resource_card_description
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, request_text, block_card_id, resource_card_id, block_desc, resource_desc))
    conn.commit()
    conn.close()