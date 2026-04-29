# admin.py

import os
import re
import aiosqlite
from datetime import datetime
from aiogram import types, F, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMINS, DB_PATH
from handlers.books import show_book_details

# ==================== ПРОВЕРКА АДМИНА ====================
def is_admin(user_id: int) -> bool:
    return user_id in ADMINS


# ==================== СОСТОЯНИЯ ====================
class AdminAddBookState(StatesGroup):
    waiting_for_book_data = State()


# ==================== АДМИН-ПАНЕЛЬ ====================
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав на доступ к админ-панели.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить книгу", callback_data="admin_add_book")],
        [InlineKeyboardButton(text="🗑 Удалить книгу", callback_data="admin_delete_book")],
        [InlineKeyboardButton(text="📋 Список пользователей", callback_data="list_users")],
        [InlineKeyboardButton(text="📬 Запросы пользователей", callback_data="admin_view_requests")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_start")]
    ])
    await message.answer("👑 Админ-панель:", reply_markup=keyboard)


# ==================== ДОБАВЛЕНИЕ КНИГ ====================
async def admin_add_book(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав.")
        return

    await callback.message.answer(
        "📖 Введите данные книги в формате:\n"
        "`Название | Описание | путь_к_файлу | путь_к_обложке | жанр | Автор`\n\n"
        "Пример:\n"
        "`Моя Книга | Интересное описание | data/books/book.pdf | data/books/covers/cover.jpg | Фэнтези | Иван Иванов`",
        parse_mode="Markdown"
    )
    await state.set_state(AdminAddBookState.waiting_for_book_data)


async def add_book_via_admin(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if "|" not in message.text:
        await message.answer(
            "⚠️ Неверный формат. Используйте:\n"
            "`Название | Описание | путь_к_файлу | путь_к_обложке | жанр | Автор`",
            parse_mode="Markdown"
        )
        return

    try:
        title, desc, file_path, cover_path, genre, author = map(str.strip, message.text.split("|"))
    except ValueError:
        await message.answer(
            "⚠️ Проверьте, чтобы было *6 полей*, разделённых `|`.",
            parse_mode="Markdown"
        )
        return

    if not os.path.exists(file_path):
        await message.answer("❌ Файл книги не найден по указанному пути.")
        return

    if not os.path.exists(cover_path):
        await message.answer("⚠️ Обложка не найдена, книга добавлена без картинки.")
        cover_path = None

    # Используем функцию add_book из database.py
    from data.database import add_book
    success = await add_book(title, author, desc, file_path, cover_path, genre)
    if not success:
        await message.answer(f"⚠️ Книга *{title}* уже существует!", parse_mode="Markdown")
        await state.clear()
        return

    await message.answer(
        f"✅ Книга *{title}* успешно добавлена!\n📚 Жанр: *{genre}*\n👤 Автор: *{author}*",
        parse_mode="Markdown"
    )
    await state.clear()



# ==================== УДАЛЕНИЕ КНИГ ====================
async def admin_delete_book(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав.")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, title FROM books")
        books = await cur.fetchall()

    if not books:
        await callback.message.answer("📚 В каталоге пока нет книг для удаления.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"❌ {title}", callback_data=f"delbook_{book_id}")]
        for book_id, title in books
    ])
    sent = await callback.message.answer("🗑 Выбери книгу, чтобы удалить:", reply_markup=keyboard)
    await state.update_data(delete_list_message_id=sent.message_id)


async def confirm_delete(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Только админ может удалять книги.")
        return

    book_id = int(callback.data.split("_")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT title FROM books WHERE id = ?", (book_id,))
        book = await cur.fetchone()

    if not book:
        await callback.answer("❌ Книга не найдена.")
        return

    title = book[0]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirmdel_{book_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")]
    ])
    sent = await callback.message.answer(
        f"Вы уверены, что хотите удалить книгу *{title}*?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.update_data(confirm_message_id=sent.message_id)


async def delete_book(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав.")
        return

    book_id = int(callback.data.split("_")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT title FROM books WHERE id = ?", (book_id,))
        book = await cur.fetchone()
        if not book:
            await callback.answer("❌ Книга не найдена.")
            return
        title = book[0]
        await db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        await db.commit()

    data = await state.get_data()
    for msg_id in [data.get("delete_list_message_id"), data.get("confirm_message_id")]:
        if msg_id:
            try:
                await callback.bot.delete_message(callback.from_user.id, msg_id)
            except Exception:
                pass

    await state.clear()
    await callback.message.answer(f"✅ Книга *{title}* успешно удалена!", parse_mode="Markdown")


async def cancel_delete(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    for msg_id in [data.get("delete_list_message_id"), data.get("confirm_message_id")]:
        if msg_id:
            try:
                await callback.bot.delete_message(callback.from_user.id, msg_id)
            except Exception:
                pass
    await state.clear()
    await callback.message.answer("❌ Вы отменили удаление книги.")


# ==================== ЗАПРОСЫ ПОЛЬЗОВАТЕЛЕЙ ====================
async def admin_view_requests(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа.")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT id, username, request_text, created_at, status
            FROM book_requests
            ORDER BY created_at DESC
            LIMIT 10
        """)
        requests = await cur.fetchall()

    if not requests:
        await callback.message.answer("📭 Нет новых запросов от пользователей.")
        return

    for req_id, username, req_text, date, status in requests:
        user_display = f"@{username}" if username else "Без username"
        status_icon = "✅" if status == "done" else "🕓"
        text = f"{status_icon} *{user_display}*\n📚 {req_text}\n🕒 {date}"
        buttons = [[InlineKeyboardButton(text="✅ Пометить как обработанный", callback_data=f"resolve_{req_id}")]] if status != "done" else []
        markup = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
        await callback.message.answer(text, parse_mode="Markdown", reply_markup=markup)
    await callback.answer()


async def resolve_request_button(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа.")
        return

    req_id = int(callback.data.split("_")[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE book_requests SET status = 'done' WHERE id = ?", (req_id,))
        await db.commit()

    await callback.answer("✅ Запрос отмечен как обработанный!")
    try:
        await callback.message.edit_reply_markup()
    except Exception:
        pass


# ==================== СПИСОК ПОЛЬЗОВАТЕЛЕЙ ====================
async def list_users(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав на просмотр пользователей.")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT username, first_seen, read_books, COALESCE(total_read_time, 0)
            FROM users
            ORDER BY first_seen ASC
        """)
        users = await cur.fetchall()

    if not users:
        await callback.message.answer("😅 В базе пока нет пользователей.")
        await callback.answer()
        return

    # собираем текст БЕЗ разметки, чтобы потом экранировать
    text = "📋 Список пользователей:\n\n"
    for username, first_seen, read_books, total_seconds in users:
        name = f"@{username}" if username else "Без username"

        # считаем дни в боте
        if isinstance(first_seen, str):
            try:
                first_date = datetime.fromisoformat(first_seen).date()
                days_in_bot = (datetime.now().date() - first_date).days
            except ValueError:
                days_in_bot = 0
        else:
            days_in_bot = 0

        # считаем время чтения
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        time_text = (
            f"{int(hours)} ч {int(minutes)} мин"
            if total_seconds >= 60
            else f"{int(total_seconds)} сек"
        )

        text += (
            f"{name}\n"
            f"📅 В боте: {days_in_bot} дн.\n"
            f"📚 Прочитал: {read_books} книг\n"
            f"⏰ Время чтения: {time_text}\n\n"
        )

    # отправляем блоками 3500 символов, чтобы точно не рвать Markdown
    MAX_LEN = 3500

    # делим по переносам — не ломает Markdown
    def split_message(txt):
        parts = []
        while len(txt) > MAX_LEN:
            split_pos = txt.rfind("\n", 0, MAX_LEN)
            if split_pos == -1:
                split_pos = MAX_LEN
            parts.append(txt[:split_pos])
            txt = txt[split_pos:]
        parts.append(txt)
        return parts

    blocks = split_message(text)

    for block in blocks:
        safe_block = escape_md(block)
        await callback.message.answer(safe_block, parse_mode="Markdown")

    await callback.answer()



# ==================== РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ====================
def register_admin_handlers(dp: Dispatcher):
    dp.message.register(admin_panel, Command("admin"))

    dp.callback_query.register(admin_add_book, F.data == "admin_add_book")
    dp.message.register(add_book_via_admin, AdminAddBookState.waiting_for_book_data)

    dp.callback_query.register(admin_delete_book, F.data == "admin_delete_book")
    dp.callback_query.register(confirm_delete, F.data.startswith("delbook_"))
    dp.callback_query.register(delete_book, F.data.startswith("confirmdel_"))
    dp.callback_query.register(cancel_delete, F.data == "cancel_delete")

    dp.callback_query.register(admin_view_requests, F.data == "admin_view_requests")
    dp.callback_query.register(resolve_request_button, F.data.startswith("resolve_"))

    dp.callback_query.register(list_users, F.data == "list_users")


def escape_md(text: str) -> str:
    if not text:
        return ""
    # убрал точку из набора символов!
    return re.sub(r'([_*\[\]()~`>#+\-=|{}!])', r'\\\1', text)
