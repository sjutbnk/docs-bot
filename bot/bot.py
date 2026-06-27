import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.utils.keyboard import InlineKeyboardBuilder

from extractor import extract_data_from_images
from generator import generate_documents

BOT_TOKEN = os.environ.get("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_files = {}
user_extracted_data = {}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Система генерации кадровых документов.\n\n"
        "Пожалуйста, отправьте сканы или фотографии документов сотрудника (перевод паспорта и патент).\n"
        "После загрузки необходимых файлов вызовите команду /generate."
    )

@dp.message(lambda message: message.photo or message.document)
async def handle_files(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_files:
        user_files[user_id] = []
        
    os.makedirs(f"downloads/{user_id}", exist_ok=True)
    
    if message.photo:
        file_id = message.photo[-1].file_id
        file = await bot.get_file(file_id)
        ext = "jpg"
    elif message.document:
        file_id = message.document.file_id
        file = await bot.get_file(file_id)
        ext = message.document.file_name.split('.')[-1]
    
    file_path = f"downloads/{user_id}/{file_id}.{ext}"
    await bot.download_file(file.file_path, file_path)
    
    user_files[user_id].append(file_path)
    await message.answer(f"✅ Документ успешно загружен. Всего файлов в очереди: {len(user_files[user_id])}.\nИспользуйте /generate для начала обработки.")

@dp.message(Command("generate"))
async def cmd_generate(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_files or not user_files[user_id]:
        await message.answer("Отсутствуют загруженные файлы. Сначала отправьте документы.")
        return
        
    await message.answer("Запущен процесс распознавания и двойной ИИ-проверки данных (Аудитор). Ожидаемое время выполнения: 20-30 секунд.")
    
    try:
        data = extract_data_from_images(user_files[user_id])
        user_extracted_data[user_id] = data
        
        builder = InlineKeyboardBuilder()
        builder.button(text="Договор о приеме", callback_data="gen_contract")
        builder.button(text="Уведомление о расторжении", callback_data="gen_termination")
        builder.button(text="Сделать оба документа", callback_data="gen_both")
        builder.adjust(1)
        
        await message.answer(
            f"✅ Распознавание завершено:\n"
            f"ФИО: {data.get('full_name')}\n"
            f"Гражданство: {data.get('citizenship')}\n\n"
            f"Выберите, какие документы необходимо сформировать:",
            reply_markup=builder.as_markup()
        )
        
        user_files[user_id] = []
        
    except Exception as e:
        error_str = str(e).lower()
        if "429" in error_str or "exhausted" in error_str or "quota" in error_str:
            await message.answer("❌ Превышен лимит запросов к нейросети (закончились токены). Пожалуйста, подождите немного и повторите попытку позднее.")
        elif "503" in error_str or "unavailable" in error_str:
            await message.answer("❌ Серверы нейросети сейчас испытывают пиковую нагрузку. Я попытался пробиться несколько раз, но безуспешно. Подождите буквально минутку и нажмите /generate еще раз.")
        else:
            await message.answer(f"❌ Произошла системная ошибка при обработке: {str(e)}")
        import traceback
        traceback.print_exc()

@dp.callback_query(F.data.startswith("gen_"))
async def callbacks_generate(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = user_extracted_data.get(user_id)
    
    if not data:
        await callback.message.answer("Данные для генерации устарели или не найдены. Пожалуйста, загрузите документы заново.")
        await callback.answer()
        return
        
    await callback.message.answer("Формирование запрошенных документов...")
    
    try:
        os.makedirs(f"output/{user_id}", exist_ok=True)
        docx_path, rtf_path = generate_documents(data, f"output/{user_id}")
        
        if callback.data == "gen_contract" or callback.data == "gen_both":
            await callback.message.answer_document(FSInputFile(docx_path))
        
        if callback.data == "gen_termination" or callback.data == "gen_both":
            await callback.message.answer_document(FSInputFile(rtf_path))
            
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при генерации файлов: {str(e)}")
        
    await callback.answer()

async def main():
    if not BOT_TOKEN:
        print("ERROR: Please set BOT_TOKEN environment variable.")
        return
        
    # Установка меню команд
    commands = [
        BotCommand(command="start", description="Перезапустить бота / Инструкция"),
        BotCommand(command="generate", description="Сгенерировать документы из файлов"),
    ]
    await bot.set_my_commands(commands)
    
    print("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
