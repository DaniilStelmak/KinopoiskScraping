from db import (
    FilmData,
    create_or_get_search_query,
    get_cached_search_results,
    replace_search_results,
    upsert_film,
)
from parsers.kinopoisk_search import search_kinopoisk
from utils.text import normalize_query


def get_search_results(query: str, force_refresh: bool = False) -> list[dict]:
    normalized_query = normalize_query(query)

    if not force_refresh:
        cached_results = get_cached_search_results(normalized_query)
        if cached_results:
            return cached_results

    parsed_results = search_kinopoisk(query)
    if not parsed_results:
        return []

    search_row = create_or_get_search_query(
        query_text=query,
        normalized_query=normalized_query,
    )

    saved_film_ids = []

    for item in parsed_results:
        film_row = upsert_film(
            FilmData(
                kinopoisk_film_id=item["kinopoisk_film_id"],
                title=item["title"],
                original_title=item.get("original_title"),
                year=item.get("year"),
                rating=item.get("rating"),
                film_url=item.get("film_url"),
                reviews_url=item.get("reviews_url"),
                poster_url=item.get("poster_url"),
            )
        )
        saved_film_ids.append(film_row["id"])

    replace_search_results(
        search_cache_id=search_row["id"],
        film_ids_in_order=saved_film_ids,
    )

    return get_cached_search_results(normalized_query)