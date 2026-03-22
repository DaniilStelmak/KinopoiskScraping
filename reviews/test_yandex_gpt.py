from pathlib import Path
from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

API_KEY = os.getenv("YANDEX_GPT_API_KEY", "").strip()
FOLDER_ID = os.getenv("YANDEX_GPT_FOLDER_ID", "").strip()
MODEL_ID = os.getenv("YANDEX_GPT_MODEL_ID", "").strip()
print("MODEL_ID =", MODEL_ID)
if not API_KEY:
    raise ValueError("Не задан YANDEX_GPT_API_KEY")
if not FOLDER_ID:
    raise ValueError("Не задан YANDEX_GPT_FOLDER_ID")
if not MODEL_ID:
    raise ValueError("Не задан YANDEX_GPT_MODEL_ID")

MODEL_URI = f"gpt://{FOLDER_ID}/{MODEL_ID}/latest"

client = OpenAI(
    base_url="https://llm.api.cloud.yandex.net/v1",
    api_key=API_KEY,
)

print("BASE URL:", "https://llm.api.cloud.yandex.net/v1")
print("MODEL URI:", MODEL_URI)

response = client.chat.completions.create(
    model=MODEL_URI,
    messages=[
        {
            "role": "system",
            "content": "Ты полезный ассистент. Отвечай кратко и по-русски."
        },
        {
            "role": "user",
            "content": "Напиши одно короткое предложение о фильме Форсаж без спойлеров."
        },
    ],
    temperature=0.3,
)

print("\n=== RESPONSE ===\n")
print(response.choices[0].message.content)