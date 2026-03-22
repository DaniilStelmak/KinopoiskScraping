import re
import requests
from bs4 import BeautifulSoup


def extract_film_id_from_url(url: str) -> int | None:
    match = re.search(r"/film/(\d+)/", url)
    if not match:
        return None
    return int(match.group(1))


def normalize_film_url(href: str) -> str:
    href = re.sub(r"/sr/\d+/?$", "/", href)
    if not href.startswith("http"):
        href = "https://www.kinopoisk.ru" + href
    return href


def build_reviews_url(film_url: str) -> str:
    if not film_url.endswith("/"):
        film_url += "/"
    return film_url + "reviews/?ord=rating"


def search_kinopoisk(query: str) -> list[dict]:
    url = "https://www.kinopoisk.ru/index.php"
    params = {"kp_query": query}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        "Referer": "https://www.kinopoisk.ru/",
    }

    response = requests.get(url, params=params, headers=headers, timeout=20)
    response.raise_for_status()
    response.encoding = "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for item in soup.select("div.search_results div.element"):
        a_tag = item.select_one("p.name a")
        if not a_tag:
            continue

        href = a_tag.get("href", "").strip()
        if not href.startswith("/film/"):
            continue

        title = a_tag.get_text(" ", strip=True).replace("\xa0", " ")

        year_tag = item.select_one("p.name span.year")
        year_text = year_tag.get_text(strip=True) if year_tag else ""
        year = int(year_text) if year_text.isdigit() else None

        film_url = normalize_film_url(href)
        reviews_url = build_reviews_url(film_url)
        kinopoisk_film_id = extract_film_id_from_url(film_url)
        if not kinopoisk_film_id:
            continue

        rating_tag = item.select_one("div.rating")
        rating = None
        if rating_tag:
            raw_rating = rating_tag.get_text(strip=True).replace(",", ".")
            try:
                rating = float(raw_rating)
            except ValueError:
                rating = None

        poster_tag = item.select_one("p.pic img")
        print(poster_tag)
        poster_src = None
        if poster_tag:
            raw_src = (poster_tag.get("src") or "").strip()
            if raw_src:
                if raw_src.startswith("/"):
                    poster_src = "https://www.kinopoisk.ru" + raw_src
                elif raw_src.startswith("//"):
                    poster_src = "https:" + raw_src
                else:
                    poster_src = raw_src
        print(poster_src)
        subtitle_blocks = item.select("span.gray")
        original_title = None
        if subtitle_blocks:
            raw = subtitle_blocks[0].get_text(" ", strip=True).replace("\xa0", " ")
            original_title = raw.split(",")[0].strip() if raw else None

        results.append({
            "kinopoisk_film_id": kinopoisk_film_id,
            "title": title,
            "original_title": original_title,
            "year": year,
            "rating": rating,
            "film_url": film_url,
            "reviews_url": reviews_url,
            "poster_url": None,
        })

    unique_results = []
    seen = set()
    for item in results:
        key = item["kinopoisk_film_id"]
        if key in seen:
            continue
        seen.add(key)
        unique_results.append(item)

    return unique_results