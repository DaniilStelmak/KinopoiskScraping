import re
import requests
from bs4 import BeautifulSoup


def _clean_text(text: str | None) -> str | None:
    if not text:
        return None
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _to_int(value: str | None) -> int | None:
    if not value:
        return None
    digits = re.sub(r"[^\d]", "", value)
    return int(digits) if digits else None


def _to_float(value: str | None) -> float | None:
    if not value:
        return None
    value = value.replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", value)
    return float(match.group(0)) if match else None


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


def _is_captcha_page(soup: BeautifulSoup, html: str, url: str) -> bool:
    if "showcaptcha" in url.lower():
        return True

    title_text = soup.title.get_text(" ", strip=True).lower() if soup.title else ""
    page_text = soup.get_text(" ", strip=True).lower()

    markers = [
        "showcaptcha",
        "подтвердите, что запросы отправляли вы",
        "captcha",
        "я не робот",
    ]

    haystack = f"{title_text} {page_text} {html.lower()}"
    return any(marker in haystack for marker in markers)


def _find_year(soup: BeautifulSoup) -> int | None:
    selectors = [
        '[itemprop="dateCreated"]',
        'a[href*="/lists/movies/year--"]',
        'span[class*="styles_year"]',
    ]
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            text = _clean_text(node.get_text(" ", strip=True))
            if text:
                match = re.search(r"\b(19|20)\d{2}\b", text)
                if match:
                    return int(match.group(0))

    if soup.title:
        title_text = soup.title.get_text(" ", strip=True)
        match = re.search(r"\b(19|20)\d{2}\b", title_text)
        if match:
            return int(match.group(0))

    return None


def _find_title(soup: BeautifulSoup) -> str | None:
    selectors = [
        "h1",
        '[itemprop="name"]',
        'span[class*="styles_title"]',
    ]
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            text = _clean_text(node.get_text(" ", strip=True))
            if text and not _is_bad_value(text):
                return text
    return None


def _find_original_title(soup: BeautifulSoup) -> str | None:
    selectors = [
        '[itemprop="alternativeHeadline"]',
        'span[class*="styles_originalTitle"]',
    ]
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            text = _clean_text(node.get_text(" ", strip=True))
            if text and not _is_bad_value(text):
                return text
    return None


def _find_rating(soup: BeautifulSoup) -> float | None:
    selectors = [
        '[itemprop="ratingValue"]',
        'span[class*="film-rating-value"]',
        'span[class*="styles_rating"]',
    ]
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            value = _to_float(node.get_text(" ", strip=True))
            if value is not None:
                return value
    return None


def _find_rating_count(soup: BeautifulSoup) -> int | None:
    selectors = [
        '[itemprop="ratingCount"]',
        'span[class*="styles_countBlock"]',
    ]
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            value = _to_int(node.get_text(" ", strip=True))
            if value is not None:
                return value
    return None


def _find_description(soup: BeautifulSoup) -> str | None:
    selectors = [
        '[itemprop="description"]',
        'div[data-tid="movie-synopsis"]',
        'div[class*="styles_synopsis"]',
        'div[class*="styles_filmSynopsis"]',
        'div[class*="styles_description"]',
        'div[class*="styles_outline"]',
    ]

    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            text = _clean_text(node.get_text(" ", strip=True))
            if text and not _is_bad_value(text):
                return text

    # fallback: ищем короткий осмысленный абзац рядом с блоками описания
    for node in soup.find_all(["div", "p", "span"]):
        text = _clean_text(node.get_text(" ", strip=True))
        if not text:
            continue
        if _is_bad_value(text):
            continue
        if len(text) < 80:
            continue
        if len(text) > 3000:
            continue

        lowered = text.lower()
        bad_snippets = [
            "войти",
            "регистрация",
            "реклама",
            "оценить фильм",
            "напишите отзыв",
            "смотреть онлайн",
        ]
        if any(snippet in lowered for snippet in bad_snippets):
            continue

        return text

    return None


def _normalize_image_url(url: str | None) -> str | None:
    if not url:
        return None

    url = url.strip()

    if url.startswith("//"):
        return "https:" + url

    if url.startswith("/"):
        return "https://www.kinopoisk.ru" + url

    return url


def _find_poster_url(soup: BeautifulSoup) -> str | None:
    selectors = [
        'img[class*="film-poster"]',
        'img[class*="styles_rootInLight"]',
        'img[itemprop="image"]',
        'img[class*="styles_posterImage"]',
    ]

    for selector in selectors:
        node = soup.select_one(selector)
        if not node:
            continue

        # сначала пробуем src
        src = _normalize_image_url(node.get("src"))
        if src and ("avatars.mds.yandex.net" in src or "kinopoisk" in src):
            return src

        # потом data-src
        data_src = _normalize_image_url(node.get("data-src"))
        if data_src and ("avatars.mds.yandex.net" in data_src or "kinopoisk" in data_src):
            return data_src

    return None


def _find_meta_info(soup: BeautifulSoup) -> dict:
    result = {
        "country": None,
        "genres": None,
        "duration_minutes": None,
    }

    genre_nodes = soup.select('[itemprop="genre"], a[href*="/lists/movies/genre--"]')
    genres = []
    for node in genre_nodes:
        text = _clean_text(node.get_text(" ", strip=True))
        if text and not _is_bad_value(text) and text.lower() not in {g.lower() for g in genres}:
            genres.append(text)
    if genres:
        result["genres"] = ", ".join(genres)

    all_text = soup.get_text("\n", strip=True)

    dur_match = re.search(r"(\d+)\s*мин", all_text, re.IGNORECASE)
    if dur_match:
        result["duration_minutes"] = int(dur_match.group(1))

    country_candidates = []
    for node in soup.select('a[href*="/lists/movies/country--"]'):
        text = _clean_text(node.get_text(" ", strip=True))
        if text and not _is_bad_value(text):
            country_candidates.append(text)
    if country_candidates:
        result["country"] = ", ".join(dict.fromkeys(country_candidates))

    return result


def parse_kinopoisk_film(film_url: str) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        "Referer": "https://www.kinopoisk.ru/",
    }

    response = requests.get(film_url, headers=headers, timeout=20)
    response.raise_for_status()
    response.encoding = "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")

    if _is_captcha_page(soup, response.text, response.url):
        raise RuntimeError("Кинопоиск вернул капчу вместо страницы фильма")

    title = _find_title(soup)
    original_title = _find_original_title(soup)
    year = _find_year(soup)
    rating = _find_rating(soup)
    rating_count = _find_rating_count(soup)
    description = _find_description(soup)
    poster_url = _find_poster_url(soup)
    meta = _find_meta_info(soup)

    return {
        "title": title,
        "original_title": original_title,
        "year": year,
        "rating": rating,
        "rating_count": rating_count,
        "description": description,
        "poster_url": poster_url,
        "country": meta["country"],
        "genres": meta["genres"],
        "duration_minutes": meta["duration_minutes"],
        "film_url": film_url,
        "reviews_url": film_url.rstrip("/") + "/reviews/?ord=rating",
    }