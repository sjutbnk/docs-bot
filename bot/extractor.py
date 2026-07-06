import json
import time
from google import genai

import config
import prompts

def generate_with_fallback(client, contents):
    """
    Helper function to generate content with fallback mechanisms across multiple Gemini models
    to handle 503 Service Unavailable and 429 Rate Limit/Quota errors gracefully.
    """
    models = ['gemini-2.5-flash-lite', 'gemini-3.1-flash-lite', 'gemini-2.5-flash', 'gemini-2.0-flash']
    last_exception = None
    
    for model_name in models:
        max_retries = 2
        for attempt in range(max_retries):
            try:
                config.logger.info(f"Attempting to generate content using model: {model_name} (attempt {attempt + 1})")
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                )
                config.logger.info(f"Successfully generated content using model: {model_name}")
                return response
            except Exception as e:
                last_exception = e
                err_str = str(e)
                config.logger.warning(f"Model {model_name} failed: {err_str}")
                
                # Check for transient Server Error (503) or Rate Limit (429) to decide if we retry or failover
                if ("503" in err_str or "429" in err_str) and attempt < max_retries - 1:
                    time.sleep(3)
                else:
                    break
                    
    # If all failovers failed, raise the last exception
    raise last_exception

def extract_data_from_images(image_paths):
    """
    Extracts, structures and validates employee details from passport and work patent scans.
    Uses direct OCR extraction combined with an Auditor validation phase.
    """
    if not config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set. Получите бесплатный ключ на aistudio.google.com")
        
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    
    # Upload all document files
    uploaded_files = []
    for path in image_paths:
        f = client.files.upload(file=path)
        uploaded_files.append(f)
        
    # Phase 1: Direct OCR Extraction
    response = generate_with_fallback(client, [prompts.EXTRACTION_PROMPT] + uploaded_files)
    
    text = response.text
    import re
    match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
    if match:
        text = match.group(1)
        
    initial_data = json.loads(text)
    
    # Phase 2: Auditor validation and data sanitization
    validator_prompt = prompts.get_validator_prompt(initial_data)
    val_response = generate_with_fallback(client, [validator_prompt] + uploaded_files)

    val_text = val_response.text
    val_match = re.search(r'```json\n(.*?)\n```', val_text, re.DOTALL)
    if val_match:
        val_text = val_match.group(1)
        
    return json.loads(val_text)
