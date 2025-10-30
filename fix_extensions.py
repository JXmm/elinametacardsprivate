#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json

def fix_png_extensions():
    """Исправляет расширения файлов с PNG на png"""
    cards_dir = 'cards'
    renamed_files = {}

    if not os.path.exists(cards_dir):
        print(">>> Директория cards не найдена!")
        return renamed_files

    print(">>> Исправление расширений PNG -> png")

    for filename in os.listdir(cards_dir):
        if filename.endswith('.PNG') and not filename.endswith('.png'):
            # Создаем новое имя с маленьким расширением
            new_filename = filename.replace('.PNG', '.png')

            old_path = os.path.join(cards_dir, filename)
            new_path = os.path.join(cards_dir, new_filename)

            try:
                os.rename(old_path, new_path)
                renamed_files[filename] = new_filename
                print(f">>> {filename} -> {new_filename}")
            except Exception as e:
                print(f">>> ERROR: {filename} - {e}")

    print(f">>> Переименовано файлов: {len(renamed_files)}")
    return renamed_files

def update_cards_json_extensions(renamed_files):
    """Обновляет ссылки в cards.json на новые расширения"""
    if not renamed_files:
        print(">>> Нет файлов для обновления в JSON")
        return True

    cards_file = 'cards.json'

    if not os.path.exists(cards_file):
        print(f">>> Файл {cards_file} не найден!")
        return False

    print(">>> Обновление расширений в cards.json")

    try:
        with open(cards_file, 'r', encoding='utf-8') as f:
            cards_data = json.load(f)
    except Exception as e:
        print(f">>> Ошибка чтения {cards_file}: {e}")
        return False

    updated_count = 0

    for card in cards_data:
        if 'image_url' in card:
            url_parts = card['image_url'].split('/')
            if url_parts:
                old_filename = url_parts[-1]

                if old_filename in renamed_files:
                    new_filename = renamed_files[old_filename]
                    card['image_url'] = card['image_url'].replace(old_filename, new_filename)
                    updated_count += 1
                    print(f">>> Карта {card['id']}: расширение исправлено")

    try:
        with open(cards_file, 'w', encoding='utf-8') as f:
            json.dump(cards_data, f, ensure_ascii=False, indent=2)
        print(f">>> Обновлено {updated_count} ссылок в cards.json")
        return True
    except Exception as e:
        print(f">>> Ошибка сохранения {cards_file}: {e}")
        return False

def main():
    print(">>> ИСПРАВЛЕНИЕ РАСШИРЕНИЙ PNG -> png")
    print(">>> Это исправит проблемы с загрузкой изображений")

    # Шаг 1: Переименование расширений
    print("\n" + "="*50)
    renamed_files = fix_png_extensions()

    # Шаг 2: Обновление JSON
    print("\n" + "="*50)
    success = update_cards_json_extensions(renamed_files)

    print("\n" + "="*50)
    if success:
        print(">>> ГОТОВО! Расширения PNG -> png исправлены")
        print(">>> Бот сможет правильно загружать изображения")
    else:
        print(">>> Ошибка в исправлении расширений")

if __name__ == "__main__":
    main()
