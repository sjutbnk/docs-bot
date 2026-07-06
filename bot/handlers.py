import os
import asyncio
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
import extractor
import generator

router = Router()

user_files = {}
user_extracted_data = {}
user_last_msg = {}
user_locks = {}

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Система генерации кадровых документов.\n\n"
        "Пожалуйста, отправьте сканы или фотографии документов сотрудника (перевод паспорта и патент).\n"
        "После загрузки файлов нажмите кнопку под сообщением или вызовите команду /generate."
    )

@router.message(lambda message: message.photo or message.document)
async def handle_files(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()
        
    async with user_locks[user_id]:
        if user_id not in user_files:
            user_files[user_id] = []
            
        user_downloads_dir = os.path.join(config.DOWNLOADS_DIR, str(user_id))
        os.makedirs(user_downloads_dir, exist_ok=True)
        
        bot = message.bot
        
        if message.photo:
            file_id = message.photo[-1].file_id
            file = await bot.get_file(file_id)
            ext = "jpg"
        elif message.document:
            file_id = message.document.file_id
            file = await bot.get_file(file_id)
            ext = message.document.file_name.split('.')[-1]
        
        file_path = os.path.join(user_downloads_dir, f"{file_id}.{ext}")
        await bot.download_file(file.file_path, file_path)
        
        user_files[user_id].append(file_path)
        
        # Remove old menu notification
        if user_id in user_last_msg and user_last_msg[user_id]:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=user_last_msg[user_id])
            except Exception as e:
                config.logger.error(f"Failed to delete old message: {e}")
                
        # Generate inline keyboard to start OCR processing
        builder = InlineKeyboardBuilder()
        builder.button(text="⚙️ Запустить обработку", callback_data="start_processing")
        
        sent_msg = await message.answer(
            f"✅ Документ успешно загружен. Всего файлов в очереди: {len(user_files[user_id])}.",
            reply_markup=builder.as_markup()
        )
        user_last_msg[user_id] = sent_msg.message_id

async def process_user_files(user_id: int, message_to_reply: types.Message):
    if user_id not in user_files or not user_files[user_id]:
        await message_to_reply.answer("Отсутствуют загруженные файлы. Сначала отправьте документы.")
        return
        
    await message_to_reply.answer("Запущен процесс распознавания и двойной ИИ-проверки данных (Аудитор). Ожидаемое время выполнения: 20-30 секунд.")
    
    try:
        data = extractor.extract_data_from_images(user_files[user_id])
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
        config.logger.error("Error during process_user_files execution", exc_info=True)

@router.message(Command("generate"))
async def cmd_generate(message: types.Message):
    await process_user_files(message.from_user.id, message)

@router.callback_query(F.data == "start_processing")
async def callback_start_processing(callback: types.CallbackQuery):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        await callback.message.edit_reply_markup(reply_markup=None)
        
    user_last_msg[callback.from_user.id] = None
    await process_user_files(callback.from_user.id, callback.message)

@router.callback_query(F.data.startswith("gen_"))
async def callbacks_generate(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = user_extracted_data.get(user_id)
    
    if not data:
        await callback.message.answer("Данные для генерации устарели или не найдены. Пожалуйста, загрузите документы заново.")
        await callback.answer()
        return
        
    await callback.message.answer("Формирование запрошенных документов...")
    
    try:
        user_output_dir = os.path.join(config.OUTPUT_DIR, str(user_id))
        os.makedirs(user_output_dir, exist_ok=True)
        
        docx_path, conclusion_path, termination_path = generator.generate_documents(data, user_output_dir)
        
        if callback.data == "gen_contract" or callback.data == "gen_all":
            await callback.message.answer_document(FSInputFile(docx_path))
        
        if callback.data == "gen_conclusion" or callback.data == "gen_all":
            await callback.message.answer_document(FSInputFile(conclusion_path))
            
        if callback.data == "gen_termination" or callback.data == "gen_all":
            await callback.message.answer_document(FSInputFile(termination_path))
            
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при генерации файлов: {str(e)}")
        config.logger.error("Error during callbacks_generate execution", exc_info=True)
        
    await callback.answer()
