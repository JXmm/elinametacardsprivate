#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import re

def rename_to_numbers():
    """Переименовывает все файлы карт из {id}_{name}_{type}.png в {id}.png"""
    cards_dir = 'cards'
    renamed_files = {}

    if not os.path.exists(cards_dir):
        print(">>> Директория cards не найдена!")
        return renamed_files

    print(">>> Переименование файлов: id_name_type.png -> id.png")

    # Получаем список всех PNG файлов
    for filename in os.listdir(cards_dir):
        if not filename.lower().endswith('.png'):
            continue

        # Извлекаем id из имени файла (число перед первым подчеркиванием)
        match = re.match(r'(\d+)', filename)
        if match:
            file_id = int(match.group(1))

            # Ищем исходное имя файла
            old_path = os.path.join(cards_dir, filename)

            # Новое имя файла - просто id.png
            new_filename = f"{file_id}.png"
            new_path = os.path.join(cards_dir, new_filename)

            # Нужен ли суффикс для указа уникальности?
            # Ресурс или блок? Возможно использовать суффикс
            # Для ресурса: 1_resource.png, для блока: 39_block.png

            # Определяем тип файла
            if '_resource' in filename.lower():
                new_filename = f"{file_id}_resource.png"
                new_path = os.path.join(cards_dir, new_filename)
            elif '_block' in filename.lower():
                new_filename = f"{file_id}_block.png"
                new_path = os.path.join(cards_dir, new_filename)
            else:
                # Если не определен тип, используем просто id.png
                new_filename = f"{file_id}.png"
                new_path = os.path.join(cards_dir, new_filename)

            if old_path != new_path:
                try:
                    os.rename(old_path, new_path)
                    renamed_files[filename] = new_filename
                    print(f"OK: {filename} -> {new_filename}")
                except Exception as e:
                    print(f"ERROR переименования {filename}: {e}")
        else:
            print(f"Пропускаем файл с некорректным именем: {filename}")

    print(f"\n>>> Переименовано {len(renamed_files)} файлов")
    return renamed_files

def update_json_urls(renamed_files):
    """Обновляет URL в cards.json на новые имена файлов"""
    cards_file = 'cards.json'
    updated_count = 0

    try:
        with open(cards_file, 'r', encoding='utf-8') as f:
            cards_data = json.load(f)
    except Exception as e:
        print(f">>> Ошибка чтения JSON: {e}")
        return False

    card_names = {}

    # Сначала создадим словарь id -> тип
    for card in cards_data:
        card_id = card['id']
        card_type = 'resource' if card['type'] == 'resource' else 'block'
        card_names[card_id] = card_type

    print(">>> Обновление ссылок в cards.json")

    for card in cards_data:
        card_id = card['id']
        if card_id in card_names:
            card_type = card_names[card_id]

            # Создаем новый URL - только id_type.png или просто id.png
            new_filename = f"{card_id}_{card_type}.png"

            # Обновляем image_url
            old_url = card['image_url']
            url_parts = old_url.split('/')
            if url_parts:
                url_parts[-1] = new_filename
                new_url = '/'.join(url_parts)
                card['image_url'] = new_url
                updated_count += 1
                print(f"Карта {card_id}: {old_url.split('/')[-1]} -> {new_filename}")

    try:
        with open(cards_file, 'w', encoding='utf-8') as f:
            json.dump(cards_data, f, ensure_ascii=False, indent=2)
        print(f"\n>>> Обновлено {updated_count} URL в cards.json")
        return True
    except Exception as e:
        print(f">>> Ошибка сохранения JSON: {e}")
        return False

def main():
    print(">>> СИСТЕМА ПЕРЕИМЕНОВАНИЯ: id_name_type.png -> id_type.png")
    print(">>> Упрощение названий до ID + типа")

    # Шаг 1: Переименование файлов
    print("\n" + "="*60)
    renames = rename_to_numbers()

    # Шаг 2: Обновление JSON
    print("\n" + "="*60)
    if renames:
        success = update_json_urls(renames)
        if success:
            print("\n>>> ГОТОВО! Файлы переименованы и ссылки обновлены")
            print(">>> Все названия: ID_TYPE.png")
        else:
            print("\n>>> Ошибка в обновлении JSON")
    else:
        print("\n>>> Нет файлов для переименования")

if __name__ == "__main__":
    main()
