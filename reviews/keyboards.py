from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def films_keyboard(films: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for film in films[:10]:
        title = film["title"]
        year = film.get("year")
        label = f"{title} ({year})" if year else title

        builder.add(
            InlineKeyboardButton(
                text=label[:64],
                callback_data=f"film:{film['id']}",
            )
        )

    builder.adjust(1)
    return builder.as_markup()


def film_card_keyboard(film_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="Получить рецензию без спойлеров",
            callback_data=f"summary:{film_id}",
        )
    )
    builder.adjust(1)
    return builder.as_markup()