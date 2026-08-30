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
    """Главное меню пользователя"""
    buttons = [
        [InlineKeyboardButton(text="💦 Товары", callback_data="user_products")]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ Админка", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cities_keyboard(cities: list, page: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура с городами для пользователя"""
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
    
    # Навигация
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
    """Главное меню админа"""
    keyboard = [
        [InlineKeyboardButton(text="📍 Города", callback_data="admin_cities")],
        [InlineKeyboardButton(text="💦 Товары", callback_data="admin_products")],
        [InlineKeyboardButton(text="💳 Оплата", callback_data="admin_payment")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_cities_admin_keyboard(cities: list, page: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура с городами для админа"""
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
    
    # Навигация
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
    """Клавиатура с городами для админа (добавление товара)"""
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
    
    # Навигация
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
    """Клавиатура с количеством товара (4 в ряд)"""
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
    """Клавиатура с описаниями"""
    descriptions = ["🔪 příkóp", "🧲 ń@ ḿ@ğñíté", "🎁 t@ÿńík"]
    keyboard = []
    for desc in descriptions:
        keyboard.append([InlineKeyboardButton(text=desc, callback_data=f"admin_desc_{desc}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_payment_keyboard(card_number: str = None) -> InlineKeyboardMarkup:
    """Клавиатура для настроек оплаты"""
    from helpers import format_card_number
    formatted_card = format_card_number(card_number) if card_number else "Не указан"
    
    keyboard = [
        [InlineKeyboardButton(text=f"💳 Ваша карта: {formatted_card}", callback_data="noop")],
        [InlineKeyboardButton(text="✏️ Изменить карту", callback_data="admin_change_card")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ==================== ОБРАБОТЧИКИ ПОЛЬЗОВАТЕЛЯ ====================

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    user = message.from_user
    db.add_user(user.id, user.username, user.first_name, user.last_name)
    
    # ПРОВЕРКА: Если пользователь в списке ADMIN_IDS, назначаем админом
    if user.id in ADMIN_IDS:
        db.set_admin(user.id)
        logging.info(f"Admin {user.id} ({user.username}) authenticated")
    
    is_admin = db.is_admin(user.id)
    text = "⚡ Привет я современный помощник, воспользуйся меню ниже ⬇️"
    
    await message.answer(
        text,
        reply_markup=get_main_menu_keyboard(is_admin)
    )
    await state.clear()

@router.callback_query(F.data == "user_back_to_menu")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
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
    """Показать доступные города для товаров"""
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
    """Перелистывание городов"""
    page = int(callback.data.split("_")[-1])
    cities = db.get_cities()
    await callback.message.edit_reply_markup(
        reply_markup=get_cities_keyboard(cities, page)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("user_city_"))
async def show_city_products(callback: types.CallbackQuery, state: FSMContext):
    """Показать товары по городу"""
    city_id = int(callback.data.split("_")[-1])
    city = db.get_city_by_id(city_id)
    products = db.get_products_by_city(city_id)
    
    if not products:
        await callback.answer("❌ В этом городе нет товаров", show_alert=True)
        return
    
    # Сохраняем в состояние
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
    """Показать детали товара"""
    product_id = int(callback.data.split("_")[-1])
    product = db.get_product_by_id(product_id)
    
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    if not product['is_available']:
        await callback.answer("❌ Товар распродан", show_alert=True)
        return
    
    # Сохраняем в состояние
    await state.update_data(product_id=product_id)
    
    # Получаем номер карты
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

@router.callback_query(F.data.startswith("user_paid_"))
async def user_paid(callback: types.CallbackQuery, state: FSMContext):
    """Пользователь подтвердил оплату"""
    product_id = int(callback.data.split("_")[-1])
    product = db.get_product_by_id(product_id)
    
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    # Создаем заказ
    user_id = callback.from_user.id
    order_id = db.create_order(
        user_id,
        product_id,
        product['city_id'],
        product['product_key'],
        product['quantity'],
        product['price'],
        product['description']
    )
    
    if order_id:
        # Отправляем сообщение пользователю
        await callback.message.edit_text(
            "Спасибо за покупку, в течение 30 минут вы получите товар!"
        )
        
        # Отправляем уведомление админам
        for admin_id in ADMIN_IDS:
            try:
                text = f"✅ Продан Товар\n📍 Город - {product['product_key']} - {product['quantity']} - {product['price']}₽ - {product['description']}"
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📸 Отправить фото", callback_data=f"admin_send_photo_{order_id}")],
                    [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close_order")]
                ])
                
                await callback.bot.send_message(
                    admin_id,
                    text,
                    reply_markup=keyboard
                )
            except Exception as e:
                logging.error(f"Error sending admin notification: {e}")
        
        # Обновляем статус товара
        db.update_product_availability(product_id, False)
        
        await callback.answer("✅ Оплата подтверждена!")
    else:
        await callback.answer("❌ Ошибка при создании заказа", show_alert=True)
    
    await state.clear()

# ==================== ОБРАБОТЧИКИ АДМИНА ====================

@router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: types.CallbackQuery, state: FSMContext):
    """Показать панель администратора"""
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
    """Возврат в главное меню админа"""
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
    """Показать статистику"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return
    
    stats = db.get_statistics()
    text = f"""📊 Статистика

👥 Пользователи: {stats['total_users']}
🏙️ Города: {stats['total_cities']}
📦 Товары в наличии: {stats['total_products']}
🛒 Заказов всего: {stats['total_orders']}"""
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data == "admin_close_order")
async def admin_close_order(callback: types.CallbackQuery):
    """Закрыть уведомление о заказе"""
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data.startswith("admin_send_photo_"))
async def admin_send_photo_start(callback: types.CallbackQuery, state: FSMContext):
    """Начать отправку фото"""
    order_id = int(callback.data.split("_")[-1])
    await state.update_data(order_id=order_id)
    
    await callback.message.edit_text(
        "Отправьте фото:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel_photo")]
        ])
    )
    await callback.answer()
    await state.set_state(AdminStates.sending_photo)

@router.callback_query(F.data == "admin_cancel_photo")
async def admin_cancel_photo(callback: types.CallbackQuery, state: FSMContext):
    """Отмена отправки фото"""
    await callback.message.delete()
    await callback.answer("Отменено")
    await state.clear()

@router.message(AdminStates.sending_photo)
async def admin_send_photo(message: types.Message, state: FSMContext):
    """Отправка фото покупателю"""
    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото")
        return
    
    data = await state.get_data()
    order_id = data.get('order_id')
    
    if not order_id:
        await message.answer("❌ Ошибка: заказ не найден")
        await state.clear()
        return
    
    # Получаем информацию о заказе
    orders = db.get_pending_orders()
    order = None
    for o in orders:
        if o[0] == order_id:
            order = o
            break
    
    if not order:
        await message.answer("❌ Заказ не найден")
        await state.clear()
        return
    
    user_id = order[8]  # user_id в таблице orders
    
    # Отправляем фото покупателю
    try:
        await message.bot.send_photo(
            chat_id=user_id,
            photo=message.photo[-1].file_id
        )
        await message.answer("✅ Фото отправлено покупателю")
        
        # Обновляем статус заказа
        db.update_order_status(order_id, 'completed')
    except Exception as e:
        logging.error(f"Error sending photo: {e}")
        await message.answer("❌ Ошибка при отправке фото")
    
    await state.clear()

# ==================== ОБРАБОТЧИКИ ГОРОДОВ ====================

@router.callback_query(F.data == "admin_cities")
async def admin_cities(callback: types.CallbackQuery, state: FSMContext):
    """Показать города в админке"""
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
    """Перелистывание городов в админке"""
    page = int(callback.data.split("_")[-1])
    cities = db.get_cities()
    await callback.message.edit_reply_markup(
        reply_markup=get_cities_admin_keyboard(cities, page)
    )
    await callback.answer()

@router.callback_query(F.data == "admin_add_city")
async def admin_add_city_start(callback: types.CallbackQuery, state: FSMContext):
    """Начать добавление города"""
    await callback.message.edit_text("Введите название города или метро")
    await callback.answer()
    await state.set_state(CityStates.adding_city)

@router.message(CityStates.adding_city)
async def admin_add_city(message: types.Message, state: FSMContext):
    """Добавление города"""
    city_name = message.text.strip()
    
    if db.add_city(city_name):
        await message.answer(f"✅ Город {city_name} добавлен!")
    else:
        await message.answer(f"❌ Город {city_name} уже существует или ошибка добавления")
    
    # Показываем обновленный список городов
    cities = db.get_cities()
    await message.answer(
        "📍 Города",
        reply_markup=get_cities_admin_keyboard(cities, 0)
    )
    await state.clear()

@router.callback_query(F.data.startswith("admin_city_delete_"))
async def admin_delete_city(callback: types.CallbackQuery):
    """Удаление города"""
    city_id = int(callback.data.split("_")[-1])
    city = db.get_city_by_id(city_id)
    
    if not city:
        await callback.answer("❌ Город не найден", show_alert=True)
        return
    
    if db.delete_city(city_id):
        # Обновляем список городов
        cities = db.get_cities()
        await callback.message.edit_text(
            "📍 Города",
            reply_markup=get_cities_admin_keyboard(cities, 0)
        )
        await callback.answer(f"✅ Город {city['name']} удален")
    else:
        await callback.answer("❌ Ошибка при удалении города", show_alert=True)

# ==================== ОБРАБОТЧИКИ ТОВАРОВ ====================

@router.callback_query(F.data == "admin_products")
async def admin_products_start(callback: types.CallbackQuery, state: FSMContext):
    """Начать процесс добавления товара - выбрать город"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return
    
    cities = db.get_cities()
    if not cities:
        await callback.answer("❌ Сначала добавьте города", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💦 Товары\n📍 Выберите город для товара",
        reply_markup=get_cities_keyboard_admin(cities, 0)
    )
    await callback.answer()
    await state.set_state(ProductStates.selecting_city)

@router.callback_query(F.data.startswith("admin_product_cities_page_"))
async def admin_product_cities_page(callback: types.CallbackQuery):
    """Перелистывание городов"""
    page = int(callback.data.split("_")[-1])
    cities = db.get_cities()
    await callback.message.edit_reply_markup(
        reply_markup=get_cities_keyboard_admin(cities, page)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_product_city_"))
async def admin_product_select_city(callback: types.CallbackQuery, state: FSMContext):
    """Выбор города для товара"""
    city_id = int(callback.data.split("_")[-1])
    await state.update_data(city_id=city_id)
    
    # Читаем список товаров из файла
    products = read_product_list()
    product_names = list(products.keys())
    
    if not product_names:
        await callback.answer("❌ Нет доступных товаров в list.txt", show_alert=True)
        return
    
    # Сохраняем все товары в состояние
    await state.update_data(all_products=products, product_names=product_names)
    
    # Создаем клавиатуру с товарами (по 3 в ряд)
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
    """Выбор конкретного товара"""
    data = callback.data.split("_")
    city_id = int(data[3])
    product_name = "_".join(data[4:])  # На случай если в названии есть подчеркивания
    
    # Получаем количества из файла
    products = read_product_list()
    quantities = products.get(product_name, [])
    
    if not quantities:
        await callback.answer("❌ Нет доступного количества", show_alert=True)
        return
    
    await state.update_data(product_name=product_name, quantities=quantities, city_id=city_id)
    
    # Показываем количества
    keyboard = get_quantity_keyboard(quantities)
    
    await callback.message.edit_text(
        "💦 Выберите количество",
        reply_markup=keyboard
    )
    await callback.answer()
    await state.set_state(ProductStates.selecting_quantity)

@router.callback_query(F.data == "admin_product_back")
async def admin_product_back(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору товара"""
    data = await state.get_data()
    city_id = data.get('city_id')
    
    if city_id:
        # Показываем список товаров снова
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
            "💦 Товары\n📍 Выберите город для товара",
            reply_markup=get_cities_keyboard_admin(db.get_cities(), 0)
        )
    
    await callback.answer()
    await state.set_state(ProductStates.selecting_city)

@router.callback_query(F.data.startswith("admin_qty_"))
async def admin_select_quantity(callback: types.CallbackQuery, state: FSMContext):
    """Выбор количества"""
    quantity = callback.data.split("_")[-1]
    await state.update_data(quantity=quantity)
    
    await callback.message.edit_text(
        "Введите цену товара"
    )
    await callback.answer()
    await state.set_state(ProductStates.entering_price)

@router.message(ProductStates.entering_price)
async def admin_enter_price(message: types.Message, state: FSMContext):
    """Ввод цены товара"""
    price = message.text.strip()
    if not price.replace('.', '').isdigit():
        await message.answer("❌ Пожалуйста, введите корректную цену (цифры)")
        return
    
    await state.update_data(price=price)
    
    # Показываем выбор описания
    await message.answer(
        "🔧 Выберите Описание",
        reply_markup=get_description_keyboard()
    )
    await state.set_state(ProductStates.selecting_description)

@router.callback_query(F.data.startswith("admin_desc_"))
async def admin_select_description(callback: types.CallbackQuery, state: FSMContext):
    """Выбор описания"""
    description = callback.data.split("_", 2)[-1]
    await state.update_data(description=description)
    
    # Получаем все данные
    data = await state.get_data()
    city_id = data.get('city_id')
    product_name = data.get('product_name')
    quantity = data.get('quantity')
    price = data.get('price')
    
    # Добавляем товар в базу
    if db.add_product(city_id, product_name, quantity, price, description):
        # Получаем город для сообщения
        city = db.get_city_by_id(city_id)
        city_name = city['name'] if city else "Неизвестный город"
        
        await callback.message.edit_text(
            f"✅ Товар добавлен 📍 Город - {city_name} - {product_name} - {quantity} - {price}₽ - {description} добавлен!"
        )
        
        # Отправляем уведомление всем пользователям
        await notify_users_about_new_product(callback.bot, city_name, product_name, quantity, price, description)
        
    else:
        await callback.message.edit_text("❌ Ошибка при добавлении товара")
    
    await callback.answer()
    await state.clear()

async def notify_users_about_new_product(bot, city_name: str, product_name: str, quantity: str, price: str, description: str):
    """Отправка уведомления о новом товаре всем пользователям"""
    users = db.get_all_users()
    
    text = f"""✅ Новый товар 
📍 Город - {city_name} - {product_name} - {quantity} - {price}₽ - {description} - ✅ В наличии"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Перейти к товару", callback_data="user_products")]
    ])
    
    for user_id in users:
        try:
            await bot.send_message(
                user_id,
                text,
                reply_markup=keyboard
            )
            await asyncio.sleep(0.05)
        except Exception as e:
            logging.error(f"Error sending notification to {user_id}: {e}")

# ==================== ОБРАБОТЧИКИ ОПЛАТЫ ====================

@router.callback_query(F.data == "admin_payment")
async def admin_payment(callback: types.CallbackQuery, state: FSMContext):
    """Показать настройки оплаты"""
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
    """Начать изменение карты"""
    await callback.message.edit_text(
        "Введите номер карты в любом формате"
    )
    await callback.answer()
    await state.set_state(PaymentStates.changing_card)

@router.message(PaymentStates.changing_card)
async def admin_change_card(message: types.Message, state: FSMContext):
    """Изменение карты"""
    card_number = ''.join(filter(str.isdigit, message.text))
    
    if len(card_number) < 16:
        await message.answer("❌ Пожалуйста, введите корректный номер карты (минимум 16 цифр)")
        return
    
    if db.update_payment_card(card_number):
        await message.answer("✅ Номер карты обновлен!")
        
        # Показываем обновленные настройки
        card_number = db.get_payment_card()
        await message.answer(
            "💳 Оплата",
            reply_markup=get_payment_keyboard(card_number)
        )
    else:
        await message.answer("❌ Ошибка при обновлении номера карты")
    
    await state.clear()

# ==================== ОБЩИЙ ОБРАБОТЧИК ====================

@router.callback_query(lambda c: c.data == "noop")
async def noop_callback(callback):
    await callback.answer()