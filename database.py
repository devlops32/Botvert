import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
import asyncio
from config import DATABASE_FILE

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._init_tables()
    
    def _init_tables(self):
        # Таблица пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица городов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица товаров
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_id INTEGER,
                product_key TEXT,
                quantity TEXT,
                price TEXT,
                description TEXT,
                is_available INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (city_id) REFERENCES cities (id)
            )
        ''')
        
        # Таблица заказов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_id INTEGER,
                city_id INTEGER,
                product_name TEXT,
                quantity TEXT,
                price TEXT,
                description TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (product_id) REFERENCES products (id),
                FOREIGN KEY (city_id) REFERENCES cities (id)
            )
        ''')
        
        # Таблица настроек оплаты
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_number TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    # Методы для работы с пользователями
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error adding user: {e}")
            return False
    
    def set_admin(self, user_id: int) -> bool:
        """Назначить пользователя администратором"""
        try:
            self.cursor.execute('''
                UPDATE users SET is_admin = 1 WHERE user_id = ?
            ''', (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error setting admin: {e}")
            return False
    
    def get_user(self, user_id: int):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def is_admin(self, user_id: int) -> bool:
        self.cursor.execute('SELECT is_admin FROM users WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        return result and result[0] == 1
    
    def get_all_users(self):
        self.cursor.execute('SELECT user_id FROM users')
        return [row[0] for row in self.cursor.fetchall()]
    
    # Методы для работы с городами
    def add_city(self, name: str) -> bool:
        try:
            self.cursor.execute('INSERT OR IGNORE INTO cities (name) VALUES (?)', (name,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error adding city: {e}")
            return False
    
    def delete_city(self, city_id: int) -> bool:
        try:
            self.cursor.execute('DELETE FROM cities WHERE id = ?', (city_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting city: {e}")
            return False
    
    def get_cities(self) -> List[Dict]:
        self.cursor.execute('SELECT id, name FROM cities ORDER BY name')
        return [{'id': row[0], 'name': row[1]} for row in self.cursor.fetchall()]
    
    def get_city_by_id(self, city_id: int):
        self.cursor.execute('SELECT id, name FROM cities WHERE id = ?', (city_id,))
        row = self.cursor.fetchone()
        return {'id': row[0], 'name': row[1]} if row else None
    
    def get_city_by_name(self, name: str):
        self.cursor.execute('SELECT id, name FROM cities WHERE name = ?', (name,))
        row = self.cursor.fetchone()
        return {'id': row[0], 'name': row[1]} if row else None
    
    # Методы для работы с товарами
    def add_product(self, city_id: int, product_key: str, quantity: str, price: str, description: str) -> bool:
        try:
            self.cursor.execute('''
                INSERT INTO products (city_id, product_key, quantity, price, description, is_available)
                VALUES (?, ?, ?, ?, ?, 1)
            ''', (city_id, product_key, quantity, price, description))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error adding product: {e}")
            return False
    
    def get_products_by_city(self, city_id: int) -> List[Dict]:
        self.cursor.execute('''
            SELECT id, product_key, quantity, price, description, is_available 
            FROM products 
            WHERE city_id = ? AND is_available = 1
            ORDER BY id
        ''', (city_id,))
        rows = self.cursor.fetchall()
        return [{
            'id': row[0],
            'product_key': row[1],
            'quantity': row[2],
            'price': row[3],
            'description': row[4],
            'is_available': bool(row[5])
        } for row in rows]
    
    def get_product_by_id(self, product_id: int):
        self.cursor.execute('''
            SELECT p.id, p.city_id, p.product_key, p.quantity, p.price, p.description, p.is_available, c.name
            FROM products p
            LEFT JOIN cities c ON p.city_id = c.id
            WHERE p.id = ?
        ''', (product_id,))
        row = self.cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'city_id': row[1],
                'product_key': row[2],
                'quantity': row[3],
                'price': row[4],
                'description': row[5],
                'is_available': bool(row[6]),
                'city_name': row[7]
            }
        return None
    
    def update_product_availability(self, product_id: int, is_available: bool) -> bool:
        try:
            self.cursor.execute('''
                UPDATE products SET is_available = ? WHERE id = ?
            ''', (1 if is_available else 0, product_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating product: {e}")
            return False
    
    # Методы для работы с заказами
    def create_order(self, user_id: int, product_id: int, city_id: int, product_name: str, 
                    quantity: str, price: str, description: str) -> Optional[int]:
        try:
            self.cursor.execute('''
                INSERT INTO orders (user_id, product_id, city_id, product_name, quantity, price, description, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            ''', (user_id, product_id, city_id, product_name, quantity, price, description))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"Error creating order: {e}")
            return None
    
    def update_order_status(self, order_id: int, status: str) -> bool:
        try:
            self.cursor.execute('''
                UPDATE orders SET status = ? WHERE id = ?
            ''', (status, order_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating order: {e}")
            return False
    
    def get_order_by_id(self, order_id: int):
        """Получить заказ по ID"""
        self.cursor.execute('''
            SELECT o.*, u.user_id, u.username 
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            WHERE o.id = ?
        ''', (order_id,))
        return self.cursor.fetchone()
    
    def get_pending_orders(self):
        self.cursor.execute('''
            SELECT o.*, u.user_id, u.username 
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            WHERE o.status = 'pending'
            ORDER BY o.created_at DESC
        ''')
        return self.cursor.fetchall()
    
    # Методы для работы с оплатой
    def get_payment_card(self) -> Optional[str]:
        self.cursor.execute('SELECT card_number FROM payment_settings ORDER BY id DESC LIMIT 1')
        row = self.cursor.fetchone()
        return row[0] if row else None
    
    def update_payment_card(self, card_number: str) -> bool:
        try:
            self.cursor.execute('''
                INSERT INTO payment_settings (card_number, updated_at)
                VALUES (?, CURRENT_TIMESTAMP)
            ''', (card_number,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating card: {e}")
            return False
    
    # Методы для статистики
    def get_statistics(self) -> Dict:
        # Общее количество пользователей
        self.cursor.execute('SELECT COUNT(*) FROM users')
        total_users = self.cursor.fetchone()[0]
        
        # Количество товаров
        self.cursor.execute('SELECT COUNT(*) FROM products WHERE is_available = 1')
        total_products = self.cursor.fetchone()[0]
        
        # Количество городов
        self.cursor.execute('SELECT COUNT(*) FROM cities')
        total_cities = self.cursor.fetchone()[0]
        
        # Количество заказов
        self.cursor.execute('SELECT COUNT(*) FROM orders')
        total_orders = self.cursor.fetchone()[0]
        
        return {
            'total_users': total_users,
            'total_products': total_products,
            'total_cities': total_cities,
            'total_orders': total_orders
        }
    
    def close(self):
        self.conn.close()

# Создаем глобальный экземпляр
db = Database()