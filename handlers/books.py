# handlers/books.py

import os
import aiosqlite
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, InputMediaPhoto
import logging
import re

from utils.keyboards import GENRE_COVERS
from utils.keyboards import catalog_start_keyboard

from data.database import (
    get_book,
    start_reading_session,
    stop_reading_session,
    increment_read_count,
    is_favorite,
    add_favorite,
    remove_favorite,
    set_last_read_book,
    mark_book_opened,
    mark_book_finished,
)
from config import DB_PATH


# ============== MARKDOWN ESCAPE ==============
def escape_md(text: str) -> str:
    """Экранирование для заголовков, авторов, жанров"""
    if not text:
        return ""
    return re.sub(r'([_*[\]()~`>#+\-=|{}!])', r'\\\1', text)


def escape_md_description(text: str) -> str:
    """
    Экранирует Markdown, но НЕ трогает точки, запятые и обычные символы,
    чтобы описания книг оставались читабельными.
    """
    if not text:
        return ""
    return re.sub(r'([_*[\]()~`>#+\-=|{}])', r'\\\1', text)

def build_book_actions_markup(book_id: int, back_callback: str, favorite: bool) -> InlineKeyboardMarkup:
    fav_text = "💔 Убрать из избранного" if favorite else "⭐ В избранное"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Читать", callback_data=f"read_{book_id}")],
        [InlineKeyboardButton(text=fav_text, callback_data=f"fav_{book_id}")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data=back_callback)],
    ])


# ====================================================================
#                     ПОКАЗ КАРТОЧКИ КНИГИ
# ====================================================================

async def show_book_details(callback: types.CallbackQuery, state: FSMContext):
    """Показывает карточку книги с кнопкой 'Читать' и 'Назад'"""

    try:
        book_id = int(callback.data.split("_")[1])
    except:
        return await callback.answer("❌ ID неверен")

    book = await get_book(book_id)
    if not book:
        return await callback.answer("❌ Книга не найдена")

    _, title, author, description, file_path, cover_path, genre, _ = book

    # Экранируем красиво
    title = escape_md(title or "Без названия")
    author = escape_md(author or "Не указан")
    genre_display = escape_md(genre or "Не указан")
    description = escape_md_description(description or "Описание отсутствует")

    caption = (
        f"📘 *{title}*\n\n"
        f"👤 Автор: _{author}_\n"
        f"📚 Жанр: _{genre_display}_\n\n"
        f"{description}"
    )

    data = await state.get_data()
    current_section = data.get("current")
    previous_source = data.get("book_source")

    if current_section == "top_books":
        book_source = "top_books"
    elif current_section in ("genre", "genres"):
        book_source = "genre"
    elif current_section == "favorites":
        book_source = "favorites"
    elif current_section == "continue":
        book_source = "continue"
    elif previous_source == "continue":
        book_source = "continue"
    elif current_section == "reading" and previous_source in ("top_books", "genre", "favorites", "continue"):
        book_source = previous_source
    elif previous_source in ("top_books", "genre", "favorites", "continue"):
        book_source = previous_source
    else:
        book_source = "genre"

    if book_source == "top_books":
        back_callback = "back_to_top_books"
    elif book_source == "favorites":
        back_callback = "back_to_favorites"
    elif book_source == "continue":
        back_callback = "back_to_continue"
    else:
        back_callback = "back_to_catalog_from_genre"
    favorite = await is_favorite(callback.from_user.id, book_id)
    markup = build_book_actions_markup(book_id, back_callback, favorite)

    # Обновляем медиа
    try:
        await callback.message.edit_media(
            InputMediaPhoto(
                media=FSInputFile(cover_path) if cover_path and os.path.exists(cover_path) else "",
                caption=caption,
                parse_mode="Markdown"
            ),
            reply_markup=markup
        )
    except Exception:
        try:
            await callback.message.delete()
        except:
            pass

        if cover_path and os.path.exists(cover_path):
            await callback.message.answer_photo(
                FSInputFile(cover_path),
                caption=caption,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            await callback.message.answer(
                caption,
                reply_markup=markup,
                parse_mode="Markdown"
            )

    await state.update_data(
        current="book",
        current_book_id=book_id,
        genre=genre,
        book_source=book_source
    )


# ====================================================================
#                          ЧТЕНИЕ PDF
# ====================================================================
async def read_book(callback: types.CallbackQuery, state: FSMContext):

    try:
        book_id = int(callback.data.split("_")[1])
    except:
        return await callback.answer("❌ ID неверен")

    book = await get_book(book_id)
    if not book:
        return await callback.answer("❌ Книга не найдена")

    _, title, _, _, file_path, _, _, _ = book

    if not os.path.exists(file_path):
        return await callback.answer("⚠ PDF не найден")

    try:
        await callback.message.delete()
    except Exception as e:
        logging.error(f"Ошибка удаления карточки: {e}")

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏱ Начать таймер", callback_data=f"start_timer_{book_id}")],
        [InlineKeyboardButton(text="✅ Книга прочитана", callback_data=f"mark_read_{book_id}")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_catalog")]
    ])

    sent = await callback.message.answer_document(
        FSInputFile(file_path),
        caption=f"📖 *{escape_md(title)}*",
        parse_mode="Markdown",
        reply_markup=markup
    )

    await state.update_data(
        current="reading",
        current_book_id=book_id,
        pdf_message_id=sent.message_id
    )
    await set_last_read_book(callback.from_user.id, book_id)
    await mark_book_opened(callback.from_user.id, book_id)

    await callback.answer()


async def back_to_catalog(callback: types.CallbackQuery, state: FSMContext):
    from handlers.catalog import show_catalog_cover
    await show_catalog_cover(callback.message, state)
    await callback.answer()


# ====================================================================
#                         ТАЙМЕР
# ====================================================================
async def toggle_timer(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    try:
        book_id = int(callback.data.split("_")[2])
    except:
        return await callback.answer("❌ ID неверен")

    elapsed = await stop_reading_session(user_id, book_id)

    if elapsed > 0:
        mins = int(elapsed // 60)
        text = f"{mins} мин." if mins > 0 else f"{int(elapsed)} сек."
        await callback.answer("⏹ Остановлено")
        await callback.message.answer(f"🕒 Вы читали: *{text}*", parse_mode="Markdown")
        new_btn = "⏱ Начать таймер"
    else:
        await start_reading_session(user_id, book_id)
        await callback.answer("⏱ Запущено")
        new_btn = "⏹ Остановить"

    new_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=new_btn, callback_data=f"start_timer_{book_id}")],
        [InlineKeyboardButton(text="✅ Книга прочитана", callback_data=f"mark_read_{book_id}")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_book")]
    ])

    try:
        await callback.message.edit_reply_markup(reply_markup=new_markup)
    except Exception as e:
        logging.error(f"Ошибка обновления таймера: {e}")


# ====================================================================
#                     ОТМЕТИТЬ ПРОЧИТАННОЙ
# ====================================================================
async def mark_book_read(callback: types.CallbackQuery, state: FSMContext):

    user_id = callback.from_user.id

    try:
        book_id = int(callback.data.split("_")[2])
    except:
        return await callback.answer("❌ ID неверен")

    await increment_read_count(book_id)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET read_books = COALESCE(read_books,0) + 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()

    await callback.answer("✅ Готово!")
    await callback.message.answer("🎉 Вы завершили чтение книги!")
    await mark_book_finished(user_id, book_id)


# ====================================================================
#                        РЕГИСТРАЦИЯ
# ====================================================================

async def toggle_favorite(callback: types.CallbackQuery, state: FSMContext):

    try:
        book_id = int(callback.data.split("_")[1])
    except Exception:
        await callback.answer("❌ ID неверен")
        return

    user_id = callback.from_user.id
    currently_favorite = await is_favorite(user_id, book_id)

    if currently_favorite:
        await remove_favorite(user_id, book_id)
        await callback.answer("Удалено из избранного")
        new_favorite = False
    else:
        await add_favorite(user_id, book_id)
        await callback.answer("Добавлено в избранное")
        new_favorite = True

    data = await state.get_data()
    source = data.get("book_source")
    if source == "top_books":
        back_callback = "back_to_top_books"
    elif source == "favorites":
        back_callback = "back_to_favorites"
    elif source == "continue":
        back_callback = "back_to_continue"
    else:
        back_callback = "back_to_catalog_from_genre"

    new_markup = build_book_actions_markup(book_id, back_callback, new_favorite)

    try:
        await callback.message.edit_reply_markup(reply_markup=new_markup)
    except Exception:
        pass


def register_handlers(dp):
    dp.callback_query.register(show_book_details, F.data.startswith("book_"))
    dp.callback_query.register(read_book, F.data.startswith("read_"))
    dp.callback_query.register(toggle_favorite, F.data.startswith("fav_"))
    dp.callback_query.register(toggle_timer, F.data.startswith("start_timer_"))
    dp.callback_query.register(mark_book_read, F.data.startswith("mark_read_"))
    dp.callback_query.register(back_to_catalog, F.data == "back_to_catalog")
