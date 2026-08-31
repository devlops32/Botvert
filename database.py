import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import asyncio
from config import DATABASE_FILE

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._init_tables()
    
    def _init_tables(self):
        # Таблица пользователей (расширенная)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                full_name TEXT,
                language_code TEXT,
                is_bot INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                is_blocked INTEGER DEFAULT 0,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
        
        # Таблица заказов (расширенная)
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
                payment_confirmed INTEGER DEFAULT 0,
                photo_sent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confirmed_at TIMESTAMP,
                photo_sent_at TIMESTAMP,
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
        
        # Таблица логов активности пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица для рассылок
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS mailings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                text TEXT,
                total_sent INTEGER DEFAULT 0,
                total_failed INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    # ============ МЕТОДЫ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ ============
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None, 
                 language_code: str = None, is_bot: bool = False) -> bool:
        try:
            full_name = f"{first_name} {last_name}".strip() if first_name else username or str(user_id)
            
            self.cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
            exists = self.cursor.fetchone()
            
            if exists:
                self.cursor.execute('''
                    UPDATE users 
                    SET username = ?, 
                        first_name = ?, 
                        last_name = ?, 
                        full_name = ?,
                        language_code = ?,
                        is_bot = ?,
                        is_blocked = 0,
                        last_activity = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (username, first_name, last_name, full_name, language_code, 1 if is_bot else 0, user_id))
            else:
                self.cursor.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name, full_name, language_code, is_bot, is_admin, is_blocked, created_at, last_activity)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (user_id, username, first_name, last_name, full_name, language_code, 1 if is_bot else 0))
            
            self.conn.commit()
            self.log_user_activity(user_id, "start", "User started bot")
            return True
        except Exception as e:
            print(f"Error adding user: {e}")
            return False
    
    def set_user_blocked(self, user_id: int, blocked: bool = True) -> bool:
        """Отметить пользователя как заблокировавшего бота"""
        try:
            self.cursor.execute('''
                UPDATE users SET is_blocked = ? WHERE user_id = ?
            ''', (1 if blocked else 0, user_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error setting user blocked: {e}")
            return False
    
    def log_user_activity(self, user_id: int, action: str, details: str = None) -> bool:
        try:
            self.cursor.execute('''
                INSERT INTO user_activity (user_id, action, details)
                VALUES (?, ?, ?)
            ''', (user_id, action, details))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error logging activity: {e}")
            return False
    
    def set_admin(self, user_id: int) -> bool:
        try:
            self.cursor.execute('''
                UPDATE users SET is_admin = 1 WHERE user_id = ?
            ''', (user_id,))
            self.conn.commit()
            self.log_user_activity(user_id, "set_admin", "User promoted to admin")
            return True
        except Exception as e:
            print(f"Error setting admin: {e}")
            return False
    
    def get_user(self, user_id: int):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def get_user_by_username(self, username: str):
        self.cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        return self.cursor.fetchone()
    
    def is_admin(self, user_id: int) -> bool:
        self.cursor.execute('SELECT is_admin FROM users WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        return result and result[0] == 1
    
    def get_all_users(self) -> List[int]:
        """Получить список всех user_id (кроме заблокировавших бота)"""
        self.cursor.execute('SELECT user_id FROM users WHERE is_blocked = 0')
        return [row[0] for row in self.cursor.fetchall()]
    
    def get_all_users_with_status(self) -> List[Dict]:
        """Получить всех пользователей с их статусом"""
        self.cursor.execute('''
            SELECT user_id, username, first_name, last_name, full_name, 
                   language_code, is_admin, is_blocked, created_at, last_activity 
            FROM users 
            ORDER BY created_at DESC
        ''')
        rows = self.cursor.fetchall()
        return [{
            'user_id': row[0],
            'username': row[1],
            'first_name': row[2],
            'last_name': row[3],
            'full_name': row[4],
            'language_code': row[5],
            'is_admin': bool(row[6]),
            'is_blocked': bool(row[7]),
            'created_at': row[8],
            'last_activity': row[9]
        } for row in rows]
    
    def get_user_stats(self) -> Dict:
        self.cursor.execute('SELECT COUNT(*) FROM users')
        total = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT COUNT(*) FROM users WHERE is_blocked = 0')
        active = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT COUNT(*) FROM users WHERE is_blocked = 1')
        blocked = self.cursor.fetchone()[0]
        
        self.cursor.execute('''
            SELECT COUNT(DISTINCT user_id) 
            FROM user_activity 
            WHERE DATE(created_at) = DATE('now')
        ''')
        today_active = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1')
        admins = self.cursor.fetchone()[0]
        
        return {
            'total': total,
            'active': active,
            'blocked': blocked,
            'today_active': today_active,
            'admins': admins
        }
    
    def update_user_activity(self, user_id: int) -> bool:
        try:
            self.cursor.execute('''
                UPDATE users SET last_activity = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating user activity: {e}")
            return False
    
    # ============ МЕТОДЫ ДЛЯ РАБОТЫ С ГОРОДАМИ ============
    
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
    
    # ============ МЕТОДЫ ДЛЯ РАБОТЫ С ТОВАРАМИ ============
    
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
    
    def get_products_by_city(self, city_id: int, show_all: bool = False) -> List[Dict]:
        query = '''
            SELECT id, city_id, product_key, quantity, price, description, is_available 
            FROM products 
            WHERE city_id = ?
        '''
        if not show_all:
            query += ' AND is_available = 1'
        query += ' ORDER BY id'
        
        self.cursor.execute(query, (city_id,))
        rows = self.cursor.fetchall()
        return [{
            'id': row[0],
            'city_id': row[1],
            'product_key': row[2],
            'quantity': row[3],
            'price': row[4],
            'description': row[5],
            'is_available': bool(row[6])
        } for row in rows]
    
    def get_all_products(self) -> List[Dict]:
        self.cursor.execute('''
            SELECT p.id, p.city_id, p.product_key, p.quantity, p.price, p.description, p.is_available, c.name
            FROM products p
            LEFT JOIN cities c ON p.city_id = c.id
            ORDER BY p.id DESC
        ''')
        rows = self.cursor.fetchall()
        return [{
            'id': row[0],
            'city_id': row[1],
            'product_key': row[2],
            'quantity': row[3],
            'price': row[4],
            'description': row[5],
            'is_available': bool(row[6]),
            'city_name': row[7] or 'Город удален'
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
                'city_name': row[7] or 'Город удален'
            }
        return None
    
    def update_product(self, product_id: int, product_key: str = None, quantity: str = None, 
                      price: str = None, description: str = None) -> bool:
        try:
            updates = []
            params = []
            
            if product_key is not None:
                updates.append("product_key = ?")
                params.append(product_key)
            if quantity is not None:
                updates.append("quantity = ?")
                params.append(quantity)
            if price is not None:
                updates.append("price = ?")
                params.append(price)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            
            if not updates:
                return False
            
            params.append(product_id)
            query = f"UPDATE products SET {', '.join(updates)} WHERE id = ?"
            self.cursor.execute(query, params)
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating product: {e}")
            return False
    
    def delete_product(self, product_id: int) -> bool:
        try:
            self.cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting product: {e}")
            return False
    
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
    
    def get_products_count(self) -> int:
        self.cursor.execute('SELECT COUNT(*) FROM products')
        return self.cursor.fetchone()[0]
    
    # ============ МЕТОДЫ ДЛЯ РАБОТЫ С ЗАКАЗАМИ ============
    
    def create_order(self, user_id: int, product_id: int, city_id: int, product_name: str, 
                    quantity: str, price: str, description: str) -> Optional[int]:
        try:
            product = self.get_product_by_id(product_id)
            if not product:
                print(f"Product {product_id} not found")
                return None
            
            self.cursor.execute('''
                INSERT INTO orders (user_id, product_id, city_id, product_name, quantity, price, description, status, payment_confirmed, photo_sent)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 0, 0)
            ''', (user_id, product_id, city_id, product_name, quantity, price, description))
            self.conn.commit()
            
            order_id = self.cursor.lastrowid
            self.log_user_activity(user_id, "create_order", f"Order #{order_id}: {product_name} - {quantity}")
            return order_id
        except Exception as e:
            print(f"Error creating order: {e}")
            return None
    
    def confirm_payment(self, order_id: int) -> bool:
        try:
            self.cursor.execute('''
                UPDATE orders 
                SET payment_confirmed = 1, 
                    confirmed_at = CURRENT_TIMESTAMP,
                    status = 'confirmed'
                WHERE id = ?
            ''', (order_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error confirming payment: {e}")
            return False
    
    def reject_payment(self, order_id: int) -> bool:
        try:
            self.cursor.execute('''
                UPDATE orders 
                SET status = 'rejected'
                WHERE id = ?
            ''', (order_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error rejecting payment: {e}")
            return False
    
    def mark_photo_sent(self, order_id: int) -> bool:
        try:
            self.cursor.execute('''
                UPDATE orders 
                SET photo_sent = 1,
                    photo_sent_at = CURRENT_TIMESTAMP,
                    status = 'completed'
                WHERE id = ?
            ''', (order_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error marking photo sent: {e}")
            return False
    
    def get_order_by_id(self, order_id: int):
        try:
            self.cursor.execute('''
                SELECT 
                    o.id,
                    o.user_id,
                    o.product_id,
                    o.city_id,
                    o.product_name,
                    o.quantity,
                    o.price,
                    o.description,
                    o.status,
                    o.payment_confirmed,
                    o.photo_sent,
                    o.created_at,
                    o.confirmed_at,
                    o.photo_sent_at,
                    u.username,
                    u.first_name,
                    u.last_name,
                    u.full_name
                FROM orders o
                LEFT JOIN users u ON o.user_id = u.user_id
                WHERE o.id = ?
            ''', (order_id,))
            row = self.cursor.fetchone()
            
            if row:
                return {
                    'id': row[0],
                    'user_id': row[1],
                    'product_id': row[2],
                    'city_id': row[3],
                    'product_name': row[4],
                    'quantity': row[5],
                    'price': row[6],
                    'description': row[7],
                    'status': row[8],
                    'payment_confirmed': bool(row[9]),
                    'photo_sent': bool(row[10]),
                    'created_at': row[11],
                    'confirmed_at': row[12],
                    'photo_sent_at': row[13],
                    'username': row[14],
                    'first_name': row[15],
                    'last_name': row[16],
                    'full_name': row[17]
                }
            return None
        except Exception as e:
            print(f"Error getting order: {e}")
            return None
    
    def get_pending_orders(self):
        try:
            self.cursor.execute('''
                SELECT 
                    o.id,
                    o.user_id,
                    o.product_id,
                    o.city_id,
                    o.product_name,
                    o.quantity,
                    o.price,
                    o.description,
                    o.status,
                    o.payment_confirmed,
                    o.photo_sent,
                    o.created_at,
                    u.username,
                    u.first_name,
                    u.last_name
                FROM orders o
                LEFT JOIN users u ON o.user_id = u.user_id
                WHERE o.status IN ('pending', 'confirmed')
                ORDER BY o.created_at DESC
            ''')
            rows = self.cursor.fetchall()
            return [{
                'id': row[0],
                'user_id': row[1],
                'product_id': row[2],
                'city_id': row[3],
                'product_name': row[4],
                'quantity': row[5],
                'price': row[6],
                'description': row[7],
                'status': row[8],
                'payment_confirmed': bool(row[9]),
                'photo_sent': bool(row[10]),
                'created_at': row[11],
                'username': row[12],
                'first_name': row[13],
                'last_name': row[14]
            } for row in rows]
        except Exception as e:
            print(f"Error getting pending orders: {e}")
            return []
    
    def get_user_orders(self, user_id: int) -> List[Dict]:
        try:
            self.cursor.execute('''
                SELECT 
                    id,
                    product_name,
                    quantity,
                    price,
                    description,
                    status,
                    payment_confirmed,
                    photo_sent,
                    created_at
                FROM orders 
                WHERE user_id = ? 
                ORDER BY created_at DESC
            ''', (user_id,))
            rows = self.cursor.fetchall()
            return [{
                'id': row[0],
                'product_name': row[1],
                'quantity': row[2],
                'price': row[3],
                'description': row[4],
                'status': row[5],
                'payment_confirmed': bool(row[6]),
                'photo_sent': bool(row[7]),
                'created_at': row[8]
            } for row in rows]
        except Exception as e:
            print(f"Error getting user orders: {e}")
            return []
    
    def get_orders_awaiting_confirmation(self):
        try:
            self.cursor.execute('''
                SELECT 
                    o.id,
                    o.user_id,
                    o.product_id,
                    o.city_id,
                    o.product_name,
                    o.quantity,
                    o.price,
                    o.description,
                    o.status,
                    o.created_at,
                    u.username,
                    u.first_name,
                    u.last_name,
                    u.full_name,
                    c.name as city_name
                FROM orders o
                LEFT JOIN users u ON o.user_id = u.user_id
                LEFT JOIN cities c ON o.city_id = c.id
                WHERE o.status = 'pending' AND o.payment_confirmed = 0
                ORDER BY o.created_at DESC
            ''')
            rows = self.cursor.fetchall()
            return [{
                'id': row[0],
                'user_id': row[1],
                'product_id': row[2],
                'city_id': row[3],
                'product_name': row[4],
                'quantity': row[5],
                'price': row[6],
                'description': row[7],
                'status': row[8],
                'created_at': row[9],
                'username': row[10],
                'first_name': row[11],
                'last_name': row[12],
                'full_name': row[13],
                'city_name': row[14]
            } for row in rows]
        except Exception as e:
            print(f"Error getting orders awaiting confirmation: {e}")
            return []
    
    # ============ МЕТОДЫ ДЛЯ РАБОТЫ С ОПЛАТОЙ ============
    
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
    
    # ============ МЕТОДЫ ДЛЯ РАБОТЫ С РАССЫЛКАМИ ============
    
    def create_mailing(self, admin_id: int, text: str) -> Optional[int]:
        """Создать запись о рассылке"""
        try:
            self.cursor.execute('''
                INSERT INTO mailings (admin_id, text, status, created_at)
                VALUES (?, ?, 'pending', CURRENT_TIMESTAMP)
            ''', (admin_id, text))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"Error creating mailing: {e}")
            return None
    
    def update_mailing_stats(self, mailing_id: int, sent: int, failed: int) -> bool:
        """Обновить статистику рассылки"""
        try:
            self.cursor.execute('''
                UPDATE mailings 
                SET total_sent = ?, 
                    total_failed = ?,
                    status = 'completed',
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (sent, failed, mailing_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating mailing stats: {e}")
            return False
    
    def get_mailings(self, limit: int = 10) -> List[Dict]:
        """Получить историю рассылок"""
        self.cursor.execute('''
            SELECT id, admin_id, text, total_sent, total_failed, status, created_at, completed_at
            FROM mailings
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        rows = self.cursor.fetchall()
        return [{
            'id': row[0],
            'admin_id': row[1],
            'text': row[2],
            'total_sent': row[3],
            'total_failed': row[4],
            'status': row[5],
            'created_at': row[6],
            'completed_at': row[7]
        } for row in rows]
    
    # ============ МЕТОДЫ ДЛЯ СТАТИСТИКИ ============
    
    def get_statistics(self) -> Dict:
        self.cursor.execute('SELECT COUNT(*) FROM users')
        total_users = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT COUNT(*) FROM products WHERE is_available = 1')
        total_products = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT COUNT(*) FROM cities')
        total_cities = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT COUNT(*) FROM orders')
        total_orders = self.cursor.fetchone()[0]
        
        self.cursor.execute('''
            SELECT status, COUNT(*) 
            FROM orders 
            GROUP BY status
        ''')
        order_status = dict(self.cursor.fetchall())
        
        self.cursor.execute('SELECT COUNT(*) FROM mailings')
        total_mailings = self.cursor.fetchone()[0]
        
        return {
            'total_users': total_users,
            'total_products': total_products,
            'total_cities': total_cities,
            'total_orders': total_orders,
            'pending_orders': order_status.get('pending', 0),
            'confirmed_orders': order_status.get('confirmed', 0),
            'completed_orders': order_status.get('completed', 0),
            'rejected_orders': order_status.get('rejected', 0),
            'total_mailings': total_mailings
        }
    
    def close(self):
        self.conn.close()

# Создаем глобальный экземпляр
db = Database()