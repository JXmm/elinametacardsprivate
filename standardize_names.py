#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import re

# Невидимый символ U+2800 (Braille Pattern Blank)
INVISIBLE_CHAR = '\u2800'

# Полная транслитерация для стандартизации названий
FULL_TRANSLIT = {
    'А': 'a', 'Б': 'b', 'В': 'v', 'Г': 'g', 'Д': 'd', 'Е': 'e', 'Ё': 'e',
    'Ж': 'zh', 'З': 'z', 'И': 'i', 'Й': 'j', 'К': 'k', 'Л': 'l', 'М': 'm',
    'Н': 'n', 'О': 'o', 'П': 'p', 'Р': 'r', 'С': 's', 'Т': 't', 'У': 'u',
    'Ф': 'f', 'Х': 'h', 'Ц': 'c', 'Ч': 'ch', 'Ш': 'sh', 'Щ': 'sh',
    'Ь': '', 'Ы': 'y', 'Ъ': '',
    'Э': 'e', 'Ю': 'yu', 'Я': 'ya',
}

def transliterate(text):
    """Транслитерирует русский текст в английский (нижний регистр)"""
    result = text.lower()
    for rus, eng in FULL_TRANSLIT.items():
        result = result.replace(rus.lower(), eng)
    return result

def clean_name(name):
    """Очищает название от пробелов и специальных символов"""
    # Убираем невидимые символы
    name = name.replace(INVISIBLE_CHAR, '')
    # Транслитерируем
    name = transliterate(name)
    # Убираем все кроме букв, цифр и _
    name = re.sub(r'[^a-z0-9_]', '', name)
    # Убираем множественные подчеркивания
    name = re.sub(r'_+', '_', name).strip('_')
    return name

def standardize_filenames():
    """Стандартизирует все файлы в cards/ по шаблону {id}_{name}_{type}.png"""
    cards_dir = 'cards'
    renamed_files = {}

    # Читаем карты из JSON
    cards_file = 'cards.json'
    try:
        with open(cards_file, 'r', encoding='utf-8') as f:
            cards_data = json.load(f)
    except Exception as e:
        print(f"Ошибка чтения {cards_file}: {e}")
        return renamed_files

    # Создаем словарь id -> правильное имя файла
    card_names = {}
    for card in cards_data:
        card_id = card['id']
        name = card['name']
        type_name = 'resource' if card['type'] == 'resource' else 'block'

        # Очищаем и транслитерируем название
        clean_name_part = clean_name(name)
        standard_name = f"{card_id}_{clean_name_part}_{type_name}.png"

        card_names[card_id] = standard_name
        print(f"Карта {card_id}: {clean_name_part} -> {standard_name.lower()}")

    print(f"\n>>> Найдено {len(card_names)} карт в JSON")

    # Переименовываем файлы
    for filename in os.listdir(cards_dir):
        if not filename.lower().endswith('.png'):
            continue

        old_path = os.path.join(cards_dir, filename)

        # Извлекаем id из имени файла
        match = re.match(r'(\d+)_', filename)
        if match:
            file_id = int(match.group(1))
            if file_id in card_names:
                new_filename = card_names[file_id].lower()
                new_path = os.path.join(cards_dir, new_filename)

                try:
                    os.rename(old_path, new_path)
                    renamed_files[filename] = new_filename
                    print(f"Переименовано: {filename} -> {new_filename}")
                except Exception as e:
                    print(f"Ошибка {filename}: {e}")
            else:
                print(f"Предупреждение: файл {filename} не найден в JSON (id={file_id})")
        else:
            print(f"Неверный формат: {filename} (не начинается с числа)")

    print(f"\n>>> Переименовано {len(renamed_files)} файлов")
    return renamed_files

def update_json_urls(renamed_files):
    """Обновляет ссылки в cards.json на новые имена файлов"""
    cards_file = 'cards.json'
    updated_count = 0

    try:
        with open(cards_file, 'r', encoding='utf-8') as f:
            cards_data = json.load(f)
    except Exception as e:
        print(f"Ошибка чтения JSON: {e}")
        return False

    for card in cards_data:
        if 'image_url' in card:
            url_parts = card['image_url'].split('/')
            if url_parts:
                old_filename = url_parts[-1]

                if old_filename in renamed_files:
                    new_filename = renamed_files[old_filename]
                    card['image_url'] = card['image_url'].replace(old_filename, new_filename)
                    updated_count += 1
                    print(f"Обновлена ссылка карты {card['id']}")

    if updated_count > 0:
        try:
            with open(cards_file, 'w', encoding='utf-8') as f:
                json.dump(cards_data, f, ensure_ascii=False, indent=2)
            print(f"Обновлено {updated_count} ссылок в cards.json")
            return True
        except Exception as e:
            print(f"Ошибка сохранения JSON: {e}")
            return False
    else:
        print("Не найдено ссылок для обновления")
        return True

def main():
    print(">>> СТАНДАРТИЗАЦИЯ НАЗВАНИЙ ФАЙЛОВ ПО ШАБЛОНУ")
    print(">>> {id}_{translit}_{type}.png (всё в нижнем регистре)")

    # Шаг 1: Переименование файлов
    renames = standardize_filenames()

    # Шаг 2: Обновление JSON
    if renames:
        success = update_json_urls(renames)

        if success:
            print("\n>>> ГОТОВО! Все файлы стандартизированы.")
            print(">>> Следуйте шаблону: {id}_{translit}_{type}.png")
        else:
            print("\n>>> Ошибка при обновлении JSON")
    else:
        print("\n>>> Не найдено файлов для переименования")

if __name__ == "__main__":
    main()
