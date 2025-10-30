#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import codecs

# Исправление кодировки вывода для Windows
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import os
import sys
import json
import re

# Таблица транслитерации русских букв в английские
TRANSLIT_DICT = {
    'А': 'A', 'а': 'a',
    'Б': 'B', 'б': 'b',
    'В': 'V', 'в': 'v',
    'Г': 'G', 'г': 'g',
    'Д': 'D', 'д': 'd',
    'Е': 'E', 'е': 'e',
    'Ё': 'E', 'ё': 'e',
    'Ж': 'ZH', 'ж': 'zh',
    'З': 'Z', 'з': 'z',
    'И': 'I', 'и': 'i',
    'Й': 'J', 'й': 'j',
    'К': 'K', 'к': 'k',
    'Л': 'L', 'л': 'l',
    'М': 'M', 'м': 'm',
    'Н': 'N', 'н': 'n',
    'О': 'O', 'о': 'o',
    'П': 'P', 'п': 'p',
    'Р': 'R', 'р': 'r',
    'С': 'S', 'с': 's',
    'Т': 'T', 'т': 't',
    'У': 'U', 'у': 'u',
    'Ф': 'F', 'ф': 'f',
    'Х': 'H', 'х': 'h',
    'Ц': 'C', 'ц': 'c',
    'Ч': 'CH', 'ч': 'ch',
    'Ш': 'SH', 'ш': 'sh',
    'Щ': 'SH', 'щ': 'sh',
    'Ъ': '', 'ъ': '',
    'Ы': 'Y', 'ы': 'y',
    'Ь': '', 'ь': '',
    'Э': 'E', 'э': 'e',
    'Ю': 'YU', 'ю': 'yu',
    'Я': 'YA', 'я': 'ya',
    ' ': '_',
}

def transliterate(text):
    """Транслитерирует русский текст в английский"""
    result = ''
    for char in text:
        if char in TRANSLIT_DICT:
            result += TRANSLIT_DICT[char]
        else:
            result += char
    return result

def rename_files_in_directory():
    """Переименовывает файлы в папке cards"""
    cards_dir = 'cards'

    if not os.path.exists(cards_dir):
        print(f">>> Директория {cards_dir} не найдена!")
        return False

    print(">>> Начинаю переименование файлов...")

    renamed_files = {}

    # Перечисляем все файлы
    for filename in os.listdir(cards_dir):
        if not filename.endswith('.PNG'):
            continue

        # Пример: "1_НАСТАВНИК_РЕСУРС.PNG" -> "1_NASTAVNIK_RESURS.PNG"
        parts = filename.split('_', 2)
        if len(parts) >= 2:
            number = parts[0]
            ext = '.PNG'

            # Оставляем номер и расширение как есть, транслитерируем остальное
            # Пример: "1_НАСТАВНИК_РЕСУРС.PNG" -> ищем позицию расширения
            name_part = filename[:-4]  # Убираем .PNG
            new_name_part = transliterate(name_part)
            new_filename = new_name_part + ext

            old_path = os.path.join(cards_dir, filename)
            new_path = os.path.join(cards_dir, new_filename)

            if old_path != new_path:
                try:
                    os.rename(old_path, new_path)
                    renamed_files[filename] = new_filename
                    print(f"OK {filename} -> {new_filename}")
                except Exception as e:
                    print(f"ERROR {filename}: {e}")

    print(f">>> Переименовано {len(renamed_files)} файлов")
    return renamed_files

def update_cards_json(renamed_files):
    """Обновляет cards.json с новыми именами файлов"""
    cards_file = 'cards.json'

    if not os.path.exists(cards_file):
        print(f">>> Файл {cards_file} не найден!")
        return False

    print(">>> Обновляю cards.json...")

    try:
        with open(cards_file, 'r', encoding='utf-8') as f:
            cards_data = json.load(f)
    except Exception as e:
        print(f">>> Ошибка чтения {cards_file}: {e}")
        return False

    updated_count = 0

    for card in cards_data:
        if 'image_url' in card:
            # Пример: "https://..." -> извлекаем последнее имя файла
            url_parts = card['image_url'].split('/')
            if url_parts:
                old_filename = url_parts[-1]
                if old_filename in renamed_files:
                    new_filename = renamed_files[old_filename]
                    # Обновляем только имя файла в URL
                    card['image_url'] = card['image_url'].replace(old_filename, new_filename)
                    updated_count += 1
                    print(f"OK Карта {card['id']}: {old_filename} -> {new_filename}")

    # Сохраняем обновленный JSON
    try:
        with open(cards_file, 'w', encoding='utf-8') as f:
            json.dump(cards_data, f, ensure_ascii=False, indent=2)
        print(f">>> Обновлено {updated_count} URL в cards.json")
        return True
    except Exception as e:
        print(f">>> Ошибка сохранения {cards_file}: {e}")
        return False

def main():
    print(">>> Начинаю транслитерацию файлов карт ElinaMetaCards\n")

    # Шаг 1: Переименование файлов
    renamed_files = rename_files_in_directory()

    if not renamed_files:
        print(">>> Не найдено файлов для переименования")
        return

    print(f"\n>>> Переименовано файлов: {len(renamed_files)}\n")

    # Шаг 2: Обновление cards.json
    success = update_cards_json(renamed_files)

    if success:
        print("\n>>> Готово! Файлы карт транслитерированы, cards.json обновлен.")
        print(">>> Проверьте работу бота: python main.py")
    else:
        print("\n>>> Ошибка обновления cards.json")

if __name__ == "__main__":
    main()
