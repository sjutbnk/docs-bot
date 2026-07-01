import os
import sys
from dotenv import load_dotenv

# Add bot to sys.path
sys.path.append(os.path.abspath('bot'))

from extractor import extract_data_from_images

load_dotenv()

pdf_paths = [
    'bot/downloads/1555793414/BQACAgIAAxkBAAMRaj7lsGU2unOT1-wgR4ktTXk_cqkAAhmaAAIeS_lJbuWsxO0otEo8BA.pdf',
    'bot/downloads/1555793414/BQACAgIAAxkBAAMSaj7lsNWqM2jWyKE1eLn1W2vkTy4AAhqaAAIeS_lJOe_SLL0VPCc8BA.pdf'
]

print("Running extraction...")
try:
    data = extract_data_from_images(pdf_paths)
    import json
    print("\n=== Extracted JSON ===")
    print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print("Error during extraction:", e)
