#database.py

import os
import aiosqlite
from datetime import datetime
from config import DB_PATH


# ==================== ИНИЦИАЛИЗАЦИЯ БАЗЫ ====================
async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        # Пользователи
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_seen DATE,
                read_books INTEGER DEFAULT 0,
                total_read_time INTEGER DEFAULT 0,
                last_book_id INTEGER,
                last_read_at TEXT
            )
        """)
        # Книги
        await db.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                author TEXT,
                description TEXT,
                file_path TEXT,
                cover_path TEXT,
                genre TEXT,
                read_count INTEGER DEFAULT 0
            )
        """)
        # Таймеры чтения
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reading_sessions (
                user_id INTEGER,
                book_id INTEGER,
                start_time DATETIME,
                UNIQUE(user_id, book_id)
            )
        """)
        # Запросы пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS book_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                request_text TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        # Избранное
        await db.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER,
                book_id INTEGER,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, book_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (book_id) REFERENCES books(id)
            )
        """)
        # Прогресс чтения по книгам пользователя
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_book_progress (
                user_id INTEGER,
                book_id INTEGER,
                last_opened_at TEXT,
                finished INTEGER DEFAULT 0,
                UNIQUE(user_id, book_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (book_id) REFERENCES books(id)
            )
        """)
        # Миграция старых баз (если колонок еще нет)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN last_book_id INTEGER")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN last_read_at TEXT")
        except Exception:
            pass
        await db.commit()


# ==================== ФУНКЦИИ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ====================
async def add_user(user_id: int, username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_seen, read_books)
            VALUES (?, ?, ?, 0)
        """, (user_id, username, datetime.now().date().isoformat()))
        await db.commit()


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT user_id, username, first_seen, read_books, total_read_time
            FROM users WHERE user_id = ?
        """, (user_id,))
        return await cur.fetchone()


async def set_last_read_book(user_id: int, book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE users
            SET last_book_id = ?, last_read_at = ?
            WHERE user_id = ?
            """,
            (book_id, datetime.now().isoformat(), user_id),
        )
        await db.commit()


async def get_last_read_book(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT b.id, b.title
            FROM users u
            JOIN books b ON b.id = u.last_book_id
            WHERE u.user_id = ?
            """,
            (user_id,),
        )
        return await cur.fetchone()


async def mark_book_opened(user_id: int, book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO user_book_progress (user_id, book_id, last_opened_at, finished)
            VALUES (?, ?, ?, 0)
            ON CONFLICT(user_id, book_id) DO UPDATE SET
                last_opened_at = excluded.last_opened_at,
                finished = 0
            """,
            (user_id, book_id, datetime.now().isoformat()),
        )
        await db.commit()


async def mark_book_finished(user_id: int, book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE user_book_progress
            SET finished = 1
            WHERE user_id = ? AND book_id = ?
            """,
            (user_id, book_id),
        )
        await db.commit()


async def get_unfinished_books(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT b.id, b.title
            FROM user_book_progress p
            JOIN books b ON b.id = p.book_id
            WHERE p.user_id = ? AND p.finished = 0
            ORDER BY p.last_opened_at DESC
            """,
            (user_id,),
        )
        return await cur.fetchall()


# ==================== ФУНКЦИИ ДЛЯ КНИГ ====================
async def add_book(title: str, author: str, description: str, file_path: str, cover_path: str, genre: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM books WHERE title = ? OR file_path = ?", (title, file_path))
        if await cur.fetchone():
            return False
        await db.execute("""
            INSERT INTO books (title, author, description, file_path, cover_path, genre)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, author, description, file_path, cover_path, genre))
        await db.commit()
        return True


async def get_book(book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT id, title, author, description, file_path, cover_path, genre, read_count
            FROM books WHERE id = ?
        """, (book_id,))
        return await cur.fetchone()


async def is_favorite(user_id: int, book_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND book_id = ?",
            (user_id, book_id),
        )
        return await cur.fetchone() is not None


async def add_favorite(user_id: int, book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO favorites (user_id, book_id) VALUES (?, ?)",
            (user_id, book_id),
        )
        await db.commit()


async def remove_favorite(user_id: int, book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM favorites WHERE user_id = ? AND book_id = ?",
            (user_id, book_id),
        )
        await db.commit()


async def get_favorite_books(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT b.id, b.title
            FROM favorites f
            JOIN books b ON b.id = f.book_id
            WHERE f.user_id = ?
            ORDER BY f.created_at DESC
            """,
            (user_id,),
        )
        return await cur.fetchall()


async def get_books_by_genre(genre: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT id, title, author, description, cover_path
            FROM books WHERE genre = ?
        """, (genre,))
        return await cur.fetchall()



async def search_books(query: str):
    query = query.strip()  # просто убираем лишние пробелы
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT id, title, author, description, cover_path, genre
            FROM books
            WHERE title LIKE ? COLLATE NOCASE
        """, (f"%{query}%",))
        results = await cur.fetchall()
        print(f"[DEBUG] search query: '{query}'")
        print(f"[DEBUG] search results: {results}")
        return results




async def get_top_books(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT id, title, author, read_count
            FROM books
            ORDER BY read_count DESC
            LIMIT ?
        """, (limit,))
        return await cur.fetchall()


async def increment_read_count(book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE books SET read_count = read_count + 1 WHERE id = ?", (book_id,))
        await db.commit()


async def delete_book(book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        await db.commit()


async def get_book_by_id(book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT id, title, author, description, file_path, cover_path, genre
            FROM books
            WHERE id = ?
        """, (book_id,))
        row = await cur.fetchone()
    if row:
        return {
            "id": row[0],
            "title": row[1],
            "author": row[2],
            "description": row[3],
            "file_path": row[4],
            "cover_path": row[5],
            "genre": row[6]
        }
    return None




# ==================== ФУНКЦИИ ДЛЯ ЧТЕНИЯ (таймер) ====================
async def start_reading_session(user_id: int, book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO reading_sessions (user_id, book_id, start_time)
            VALUES (?, ?, ?)
        """, (user_id, book_id, datetime.now().isoformat()))
        await db.commit()


async def stop_reading_session(user_id: int, book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT start_time FROM reading_sessions
            WHERE user_id = ? AND book_id = ?
        """, (user_id, book_id))
        active = await cur.fetchone()
        if not active:
            return 0
        start_time = datetime.fromisoformat(active[0])
        elapsed_seconds = (datetime.now() - start_time).total_seconds()
        await db.execute("DELETE FROM reading_sessions WHERE user_id = ? AND book_id = ?", (user_id, book_id))
        await db.execute("""
            UPDATE users
            SET total_read_time = COALESCE(total_read_time, 0) + ?
            WHERE user_id = ?
        """, (int(elapsed_seconds), user_id))
        await db.commit()
        return int(elapsed_seconds)


# ==================== ФУНКЦИИ ДЛЯ ЗАПРОСОВ ПОЛЬЗОВАТЕЛЕЙ ====================
async def add_book_request(user_id: int, username: str, request_text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO book_requests (user_id, username, request_text)
            VALUES (?, ?, ?)
        """, (user_id, username, request_text))
        await db.commit()


async def get_pending_requests(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT id, user_id, username, request_text, created_at, status
            FROM book_requests
            WHERE status = 'pending'
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        return await cur.fetchall()


async def mark_request_done(request_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE book_requests SET status = 'done' WHERE id = ?", (request_id,))
        await db.commit()
