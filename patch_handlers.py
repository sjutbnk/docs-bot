import re

with open('bot/handlers.py', 'r') as f:
    code = f.read()

# 1. Update DocumentFlow to include waiting_for_dms_issue_date
code = code.replace("    waiting_for_dms_date    = State()",
                    "    waiting_for_dms_issue_date = State()\n    waiting_for_dms_date    = State()")

# 2. Add ReplyKeyboard helper
keyboard_code = """
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def _get_cancel_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🔙 Назад")
    kb.button(text="❌ Отмена")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

@router.message(F.text == "❌ Отмена")
async def cancel_flow(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено. Загрузите файлы заново, чтобы начать новую генерацию.", reply_markup=types.ReplyKeyboardRemove())

@router.message(F.text == "🔙 Назад")
async def go_back(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    
    # Simple state transition dictionary
    back_transitions = {
        DocumentFlow.waiting_for_phone: DocumentFlow.waiting_for_inn,
        DocumentFlow.waiting_for_profession: DocumentFlow.waiting_for_phone,
        DocumentFlow.waiting_for_contract_date: DocumentFlow.waiting_for_profession,
        DocumentFlow.waiting_for_contract_end: DocumentFlow.waiting_for_contract_date,
        DocumentFlow.waiting_for_patent_date: DocumentFlow.waiting_for_contract_end,
        DocumentFlow.waiting_for_dms_number: DocumentFlow.waiting_for_patent_date,  # default fallback, might skip patent
        DocumentFlow.waiting_for_dms_issue_date: DocumentFlow.waiting_for_dms_number,
        DocumentFlow.waiting_for_dms_date: DocumentFlow.waiting_for_dms_issue_date,
    }
    
    # Handling conditional back from dms_number
    if current_state == DocumentFlow.waiting_for_dms_number.state:
        state_data = await state.get_data()
        ext_data = state_data.get("extracted_data") or {}
        citizen = str(ext_data.get("citizenship") or "").strip().lower()
        needs_patent = not any(k in citizen for k in ("беларус", "казах", "армен", "киргиз", "еаэс"))
        patent_issue_date = str(ext_data.get("patent_issue_date") or "").strip()
        if not needs_patent or patent_issue_date:
            await state.set_state(DocumentFlow.waiting_for_contract_end)
            await message.answer("🔙 Шаг назад. Введите дату окончания гражданско-правового договора (ДД.ММ.ГГГГ):", reply_markup=_get_cancel_kb())
            return
            
    prev_state = back_transitions.get(current_state)
    if not prev_state:
        await state.clear()
        await message.answer("🔙 Возврат невозможен. Загрузите файлы заново.", reply_markup=types.ReplyKeyboardRemove())
        return
        
    await state.set_state(prev_state)
    
    # Prompt user again based on prev_state
    prompts = {
        DocumentFlow.waiting_for_inn: "🔎 Введите ИНН (12 цифр) или `-`:",
        DocumentFlow.waiting_for_phone: "📱 Введите контактный телефон сотрудника (11 цифр):",
        DocumentFlow.waiting_for_profession: "💼 Введите профессию сотрудника или `-`:",
        DocumentFlow.waiting_for_contract_date: "📅 Введите дату заключения гражданско-правового договора (ДД.ММ.ГГГГ):",
        DocumentFlow.waiting_for_contract_end: "📅 Введите дату окончания гражданско-правового договора (ДД.ММ.ГГГГ):",
        DocumentFlow.waiting_for_patent_date: "📅 Введите дату выдачи патента сотрудника в формате ДД.ММ.ГГГГ:",
        DocumentFlow.waiting_for_dms_number: "📄 Введите номер полиса ДМС сотрудника или `-`:",
        DocumentFlow.waiting_for_dms_issue_date: "📅 Введите дату выдачи полиса ДМС в формате ДД.ММ.ГГГГ или `-`:",
    }
    await message.answer(f"🔙 Шаг назад. {prompts.get(prev_state, '')}", reply_markup=_get_cancel_kb())
"""

code = code.replace("user_extracted_data: dict[int, dict]      = {}", "")

# 3. Add ReplyMarkup to all manual prompts in handlers
code = code.replace('await message.answer("❌ ИНН должен состоять', 'await message.answer("❌ ИНН должен состоять') # No change for error
code = code.replace('await message.answer("📱 Введите контактный телефон сотрудника', 'await message.answer("📱 Введите контактный телефон сотрудника (11 цифр, например 89000000000):", reply_markup=_get_cancel_kb()')
# Fix if there are multiple replacements, use regex or replace exactly
code = code.replace('await reply_to.answer(\n            "🔎 ИНН сотрудника не обнаружен или некорректен.\\n"\n            "Введите ИНН (12 цифр) или `-` если отсутствует:"\n        )', 
                    'await reply_to.answer("🔎 ИНН сотрудника не обнаружен или некорректен.\\nВведите ИНН (12 цифр) или `-` если отсутствует:", reply_markup=_get_cancel_kb())')

code = code.replace('reply_to.answer("📱 Введите контактный телефон', 'reply_to.answer("📱 Введите контактный телефон сотрудника (11 цифр, например 89000000000):", reply_markup=_get_cancel_kb()')
code = code.replace('await message.answer(\n        f"💼 Введите профессию сотрудника', 'await message.answer(f"💼 Введите профессию сотрудника (по умолчанию: {sugg_prof}, введите `-` чтобы оставить по умолчанию):", reply_markup=_get_cancel_kb()')

code = code.replace('await message.answer("📅 Введите дату заключения', 'await message.answer("📅 Введите дату заключения гражданско-правового договора (ДД.ММ.ГГГГ):", reply_markup=_get_cancel_kb()')
code = code.replace('await message.answer("📅 Введите дату окончания', 'await message.answer("📅 Введите дату окончания гражданско-правового договора (ДД.ММ.ГГГГ):", reply_markup=_get_cancel_kb()')
code = code.replace('await message.answer("📅 Введите дату выдачи патента', 'await message.answer("📅 Введите дату выдачи патента сотрудника в формате ДД.ММ.ГГГГ:", reply_markup=_get_cancel_kb()')
code = code.replace('await message.answer("📄 Введите номер полиса ДМС', 'await message.answer("📄 Введите номер полиса ДМС сотрудника или `-` если отсутствует:", reply_markup=_get_cancel_kb()')

# 4. Add DMS issue date prompt
dms_number_handler = """@router.message(DocumentFlow.waiting_for_dms_number)
async def process_dms_number(message: types.Message, state: FSMContext):
    val = message.text.strip()
    await state.update_data(dms_number=val if val != "-" else "")
    await message.answer("📅 Введите дату выдачи полиса ДМС в формате ДД.ММ.ГГГГ или `-`:", reply_markup=_get_cancel_kb())
    await state.set_state(DocumentFlow.waiting_for_dms_issue_date)

@router.message(DocumentFlow.waiting_for_dms_issue_date)
async def process_dms_issue_date(message: types.Message, state: FSMContext):
    val = message.text.strip()
    if val != "-" and not _validate_date(val):
        await message.answer("❌ Формат: ДД.ММ.ГГГГ (например, 14.05.2026) или `-`:")
        return
    await state.update_data(dms_issue_date=val if val != "-" else "")
    await message.answer("📅 Введите дату окончания ДМС в формате ДД.ММ.ГГГГ или `-`:", reply_markup=_get_cancel_kb())
    await state.set_state(DocumentFlow.waiting_for_dms_date)"""

code = re.sub(r"@router\.message\(DocumentFlow\.waiting_for_dms_number\).*?await state\.set_state\(DocumentFlow\.waiting_for_dms_date\)", 
              dms_number_handler, code, flags=re.DOTALL)

# 5. Fix _show_generation_menu
menu_replace = """async def _show_generation_menu(message: types.Message, state: FSMContext):
    \"\"\"Merge all gathered FSM data back into extracted_data and show the menu.\"\"\"
    state_data = await state.get_data()
    extracted  = state_data.get("extracted_data", {})

    # Merge optional manually-entered fields
    for key in ("inn", "phone", "dms_number", "dms_issue_date", "dms_date", "profession", "contract_date", "contract_end_date"):
        if key in state_data:
            extracted[key] = state_data[key]

    await state.update_data(extracted_data=extracted)

    await message.answer(
        f"✅ Данные подготовлены:\\n"
        f"ФИО: {extracted.get('full_name') or '—'}\\n"
        f"Профессия: {extracted.get('profession') or 'Не указана'}\\n"
        f"ИНН: {extracted.get('inn') or 'Не указан'}\\n"
        f"Телефон: {extracted.get('phone') or 'Не указан'}\\n"
        f"Полис ДМС: {extracted.get('dms_number') or 'Не указан'} "
        f"(до {extracted.get('dms_date') or '—'})\\n\\n"
        f"Выберите документы для формирования:",
        reply_markup=_build_generation_menu(extracted.get('citizenship', '')),
    )
    
    # Send a small cleanup message to remove the ReplyKeyboard
    await message.answer("Для отмены или возврата к началу отправьте новые документы.", reply_markup=types.ReplyKeyboardRemove())"""

code = re.sub(r"async def _show_generation_menu.*?reply_markup=_build_generation_menu\(extracted\.get\('citizenship', ''\)\),\n    \)", 
              menu_replace, code, flags=re.DOTALL)

# 6. Fix cb_generate
cb_generate_replace = """@router.callback_query(F.data.startswith("gen_"))
async def cb_generate(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    state_data = await state.get_data()
    data = state_data.get("extracted_data")

    if not data:
        await callback.message.answer(
            "⚠️ Данные не найдены или устарели. Загрузите документы заново."
        )"""

code = re.sub(r"@router\.callback_query\(F\.data\.startswith\(\"gen_\"\)\)\nasync def cb_generate\(callback: types\.CallbackQuery\):\n    user_id = callback\.from_user\.id\n    data    = user_extracted_data\.get\(user_id\)\n\n    if not data:\n        await callback\.message\.answer\(\n            \"⚠️ Данные не найдены или устарели\. Загрузите документы заново\.\"\n        \)", 
              cb_generate_replace, code, flags=re.DOTALL)

# Insert the keyboard_code near the top
code = code.replace("# ---------------------------------------------------------------------------\n# /start", 
                    keyboard_code + "\n\n# ---------------------------------------------------------------------------\n# /start")

with open('bot/handlers.py', 'w') as f:
    f.write(code)
print("Patch applied to handlers.py successfully.")
