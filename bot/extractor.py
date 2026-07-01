import os
import json
import time
import logging
from google import genai

logger = logging.getLogger(__name__)

def generate_with_fallback(client, contents):
    models = ['gemini-2.5-flash-lite', 'gemini-3.1-flash-lite', 'gemini-2.5-flash', 'gemini-2.0-flash']
    last_exception = None
    
    for model_name in models:
        max_retries = 2
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to generate content using model: {model_name} (attempt {attempt + 1})")
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                )
                logger.info(f"Successfully generated content using model: {model_name}")
                return response
            except Exception as e:
                last_exception = e
                err_str = str(e)
                logger.warning(f"Model {model_name} failed: {err_str}")
                
                # Check for transient Server Error (503) or Rate Limit (429) to decide if we retry or failover
                if ("503" in err_str or "429" in err_str) and attempt < max_retries - 1:
                    time.sleep(3)
                else:
                    break
                    
    # If we exhausted all models, raise the last encountered error
    raise last_exception

def extract_data_from_images(image_paths):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Получите бесплатный ключ на aistudio.google.com")
        
    client = genai.Client(api_key=api_key)
    
    prompt = """
    Извлеки данные из приложенных документов (паспорт и патент на работу РФ).
    Верни строго в формате JSON со следующими ключами (все значения строковые):
    - full_name (ФИО полностью на русском)
    - citizenship (гражданство)
    - birth_date (дата рождения в формате ДД.ММ.ГГГГ)
    - passport_series (серия паспорта, буквы/цифры до номера)
    - passport_number (номер паспорта)
    - passport_issue_date (дата выдачи паспорта)
    - passport_issued_by (кем выдан)
    - address (адрес регистрации/проживания, если есть. Если нет - пустая строка "")
    - patent_series (серия патента, обычно 2 цифры, например 30)
    - patent_number (номер патента, 10 цифр)
    - patent_issue_date (дата выдачи патента в формате ДД.ММ.ГГГГ)
    - patent_expiry_date (срок действия патента - дата окончания в формате ДД.ММ.ГГГГ)
    - profession (профессия/специальность в патенте, например Подсобный рабочий, Овощевод. Если нет - пиши Овощевод)
    
    Если чего-то нет на фото, пиши пустую строку. Никакого текста кроме валидного JSON!
    """
    
    uploaded_files = []
    for path in image_paths:
        f = client.files.upload(file=path)
        uploaded_files.append(f)
        
    # Step 1: Extract initial data using model fallback
    response = generate_with_fallback(client, [prompt] + uploaded_files)
    
    text = response.text
    import re
    match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
    if match:
        text = match.group(1)
        
    initial_data = json.loads(text)
    
    validator_prompt = f"""
    Ниже представлен JSON с предварительными данными, извлеченными из фото документов:
    {json.dumps(initial_data, ensure_ascii=False)}
    
    Твоя задача — выступить в роли строгого проверяющего (Аудитора).
    1. Сверь каждую букву и цифру в этом JSON с приложенными фото.
    2. Если есть ошибки распознавания (опечатки в фамилии, датах, номерах) — исправь их!
    3. Приведи ФИО к нормальному регистру (например: Кенжаев Бахром Хуррамович, а не КЕНЖАЕВ БАХРОМ).
    4. Приведи гражданство к нормальному виду (например: Узбекистан).
    
    Верни строго финальный, проверенный и исправленный JSON с теми же самыми ключами. Никакого лишнего текста!
    """
    
    # Step 2: Run Auditor verification using model fallback
    val_response = generate_with_fallback(client, [validator_prompt] + uploaded_files)

    val_text = val_response.text
    val_match = re.search(r'```json\n(.*?)\n```', val_text, re.DOTALL)
    if val_match:
        val_text = val_match.group(1)
        
    return json.loads(val_text)
