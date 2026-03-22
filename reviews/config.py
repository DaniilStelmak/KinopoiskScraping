import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")


def get_env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"Не найдена переменная окружения: {name}")
    return value or ""


BOT_TOKEN = get_env("BOT_TOKEN", required=True)

POSTGRES_HOST = get_env("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(get_env("POSTGRES_PORT", "5432"))
POSTGRES_DB = get_env("POSTGRES_DB", required=True)
POSTGRES_USER = get_env("POSTGRES_USER", required=True)
POSTGRES_PASSWORD = get_env("POSTGRES_PASSWORD", required=True)

YANDEX_GPT_API_KEY = get_env("YANDEX_GPT_API_KEY", "")
YANDEX_GPT_FOLDER_ID = get_env("YANDEX_GPT_FOLDER_ID", "")
YANDEX_GPT_BASE_URL = get_env("YANDEX_GPT_BASE_URL", "https://llm.api.cloud.yandex.net/v1")
YANDEX_GPT_MODEL = get_env("YANDEX_GPT_MODEL", "")
YANDEX_GPT_MODEL_ID = get_env("YANDEX_GPT_MODEL_ID", "")
YANDEX_GPT_TEMPERATURE = float(get_env("YANDEX_GPT_TEMPERATURE", "0.4"))