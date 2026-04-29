import os
import aiosqlite
import logging
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from config import DB_PATH, ADMINS

# ==================== STATE ====================
class SearchBookState(StatesGroup):
    waiting_for_query = State()
    waiting_for_user_request = State()

# ==================== КНОПКА "🔎 Найти книгу" ====================
async def search_book_button(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "🔎 Введите название книги для поиска. Для 100% нахождения книги введите название как в оригинальном названии.\n"
        "Например: *Колобок ✅ колобок 🚫*",
        parse_mode="Markdown"
    )
    await state.set_state(SearchBookState.waiting_for_query)

# ==================== ПОИСК КНИГИ ====================
async def handle_search_text(message: types.Message, state: FSMContext):
    query = message.text.strip()
    normalized_query = query.casefold()

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT id, title, description, cover_path, genre
            FROM books
        """)
        all_books = await cur.fetchall()

    books = [
        row for row in all_books
        if normalized_query in (row[1] or "").casefold()
    ]

    if books:
        for book_id, title, desc, cover_path, genre in books:
            caption = (
                f"📘 *{title}*\n\n"
                f"📚 Жанр: _{genre or 'Не указан'}_\n\n"
                f"{desc or 'Описание отсутствует.'}"
            )
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📖 Читать", callback_data=f"read_{book_id}")],
                [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_catalog_from_genre")]
            ])

            if cover_path and os.path.exists(cover_path):
                await message.answer_photo(
                    FSInputFile(cover_path),
                    caption=caption,
                    reply_markup=markup,
                    parse_mode="Markdown"
                )
            else:
                await message.answer(caption, reply_markup=markup, parse_mode="Markdown")

        await state.clear()
        return

    # Книга не найдена → предлагаем пользователю отправить запрос
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_book_request")]
    ])

    await message.answer(
        "😔 Книга не найдена.\n\n"
        "📬 Напишите *название и автора* (например: `Колобок | Народная сказка`),\n"
        "и мы передадим запрос администраторам.\n\n"
        "_Если передумали — нажмите «Отмена»._",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    await state.update_data(original_query=query)
    await state.set_state(SearchBookState.waiting_for_user_request)

# ==================== ПОЛЬЗОВАТЕЛЬ ОТПРАВИЛ ЗАПРОС ====================
async def handle_user_request(message: types.Message, state: FSMContext):
    user_request = message.text.strip()
    data = await state.get_data()
    original_query = data.get("original_query", "-")

    # сохраняем в БД
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO book_requests (user_id, username, request_text)
            VALUES (?, ?, ?)
        """, (message.from_user.id, message.from_user.username, user_request))
        await db.commit()

    # уведомляем админов
    for admin_id in ADMINS:
        try:
            await message.bot.send_message(
                admin_id,
                f"📩 *Новый запрос на книгу!*\n\n"
                f"👤 Пользователь: @{message.from_user.username or 'Без username'}\n"
                f"🆔 ID: `{message.from_user.id}`\n"
                f"🔎 Искал: *{original_query}*\n"
                f"📚 Предложение: {user_request}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Не удалось отправить запрос админу {admin_id}: {e}")

    await message.answer(
        "✅ Спасибо! Ваш запрос отправлен администраторам. Мы рассмотрим его в ближайшее время 🙌"
    )
    await state.clear()

# ==================== ОТМЕНА ====================
async def cancel_book_request(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🚫 Запрос отменён. Вы можете попробовать снова через каталог.",
        parse_mode="Markdown"
    )

# ==================== РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ====================
def register_handlers(dp):
    dp.callback_query.register(search_book_button, F.data == "search_book")
    dp.message.register(handle_search_text, SearchBookState.waiting_for_query)
    dp.message.register(handle_user_request, SearchBookState.waiting_for_user_request)
    dp.callback_query.register(cancel_book_request, F.data == "cancel_book_request")
