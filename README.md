---
noteId: "6f5f8750264011f1a2947d0bc2a4e662"
tags: []

---

## Telegram Bot for Movie Search and Reviews

A Telegram bot for searching movies on Kinopoisk and generating short spoiler-free reviews using **YandexGPT**.

---

## Architecture

The project is divided into four layers:

- **Telegram** — handlers and user interface  
- **Services** — business logic  
- **Parsers** — data collection from Kinopoisk  
- **Database** — PostgreSQL  

---

## Main Workflow

1. The user enters a movie title  
2. The bot shows up to 10 search results  
3. The user selects a movie  
4. The bot displays the movie card  
5. The user requests a review  
6. The bot:
   - retrieves reviews (from cache or via Selenium)  
   - generates a summary through YandexGPT  
   - saves the result to the database  

---

## Project Structure

### Main Files

- `bot.py` — Telegram logic  
- `config.py` — configuration  
- `db.py`, `schema.sql` — database operations  
- `keyboards.py` — inline buttons  

---

### Parsers

- `kinopoisk_search.py` — search  
- `kinopoisk_film.py` — movie card  
- `kinopoisk_reviews.py` — reviews  
- `browser.py` — Selenium is used as the main parsing library  

---

### Services

- `search_service.py` — search and cache  
- `film_service.py` — movie card  
- `review_service.py` — review collection  
- `summary_service.py` — review generation  

---

### Other

- `text.py` — text normalization  
- `spoiler_free_review.txt` — system prompt  

---

## Key Features

- Caching:
  - search  
  - movies  
  - reviews  
  - summary  

- CAPTCHA handling through Selenium (with manual confirmation)  
- Text generation via an OpenAI-compatible API (YandexGPT)  
- Upsert logic for all entities  
- Clear separation into independent layers  

---

## Dependencies

### Main

- `aiogram`  
- `selenium` + `webdriver-manager`  
- `beautifulsoup4`  
- `requests`  
- `psycopg`  
- `python-dotenv`  
- `openai`  

---

## Running the Project

First, you need to obtain a token for the Telegram bot, as well as a token for YandexGPT.
You also need to configure the database; the SQL file is attached.


Initialize `.env`  file
```
BOT_TOKEN=

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=film_reviewer
POSTGRES_USER=postgres
POSTGRES_PASSWORD=None

YANDEX_GPT_API_KEY=
YANDEX_GPT_FOLDER_ID=
YANDEX_GPT_BASE_URL=
YANDEX_GPT_MODEL=
YANDEX_GPT_MODEL_ID=
YANDEX_GPT_TEMPERATURE=0.4
```
```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux / macOS

pip install -r requirements.txt
python bot.py
```
