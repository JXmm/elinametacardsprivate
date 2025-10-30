#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json

# Символ U+2800 (Braille Pattern Blank) - невидимый символ
INVISIBLE_CHAR = '\u2800'

def find_and_rename_files():
    """Находит и переименовывает файлы с невидимыми символами"""
    cards_dir = 'cards'
    renamed_files = {}

    if not os.path.exists(cards_dir):
        print("Директория cards не найдена!")
        return False

    print("Ищу файлы с невидимыми символами...")

    for filename in os.listdir(cards_dir):
        if not filename.endswith('.PNG'):
            continue

        # Проверяем, содержит ли файл невидимый символ U+2800
        if INVISIBLE_CHAR in filename:
            # Создаем новое имя без невидимого символа
            new_filename = filename.replace(INVISIBLE_CHAR, '')

            if new_filename != filename:  # Если действительно произошло изменение
                old_path = os.path.join(cards_dir, filename)
                new_path = os.path.join(cards_dir, new_filename)

                try:
                    os.rename(old_path, new_path)
                    renamed_files[filename] = new_filename
                    print(f"Переименовано: {filename} -> {new_filename}")
                except Exception as e:
                    print(f"Ошибка переименования {filename}: {e}")

    return renamed_files

def update_cards_json(renamed_files):
    """Обновляет cards.json с новыми именами файлов"""
    cards_file = 'cards.json'

    if not os.path.exists(cards_file):
        print(f"Файл {cards_file} не найден!")
        return False

    print("Обновляю cards.json...")

    try:
        with open(cards_file, 'r', encoding='utf-8') as f:
            cards_data = json.load(f)
    except Exception as e:
        print(f"Ошибка чтения {cards_file}: {e}")
        return False

    updated_count = 0

    for card in cards_data:
        if 'image_url' in card:
            url_parts = card['image_url'].split('/')
            if url_parts:
                old_filename = url_parts[-1]

                # Если ссылки содержат невидимый символ из названии файла
                if old_filename in renamed_files:
                    new_filename = renamed_files[old_filename]
                    card['image_url'] = card['image_url'].replace(old_filename, new_filename)
                    updated_count += 1
                    print(f"Обновлена ссылка для карты {card['id']}")

                # Также проверяем, есть ли невидимый символ в названии прямо в URL
                if INVISIBLE_CHAR in old_filename:
                    clean_filename = old_filename.replace(INVISIBLE_CHAR, '')
                    if old_filename != clean_filename:
                        card['image_url'] = card['image_url'].replace(old_filename, clean_filename)
                        updated_count += 1
                        print(f"Очищена ссылка от невидимого символа для карты {card['id']}")

    if updated_count > 0:
        try:
            with open(cards_file, 'w', encoding='utf-8') as f:
                json.dump(cards_data, f, ensure_ascii=False, indent=2)
            print(f"Обновлено {updated_count} ссылок в cards.json")
            return True
        except Exception as e:
            print(f"Ошибка сохранения {cards_file}: {e}")
            return False
    else:
        print("Не найдено ссылок для обновления")
        return True

def main():
    print("Удаление невидимого символа U+2800 из названий файлов...")

    # Шаг 1: Переименование файлов
    renamed_files = find_and_rename_files()

    if renamed_files:
        print(f"\nПереименовано файлов: {len(renamed_files)}")
    else:
        print("\nФайлы с невидимым символом не найдены")

    # Шаг 2: Обновление cards.json
    success = update_cards_json(renamed_files)

    if success:
        print("\nГотово! Невидимые символы удалены.")
    else:
        print("\nОшибка обработки файлов.")

if __name__ == "__main__":
    main()
