import os
import logging
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton

from handlers.books import show_book_details
from utils.helpers import safe_edit_message
from utils.keyboards import (
    catalog_start_keyboard,
    genre_books_keyboard,
    main_menu_keyboard,
)
from data.database import get_books_by_genre, get_top_books, get_favorite_books, get_unfinished_books


CATALOG_COVER_PATH = r"C:\Users\User\Desktop\bot\catalogue.jpg"
CONTINUE_READING_COVER_PATH = r"C:\Users\User\Desktop\bot\covers\continue_reading.jpg"
FAVORITES_COVER_PATH = r"C:\Users\User\Desktop\bot\covers\favorites.jpg"


async def show_catalog_cover(callback_or_message, state: FSMContext):
    text = (
        "📚 *Меню ABook*\n\n"
        "Выберите раздел: Жанры, Поиск, Топ, Мое или Чат с AI ABook."
    )
    markup = main_menu_keyboard()

    sent = None
    try:
        if isinstance(callback_or_message, types.Message):
            if os.path.exists(CATALOG_COVER_PATH):
                sent = await callback_or_message.answer_photo(
                    FSInputFile(CATALOG_COVER_PATH),
                    caption=text,
                    reply_markup=markup,
                    parse_mode="Markdown",
                )
            else:
                sent = await callback_or_message.answer(
                    text, reply_markup=markup, parse_mode="Markdown"
                )
        else:
            if os.path.exists(CATALOG_COVER_PATH):
                sent = await callback_or_message.message.answer_photo(
                    FSInputFile(CATALOG_COVER_PATH),
                    caption=text,
                    reply_markup=markup,
                    parse_mode="Markdown",
                )
            else:
                sent = await callback_or_message.message.answer(
                    text, reply_markup=markup, parse_mode="Markdown"
                )
    except Exception as e:
        logging.error(f"Ошибка показа меню: {e}")
        if isinstance(callback_or_message, types.Message):
            sent = await callback_or_message.answer(
                text, reply_markup=markup, parse_mode="Markdown"
            )
        else:
            sent = await callback_or_message.message.answer(
                text, reply_markup=markup, parse_mode="Markdown"
            )

    if sent:
        await state.update_data(catalog_message_id=sent.message_id)
    await state.update_data(current="menu")


async def show_genres_menu(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    text = "🧩 *Жанры*\n\nВыберите интересующий жанр:"
    if os.path.exists(CATALOG_COVER_PATH):
        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.message.answer_photo(
            FSInputFile(CATALOG_COVER_PATH),
            caption=text,
            reply_markup=catalog_start_keyboard(),
            parse_mode="Markdown",
        )
    else:
        await safe_edit_message(
            callback.message,
            text,
            reply_markup=catalog_start_keyboard(),
            parse_mode="Markdown",
        )
    await state.update_data(current="genres")


async def show_my_section(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧑 Профиль", callback_data="profile")],
            [InlineKeyboardButton(text="▶ Продолжить чтение", callback_data="continue_reading")],
            [InlineKeyboardButton(text="⭐ Избранное", callback_data="my_favorites")],
            [InlineKeyboardButton(text="⬅ В меню", callback_data="back_to_menu")],
        ]
    )
    await safe_edit_message(
        callback.message,
        "👤 *Мое*\n\nЗдесь доступны профиль, избранное и продолжение чтения.",
        reply_markup=markup,
        parse_mode="Markdown",
    )
    await state.update_data(current="my")


async def show_favorites(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    books = await get_favorite_books(callback.from_user.id)

    if not books:
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_my")]
            ]
        )
        text = "⭐ *Избранное*\n\nПока нет избранных книг."
        if os.path.exists(FAVORITES_COVER_PATH):
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer_photo(
                FSInputFile(FAVORITES_COVER_PATH),
                caption=text,
                reply_markup=markup,
                parse_mode="Markdown",
            )
        else:
            await safe_edit_message(
                callback.message,
                text,
                reply_markup=markup,
                parse_mode="Markdown",
            )
        await state.update_data(current="favorites", book_source="favorites")
        return

    buttons = [[InlineKeyboardButton(text=title, callback_data=f"book_{book_id}")] for book_id, title in books]
    buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_my")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    text = "⭐ *Избранное*\n\nВыберите книгу:"
    if os.path.exists(FAVORITES_COVER_PATH):
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_photo(
            FSInputFile(FAVORITES_COVER_PATH),
            caption=text,
            reply_markup=markup,
            parse_mode="Markdown",
        )
    else:
        await safe_edit_message(
            callback.message,
            text,
            reply_markup=markup,
            parse_mode="Markdown",
        )
    await state.update_data(current="favorites", book_source="favorites")


async def continue_reading(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    books = await get_unfinished_books(callback.from_user.id)
    if not books:
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_my")]
            ]
        )
        text = "⏱ *Продолжить чтение*\n\nНет незавершённых книг."
        if os.path.exists(CONTINUE_READING_COVER_PATH):
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer_photo(
                FSInputFile(CONTINUE_READING_COVER_PATH),
                caption=text,
                reply_markup=markup,
                parse_mode="Markdown",
            )
        else:
            await safe_edit_message(
                callback.message,
                text,
                reply_markup=markup,
                parse_mode="Markdown",
            )
        await state.update_data(current="continue", book_source="continue")
        return

    buttons = [[InlineKeyboardButton(text=title, callback_data=f"book_{book_id}")] for book_id, title in books]
    buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_my")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    text = "⏱ *Продолжить чтение*\n\nВыберите книгу:"
    if os.path.exists(CONTINUE_READING_COVER_PATH):
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_photo(
            FSInputFile(CONTINUE_READING_COVER_PATH),
            caption=text,
            reply_markup=markup,
            parse_mode="Markdown",
        )
    else:
        await safe_edit_message(
            callback.message,
            text,
            reply_markup=markup,
            parse_mode="Markdown",
        )
    await state.update_data(current="continue", book_source="continue")


async def show_ai_chat_placeholder(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅ В меню", callback_data="back_to_menu")]
        ]
    )
    await safe_edit_message(
        callback.message,
        "🤖 *Чат с AI ABook*\n\nРаздел подготовлен, интеграцию AI можно подключить следующим шагом.",
        reply_markup=markup,
        parse_mode="Markdown",
    )
    await state.update_data(current="ai_chat")


async def show_genre_books(callback: types.CallbackQuery, state: FSMContext):
    genre = callback.data.replace("genre_", "")
    await state.update_data(current="genre", genre=genre, book_source="genre")

    from utils.keyboards import GENRE_COVERS

    genre_cover_path = GENRE_COVERS.get(genre)
    cover_exists = genre_cover_path and os.path.exists(genre_cover_path)
    books = await get_books_by_genre(genre)

    if not books:
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_catalog_from_genre")]
            ]
        )
        if cover_exists:
            try:
                await callback.message.delete()
            except Exception:
                pass

            await callback.message.answer_photo(
                FSInputFile(genre_cover_path),
                caption=f"📭 В жанре *{genre}* пока нет книг.",
                reply_markup=markup,
                parse_mode="Markdown",
            )
            return

        await safe_edit_message(
            callback.message,
            f"📭 В жанре *{genre}* пока нет книг.",
            reply_markup=markup,
            parse_mode="Markdown",
        )
        return

    markup = genre_books_keyboard([(b[0], b[1]) for b in books])

    if cover_exists:
        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.message.answer_photo(
            FSInputFile(genre_cover_path),
            caption=f"📚 *Книги в жанре:* _{genre}_",
            reply_markup=markup,
            parse_mode="Markdown",
        )
        return

    await safe_edit_message(
        callback.message,
        f"📚 *Книги в жанре:* _{genre}_",
        reply_markup=markup,
        parse_mode="Markdown",
    )


async def show_top_books(callback: types.CallbackQuery, state: FSMContext):
    books = await get_top_books(10)

    if not books:
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅ В меню", callback_data="back_to_menu")]
            ]
        )
        await safe_edit_message(
            callback.message,
            "😔 Пока нет данных о популярных книгах.",
            reply_markup=markup,
            parse_mode="Markdown",
        )
        return

    text_lines = []
    buttons = []

    for idx, book in enumerate(books, start=1):
        book_id, title, _, read_count = book
        text_lines.append(f"{idx}. {title} — 👁 {read_count} прочтений")
        buttons.append([InlineKeyboardButton(text=f"{idx}. {title}", callback_data=f"book_{book_id}")])

    buttons.append([InlineKeyboardButton(text="⬅ В меню", callback_data="back_to_menu")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    await safe_edit_message(
        callback.message,
        f"🔥 *Самые читаемые книги:*\n\n{chr(10).join(text_lines)}",
        reply_markup=markup,
        parse_mode="Markdown",
    )
    await state.update_data(current="top_books", book_source="top_books")


async def back_to_catalog(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current = data.get("current")
    genre = data.get("genre")
    book_id = data.get("current_book_id")
    book_source = data.get("book_source")

    if current == "book" and book_source == "top_books":
        await show_top_books(callback, state)
        return

    if current == "book" and book_source == "favorites":
        await show_favorites(callback, state)
        return

    if current == "book" and book_source == "continue":
        await continue_reading(callback, state)
        return

    if current == "book" and genre:
        from utils.keyboards import GENRE_COVERS

        books = await get_books_by_genre(genre)
        markup = genre_books_keyboard([(b[0], b[1]) for b in books])
        genre_cover_path = GENRE_COVERS.get(genre)
        cover_exists = genre_cover_path and os.path.exists(genre_cover_path)

        if cover_exists:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer_photo(
                FSInputFile(genre_cover_path),
                caption=f"📚 *Книги в жанре:* _{genre}_",
                reply_markup=markup,
                parse_mode="Markdown",
            )
        else:
            await safe_edit_message(
                callback.message,
                f"📚 *Книги в жанре:* _{genre}_",
                reply_markup=markup,
                parse_mode="Markdown",
            )

        await state.update_data(current="genre")
        return

    if current == "reading" and book_id:
        fake_callback = types.CallbackQuery(
            id=callback.id,
            from_user=callback.from_user,
            chat_instance=callback.chat_instance,
            message=callback.message,
            data=f"book_{book_id}",
        )
        await show_book_details(fake_callback, state)
        return

    if current == "genre":
        await show_genres_menu(callback, state)
        return

    if current == "favorites":
        await show_my_section(callback, state)
        return

    if current == "continue":
        await show_my_section(callback, state)
        return

    try:
        await callback.message.delete()
    except Exception:
        pass
    await show_catalog_cover(callback, state)


async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await show_catalog_cover(callback, state)


def register_handlers(dp):
    dp.callback_query.register(show_genres_menu, F.data == "menu_genres")
    dp.callback_query.register(show_my_section, F.data == "menu_my")
    dp.callback_query.register(show_my_section, F.data == "back_to_my")
    dp.callback_query.register(show_favorites, F.data == "my_favorites")
    dp.callback_query.register(continue_reading, F.data == "continue_reading")
    dp.callback_query.register(show_ai_chat_placeholder, F.data == "menu_ai_chat")
    dp.callback_query.register(back_to_menu, F.data == "back_to_menu")

    dp.callback_query.register(show_genre_books, F.data.startswith("genre_"))
    dp.callback_query.register(show_top_books, F.data == "top_books")
    dp.callback_query.register(
        back_to_catalog,
        F.data.in_(["back_to_catalog", "back_to_catalog_from_genre", "back_to_book", "back_to_top_books", "back_to_favorites", "back_to_continue"]),
    )


