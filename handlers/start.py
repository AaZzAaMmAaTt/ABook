import os
from datetime import datetime
from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from data.database import add_user, get_user
from utils.keyboards import start_keyboard, back_to_start_keyboard
from handlers import catalog
from config import ADMINS


def is_admin(user_id: int) -> bool:
    return user_id in ADMINS


async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await add_user(message.from_user.id, message.from_user.username)

    logo_path = "970111763390b956fad9089dd2cefcf0.jpg"
    caption = (
        "📚 Привет, читатель!\n\n"
        "Добро пожаловать в *ABook* 📖\n\n"
        "Выбери действие ниже:"
    )

    if os.path.exists(logo_path):
        sent = await message.answer_photo(
            photo=types.FSInputFile(logo_path),
            caption=caption,
            reply_markup=start_keyboard(),
            parse_mode="Markdown",
        )
    else:
        sent = await message.answer(
            caption,
            reply_markup=start_keyboard(),
            parse_mode="Markdown",
        )
    await state.update_data(main_message_id=sent.message_id, current="start")


async def show_profile(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()

    main_message_id = data.get("main_message_id")
    if main_message_id:
        try:
            await callback.bot.delete_message(user_id, main_message_id)
        except Exception:
            pass
        await state.update_data(main_message_id=None)

    user = await get_user(user_id)
    if not user:
        await callback.message.answer("❌ Профиль не найден.")
        return

    _, _, first_seen, read_books, total_seconds = user
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    total_time_text = (
        f"{int(hours)} ч {int(minutes)} мин"
        if hours
        else f"{int(minutes)} мин"
        if minutes
        else "меньше минуты"
    )
    days_in_bot = (datetime.now().date() - datetime.fromisoformat(first_seen).date()).days

    profile_text = (
        f"👤 *Ваш профиль*\n\n"
        f"📅 В боте: *{days_in_bot}* дн.\n"
        f"📚 Прочитано книг: *{read_books}*\n"
        f"⏰ Время чтения: *{total_time_text}*"
    )

    logo_path = "970111763390b956fad9089dd2cefcf0.jpg"
    back_button = back_to_start_keyboard()

    if os.path.exists(logo_path):
        sent = await callback.message.answer_photo(
            photo=types.FSInputFile(logo_path),
            caption=profile_text,
            reply_markup=back_button,
            parse_mode="Markdown",
        )
    else:
        sent = await callback.message.answer(
            profile_text,
            reply_markup=back_button,
            parse_mode="Markdown",
        )

    await state.update_data(current="profile", profile_message_id=sent.message_id)


async def back_to_start(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    for key in ["profile_message_id", "book_message_id", "catalog_message_id"]:
        message_id = data.get(key)
        if message_id:
            try:
                await callback.bot.delete_message(callback.from_user.id, message_id)
            except Exception:
                pass
            await state.update_data(**{key: None})

    logo_path = "970111763390b956fad9089dd2cefcf0.jpg"
    caption = (
        "📚 Привет, читатель!\n\n"
        "Добро пожаловать в *ABook* 📖\n\n"
        "Выбери действие ниже:"
    )
    if os.path.exists(logo_path):
        sent = await callback.message.answer_photo(
            photo=types.FSInputFile(logo_path),
            caption=caption,
            reply_markup=start_keyboard(),
            parse_mode="Markdown",
        )
    else:
        sent = await callback.message.answer(
            caption,
            reply_markup=start_keyboard(),
            parse_mode="Markdown",
        )
    await state.update_data(main_message_id=sent.message_id, current="start")


async def open_menu(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    main_message_id = data.get("main_message_id")

    if main_message_id:
        try:
            await callback.bot.delete_message(callback.from_user.id, main_message_id)
        except Exception:
            pass
        await state.update_data(main_message_id=None)

    await catalog.show_catalog_cover(callback, state)
    await state.update_data(current="menu")


def register_handlers(dp):
    dp.message.register(cmd_start, Command("start"))
    dp.callback_query.register(show_profile, F.data == "profile")
    dp.callback_query.register(back_to_start, F.data == "back_to_start")
    dp.callback_query.register(open_menu, F.data == "menu")
