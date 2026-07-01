import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.utils.keyboard import InlineKeyboardBuilder

from extractor import extract_data_from_images
from generator import generate_documents

# Простой загрузчик .env файлов
def load_env():
    possible_paths = [".env", "../.env", "bot/.env"]
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        os.environ[key.strip()] = val.strip().strip("'").strip('"')
            break

load_env()

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

user_files = {}
user_extracted_data = {}
user_last_msg = {}  # Хранит ID последнего сообщения с кнопкой обработки для каждого пользователя
user_locks = {}     # Блокировки для предотвращения race condition при быстрой загрузке нескольких файлов

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Система генерации кадровых документов.\n\n"
        "Пожалуйста, отправьте сканы или фотографии документов сотрудника (перевод паспорта и патент).\n"
        "После загрузки файлов нажмите кнопку под сообщением или вызовите команду /generate."
    )

@dp.message(lambda message: message.photo or message.document)
async def handle_files(message: types.Message):
    user_id = message.from_user.id
    
    # Инициализируем блокировку для пользователя, чтобы файлы обрабатывались строго по очереди
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()
        
    async with user_locks[user_id]:
        if user_id not in user_files:
            user_files[user_id] = []
            
        os.makedirs(f"downloads/{user_id}", exist_ok=True)
        
        bot = message.bot
        
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
        
        # Удаляем предыдущее сообщение со старым счетчиком и кнопкой
        if user_id in user_last_msg and user_last_msg[user_id]:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=user_last_msg[user_id])
            except Exception as e:
                logging.error(f"Не удалось удалить старое сообщение: {e}")
                
        # Создаем инлайн-кнопку запуска обработки
        builder = InlineKeyboardBuilder()
        builder.button(text="⚙️ Запустить обработку", callback_data="start_processing")
        
        sent_msg = await message.answer(
            f"✅ Документ успешно загружен. Всего файлов в очереди: {len(user_files[user_id])}.",
            reply_markup=builder.as_markup()
        )
        user_last_msg[user_id] = sent_msg.message_id

# Общая логика распознавания и подготовки
async def process_user_files(user_id: int, message_to_reply: types.Message):
    if user_id not in user_files or not user_files[user_id]:
        await message_to_reply.answer("Отсутствуют загруженные файлы. Сначала отправьте документы.")
        return
        
    await message_to_reply.answer("Запущен процесс распознавания и двойной ИИ-проверки данных (Аудитор). Ожидаемое время выполнения: 20-30 секунд.")
    
    try:
        data = extract_data_from_images(user_files[user_id])
        user_extracted_data[user_id] = data
        
        builder = InlineKeyboardBuilder()
        builder.button(text="Договор о приеме (DOCX)", callback_data="gen_contract")
        builder.button(text="Уведомление о приеме (DOCX)", callback_data="gen_conclusion")
        builder.button(text="Уведомление о расторжении (DOCX)", callback_data="gen_termination")
        builder.button(text="Сделать все 3 документа (DOCX)", callback_data="gen_all")
        builder.adjust(1)
        
        await message_to_reply.answer(
            f"✅ Распознавание завершено:\n"
            f"ФИО: {data.get('full_name')}\n"
            f"Гражданство: {data.get('citizenship')}\n\n"
            f"Выберите, какие документы необходимо сформировать:",
            reply_markup=builder.as_markup()
        )
        
        user_files[user_id] = []
        user_last_msg[user_id] = None
        
    except Exception as e:
        error_str = str(e).lower()
        if "429" in error_str or "exhausted" in error_str or "quota" in error_str:
            await message_to_reply.answer("❌ Превышен лимит запросов к нейросети (закончились токены). Пожалуйста, подождите немного и повторите попытку позднее.")
        elif "503" in error_str or "unavailable" in error_str:
            await message_to_reply.answer("❌ Серверы нейросети сейчас испытывают пиковую нагрузку. Я попытался пробиться несколько раз, но безуспешно. Подождите буквально минутку и нажмите кнопку обработки еще раз.")
        else:
            await message_to_reply.answer(f"❌ Произошла системная ошибка при обработке: {str(e)}")
        import traceback
        traceback.print_exc()

@dp.message(Command("generate"))
async def cmd_generate(message: types.Message):
    await process_user_files(message.from_user.id, message)

# Обработка нажатия на кнопку "Запустить обработку"
@dp.callback_query(F.data == "start_processing")
async def callback_start_processing(callback: types.CallbackQuery):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        await callback.message.edit_reply_markup(reply_markup=None)
        
    user_last_msg[callback.from_user.id] = None
    await process_user_files(callback.from_user.id, callback.message)

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
        docx_path, conclusion_path, termination_path = generate_documents(data, f"output/{user_id}")
        
        if callback.data == "gen_contract" or callback.data == "gen_all":
            await callback.message.answer_document(FSInputFile(docx_path))
        
        if callback.data == "gen_conclusion" or callback.data == "gen_all":
            await callback.message.answer_document(FSInputFile(conclusion_path))
            
        if callback.data == "gen_termination" or callback.data == "gen_all":
            await callback.message.answer_document(FSInputFile(termination_path))
            
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при генерации файлов: {str(e)}")
        import traceback
        traceback.print_exc()
        
    await callback.answer()

async def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("\n❌ ОШИБКА: Переменная BOT_TOKEN не задана!")
        print("Сделайте одно из двух:")
        print("1. Введите в терминале: export BOT_TOKEN=\"ваш_токен\"")
        print("2. Либо создайте файл .env в корне проекта и запишите туда: BOT_TOKEN=ваш_токен\n")
        return
        
    bot = Bot(token=token)
    
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
