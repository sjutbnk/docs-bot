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

# ---------------------------------------------------------------------------
# FSM states
# ---------------------------------------------------------------------------

class DocumentFlow(StatesGroup):
    waiting_for_inn        = State()
    waiting_for_phone      = State()
    waiting_for_dms_number = State()
    waiting_for_dms_date   = State()


# ---------------------------------------------------------------------------
# Per-user in-memory storage
# ---------------------------------------------------------------------------

user_files:          dict[int, list[str]] = {}
user_extracted_data: dict[int, dict]      = {}
user_last_msg:       dict[int, int | None] = {}
user_locks:          dict[int, asyncio.Lock] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_inn(value: str) -> bool:
    return bool(re.fullmatch(r"\d{12}", value))

def _validate_date(value: str) -> bool:
    return bool(re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", value))


def _build_generation_menu(citizenship: str = ""):
    builder = InlineKeyboardBuilder()
    
    citizen = citizenship.strip().lower()
    if "узбек" in citizen:
        cit_str = "от узбека"
    elif "таджик" in citizen:
        cit_str = "от таджика"
    elif citizen:
        cit_str = f"от гражданина {citizenship}"
    else:
        cit_str = "от иностранца"

    builder.button(text="Договор о приеме (DOCX)",           callback_data="gen_contract")
    builder.button(text="Уведомление о приеме (DOCX)",       callback_data="gen_conclusion")
    builder.button(text="Уведомление о расторжении (DOCX)",  callback_data="gen_termination")
    builder.button(text=f"Уведомление о приеме ({cit_str}) (DOCX)", callback_data="gen_patent_notif")
    builder.button(text="Сделать все 4 документа",           callback_data="gen_all")
    builder.adjust(1)
    return builder.as_markup()

async def _show_generation_menu(message: types.Message, state: FSMContext):
    """Merge all gathered FSM data back into extracted_data and show the menu."""
    state_data = await state.get_data()
    extracted  = state_data.get("extracted_data", {})

    # Merge optional manually-entered fields
    for key in ("inn", "phone", "dms_number", "dms_date"):
        if key in state_data:
            extracted[key] = state_data[key]

    user_id = message.from_user.id
    user_extracted_data[user_id] = extracted
    await state.clear()

    await message.answer(
        f"✅ Данные подготовлены:\n"
        f"ФИО: {extracted.get('full_name') or '—'}\n"
        f"ИНН: {extracted.get('inn') or 'Не указан'}\n"
        f"Телефон: {extracted.get('phone') or 'Не указан'}\n"
        f"Полис ДМС: {extracted.get('dms_number') or 'Не указан'} "
        f"(до {extracted.get('dms_date') or '—'})\n\n"
        f"Выберите документы для формирования:",
        reply_markup=_build_generation_menu(extracted.get('citizenship', '')),
    )


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Система генерации кадровых документов.\n\n"
        "Отправьте сканы / фото документов сотрудника:\n"
        "• перевод паспорта\n• патент\n• карта партнёра (необязательно)\n\n"
        "После загрузки нажмите кнопку «⚙️ Запустить обработку»."
    )


# ---------------------------------------------------------------------------
# File upload handler
# ---------------------------------------------------------------------------

@router.message(F.photo | F.document)
async def handle_files(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()

    async with user_locks[user_id]:
        user_files.setdefault(user_id, [])

        user_dir = os.path.join(config.DOWNLOADS_DIR, str(user_id))
        os.makedirs(user_dir, exist_ok=True)

        bot = message.bot

        if message.photo:
            file_id = message.photo[-1].file_id
            file    = await bot.get_file(file_id)
            ext     = "jpg"
        else:
            file_id = message.document.file_id
            file    = await bot.get_file(file_id)
            ext     = (message.document.file_name or "file.bin").rsplit(".", 1)[-1]

        file_path = os.path.join(user_dir, f"{file_id}.{ext}")
        await bot.download_file(file.file_path, file_path)
        user_files[user_id].append(file_path)

        # Clear any in-progress FSM session so stale state doesn't leak
        await state.clear()

        # Remove the previous "ready" button message
        prev_msg_id = user_last_msg.get(user_id)
        if prev_msg_id:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_msg_id)
            except Exception:
                pass

        builder = InlineKeyboardBuilder()
        builder.button(text="⚙️ Запустить обработку", callback_data="start_processing")

        sent = await message.answer(
            f"✅ Загружено: {len(user_files[user_id])} файл(ов). Нажмите кнопку, когда все файлы отправлены.",
            reply_markup=builder.as_markup(),
        )
        user_last_msg[user_id] = sent.message_id


# ---------------------------------------------------------------------------
# Core OCR + FSM flow
# ---------------------------------------------------------------------------

async def _process_user_files(user_id: int, reply_to: types.Message, state: FSMContext):
    files = user_files.get(user_id)
    if not files:
        await reply_to.answer("⚠️ Файлы не найдены. Сначала отправьте документы.")
        return

    await reply_to.answer(
        "⏳ Запускаю распознавание и двойную ИИ-проверку данных (Аудитор). "
        "Обычно занимает 20–60 секунд (при нагрузке на серверы — до 2 минут)…"
    )

    try:
        data = extractor.extract_data_from_images(files)
    except Exception as e:
        err = str(e)
        if "429" in err or "quota" in err.lower() or "exhausted" in err.lower():
            msg = "❌ Лимит запросов к нейросети исчерпан. Попробуйте снова через несколько минут."
        elif "503" in err or "unavailable" in err.lower() or "overloaded" in err.lower():
            msg = "❌ Серверы нейросети перегружены (бот уже пытался повторить несколько раз). Попробуйте снова через 2–3 минуты."
        else:
            msg = f"❌ Ошибка при обработке: {err}"
        await reply_to.answer(msg)
        config.logger.error("extract_data_from_images failed", exc_info=True)
        await state.clear()
        return
    finally:
        # Always clear files and last-message pointer after attempt
        user_files[user_id] = []
        user_last_msg[user_id] = None

    await state.update_data(extracted_data=data)

    # Check INN — prompt manually if missing or invalid
    inn = str(data.get("inn") or "").strip()
    if not _validate_inn(inn):
        await reply_to.answer(
            "🔎 ИНН сотрудника не обнаружен или некорректен.\n"
            "Введите ИНН (12 цифр) или `-` если отсутствует:"
        )
        await state.set_state(DocumentFlow.waiting_for_inn)
    else:
        await state.update_data(inn=inn)
        await reply_to.answer("📱 Введите контактный телефон сотрудника (11 цифр, например 89000000000):")
        await state.set_state(DocumentFlow.waiting_for_phone)


# ---------------------------------------------------------------------------
# FSM handlers
# ---------------------------------------------------------------------------

@router.message(DocumentFlow.waiting_for_inn)
async def process_inn(message: types.Message, state: FSMContext):
    val = message.text.strip()
    if val != "-" and not _validate_inn(val):
        await message.answer("❌ ИНН должен состоять ровно из 12 цифр. Попробуйте ещё раз или введите `-`:")
        return
    await state.update_data(inn=val if val != "-" else "")
    await message.answer("📱 Введите контактный телефон сотрудника (11 цифр, например 89000000000):")
    await state.set_state(DocumentFlow.waiting_for_phone)


@router.message(DocumentFlow.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    digits = "".join(c for c in message.text if c.isdigit())
    if not (10 <= len(digits) <= 15):
        await message.answer("❌ Некорректный номер телефона. Введите, например: 89000000000")
        return
    await state.update_data(phone=digits)
    await message.answer("📄 Введите номер полиса ДМС сотрудника или `-` если отсутствует:")
    await state.set_state(DocumentFlow.waiting_for_dms_number)


@router.message(DocumentFlow.waiting_for_dms_number)
async def process_dms_number(message: types.Message, state: FSMContext):
    val = message.text.strip()
    await state.update_data(dms_number=val if val != "-" else "")
    await message.answer(
        "📅 Введите дату окончания ДМС в формате ДД.ММ.ГГГГ или `-` если отсутствует:"
    )
    await state.set_state(DocumentFlow.waiting_for_dms_date)


@router.message(DocumentFlow.waiting_for_dms_date)
async def process_dms_date(message: types.Message, state: FSMContext):
    val = message.text.strip()
    if val != "-" and not _validate_date(val):
        await message.answer("❌ Формат: ДД.ММ.ГГГГ (например, 14.05.2027) или `-`:")
        return
    await state.update_data(dms_date=val if val != "-" else "")
    await _show_generation_menu(message, state)


# ---------------------------------------------------------------------------
# /generate command
# ---------------------------------------------------------------------------

@router.message(Command("generate"))
async def cmd_generate(message: types.Message, state: FSMContext):
    await _process_user_files(message.from_user.id, message, state)


# ---------------------------------------------------------------------------
# Inline keyboard callbacks
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "start_processing")
async def cb_start_processing(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
    user_last_msg[callback.from_user.id] = None
    await _process_user_files(callback.from_user.id, callback.message, state)


@router.callback_query(F.data.startswith("gen_"))
async def cb_generate(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data    = user_extracted_data.get(user_id)

    if not data:
        await callback.message.answer(
            "⚠️ Данные не найдены или устарели. Загрузите документы заново."
        )
        await callback.answer()
        return

    await callback.message.answer("📝 Формирую документы…")

    try:
        out_dir = os.path.join(config.OUTPUT_DIR, str(user_id))
        os.makedirs(out_dir, exist_ok=True)

        action = callback.data
        contract_path, conclusion_path, termination_path, patent_path = \
            generator.generate_documents(data, out_dir)

        if action in ("gen_contract", "gen_all"):
            await callback.message.answer_document(FSInputFile(contract_path))
        if action in ("gen_conclusion", "gen_all"):
            await callback.message.answer_document(FSInputFile(conclusion_path))
        if action in ("gen_termination", "gen_all"):
            await callback.message.answer_document(FSInputFile(termination_path))
        if action in ("gen_patent_notif", "gen_all"):
            await callback.message.answer_document(FSInputFile(patent_path))

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при генерации: {e}")
        config.logger.error("cb_generate failed", exc_info=True)

    await callback.answer()
