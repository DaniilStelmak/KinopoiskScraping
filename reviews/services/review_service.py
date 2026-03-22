import asyncio

from db import (
    ReviewData,
    create_generation_job,
    get_film_by_id,
    get_film_reviews,
    replace_film_reviews,
    update_generation_job,
)
from parsers.browser import create_driver
from parsers.kinopoisk_reviews import (
    is_captcha_page,
    normalize_reviews_url,
    parse_reviews_from_html,
)

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = create_driver()
    return _driver


def shutdown_driver():
    global _driver
    if _driver is not None:
        try:
            _driver.quit()
        finally:
            _driver = None


async def wait_for_manual_confirmation(chat_id: int) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        input,
        f"\n[chat_id={chat_id}] Пройди капчу в браузере сервера, дождись открытия страницы отзывов и только потом нажми Enter...\n",
    )

async def ensure_reviews_for_film(film_id: int, chat_id: int) -> list[dict]:
    existing_reviews = get_film_reviews(film_id)
    if len(existing_reviews) >= 10:
        return existing_reviews

    film = get_film_by_id(film_id)
    if not film:
        raise ValueError("Фильм не найден в базе")

    reviews_url = film.get("reviews_url") or film.get("film_url")
    if not reviews_url:
        raise ValueError("У фильма нет ссылки на отзывы")

    reviews_url = normalize_reviews_url(reviews_url)

    job = create_generation_job(film_id=film_id, status="pending")
    driver = get_driver()

    try:
        update_generation_job(job["id"], "parsing")
        driver.get(reviews_url)

        html = driver.page_source
        current_url = driver.current_url

        if is_captcha_page(html, current_url):
            update_generation_job(job["id"], "captcha_wait")
            print(f"[film_id={film_id}] Поймали капчу. Ожидаем ручное подтверждение.")

            max_attempts = 5

            for attempt in range(1, max_attempts + 1):
                print(f"[film_id={film_id}] Попытка подтверждения {attempt}/{max_attempts}")
                await wait_for_manual_confirmation(chat_id)

                html = driver.page_source
                current_url = driver.current_url

                if not is_captcha_page(html, current_url):
                    print(f"[film_id={film_id}] Капча пройдена, продолжаю парсинг.")
                    update_generation_job(job["id"], "parsing")
                    break

                print(f"[film_id={film_id}] Страница отзывов еще не открылась.")
            else:
                update_generation_job(job["id"], "failed", "Капча не пройдена")
                raise RuntimeError("Капча не пройдена или страница отзывов не открылась")

        parsed_reviews = parse_reviews_from_html(html)
        if not parsed_reviews:
            update_generation_job(job["id"], "failed", "Отзывы не найдены")
            raise RuntimeError("Отзывы не найдены на странице")

        review_objects = [
            ReviewData(
                kinopoisk_review_id=item["kinopoisk_review_id"],
                author_name=item.get("author_name"),
                review_title=item.get("review_title"),
                review_text=item["review_text"],
                review_type=item["review_type"],
                review_date_text=item.get("review_date_text"),
                helpful_yes=item.get("helpful_yes", 0),
                helpful_no=item.get("helpful_no", 0),
                review_url=item.get("review_url"),
                position_in_top=item.get("position_in_top"),
            )
            for item in parsed_reviews
        ]

        replace_film_reviews(film_id, review_objects)
        update_generation_job(job["id"], "done")

        return get_film_reviews(film_id)

    except Exception as e:
        update_generation_job(job["id"], "failed", str(e))
        raise