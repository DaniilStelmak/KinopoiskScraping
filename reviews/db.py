from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from config import (
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DB,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
)


@dataclass
class FilmData:
    kinopoisk_film_id: int
    title: str
    original_title: str | None = None
    year: int | None = None
    rating: float | None = None
    rating_count: int | None = None
    film_url: str | None = None
    reviews_url: str | None = None
    poster_url: str | None = None
    country: str | None = None
    genres: str | None = None
    duration_minutes: int | None = None
    description: str | None = None
    details_loaded: bool | None = None

@dataclass
class ReviewData:
    kinopoisk_review_id: int
    author_name: str | None
    review_title: str | None
    review_text: str
    review_type: str
    review_date_text: str | None = None
    helpful_yes: int = 0
    helpful_no: int = 0
    review_url: str | None = None
    position_in_top: int | None = None


def get_connection() -> psycopg.Connection:
    return psycopg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        row_factory=dict_row,
    )


def init_db() -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    schema_sql = schema_path.read_text(encoding="utf-8")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()


def get_film_by_kinopoisk_id(kinopoisk_film_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM films
                WHERE kinopoisk_film_id = %s
                """,
                (kinopoisk_film_id,),
            )
            return cur.fetchone()


def get_film_by_id(film_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM films
                WHERE id = %s
                """,
                (film_id,),
            )
            return cur.fetchone()


def upsert_film(film: FilmData) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO films (
                    kinopoisk_film_id,
                    title,
                    original_title,
                    year,
                    rating,
                    rating_count,
                    film_url,
                    reviews_url,
                    poster_url,
                    country,
                    genres,
                    duration_minutes,
                    description,
                    details_loaded,
                    details_updated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    CASE WHEN %s THEN NOW() ELSE NULL END
                )
                ON CONFLICT (kinopoisk_film_id)
                DO UPDATE SET
                    title = EXCLUDED.title,
                    original_title = EXCLUDED.original_title,
                    year = EXCLUDED.year,
                    rating = EXCLUDED.rating,
                    rating_count = EXCLUDED.rating_count,
                    film_url = EXCLUDED.film_url,
                    reviews_url = EXCLUDED.reviews_url,
                    poster_url = EXCLUDED.poster_url,
                    country = EXCLUDED.country,
                    genres = EXCLUDED.genres,
                    duration_minutes = EXCLUDED.duration_minutes,
                    description = EXCLUDED.description,
                    details_loaded = EXCLUDED.details_loaded,
                    details_updated_at = CASE
                        WHEN EXCLUDED.details_loaded THEN NOW()
                        ELSE films.details_updated_at
                    END,
                    updated_at = NOW()
                RETURNING *
                """,
                (
                    film.kinopoisk_film_id,
                    film.title,
                    film.original_title,
                    film.year,
                    film.rating,
                    film.rating_count,
                    film.film_url,
                    film.reviews_url,
                    film.poster_url,
                    film.country,
                    film.genres,
                    film.duration_minutes,
                    film.description,
                    film.details_loaded if film.details_loaded is not None else False,
                    film.details_loaded if film.details_loaded is not None else False,
                ),
            )
            row = cur.fetchone()
        conn.commit()
        return row


def create_or_get_search_query(query_text: str, normalized_query: str) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO search_cache (query_text, normalized_query)
                VALUES (%s, %s)
                ON CONFLICT (normalized_query)
                DO UPDATE SET
                    query_text = EXCLUDED.query_text,
                    updated_at = NOW()
                RETURNING *
                """,
                (query_text, normalized_query),
            )
            row = cur.fetchone()
        conn.commit()
        return row


def replace_search_results(search_cache_id: int, film_ids_in_order: list[int]) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM film_search_results
                WHERE search_cache_id = %s
                """,
                (search_cache_id,),
            )

            for position, film_id in enumerate(film_ids_in_order, start=1):
                cur.execute(
                    """
                    INSERT INTO film_search_results (search_cache_id, film_id, position)
                    VALUES (%s, %s, %s)
                    """,
                    (search_cache_id, film_id, position),
                )
        conn.commit()


def get_cached_search_results(normalized_query: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    f.*,
                    fsr.position,
                    sc.id AS search_cache_id,
                    sc.query_text,
                    sc.normalized_query
                FROM search_cache sc
                JOIN film_search_results fsr
                    ON fsr.search_cache_id = sc.id
                JOIN films f
                    ON f.id = fsr.film_id
                WHERE sc.normalized_query = %s
                ORDER BY fsr.position ASC
                """,
                (normalized_query,),
            )
            return cur.fetchall()


def replace_film_reviews(film_id: int, reviews: list[ReviewData]) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM film_reviews
                WHERE film_id = %s
                """,
                (film_id,),
            )

            for review in reviews:
                cur.execute(
                    """
                    INSERT INTO film_reviews (
                        film_id,
                        kinopoisk_review_id,
                        author_name,
                        review_title,
                        review_text,
                        review_type,
                        review_date_text,
                        helpful_yes,
                        helpful_no,
                        review_url,
                        position_in_top
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (kinopoisk_review_id)
                    DO UPDATE SET
                        film_id = EXCLUDED.film_id,
                        author_name = EXCLUDED.author_name,
                        review_title = EXCLUDED.review_title,
                        review_text = EXCLUDED.review_text,
                        review_type = EXCLUDED.review_type,
                        review_date_text = EXCLUDED.review_date_text,
                        helpful_yes = EXCLUDED.helpful_yes,
                        helpful_no = EXCLUDED.helpful_no,
                        review_url = EXCLUDED.review_url,
                        position_in_top = EXCLUDED.position_in_top,
                        updated_at = NOW()
                    """,
                    (
                        film_id,
                        review.kinopoisk_review_id,
                        review.author_name,
                        review.review_title,
                        review.review_text,
                        review.review_type,
                        review.review_date_text,
                        review.helpful_yes,
                        review.helpful_no,
                        review.review_url,
                        review.position_in_top,
                    ),
                )
        conn.commit()


def get_film_reviews(film_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM film_reviews
                WHERE film_id = %s
                ORDER BY position_in_top ASC NULLS LAST, helpful_yes DESC, id ASC
                """,
                (film_id,),
            )
            return cur.fetchall()


def save_film_summary(
    film_id: int,
    summary_type: str,
    summary_text: str,
    model_name: str | None = None,
    prompt_version: str | None = None,
    source_reviews_count: int = 0,
    is_spoiler_free: bool = True,
) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO film_summaries (
                    film_id,
                    summary_type,
                    model_name,
                    prompt_version,
                    source_reviews_count,
                    summary_text,
                    is_spoiler_free
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (film_id, summary_type)
                DO UPDATE SET
                    model_name = EXCLUDED.model_name,
                    prompt_version = EXCLUDED.prompt_version,
                    source_reviews_count = EXCLUDED.source_reviews_count,
                    summary_text = EXCLUDED.summary_text,
                    is_spoiler_free = EXCLUDED.is_spoiler_free,
                    updated_at = NOW()
                RETURNING *
                """,
                (
                    film_id,
                    summary_type,
                    model_name,
                    prompt_version,
                    source_reviews_count,
                    summary_text,
                    is_spoiler_free,
                ),
            )
            row = cur.fetchone()
        conn.commit()
        return row


def get_film_summary(film_id: int, summary_type: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM film_summaries
                WHERE film_id = %s AND summary_type = %s
                """,
                (film_id, summary_type),
            )
            return cur.fetchone()


def create_generation_job(film_id: int, status: str = "pending") -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO review_generation_jobs (film_id, status)
                VALUES (%s, %s)
                RETURNING *
                """,
                (film_id, status),
            )
            row = cur.fetchone()
        conn.commit()
        return row


def update_generation_job(job_id: int, status: str, error_message: str | None = None) -> dict[str, Any] | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE review_generation_jobs
                SET
                    status = %s,
                    error_message = %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING *
                """,
                (status, error_message, job_id),
            )
            row = cur.fetchone()
        conn.commit()
        return row


def get_latest_generation_job(film_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM review_generation_jobs
                WHERE film_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (film_id,),
            )
            return cur.fetchone()