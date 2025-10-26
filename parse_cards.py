import json

with open('cards/description.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Split by lines
lines = [line.strip() for line in content.split('\n') if line.strip()]

cards = []
i = 0
while i < len(lines):
    if lines[i].strip('.').isdigit():  # is id
        card_id = int(lines[i].strip('.'))
        i += 1
        if i < len(lines):
            name = lines[i]
            i += 1
            description = []
            while i < len(lines) and not ('.'.join(lines[i].split('.')[:-1]).strip().isdigit() or lines[i].strip('.').isdigit()):
                description.append(lines[i])
                i += 1
            desc_text = '\n'.join(description).strip()
            cards.append({
                'id': card_id,
                'name': name,
                'description': desc_text,
                'type': 'resource' if card_id <= 38 else 'block'
            })
        else:
            break
    else:
        i += 1

with open('cards.json', 'w', encoding='utf-8') as f:
    json.dump(cards, f, ensure_ascii=False, indent=2)

print(f'Updated cards.json with {len(cards)} cards')
