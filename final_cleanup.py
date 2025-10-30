#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import re

# Полная транслитерация всех русских букв
FULL_TRANSLIT = {
    # Заглавные буквы
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'E',
    'Ж': 'ZH', 'З': 'Z', 'И': 'I', 'Й': 'J', 'К': 'K', 'Л': 'L', 'М': 'M',
    'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
    'Ф': 'F', 'Х': 'H', 'Ц': 'C', 'Ч': 'CH', 'Ш': 'SH', 'Щ': 'SH',
    'Ь': '', 'Ы': 'Y', 'Ъ': '',
    'Э': 'E', 'Ю': 'YU', 'Я': 'YA',
    # Строчные буквы
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'j', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'sh',
    'ь': '', 'ы': 'y', 'ъ': '',
    'э': 'e', 'ю': 'yu', 'я': 'ya',
}

def has_cyrillic(text):
    """Проверяет, содержит ли текст кириллические буквы"""
    for char in text:
        if char in FULL_TRANSLIT:
            return True
    return False

def complete_transliterate(text):
    """Полная транслитерация с удалением всех специальных символов"""
    # Сначала транслитерируем русские буквы
    result = ''
    for char in text:
        if char in FULL_TRANSLIT:
            result += FULL_TRANSLIT[char]
        else:
            result += char

    # Удаляем все не алфавитно-цифровые символы кроме _ и .
    result = re.sub(r'[^a-zA-Z0-9._]', '', result)

    return result

def clean_cards_directory():
    """Выполняет полную очистку папки cards"""
    cards_dir = 'cards'
    renamed_files = {}

    if not os.path.exists(cards_dir):
        print(">>> Директория cards не найдена!")
        return renamed_files

    print(">>> Полная проверка всех файлов в cards/")

    count_problems = 0

    for filename in os.listdir(cards_dir):
        if not filename.endswith('.PNG') and not filename.endswith('.png'):
            continue

        original_name = filename

        # Проверяем на русские буквы
        if has_cyrillic(filename):
            count_problems += 1
            print(f"! Русские буквы в: {filename}")

        # Производим полную транслитерацию
        new_filename = complete_transliterate(filename)

        # Если имя изменилось - переименовываем
        if new_filename != original_name:
            count_problems += 1
            print(f"Переименование: {original_name} -> {new_filename}")

            old_path = os.path.join(cards_dir, original_name)
            new_path = os.path.join(cards_dir, new_filename)

            try:
                os.rename(old_path, new_path)
                renamed_files[original_name] = new_filename
                print(f"OK: {original_name} -> {new_filename}")
            except Exception as e:
                print(f"ERROR переименования {original_name}: {e}")

    print(f">>> Найдено проблем: {count_problems}")
    print(f">>> Переименовано файлов: {len(renamed_files)}")

    return renamed_files

def update_cards_json_links(renamed_files):
    """Обновляет все ссылки в cards.json"""
    cards_file = 'cards.json'

    if not os.path.exists(cards_file):
        print(f">>> Файл {cards_file} не найден!")
        return False

    print(">>> Обновление cards.json со всеми ссылками")

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

                # Проверяем, если файл был переименован
                if old_filename in renamed_files:
                    new_filename = renamed_files[old_filename]
                    card['image_url'] = card['image_url'].replace(old_filename, new_filename)
                    updated_count += 1
                    print(f">>> Карта {card['id']}: {old_filename} -> {new_filename}")

                # Дополнительная проверка на русские буквы в URL
                elif has_cyrillic(old_filename):
                    new_filename = complete_transliterate(old_filename)
                    if new_filename != old_filename:
                        card['image_url'] = card['image_url'].replace(old_filename, new_filename)
                        updated_count += 1
                        print(f">>> Карта {card['id']}: очищена от русских букв")

    try:
        with open(cards_file, 'w', encoding='utf-8') as f:
            json.dump(cards_data, f, ensure_ascii=False, indent=2)
        print(f">>> Обновлено {updated_count} ссылок в cards.json")
        return True
    except Exception as e:
        print(f">>> Ошибка сохранения {cards_file}: {e}")
        return False

def main():
    print(">>> ФИНАЛЬНАЯ ОЧИСТКА НАЗВАНИЙ ФАЙЛОВ В PAPKE CARDS")
    print(">>> Удаление всех русских букв и специальных символов")

    # Шаг 1: Очистка файлов
    print("\n" + "="*50)
    renamed_files = clean_cards_directory()

    # Шаг 2: Обновление ссылок
    print("\n" + "="*50)
    success = update_cards_json_links(renamed_files)

    print("\n" + "="*50)
    if success:
        print(">>> ГОТОВО! Все файлы полностью очищены от русских символов.")
        print(">>> Названия файлов состоят только из английских букв, цифр и _")
        print(">>> Ссылки в cards.json соответствуют именам файлов")
    else:
        print(">>> ОШИБКА в финальной обработке")

    # Финальная проверка
    print("\n>>> ФИНАЛЬНАЯ ПРОВЕРКА:")
    cards_dir = 'cards'
    if os.path.exists(cards_dir):
        clean_files = 0
        total_files = 0

        for filename in os.listdir(cards_dir):
            if filename.endswith('.PNG') or filename.endswith('.png'):
                total_files += 1
                if not has_cyrillic(filename) and re.match(r'^[a-zA-Z0-9_.]+$', filename):
                    clean_files += 1

        print(f">>> Всего PNG файлов: {total_files}")
        print(f">>> Чистые файлы: {clean_files}")

        if clean_files == total_files:
            print(">>> ✅ ВСЕ ФАЙЛЫ ПРОХОДЯТ ПРОВЕРКУ!")
        else:
            print(">>> ❌ ЕЩЕ ЕСТЬ ПРОБЛЕМЫ В ФАЙЛАХ")

if __name__ == "__main__":
    main()
