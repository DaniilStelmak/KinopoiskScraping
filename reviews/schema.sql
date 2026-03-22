CREATE TABLE IF NOT EXISTS films (
    id BIGSERIAL PRIMARY KEY,
    kinopoisk_film_id BIGINT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    original_title TEXT,
    year INTEGER,
    rating NUMERIC(3,1),
    rating_count INTEGER,
    film_url TEXT NOT NULL UNIQUE,
    reviews_url TEXT,
    poster_url TEXT,
    country TEXT,
    genres TEXT,
    duration_minutes INTEGER,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS film_reviews (
    id BIGSERIAL PRIMARY KEY,
    film_id BIGINT NOT NULL REFERENCES films(id) ON DELETE CASCADE,
    kinopoisk_review_id BIGINT NOT NULL UNIQUE,
    author_name TEXT,
    review_title TEXT,
    review_text TEXT NOT NULL,
    review_type TEXT NOT NULL CHECK (review_type IN ('positive', 'negative', 'neutral')),
    review_date_text TEXT,
    helpful_yes INTEGER NOT NULL DEFAULT 0,
    helpful_no INTEGER NOT NULL DEFAULT 0,
    review_url TEXT UNIQUE,
    position_in_top INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_film_review_position UNIQUE (film_id, position_in_top)
);

CREATE TABLE IF NOT EXISTS film_summaries (
    id BIGSERIAL PRIMARY KEY,
    film_id BIGINT NOT NULL REFERENCES films(id) ON DELETE CASCADE,
    summary_type TEXT NOT NULL,
    model_name TEXT,
    prompt_version TEXT,
    source_reviews_count INTEGER NOT NULL DEFAULT 0,
    summary_text TEXT NOT NULL,
    is_spoiler_free BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_film_summary UNIQUE (film_id, summary_type)
);

CREATE TABLE IF NOT EXISTS search_cache (
    id BIGSERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    normalized_query TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS film_search_results (
    id BIGSERIAL PRIMARY KEY,
    search_cache_id BIGINT NOT NULL REFERENCES search_cache(id) ON DELETE CASCADE,
    film_id BIGINT NOT NULL REFERENCES films(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_search_result UNIQUE (search_cache_id, film_id),
    CONSTRAINT uq_search_position UNIQUE (search_cache_id, position)
);

CREATE TABLE IF NOT EXISTS review_generation_jobs (
    id BIGSERIAL PRIMARY KEY,
    film_id BIGINT NOT NULL REFERENCES films(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('pending', 'captcha_wait', 'parsing', 'generating', 'done', 'failed')),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_films_title ON films(title);
CREATE INDEX IF NOT EXISTS idx_films_year ON films(year);
CREATE INDEX IF NOT EXISTS idx_films_rating ON films(rating);

CREATE INDEX IF NOT EXISTS idx_film_reviews_film_id ON film_reviews(film_id);
CREATE INDEX IF NOT EXISTS idx_film_reviews_position_in_top ON film_reviews(position_in_top);

CREATE INDEX IF NOT EXISTS idx_search_cache_normalized_query ON search_cache(normalized_query);
CREATE INDEX IF NOT EXISTS idx_film_search_results_search_cache_id ON film_search_results(search_cache_id);
CREATE INDEX IF NOT EXISTS idx_film_search_results_film_id ON film_search_results(film_id);

CREATE INDEX IF NOT EXISTS idx_review_generation_jobs_film_id ON review_generation_jobs(film_id);
CREATE INDEX IF NOT EXISTS idx_review_generation_jobs_status ON review_generation_jobs(status);