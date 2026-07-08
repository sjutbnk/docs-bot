import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage

import config
from handlers import router

async def main():
    if not config.BOT_TOKEN:
        print("\n❌ ОШИБКА: Переменная BOT_TOKEN не задана!")
        print("Сделайте одно из двух:")
        print("1. Введите в терминале: export BOT_TOKEN=\"ваш_токен\"")
        print("2. Либо создайте файл .env в корне проекта и запишите туда: BOT_TOKEN=ваш_токен\n")
        return
        
    bot = Bot(token=config.BOT_TOKEN)
    
    # Initialize dispatcher with MemoryStorage for FSM state tracking
    dp = Dispatcher(storage=MemoryStorage())
    
    # Register router containing all handlers
    dp.include_router(router)
    
    # Set bot commands menu
    commands = [
        BotCommand(command="start", description="Перезапустить бота / Инструкция"),
        BotCommand(command="generate", description="Сгенерировать документы из файлов"),
    ]
    await bot.set_my_commands(commands)
    
    config.logger.info("Starting bot polling loop...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        config.logger.info("Bot stopped.")
