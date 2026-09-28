import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage

import config
from handlers import router

async def main():
    try:
        config.validate_runtime_secrets()
    except RuntimeError as exc:
        config.logger.error("Invalid runtime configuration: %s", exc)
        return
        
    bot = Bot(token=config.BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    await bot.set_my_commands([
        BotCommand(command="start",    description="Перезапустить бота / Инструкция"),
        BotCommand(command="generate", description="Сгенерировать документы из файлов"),
    ])

    config.logger.info("Bot started.")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        config.logger.info("Bot session closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        config.logger.info("Bot stopped.")
