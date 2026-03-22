import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def normalize_reviews_url(url: str) -> str:
    url = url.strip()

    if "/reviews" in url:
        if "ord=rating" in url:
            return url
        if "?" in url:
            return url + "&ord=rating"
        return url.rstrip("/") + "/?ord=rating"

    match = re.search(r"(https?://www\.kinopoisk\.ru/film/\d+/?)", url)
    if match:
        base = match.group(1)
        if not base.endswith("/"):
            base += "/"
        return base + "reviews/?ord=rating"

    return url


def is_captcha_page(html: str, current_url: str) -> bool:
    if "showcaptcha" in current_url.lower():
        return True

    soup = BeautifulSoup(html, "html.parser")
    title_text = soup.title.get_text(" ", strip=True).lower() if soup.title else ""
    page_text = soup.get_text(" ", strip=True).lower()

    markers = [
        "showcaptcha",
        "подтвердите, что запросы отправляли вы",
        "captcha",
        "я не робот",
    ]

    haystack = f"{title_text} {page_text}"
    return any(marker in haystack for marker in markers)


def _parse_helpful(text: str) -> tuple[int, int]:
    numbers = re.findall(r"\d+", text or "")
    if len(numbers) >= 2:
        return int(numbers[0]), int(numbers[1])
    if len(numbers) == 1:
        return int(numbers[0]), 0
    return 0, 0


def parse_reviews_from_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    reviews = []

    for idx, item in enumerate(soup.select("div.reviewItem.userReview"), start=1):
        review_id_raw = item.get("data-id", "").strip()
        if not review_id_raw.isdigit():
            continue

        review_id = int(review_id_raw)

        response_block = item.select_one("div.response")
        review_type = ""
        if response_block:
            classes = response_block.get("class", [])
            if "good" in classes:
                review_type = "positive"
            elif "bad" in classes:
                review_type = "negative"
            elif "neutral" in classes:
                review_type = "neutral"

        author_tag = item.select_one('[itemprop="author"] [itemprop="name"]')
        title_tag = item.select_one("p.sub_title")
        body_tag = item.select_one('[itemprop="reviewBody"]')
        date_tag = item.select_one("span.date")
        useful_tag = item.select_one('li[id^="comment_num_vote_"]')
        link_tag = item.select_one("p.links a")

        helpful_yes, helpful_no = _parse_helpful(
            useful_tag.get_text(" ", strip=True) if useful_tag else ""
        )

        reviews.append({
            "kinopoisk_review_id": review_id,
            "author_name": author_tag.get_text(strip=True) if author_tag else None,
            "review_title": title_tag.get_text(" ", strip=True) if title_tag else None,
            "review_text": body_tag.get_text("\n", strip=True) if body_tag else "",
            "review_type": review_type or "neutral",
            "review_date_text": date_tag.get_text(" ", strip=True) if date_tag else None,
            "helpful_yes": helpful_yes,
            "helpful_no": helpful_no,
            "review_url": urljoin("https://www.kinopoisk.ru", link_tag["href"]) if link_tag and link_tag.get("href") else None,
            "position_in_top": idx,
        })

    return reviews[:10]