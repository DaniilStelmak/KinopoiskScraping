import asyncio
import traceback

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from config import BOT_TOKEN
from db import init_db
from keyboards import films_keyboard, film_card_keyboard
from services.search_service import get_search_results
from services.film_service import get_film_card
from services.review_service import ensure_reviews_for_film, shutdown_driver
from services.summary_service import get_or_create_spoiler_free_summary

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def build_film_card_text(film: dict) -> str:
    parts = [f"<b>{film['title']}</b>"]

    subtitle_parts = []
    if film.get("original_title"):
        subtitle_parts.append(film["original_title"])
    if film.get("year"):
        subtitle_parts.append(str(film["year"]))
    if subtitle_parts:
        parts.append(" / ".join(subtitle_parts))

    if film.get("rating") is not None:
        rating_line = f"Рейтинг: {film['rating']}"
        if film.get("rating_count"):
            rating_line += f" ({film['rating_count']} оценок)"
        parts.append(rating_line)

    if film.get("country"):
        parts.append(f"Страна: {film['country']}")

    if film.get("genres"):
        parts.append(f"Жанры: {film['genres']}")

    if film.get("duration_minutes"):
        parts.append(f"Длительность: {film['duration_minutes']} мин.")

    if film.get("description"):
        parts.append("")
        parts.append(film["description"])

    if film.get("film_url"):
        parts.append("")
        parts.append(f"Ссылка: {film['film_url']}")

    return "\n".join(parts)


@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "Привет.\n"
        "Напиши название фильма, и я найду варианты на Кинопоиске."
    )


@dp.message(F.text)
async def search_handler(message: Message):
    query = message.text.strip()
    if not query:
        await message.answer("Введи название фильма.")
        return

    await message.answer("Ищу фильмы...")

    try:
        films = get_search_results(query)
    except Exception as e:
        print("ERROR search_handler:")
        traceback.print_exc()
        await message.answer("Не удалось выполнить поиск. Попробуйте позже.")
        return

    if not films:
        await message.answer("Ничего не найдено.")
        return

    await message.answer(
        "Выбери фильм:",
        reply_markup=films_keyboard(films),
    )

@dp.callback_query(F.data.startswith("film:"))
async def film_card_handler(callback: CallbackQuery):
    await callback.answer()

    film_id = int(callback.data.split(":", 1)[1])

    try:
        film = get_film_card(film_id)
    except Exception:
        print("ERROR film_card_handler:")
        traceback.print_exc()
        await callback.message.answer("Не удалось загрузить данные фильма. Попробуйте позже.")
        return

    if not film:
        await callback.message.answer("Фильм не найден в базе.")
        return

    text = build_film_card_text(film)
    poster_url = film.get("poster_url")

    if poster_url:
        try:
            await callback.message.answer_photo(
                photo=poster_url,
                caption=text,
                reply_markup=film_card_keyboard(film_id),
                parse_mode="HTML",
            )
        except Exception:
            await callback.message.answer(
                text,
                reply_markup=film_card_keyboard(film_id),
                parse_mode="HTML",
            )
    else:
        await callback.message.answer(
            text,
            reply_markup=film_card_keyboard(film_id),
            parse_mode="HTML",
        )

@dp.callback_query(F.data.startswith("summary:"))
async def summary_handler(callback: CallbackQuery):
    film_id = int(callback.data.split(":", 1)[1])

    await callback.answer()

    await callback.message.answer(
        "Готовлю рецензию без спойлеров.\n"
        "Если отзывов еще нет в кэше, сначала соберу их. Это может занять время."
    )

    try:
        summary = await get_or_create_spoiler_free_summary(
            film_id=film_id,
            chat_id=callback.message.chat.id,
        )
    except Exception:
        print("ERROR summary_handler:")
        traceback.print_exc()
        await callback.message.answer(
            "Не удалось подготовить рецензию без спойлеров. Попробуйте позже."
        )
        return

    await callback.message.answer(summary["summary_text"])

async def main():
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен вручную.")
    finally:
        shutdown_driver()