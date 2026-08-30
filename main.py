import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import BOT_TOKEN
from handlers import router
from proxy_manager import proxy_manager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Создаем бота и диспетчер
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher()

# Регистрируем роутер
dp.include_router(router)

async def main():
    """Основная функция запуска бота"""
    # Загружаем прокси
    proxy_manager.load_proxies()
    
    # Запускаем бота
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Error starting bot: {e}")
    finally:
        # Закрываем соединение с базой данных
        from database import db
        db.close()

if __name__ == "__main__":
    asyncio.run(main())