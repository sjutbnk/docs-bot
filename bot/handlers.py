import os
import asyncio
import re
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

import config
import extractor
import generator

router = Router()

# State definitions for gathering additional employee details
class DocumentFlow(StatesGroup):
    waiting_for_inn = State()
    waiting_for_phone = State()
    waiting_for_dms_number = State()
    waiting_for_dms_date = State()

user_files = {}
user_extracted_data = {}
user_last_msg = {}
user_locks = {}

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Система генерации кадровых документов.\n\n"
        "Пожалуйста, отправьте сканы или фотографии документов сотрудника (перевод паспорта и патент).\n"
        "После загрузки файлов нажмите кнопку под сообщением или вызовите команду /generate."
    )

@router.message(F.photo | F.document)
async def handle_files(message: types.Message, state: FSMContext):
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
        
        # Clear FSM state on new document upload just in case
        await state.clear()
        
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

async def process_user_files(user_id: int, message_to_reply: types.Message, state: FSMContext):
    if user_id not in user_files or not user_files[user_id]:
        await message_to_reply.answer("Отсутствуют загруженные файлы. Сначала отправьте документы.")
        return
        
    await message_to_reply.answer("Запущен процесс распознавания и двойной ИИ-проверки данных (Аудитор). Ожидаемое время выполнения: 20-30 секунд.")
    
    try:
        # 1. OCR Extraction using model fallbacks
        data = extractor.extract_data_from_images(user_files[user_id])
        
        # Save OCR data inside the FSM context
        await state.update_data(extracted_data=data)
        
        user_files[user_id] = []
        user_last_msg[user_id] = None
        
        # Check if INN was extracted (must be a valid 12-digit number)
        extracted_inn = str(data.get('inn', '')).strip()
        
        if not extracted_inn or not re.match(r'^\d{12}$', extracted_inn):
            await message_to_reply.answer(
                "🔎 ИНН сотрудника не обнаружен на фотографиях.\n"
                "Пожалуйста, введите ИНН сотрудника (12 цифр) или отправьте `-`, если ИНН отсутствует:"
            )
            await state.set_state(DocumentFlow.waiting_for_inn)
        else:
            await state.update_data(inn=extracted_inn)
            await message_to_reply.answer(
                "📱 Введите контактный телефон сотрудника (11 цифр, например 89608626599):"
            )
            await state.set_state(DocumentFlow.waiting_for_phone)
        
    except Exception as e:
        error_str = str(e).lower()
        if "429" in error_str or "exhausted" in error_str or "quota" in error_str:
            await message_to_reply.answer("❌ Превышен лимит запросов к нейросети (закончились токены). Пожалуйста, подождите немного и повторите попытку позднее.")
        elif "503" in error_str or "unavailable" in error_str:
            await message_to_reply.answer("❌ Серверы нейросети сейчас испытывают пиковую нагрузку. Я попытался пробиться несколько раз, но безуспешно. Подождите буквально минутку и нажмите кнопку обработки еще раз.")
        else:
            await message_to_reply.answer(f"❌ Произошла системная ошибка при обработке: {str(e)}")
        config.logger.error("Error during process_user_files execution", exc_info=True)
        await state.clear()

# Message FSM transitions
@router.message(DocumentFlow.waiting_for_inn)
async def process_inn(message: types.Message, state: FSMContext):
    val = message.text.strip()
    if val != '-':
        if not val.isdigit() or len(val) != 12:
            await message.answer("❌ Некорректный формат. ИНН должен состоять ровно из 12 цифр. Попробуйте еще раз или введите `-`:")
            return
            
    await state.update_data(inn=val if val != '-' else "")
    await message.answer("📱 Введите контактный телефон сотрудника (11 цифр, например 89608626599):")
    await state.set_state(DocumentFlow.waiting_for_phone)

@router.message(DocumentFlow.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    val = message.text.strip()
    clean_val = "".join([c for c in val if c.isdigit()])
    if len(clean_val) < 10 or len(clean_val) > 15:
        await message.answer("❌ Некорректный формат телефона. Введите номер телефона (например, 89608626599):")
        return
        
    await state.update_data(phone=clean_val)
    await message.answer("📄 Введите номер полиса ДМС сотрудника (или `-` если отсутствует):")
    await state.set_state(DocumentFlow.waiting_for_dms_number)

@router.message(DocumentFlow.waiting_for_dms_number)
async def process_dms_number(message: types.Message, state: FSMContext):
    val = message.text.strip()
    await state.update_data(dms_number=val if val != '-' else "")
    await message.answer("📅 Введите дату окончания действия полиса ДМС в формате ДД.ММ.ГГГГ (или `-` если отсутствует):")
    await state.set_state(DocumentFlow.waiting_for_dms_date)

@router.message(DocumentFlow.waiting_for_dms_date)
async def process_dms_date(message: types.Message, state: FSMContext):
    val = message.text.strip()
    if val != '-':
        if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', val):
            await message.answer("❌ Некорректный формат даты. Введите в формате ДД.ММ.ГГГГ (например, 14.05.2027) или `-`:")
            return
            
    await state.update_data(dms_date=val if val != '-' else "")
    
    # Collate all user-provided and OCR-extracted details
    state_data = await state.get_data()
    extracted = state_data.get('extracted_data', {})
    
    extracted['inn'] = state_data.get('inn', '')
    extracted['phone'] = state_data.get('phone', '')
    extracted['dms_number'] = state_data.get('dms_number', '')
    extracted['dms_date'] = state_data.get('dms_date', '')
    
    user_id = message.from_user.id
    user_extracted_data[user_id] = extracted
    
    # Clear FSM State
    await state.clear()
    
    # Present output menu
    builder = InlineKeyboardBuilder()
    builder.button(text="Договор о приеме (DOCX)", callback_data="gen_contract")
    builder.button(text="Уведомление о приеме (DOCX)", callback_data="gen_conclusion")
    builder.button(text="Уведомление о расторжении (DOCX)", callback_data="gen_termination")
    builder.button(text="Сделать все 3 документа (DOCX)", callback_data="gen_all")
    builder.adjust(1)
    
    await message.answer(
        f"✅ Все данные подготовлены:\n"
        f"ФИО: {extracted.get('full_name')}\n"
        f"ИНН: {extracted.get('inn') or 'Не указан'}\n"
        f"Телефон: {extracted.get('phone') or 'Не указан'}\n"
        f"Полис ДМС: {extracted.get('dms_number') or 'Не указан'} (до {extracted.get('dms_date') or '-'})\n\n"
        f"Выберите, какие документы необходимо сформировать:",
        reply_markup=builder.as_markup()
    )

@router.message(Command("generate"))
async def cmd_generate(message: types.Message, state: FSMContext):
    await process_user_files(message.from_user.id, message, state)

@router.callback_query(F.data == "start_processing")
async def callback_start_processing(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        await callback.message.edit_reply_markup(reply_markup=None)
        
    user_last_msg[callback.from_user.id] = None
    await process_user_files(callback.from_user.id, callback.message, state)

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
