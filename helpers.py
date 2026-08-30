import re
from typing import List

def format_card_number(card_number: str) -> str:
    """Форматирование номера карты с пробелами"""
    # Удаляем все нецифровые символы
    digits = re.sub(r'\D', '', card_number)
    # Разбиваем по 4 цифры
    return ' '.join([digits[i:i+4] for i in range(0, len(digits), 4)])

def parse_product_line(line: str) -> dict:
    """Парсинг строки товара из list.txt"""
    parts = [p.strip() for p in line.split('|')]
    if len(parts) >= 2:
        return {
            'name': parts[0],
            'quantities': parts[1:] if len(parts) > 1 else []
        }
    return None

def read_product_list() -> dict:
    """Чтение списка товаров из файла"""
    products = {}
    try:
        with open('list.txt', 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    product = parse_product_line(line)
                    if product:
                        products[product['name']] = product['quantities']
    except FileNotFoundError:
        print("list.txt not found")
    return products

def chunk_list(items: List, chunk_size: int) -> List[List]:
    """Разбиение списка на чанки"""
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

def escape_markdown(text: str) -> str:
    """Экранирование Markdown символов"""
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text

def format_product_text(product: dict, city_name: str = None) -> str:
    """Форматирование текста товара"""
    text = f"✅ Продан Товар\n"
    if city_name:
        text += f"📍 Город - "
    text += f"{product['product_key']} - {product['quantity']} - {product['price']}₽ - {product['description']}"
    return text