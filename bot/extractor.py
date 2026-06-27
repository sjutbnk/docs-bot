import os
import json
from google import genai

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
    
    Если чего-то нет на фото, пиши пустую строку. Никакого текста кроме валидного JSON!
    """
    
    uploaded_files = []
    for path in image_paths:
        f = client.files.upload(file=path)
        uploaded_files.append(f)
        
    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[prompt] + uploaded_files,
            )
            break
        except Exception as e:
            if "503" in str(e) and attempt < max_retries - 1:
                time.sleep(5)
            else:
                raise e
    
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
    
    for attempt in range(max_retries):
        try:
            val_response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[validator_prompt] + uploaded_files,
            )
            break
        except Exception as e:
            if "503" in str(e) and attempt < max_retries - 1:
                time.sleep(5)
            else:
                raise e

    val_text = val_response.text
    val_match = re.search(r'```json\n(.*?)\n```', val_text, re.DOTALL)
    if val_match:
        val_text = val_match.group(1)
        
    return json.loads(val_text)
