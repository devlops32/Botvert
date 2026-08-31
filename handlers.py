from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
from helpers import format_card_number, read_product_list, chunk_list
from config import ADMIN_IDS, ITEMS_PER_PAGE
import asyncio
import logging
import datetime

router = Router()

class UserStates(StatesGroup):
    viewing_products = State()
    viewing_product_detail = State()
    order_confirmation = State()

class AdminStates(StatesGroup):
    adding_city = State()
    selecting_city_for_product = State()
    selecting_product = State()
    selecting_quantity = State()
    entering_price = State()
    selecting_description = State()
    changing_card = State()
    sending_photo = State()
    managing_products = State()
    editing_product = State()
    editing_product_field = State()
    confirming_delete = State()
    confirming_payment = State()
    mailing_text = State()  # Новое состояние для рассылки

class ProductStates(StatesGroup):
    selecting_city = State()
    selecting_product = State()
    selecting_quantity = State()
    entering_price = State()
    selecting_description = State()

class CityStates(StatesGroup):
    adding_city = State()

class PaymentStates(StatesGroup):
    changing_card = State()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="💦 Товары", callback_data="user_products")]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ Админка", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cities_keyboard(cities: list, page: int = 0) -> InlineKeyboardMarkup:
    total_pages = (len(cities) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE if cities else 1
    start_idx = page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, len(cities))
    page_cities = cities[start_idx:end_idx]
    
    keyboard = []
    for city in page_cities:
        keyboard.append([InlineKeyboardButton(
            text=f"📍 {city['name']}",
            callback_data=f"user_city_{city['id']}"
        )])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"user_cities_page_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"user_cities_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="user_back_to_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="📍 Города", callback_data="admin_cities")],
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_products")],
        [InlineKeyboardButton(text="📦 Управление товарами", callback_data="admin_manage_products")],
        [InlineKeyboardButton(text="💳 Оплата", callback_data="admin_payment")],
        [InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_mailing")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_cities_admin_keyboard(cities: list, page: int = 0) -> InlineKeyboardMarkup:
    total_pages = (len(cities) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE if cities else 1
    start_idx = page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, len(cities))
    page_cities = cities[start_idx:end_idx]
    
    keyboard = []
    for city in page_cities:
        keyboard.append([
            InlineKeyboardButton(text=f"📍 {city['name']}", callback_data=f"admin_city_view_{city['id']}"),
            InlineKeyboardButton(text="❌", callback_data=f"admin_city_delete_{city['id']}")
        ])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_cities_page_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_cities_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton(text="➕ Добавить город", callback_data="admin_add_city")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_cities_keyboard_admin(cities: list, page: int = 0) -> InlineKeyboardMarkup:
    total_pages = (len(cities) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE if cities else 1
    start_idx = page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, len(cities))
    page_cities = cities[start_idx:end_idx]
    
    keyboard = []
    for city in page_cities:
        keyboard.append([InlineKeyboardButton(
            text=f"📍 {city['name']}",
            callback_data=f"admin_product_city_{city['id']}"
        )])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_product_cities_page_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_product_cities_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_quantity_keyboard(quantities: list) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for i, qty in enumerate(quantities):
        row.append(InlineKeyboardButton(text=qty, callback_data=f"admin_qty_{qty}"))
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_product_back")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_description_keyboard() -> InlineKeyboardMarkup:
    descriptions = ["🔪 příkóp", "🧲 ń@ ḿ@ğñíté", "🎁 t@ÿńík"]
    keyboard = []
    for desc in descriptions:
        keyboard.append([InlineKeyboardButton(text=desc, callback_data=f"admin_desc_{desc}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_payment_keyboard(card_number: str = None) -> InlineKeyboardMarkup:
    from helpers import format_card_number
    formatted_card = format_card_number(card_number) if card_number else "Не указан"
    
    keyboard = [
        [InlineKeyboardButton(text=f"💳 Ваша карта: {formatted_card}", callback_data="noop")],
        [InlineKeyboardButton(text="✏️ Изменить карту", callback_data="admin_change_card")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_products_management_keyboard(products: list, page: int = 0) -> InlineKeyboardMarkup:
    from config import ITEMS_PER_PAGE
    
    total_pages = (len(products) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE if products else 1
    start_idx = page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, len(products))
    page_products = products[start_idx:end_idx]
    
    keyboard = []
    for product in page_products:
        status = "✅ В наличии" if product['is_available'] else "❌ Нет в наличии"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{product['product_key'][:20]} | {status}",
                callback_data=f"admin_product_detail_{product['id']}"
            )
        ])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_products_page_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_products_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_products")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_product_detail_keyboard(product_id: int, is_available: bool) -> InlineKeyboardMarkup:
    status_text = "📦 Сделать недоступным" if is_available else "📦 Сделать доступным"
    status_callback = f"admin_product_toggle_{product_id}"
    
    keyboard = [
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"admin_product_edit_{product_id}")],
        [InlineKeyboardButton(text=status_text, callback_data=status_callback)],
        [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"admin_product_delete_{product_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_manage_products")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_edit_product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="✏️ Название", callback_data=f"admin_edit_field_{product_id}_name")],
        [InlineKeyboardButton(text="✏️ Количество", callback_data=f"admin_edit_field_{product_id}_quantity")],
        [InlineKeyboardButton(text="✏️ Цена", callback_data=f"admin_edit_field_{product_id}_price")],
        [InlineKeyboardButton(text="✏️ Описание", callback_data=f"admin_edit_field_{product_id}_description")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin_product_detail_{product_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_payment_confirmation_keyboard(order_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="✅ Да", callback_data=f"admin_confirm_payment_{order_id}")],
        [InlineKeyboardButton(text="❌ Нет", callback_data=f"admin_reject_payment_{order_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_mailing_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="📨 Начать рассылку", callback_data="admin_start_mailing")],
        [InlineKeyboardButton(text="📊 История рассылок", callback_data="admin_mailing_history")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ==================== ОБРАБОТЧИКИ ПОЛЬЗОВАТЕЛЯ ====================

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user = message.from_user
    
    db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code,
        is_bot=user.is_bot
    )
    
    db.update_user_activity(user.id)
    logging.info(f"User started bot: {user.id} (@{user.username}) - {user.first_name} {user.last_name or ''}")
    
    if user.id in ADMIN_IDS:
        db.set_admin(user.id)
        logging.info(f"Admin {user.id} (@{user.username}) authenticated")
    
    is_admin = db.is_admin(user.id)
    text = "⚡ Привет я современный помощник, воспользуйся меню ниже ⬇️"
    
    await message.answer(
        text,
        reply_markup=get_main_menu_keyboard(is_admin)
    )
    await state.clear()

@router.callback_query(F.data == "user_back_to_menu")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    is_admin = db.is_admin(callback.from_user.id)
    await callback.message.answer(
        "⚡ Привет я современный помощник, воспользуйся меню ниже ⬇️",
        reply_markup=get_main_menu_keyboard(is_admin)
    )
    await callback.answer()
    await state.clear()

@router.callback_query(F.data == "user_products")
async def show_user_products(callback: types.CallbackQuery, state: FSMContext):
    cities = db.get_cities()
    if not cities:
        await callback.answer("❌ Нет доступных городов", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💦 Выберите город",
        reply_markup=get_cities_keyboard(cities, 0)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("user_cities_page_"))
async def user_cities_page(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[-1])
    cities = db.get_cities()
    await callback.message.edit_reply_markup(
        reply_markup=get_cities_keyboard(cities, page)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("user_city_"))
async def show_city_products(callback: types.CallbackQuery, state: FSMContext):
    city_id = int(callback.data.split("_")[-1])
    city = db.get_city_by_id(city_id)
    products = db.get_products_by_city(city_id)
    
    if not products:
        await callback.answer("❌ В этом городе нет товаров", show_alert=True)
        return
    
    await state.update_data(city_id=city_id, city_name=city['name'])
    
    keyboard = []
    for product in products:
        keyboard.append([InlineKeyboardButton(
            text=f"{product['product_key']} | {product['quantity']} | {product['price']}₽ | ✅ В наличии",
            callback_data=f"user_product_{product['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="user_back_to_menu")])
    
    await callback.message.edit_text(
        f"Товары по городу {city['name']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()
    await state.set_state(UserStates.viewing_products)

@router.callback_query(F.data.startswith("user_product_"))
async def show_product_detail(callback: types.CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[-1])
    product = db.get_product_by_id(product_id)
    
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    if not product['is_available']:
        await callback.answer("❌ Товар распродан", show_alert=True)
        return
    
    await state.update_data(product_id=product_id)
    
    card_number = db.get_payment_card() or "Не указан"
    formatted_card = format_card_number(card_number) if card_number else "Не указан"
    
    text = f"""*Товар* : {product['product_key']}
*Количество* : {product['quantity']}
*Цена* : {product['price']}₽
*Описание* : {product['description']}
*Статус* : ✅ В наличии

*💳 Перевод на карту* : `{formatted_card}`

❗ После оплаты обязательно нажмите кнопку ✅ Я оплатил ❗"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"user_paid_{product_id}")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="user_back_to_menu")]
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()
    await state.set_state(UserStates.viewing_product_detail)

# ==================== ОБРАБОТЧИК ОПЛАТЫ ====================

@router.callback_query(F.data.startswith("user_paid_"))
async def user_paid(callback: types.CallbackQuery, state: FSMContext):
    """Пользователь подтвердил оплату - ТОВАР НЕ СКРЫВАЕТСЯ!"""
    product_id = int(callback.data.split("_")[-1])
    product = db.get_product_by_id(product_id)
    
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    user_id = callback.from_user.id
    data = await state.get_data()
    city_id = data.get('city_id', product['city_id'])
    
    user = db.get_user(user_id)
    username = user[1] if user else "Unknown"
    
    order_id = db.create_order(
        user_id=user_id,
        product_id=product_id,
        city_id=city_id,
        product_name=product['product_key'],
        quantity=product['quantity'],
        price=product['price'],
        description=product['description']
    )
    
    if order_id:
        await callback.message.edit_text(
            "⏳ Ожидайте подтверждения оплаты..."
        )
        
        for admin_id in ADMIN_IDS:
            try:
                text = f"""*Подтверждение оплаты!*
📍 {product['city_name']} - {product['product_key']} - {product['quantity']} - {product['price']}₽ - {product['description']}
Пользователь: @{username if username else 'Unknown'}, ждет товар, вам пришли {product['price']}₽?"""
                
                keyboard = get_payment_confirmation_keyboard(order_id)
                
                await callback.bot.send_message(
                    admin_id,
                    text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logging.error(f"Error sending admin notification: {e}")
        
        await callback.answer("✅ Оплата отправлена на подтверждение!")
    else:
        await callback.answer("❌ Ошибка при создании заказа", show_alert=True)
    
    await state.clear()

# ==================== ОБРАБОТЧИКИ ПОДТВЕРЖДЕНИЯ ОПЛАТЫ ====================

@router.callback_query(F.data.startswith("admin_confirm_payment_"))
async def admin_confirm_payment(callback: types.CallbackQuery, state: FSMContext):
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return
    
    order_id = int(callback.data.split("_")[-1])
    order = db.get_order_by_id(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    product_id = order['product_id']
    
    if db.confirm_payment(order_id):
        db.update_product_availability(product_id, False)
        
        await callback.message.edit_text(
            f"✅ Оплата подтверждена!\n"
            f"Заказ #{order_id} - {order['product_name']}\n"
            f"✅ Товар скрыт с витрины!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📸 Отправить фото", callback_data=f"admin_send_photo_{order_id}")],
                [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close_order")]
            ])
        )
        
        try:
            await callback.bot.send_message(
                order['user_id'],
                "✅ Ваша оплата подтверждена! В течение 30 минут вы получите товар!"
            )
        except Exception as e:
            logging.error(f"Error sending confirmation to user: {e}")
            # Если пользователь заблокировал бота - отмечаем это
            if "bot was blocked" in str(e).lower():
                db.set_user_blocked(order['user_id'], True)
        
        await callback.answer("✅ Оплата подтверждена, товар скрыт с витрины!")
        asyncio.create_task(send_photo_after_delay(callback.bot, order_id))
    else:
        await callback.answer("❌ Ошибка при подтверждении", show_alert=True)

@router.callback_query(F.data.startswith("admin_reject_payment_"))
async def admin_reject_payment(callback: types.CallbackQuery, state: FSMContext):
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return
    
    order_id = int(callback.data.split("_")[-1])
    order = db.get_order_by_id(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    if db.reject_payment(order_id):
        await callback.message.edit_text(
            f"❌ Оплата отклонена!\n"
            f"Заказ #{order_id} - {order['product_name']}\n"
            f"✅ Товар остался на витрине!"
        )
        
        try:
            await callback.bot.send_message(
                order['user_id'],
                "❌ Ваша оплата не найдена!"
            )
        except Exception as e:
            logging.error(f"Error sending rejection to user: {e}")
            if "bot was blocked" in str(e).lower():
                db.set_user_blocked(order['user_id'], True)
        
        await callback.answer("❌ Оплата отклонена, товар доступен")
    else:
        await callback.answer("❌ Ошибка при отклонении", show_alert=True)

# ==================== ФУНКЦИЯ ОТПРАВКИ ФОТО ЧЕРЕЗ 30 МИНУТ ====================

async def send_photo_after_delay(bot, order_id: int):
    await asyncio.sleep(1800)
    
    order = db.get_order_by_id(order_id)
    if not order:
        logging.error(f"Order {order_id} not found for delayed photo")
        return
    
    if order['photo_sent']:
        return
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"⏰ Прошло 30 минут! Отправьте фото для заказа #{order_id}\n"
                f"Пользователь: {order['full_name'] or 'Unknown'}\n"
                f"Товар: {order['product_name']}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📸 Отправить фото", callback_data=f"admin_send_photo_{order_id}")]
                ])
            )
        except Exception as e:
            logging.error(f"Error notifying admin about delayed photo: {e}")

# ==================== ОБРАБОТЧИКИ РАССЫЛКИ ====================

@router.callback_query(F.data == "admin_mailing")
async def admin_mailing_menu(callback: types.CallbackQuery, state: FSMContext):
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return
    
    stats = db.get_user_stats()
    
    text = f"""📨 *Рассылка*

👥 Всего пользователей: {stats['total']}
✅ Активных: {stats['active']}
🚫 Заблокировали бота: {stats['blocked']}

Выберите действие:"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_mailing_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()
    await state.clear()

@router.callback_query(F.data == "admin_start_mailing")
async def admin_start_mailing(callback: types.CallbackQuery, state: FSMContext):
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📨 *Отправьте текст рассылки*\n\n"
        "Текст будет отправлен ВСЕМ пользователям бота.\n"
        "⚠️ Отправьте текст сообщения (можно с эмодзи и форматированием).\n\n"
        "❌ Для отмены нажмите кнопку ниже:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_mailing")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()
    await state.set_state(AdminStates.mailing_text)

@router.message(AdminStates.mailing_text)
async def admin_send_mailing(message: types.Message, state: FSMContext):
    if not db.is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав")
        await state.clear()
        return
    
    # Получаем текст рассылки
    mailing_text = message.text
    
    if not mailing_text:
        await message.answer("❌ Текст не может быть пустым")
        return
    
    # Создаем запись о рассылке
    mailing_id = db.create_mailing(message.from_user.id, mailing_text)
    
    if not mailing_id:
        await message.answer("❌ Ошибка при создании рассылки")
        await state.clear()
        return
    
    # Отправляем статус
    status_msg = await message.answer("⏳ Начинаю рассылку...")
    
    # Получаем всех пользователей
    users = db.get_all_users()
    total_users = len(users)
    
    if total_users == 0:
        await status_msg.edit_text("❌ Нет пользователей для рассылки")
        await state.clear()
        return
    
    sent = 0
    failed = 0
    
    # Отправляем рассылку
    for user_id in users:
        try:
            await message.bot.send_message(
                chat_id=user_id,
                text=mailing_text,
                parse_mode="Markdown"
            )
            sent += 1
            await asyncio.sleep(0.05)  # Защита от флуда
        except Exception as e:
            failed += 1
            error_msg = str(e)
            logging.error(f"Error sending mailing to {user_id}: {error_msg}")
            
            # Если пользователь заблокировал бота - отмечаем это
            if "bot was blocked" in error_msg.lower():
                db.set_user_blocked(user_id, True)
            elif "chat not found" in error_msg.lower():
                db.set_user_blocked(user_id, True)
        
        # Обновляем статус каждые 10 пользователей
        if (sent + failed) % 10 == 0:
            await status_msg.edit_text(
                f"⏳ Рассылка...\n"
                f"📤 Отправлено: {sent}\n"
                f"❌ Ошибок: {failed}\n"
                f"📊 Осталось: {total_users - sent - failed}"
            )
    
    # Обновляем статистику рассылки
    db.update_mailing_stats(mailing_id, sent, failed)
    
    # Финальный отчет
    await status_msg.edit_text(
        f"✅ *Рассылка завершена!*\n\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"📊 Доставлено: {sent}/{total_users}\n"
        f"📅 ID рассылки: #{mailing_id}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 История рассылок", callback_data="admin_mailing_history")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_mailing")]
        ])
    )
    
    await state.clear()

@router.callback_query(F.data == "admin_mailing_history")
async def admin_mailing_history(callback: types.CallbackQuery, state: FSMContext):
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return
    
    mailings = db.get_mailings(20)
    
    if not mailings:
        await callback.message.edit_text(
            "📊 История рассылок пуста",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_mailing")]
            ])
        )
        await callback.answer()
        return
    
    text = "📊 *История рассылок*\n\n"
    
    for m in mailings:
        status_emoji = "✅" if m['status'] == 'completed' else "⏳"
        text += f"{status_emoji} #{m['id']} | {m['created_at'][:16]}\n"
        text += f"   📤 {m['total_sent']} доставлено | ❌ {m['total_failed']} ошибок\n"
        text += f"   📝 {m['text'][:50]}...\n\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_mailing")]
        ])
    )
    await callback.answer()

# ==================== ОСТАЛЬНЫЕ ОБРАБОТЧИКИ ====================

@router.callback_query(F.data == "admin_close_order")
async def admin_close_order(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data.startswith("admin_send_photo_"))
async def admin_send_photo_start(callback: types.CallbackQuery, state: FSMContext):
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return
    
    order_id = int(callback.data.split("_")[-1])
    await state.update_data(order_id=order_id)
    
    order = db.get_order_by_id(order_id)
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    user_id = order['user_id']
    user = db.get_user(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"📸 Отправьте фото для покупателя:\n"
        f"👤 {order['full_name'] or order['first_name'] or 'Пользователь'}\n"
        f"🆔 ID: {user_id}\n"
        f"📦 Товар: {order['product_name']}\n"
        f"💰 Цена: {order['price']}₽",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel_photo")]
        ])
    )
    await callback.answer()
    await state.set_state(AdminStates.sending_photo)

@router.callback_query(F.data == "admin_cancel_photo")
async def admin_cancel_photo(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.answer("❌ Отменено")
    await state.clear()

@router.message(AdminStates.sending_photo)
async def admin_send_photo(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.answer("❌ Пожалуйста, отправьте фото")
        return
    
    data = await state.get_data()
    order_id = data.get('order_id')
    
    if not order_id:
        await message.answer("❌ Ошибка: ID заказа не найден")
        await state.clear()
        return
    
    order = db.get_order_by_id(order_id)
    if not order:
        await message.answer(f"❌ Заказ #{order_id} не найден")
        await state.clear()
        return
    
    user_id = order['user_id']
    photo_file_id = message.photo[-1].file_id
    
    user = db.get_user(user_id)
    if not user:
        await message.answer(f"❌ Пользователь с ID {user_id} не найден")
        await state.clear()
        return
    
    status_msg = await message.answer(f"⏳ Отправка фото пользователю...")
    
    try:
        await message.bot.send_photo(
            chat_id=user_id,
            photo=photo_file_id
        )
        
        await status_msg.edit_text("✅ Фото успешно отправлено покупателю!")
        db.mark_photo_sent(order_id)
        db.log_user_activity(user_id, "photo_sent", f"Photo sent for order #{order_id}")
        await message.delete()
        
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error sending photo to user {user_id}: {error_msg}")
        
        error_text = "❌ Ошибка при отправке фото:\n\n"
        
        if "chat not found" in error_msg:
            error_text += (
                f"Пользователь (ID: {user_id}) не начал диалог с ботом.\n\n"
                f"💡 Решение: Попросите пользователя написать боту /start"
            )
            db.set_user_blocked(user_id, True)
        elif "bot was blocked" in error_msg:
            error_text += f"Пользователь (ID: {user_id}) заблокировал бота."
            db.set_user_blocked(user_id, True)
        elif "user is deactivated" in error_msg:
            error_text += f"Аккаунт пользователя (ID: {user_id}) деактивирован."
            db.set_user_blocked(user_id, True)
        else:
            error_text += f"{error_msg}\n\n💡 Попробуйте еще раз"
        
        await status_msg.edit_text(error_text)
    
    await state.clear()

# ==================== ОБРАБОТЧИКИ УПРАВЛЕНИЯ ТОВАРАМИ ====================

@router.callback_query(F.data == "admin_manage_products")
async def admin_manage_products(callback: types.CallbackQuery, state: FSMContext):
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return
    
    products = db.get_all_products()
    
    if not products:
        await callback.message.edit_text(
            "📦 Список товаров пуст\n\n➕ Нажмите 'Добавить товар' чтобы создать новый товар",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_products")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
            ])
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "📦 Управление товарами\n\nВыберите товар для редактирования:",
        reply_markup=get_products_management_keyboard(products, 0)
    )
    await callback.answer()
    await state.set_state(AdminStates.managing_products)

@router.callback_query(F.data.startswith("admin_products_page_"))
async def admin_products_page(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[-1])
    products = db.get_all_products()
    await callback.message.edit_reply_markup(
        reply_markup=get_products_management_keyboard(products, page)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_product_detail_"))
async def admin_product_detail(callback: types.CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[-1])
    product = db.get_product_by_id(product_id)
    
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    status = "✅ В наличии" if product['is_available'] else "❌ Нет в наличии"
    
    text = f"""📦 *Информация о товаре*

🏷️ Название: {product['product_key']}
📍 Город: {product['city_name']}
📊 Количество: {product['quantity']}
💰 Цена: {product['price']}₽
📝 Описание: {product['description']}
📌 Статус: {status}
🆔 ID: {product['id']}"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_product_detail_keyboard(product_id, product['is_available']),
        parse_mode="Markdown"
    )
    await callback.answer()

# ==================== РЕДАКТИРОВАНИЕ ТОВАРА ====================

@router.callback_query(F.data.startswith("admin_product_edit_"))
async def admin_product_edit(callback: types.CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[-1])
    product = db.get_product_by_id(product_id)
    
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    await state.update_data(editing_product_id=product_id)
    
    await callback.message.edit_text(
        f"✏️ Редактирование товара\n\nВыберите поле для изменения:",
        reply_markup=get_edit_product_keyboard(product_id)
    )
    await callback.answer()
    await state.set_state(AdminStates.editing_product)

@router.callback_query(F.data.startswith("admin_edit_field_"))
async def admin_edit_field(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data.split("_")
    product_id = int(data[3])
    field = data[4]
    
    field_names = {
        'name': 'название',
        'quantity': 'количество',
        'price': 'цену',
        'description': 'описание'
    }
    
    await state.update_data(editing_product_id=product_id, editing_field=field)
    
    await callback.message.edit_text(
        f"✏️ Введите новое {field_names.get(field, field)} для товара:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_product_edit_{product_id}")]
        ])
    )
    await callback.answer()
    await state.set_state(AdminStates.editing_product_field)

@router.message(AdminStates.editing_product_field)
async def admin_save_edited_field(message: types.Message, state: FSMContext):
    data = await state.get_data()
    product_id = data.get('editing_product_id')
    field = data.get('editing_field')
    
    if not product_id or not field:
        await message.answer("❌ Ошибка: данные не найдены")
        await state.clear()
        return
    
    new_value = message.text.strip()
    
    if not new_value:
        await message.answer("❌ Значение не может быть пустым")
        return
    
    field_mapping = {
        'name': 'product_key',
        'quantity': 'quantity',
        'price': 'price',
        'description': 'description'
    }
    
    db_field = field_mapping.get(field)
    if not db_field:
        await message.answer("❌ Неизвестное поле")
        await state.clear()
        return
    
    if field == 'price':
        if not new_value.replace('.', '').isdigit():
            await message.answer("❌ Цена должна быть числом")
            return
    
    product = db.get_product_by_id(product_id)
    if not product:
        await message.answer("❌ Товар не найден")
        await state.clear()
        return
    
    if db.update_product(product_id, **{db_field: new_value}):
        await message.answer(f"✅ {field.capitalize()} обновлено на: {new_value}")
        
        updated_product = db.get_product_by_id(product_id)
        status = "✅ В наличии" if updated_product['is_available'] else "❌ Нет в наличии"
        
        text = f"""📦 *Информация о товаре*

🏷️ Название: {updated_product['product_key']}
📍 Город: {updated_product['city_name']}
📊 Количество: {updated_product['quantity']}
💰 Цена: {updated_product['price']}₽
📝 Описание: {updated_product['description']}
📌 Статус: {status}
🆔 ID: {updated_product['id']}"""
        
        await message.answer(
            text,
            reply_markup=get_product_detail_keyboard(product_id, updated_product['is_available']),
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ Ошибка при обновлении")
    
    await state.clear()

# ==================== ВКЛЮЧЕНИЕ/ОТКЛЮЧЕНИЕ ТОВАРА ====================

@router.callback_query(F.data.startswith("admin_product_toggle_"))
async def admin_product_toggle(callback: types.CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[-1])
    product = db.get_product_by_id(product_id)
    
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    new_status = not product['is_available']
    db.update_product_availability(product_id, new_status)
    
    status_text = "доступен" if new_status else "недоступен"
    await callback.answer(f"✅ Товар теперь {status_text}")
    
    updated_product = db.get_product_by_id(product_id)
    status = "✅ В наличии" if updated_product['is_available'] else "❌ Нет в наличии"
    
    text = f"""📦 *Информация о товаре*

🏷️ Название: {updated_product['product_key']}
📍 Город: {updated_product['city_name']}
📊 Количество: {updated_product['quantity']}
💰 Цена: {updated_product['price']}₽
📝 Описание: {updated_product['description']}
📌 Статус: {status}
🆔 ID: {updated_product['id']}"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_product_detail_keyboard(product_id, updated_product['is_available']),
        parse_mode="Markdown"
    )

# ==================== УДАЛЕНИЕ ТОВАРА ====================

@router.callback_query(F.data.startswith("admin_product_delete_"))
async def admin_product_delete_confirm(callback: types.CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[-1])
    product = db.get_product_by_id(product_id)
    
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    await state.update_data(deleting_product_id=product_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"admin_product_delete_confirm_{product_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_product_detail_{product_id}")]
    ])
    
    await callback.message.edit_text(
        f"⚠️ *Вы уверены, что хотите удалить товар?*\n\n"
        f"🏷️ {product['product_key']}\n"
        f"📍 {product['city_name']}\n"
        f"💰 {product['price']}₽\n\n"
        f"Это действие нельзя отменить!",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_product_delete_confirm_"))
async def admin_product_delete(callback: types.CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[-1])
    
    if db.delete_product(product_id):
        await callback.answer("✅ Товар удален")
        await callback.message.edit_text(
            "🗑️ Товар успешно удален",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📦 Управление товарами", callback_data="admin_manage_products")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
            ])
        )
    else:
        await callback.answer("❌ Ошибка при удалении", show_alert=True)
    
    await state.clear()

# ==================== ОБРАБОТЧИКИ АДМИНА (ОСТАЛЬНЫЕ) ====================

@router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: types.CallbackQuery, state: FSMContext):
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "⚙️ Админка",
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()
    await state.clear()

@router.callback_query(F.data == "admin_back_to_menu")
async def admin_back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    is_admin = db.is_admin(callback.from_user.id)
    await callback.message.answer(
        "⚡ Привет я современный помощник, воспользуйся меню ниже ⬇️",
        reply_markup=get_main_menu_keyboard(is_admin)
    )
    await callback.answer()
    await state.clear()

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return
    
    stats = db.get_statistics()
    user_stats = db.get_user_stats()
    
    text = f"""📊 *Статистика*

👥 *Пользователи*
• Всего: {stats['total_users']}
• Активных: {user_stats['active']}
• Заблокировали бота: {user_stats['blocked']}
• Администраторов: {user_stats['admins']}

🏙️ *Города*: {stats['total_cities']}
📦 *Товары в наличии*: {stats['total_products']}

🛒 *Заказы*
• Всего: {stats['total_orders']}
• ⏳ Ожидают оплаты: {stats['pending_orders']}
• ✅ Подтверждено: {stats['confirmed_orders']}
• 📸 Завершено: {stats['completed_orders']}
• ❌ Отклонено: {stats['rejected_orders']}

📨 *Рассылки*: {stats['total_mailings']}"""
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
        ])
    )
    await callback.answer()

# ==================== ОБРАБОТЧИКИ ГОРОДОВ ====================

@router.callback_query(F.data == "admin_cities")
async def admin_cities(callback: types.CallbackQuery, state: FSMContext):
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return
    
    cities = db.get_cities()
    await callback.message.edit_text(
        "📍 Города",
        reply_markup=get_cities_admin_keyboard(cities, 0)
    )
    await callback.answer()
    await state.clear()

@router.callback_query(F.data.startswith("admin_cities_page_"))
async def admin_cities_page(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[-1])
    cities = db.get_cities()
    await callback.message.edit_reply_markup(
        reply_markup=get_cities_admin_keyboard(cities, page)
    )
    await callback.answer()

@router.callback_query(F.data == "admin_add_city")
async def admin_add_city_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✏️ Введите название города или метро")
    await callback.answer()
    await state.set_state(CityStates.adding_city)

@router.message(CityStates.adding_city)
async def admin_add_city(message: types.Message, state: FSMContext):
    city_name = message.text.strip()
    
    if db.add_city(city_name):
        await message.answer(f"✅ Город {city_name} добавлен!")
    else:
        await message.answer(f"❌ Город {city_name} уже существует или ошибка добавления")
    
    cities = db.get_cities()
    await message.answer(
        "📍 Города",
        reply_markup=get_cities_admin_keyboard(cities, 0)
    )
    await state.clear()

@router.callback_query(F.data.startswith("admin_city_delete_"))
async def admin_delete_city(callback: types.CallbackQuery):
    city_id = int(callback.data.split("_")[-1])
    city = db.get_city_by_id(city_id)
    
    if not city:
        await callback.answer("❌ Город не найден", show_alert=True)
        return
    
    if db.delete_city(city_id):
        cities = db.get_cities()
        await callback.message.edit_text(
            "📍 Города",
            reply_markup=get_cities_admin_keyboard(cities, 0)
        )
        await callback.answer(f"✅ Город {city['name']} удален")
    else:
        await callback.answer("❌ Ошибка при удалении города", show_alert=True)

# ==================== ОБРАБОТЧИКИ ДОБАВЛЕНИЯ ТОВАРА ====================

@router.callback_query(F.data == "admin_products")
async def admin_products_start(callback: types.CallbackQuery, state: FSMContext):
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return
    
    cities = db.get_cities()
    if not cities:
        await callback.answer("❌ Сначала добавьте города", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💦 Добавление товара\n📍 Выберите город для товара",
        reply_markup=get_cities_keyboard_admin(cities, 0)
    )
    await callback.answer()
    await state.set_state(ProductStates.selecting_city)

@router.callback_query(F.data.startswith("admin_product_cities_page_"))
async def admin_product_cities_page(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[-1])
    cities = db.get_cities()
    await callback.message.edit_reply_markup(
        reply_markup=get_cities_keyboard_admin(cities, page)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_product_city_"))
async def admin_product_select_city(callback: types.CallbackQuery, state: FSMContext):
    city_id = int(callback.data.split("_")[-1])
    await state.update_data(city_id=city_id)
    
    products = read_product_list()
    product_names = list(products.keys())
    
    if not product_names:
        await callback.answer("❌ Нет доступных товаров в list.txt", show_alert=True)
        return
    
    await state.update_data(all_products=products, product_names=product_names)
    
    keyboard = []
    row = []
    for i, name in enumerate(product_names):
        row.append(InlineKeyboardButton(text=name, callback_data=f"admin_product_select_{city_id}_{name}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_products")])
    
    await callback.message.edit_text(
        "💦 Выберите товар",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()
    await state.set_state(ProductStates.selecting_product)

@router.callback_query(F.data.startswith("admin_product_select_"))
async def admin_product_select(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data.split("_")
    city_id = int(data[3])
    product_name = "_".join(data[4:])
    
    products = read_product_list()
    quantities = products.get(product_name, [])
    
    if not quantities:
        await callback.answer("❌ Нет доступного количества", show_alert=True)
        return
    
    await state.update_data(product_name=product_name, quantities=quantities, city_id=city_id)
    
    keyboard = get_quantity_keyboard(quantities)
    
    await callback.message.edit_text(
        "💦 Выберите количество",
        reply_markup=keyboard
    )
    await callback.answer()
    await state.set_state(ProductStates.selecting_quantity)

@router.callback_query(F.data == "admin_product_back")
async def admin_product_back(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    city_id = data.get('city_id')
    
    if city_id:
        products = read_product_list()
        product_names = list(products.keys())
        
        keyboard = []
        row = []
        for i, name in enumerate(product_names):
            row.append(InlineKeyboardButton(text=name, callback_data=f"admin_product_select_{city_id}_{name}"))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_products")])
        
        await callback.message.edit_text(
            "💦 Выберите товар",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    else:
        await callback.message.edit_text(
            "💦 Добавление товара\n📍 Выберите город для товара",
            reply_markup=get_cities_keyboard_admin(db.get_cities(), 0)
        )
    
    await callback.answer()
    await state.set_state(ProductStates.selecting_city)

@router.callback_query(F.data.startswith("admin_qty_"))
async def admin_select_quantity(callback: types.CallbackQuery, state: FSMContext):
    quantity = callback.data.split("_")[-1]
    await state.update_data(quantity=quantity)
    
    await callback.message.edit_text(
        "💵 Введите цену товара"
    )
    await callback.answer()
    await state.set_state(ProductStates.entering_price)

@router.message(ProductStates.entering_price)
async def admin_enter_price(message: types.Message, state: FSMContext):
    price = message.text.strip()
    if not price.replace('.', '').isdigit():
        await message.answer("❌ Пожалуйста, введите корректную цену (цифры)")
        return
    
    await state.update_data(price=price)
    
    await message.answer(
        "🔧 Выберите Описание",
        reply_markup=get_description_keyboard()
    )
    await state.set_state(ProductStates.selecting_description)

@router.callback_query(F.data.startswith("admin_desc_"))
async def admin_select_description(callback: types.CallbackQuery, state: FSMContext):
    description = callback.data.split("_", 2)[-1]
    await state.update_data(description=description)
    
    data = await state.get_data()
    city_id = data.get('city_id')
    product_name = data.get('product_name')
    quantity = data.get('quantity')
    price = data.get('price')
    
    if db.add_product(city_id, product_name, quantity, price, description):
        city = db.get_city_by_id(city_id)
        city_name = city['name'] if city else "Неизвестный город"
        
        admin_text = f"*✅ Товар добавлен*\n📍 {city_name} - {product_name} - {quantity} - {price}₽ - {description}"
        
        await callback.message.edit_text(
            admin_text,
            parse_mode="Markdown"
        )
        
        await notify_users_about_new_product(callback.bot, city_name, product_name, quantity, price, description)
        
    else:
        await callback.message.edit_text("❌ Ошибка при добавлении товара")
    
    await callback.answer()
    await state.clear()

async def notify_users_about_new_product(bot, city_name: str, product_name: str, quantity: str, price: str, description: str):
    users = db.get_all_users()
    
    text = f"*✅ Новый товар*\n📍 {city_name} - {product_name} - {quantity} - {price}₽ - {description} - ✅ В наличии"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Перейти к товару", callback_data="user_products")]
    ])
    
    for user_id in users:
        try:
            await bot.send_message(
                user_id,
                text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await asyncio.sleep(0.05)
        except Exception as e:
            logging.error(f"Error sending notification to {user_id}: {e}")
            if "bot was blocked" in str(e).lower():
                db.set_user_blocked(user_id, True)

# ==================== ОБРАБОТЧИКИ ОПЛАТЫ ====================

@router.callback_query(F.data == "admin_payment")
async def admin_payment(callback: types.CallbackQuery, state: FSMContext):
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return
    
    card_number = db.get_payment_card()
    await callback.message.edit_text(
        "💳 Оплата",
        reply_markup=get_payment_keyboard(card_number)
    )
    await callback.answer()
    await state.clear()

@router.callback_query(F.data == "admin_change_card")
async def admin_change_card_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "✏️ Введите номер карты в любом формате"
    )
    await callback.answer()
    await state.set_state(PaymentStates.changing_card)

@router.message(PaymentStates.changing_card)
async def admin_change_card(message: types.Message, state: FSMContext):
    card_number = ''.join(filter(str.isdigit, message.text))
    
    if len(card_number) < 16:
        await message.answer("❌ Пожалуйста, введите корректный номер карты (минимум 16 цифр)")
        return
    
    if db.update_payment_card(card_number):
        await message.answer("✅ Номер карты обновлен!")
        card_number = db.get_payment_card()
        await message.answer(
            "💳 Оплата",
            reply_markup=get_payment_keyboard(card_number)
        )
    else:
        await message.answer("❌ Ошибка при обновлении номера карты")
    
    await state.clear()

# ==================== ОБРАБОТЧИКИ ПОЛЬЗОВАТЕЛЕЙ (АДМИН) ====================

@router.callback_query(F.data == "admin_users")
async def admin_users_list(callback: types.CallbackQuery):
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return
    
    users = db.get_all_users_with_status()
    stats = db.get_user_stats()
    
    text = f"""👥 Список пользователей

📊 Статистика:
• Всего: {stats['total']}
• Активных: {stats['active']}
• Заблокировали бота: {stats['blocked']}
• Активны сегодня: {stats['today_active']}
• Администраторов: {stats['admins']}

📋 Последние пользователи:
"""
    
    for user in users[:10]:
        username = f"@{user['username']}" if user['username'] else "Нет username"
        status_icon = "🚫" if user['is_blocked'] else "✅"
        text += f"\n• {status_icon} {user['user_id']} | {username} | {user['full_name']}"
        if user['is_admin']:
            text += " 👑"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Полная статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard
    )
    await callback.answer()

# ==================== ОБЩИЙ ОБРАБОТЧИК ====================

@router.callback_query(lambda c: c.data == "noop")
async def noop_callback(callback):
    await callback.answer()