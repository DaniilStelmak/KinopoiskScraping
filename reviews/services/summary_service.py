from pathlib import Path

from openai import OpenAI

from config import (
    YANDEX_GPT_API_KEY,
    YANDEX_GPT_BASE_URL,
    YANDEX_GPT_MODEL_ID,
    YANDEX_GPT_TEMPERATURE,
)
from db import (
    get_film_by_id,
    get_film_reviews,
    get_film_summary,
    save_film_summary,
    update_generation_job,
    create_generation_job,
)
from services.review_service import ensure_reviews_for_film

SUMMARY_TYPE = "spoiler_free_review"
PROMPT_VERSION = "v1"


def load_system_prompt() -> str:
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "spoiler_free_review.txt"
    return prompt_path.read_text(encoding="utf-8").strip()


def build_reviews_prompt(film: dict, reviews: list[dict]) -> str:
    film_block = [
        f"Название фильма: {film.get('title') or '—'}",
        f"Оригинальное название: {film.get('original_title') or '—'}",
        f"Год: {film.get('year') or '—'}",
        f"Рейтинг: {film.get('rating') or '—'}",
        f"Жанры: {film.get('genres') or '—'}",
        f"Страна: {film.get('country') or '—'}",
        f"Длительность: {film.get('duration_minutes') or '—'} мин.",
    ]

    reviews_block = []
    for idx, review in enumerate(reviews[:10], start=1):
        reviews_block.append(
            "\n".join(
                [
                    f"Отзыв #{idx}",
                    f"Автор: {review.get('author_name') or '—'}",
                    f"Заголовок: {review.get('review_title') or '—'}",
                    f"Тип: {review.get('review_type') or '—'}",
                    f"Дата: {review.get('review_date_text') or '—'}",
                    f"Полезность: {review.get('helpful_yes', 0)} / {review.get('helpful_no', 0)}",
                    f"Текст:\n{review.get('review_text') or ''}",
                ]
            )
        )

    return (
        "Информация о фильме:\n"
        + "\n".join(film_block)
        + "\n\nОтзывы пользователей:\n\n"
        + "\n\n".join(reviews_block)
    )

def load_system_prompt() -> str:
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "spoiler_free_review.txt"
    prompt = prompt_path.read_text(encoding="utf-8").strip()

    if not prompt:
        raise ValueError(f"Файл промпта пустой: {prompt_path}")

    return prompt
def call_yandex_gpt(system_prompt: str, user_prompt: str) -> str:
    if not YANDEX_GPT_API_KEY:
        raise ValueError("Не задан YANDEX_GPT_API_KEY")
    if not YANDEX_GPT_MODEL_ID:
        raise ValueError("Не задан YANDEX_GPT_MODEL_ID")

    client = OpenAI(
        base_url=YANDEX_GPT_BASE_URL.rstrip("/"),
        api_key=YANDEX_GPT_API_KEY,
    )

    print("GPT BASE URL:", YANDEX_GPT_BASE_URL.rstrip("/"))
    print("GPT MODEL:", YANDEX_GPT_MODEL_ID)
    print("SYSTEM PROMPT EMPTY:", not bool(system_prompt.strip()))
    print("USER PROMPT EMPTY:", not bool(user_prompt.strip()))
    print("SYSTEM PROMPT LEN:", len(system_prompt))
    print("USER PROMPT LEN:", len(user_prompt))
    print("SYSTEM PROMPT PREVIEW:", repr(system_prompt[:200]))
    print("USER PROMPT PREVIEW:", repr(user_prompt[:500]))

    response = client.chat.completions.create(
        model=YANDEX_GPT_MODEL_ID,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=YANDEX_GPT_TEMPERATURE,
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Yandex GPT вернул пустой ответ")

    return content.strip()


async def get_or_create_spoiler_free_summary(film_id: int, chat_id: int) -> dict:
    cached = get_film_summary(film_id, SUMMARY_TYPE)
    if cached:
        return cached

    film = get_film_by_id(film_id)
    if not film:
        raise ValueError("Фильм не найден в базе")

    reviews = get_film_reviews(film_id)
    if len(reviews) < 10:
        reviews = await ensure_reviews_for_film(film_id=film_id, chat_id=chat_id)

    if not reviews:
        raise RuntimeError("Не удалось получить отзывы для summary")

    job = create_generation_job(film_id=film_id, status="generating")

    try:
        system_prompt = load_system_prompt()
        user_prompt = build_reviews_prompt(film, reviews[:10])
        summary_text = call_yandex_gpt(system_prompt, user_prompt)

        summary_row = save_film_summary(
            film_id=film_id,
            summary_type=SUMMARY_TYPE,
            summary_text=summary_text,
            model_name=YANDEX_GPT_MODEL_ID,
            prompt_version=PROMPT_VERSION,
            source_reviews_count=min(len(reviews), 10),
            is_spoiler_free=True,
        )

        update_generation_job(job["id"], "done")
        return summary_row

    except Exception as e:
        update_generation_job(job["id"], "failed", str(e))
        raise