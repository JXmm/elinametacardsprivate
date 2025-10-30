#!/usr/bin/env python3
import sqlite3
import os

def check_database():
    db_path = os.path.join(os.getcwd(), "bot_database.db")

    if not os.path.exists(db_path):
        print("Файл bot_database.db не найден!")
        return

    print(f"База данных: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Проверяем таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        print("Таблицы в базе данных:")
        for table_name in tables:
            print(f"  - {table_name[0]}")

        # Проверяем пользователей
        cursor.execute("SELECT COUNT(*) FROM users;")
        user_count = cursor.fetchone()[0]
        print(f"Количество пользователей: {user_count}")

        if user_count > 0:
            cursor.execute("SELECT user_id, first_name, created_at, current_request FROM users LIMIT 5;")
            users = cursor.fetchall()
            print("Пользователи (первые 5):")
            for user in users:
                print(f"  ID: {user[0]}, Name: OK, Created: {user[2]}")

        # Проверяем запросы
        cursor.execute("SELECT COUNT(*) FROM requests;")
        request_count = cursor.fetchone()[0]
        print(f"Количество запросов: {request_count}")

        if request_count > 0:
            cursor.execute("""
                SELECT r.id, r.user_id, r.request_text, r.block_card_id, r.resource_card_id, r.requested_at
                FROM requests r
                ORDER BY r.id DESC LIMIT 3;
            """)
            requests = cursor.fetchall()
            print("Последние запросы (3):")
            for req in requests:
                print(f"  ID: {req[0]}, User: {req[1]}, Request: {req[2][:50]}..., Block: {req[3]}, Resource: {req[4]}, Time: {req[5]}")

        conn.close()

    except Exception as e:
        print(f"Ошибка проверки базы данных: {e}")

if __name__ == "__main__":
    check_database()
