from db import FilmData, get_film_by_id, upsert_film
from parsers.kinopoisk_film import parse_kinopoisk_film


def _is_bad_value(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.lower()
    markers = [
        "подтвердите, что запросы отправляли вы",
        "captcha",
        "showcaptcha",
        "я не робот",
    ]
    return any(marker in lowered for marker in markers)


def _pick_better(new_value, old_value):
    if new_value is None:
        return old_value
    if isinstance(new_value, str):
        if not new_value.strip():
            return old_value
        if _is_bad_value(new_value):
            return old_value
    return new_value


def _needs_refresh(film: dict) -> bool:
    important_fields = [
        "description",
        "genres",
        "country",
        "duration_minutes",
        "poster_url",
    ]
    return any(not film.get(field) for field in important_fields)


def refresh_film_details(film_id: int) -> dict | None:
    film = get_film_by_id(film_id)
    if not film:
        return None

    film_url = film.get("film_url")
    if not film_url:
        return film

    parsed = parse_kinopoisk_film(film_url)

    updated_film = upsert_film(
        FilmData(
            kinopoisk_film_id=film["kinopoisk_film_id"],
            title=_pick_better(parsed.get("title"), film.get("title")),
            original_title=_pick_better(parsed.get("original_title"), film.get("original_title")),
            year=_pick_better(parsed.get("year"), film.get("year")),
            rating=_pick_better(parsed.get("rating"), film.get("rating")),
            rating_count=_pick_better(parsed.get("rating_count"), film.get("rating_count")),
            film_url=film["film_url"],
            reviews_url=_pick_better(parsed.get("reviews_url"), film.get("reviews_url")),
            poster_url=_pick_better(parsed.get("poster_url"), film.get("poster_url")),
            country=_pick_better(parsed.get("country"), film.get("country")),
            genres=_pick_better(parsed.get("genres"), film.get("genres")),
            duration_minutes=_pick_better(parsed.get("duration_minutes"), film.get("duration_minutes")),
            description=_pick_better(parsed.get("description"), film.get("description")),
        )
    )
    return updated_film


def get_film_card(film_id: int, force_refresh: bool = False) -> dict | None:
    film = get_film_by_id(film_id)
    if not film:
        return None

    if not (force_refresh or _needs_refresh(film)):
        return film

    try:
        refreshed = refresh_film_details(film_id)
        return refreshed or film
    except RuntimeError as e:
        print(f"[film_id={film_id}] Не удалось обновить карточку фильма: {e}")
        return film
    except Exception as e:
        print(f"[film_id={film_id}] Ошибка обновления карточки фильма: {e}")
        return film