import aiosqlite
from gifts import GIFTS

DB_NAME = "bot.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS gifts (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            qty INTEGER NOT NULL,
            photo TEXT
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER UNIQUE,
            username TEXT,
            telegram_full_name TEXT,
            full_name TEXT NOT NULL,
            xj_id TEXT UNIQUE NOT NULL,
            gift_id INTEGER NOT NULL,
            gift_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        for gift in GIFTS:
            await db.execute("""
            INSERT OR IGNORE INTO gifts (id, name, qty, photo)
            VALUES (?, ?, ?, ?)
            """, (gift["id"], gift["name"], gift["qty"], gift["photo"]))

        await db.commit()


async def user_has_order(telegram_user_id: int) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id FROM orders WHERE telegram_user_id = ?",
            (telegram_user_id,)
        )
        row = await cursor.fetchone()
        return row is not None


async def xj_id_exists(xj_id: str) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id FROM orders WHERE xj_id = ?",
            (xj_id,)
        )
        row = await cursor.fetchone()
        return row is not None


async def get_gifts():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id, name, qty, photo FROM gifts ORDER BY id"
        )
        rows = await cursor.fetchall()
        return rows


async def get_gift(gift_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id, name, qty, photo FROM gifts WHERE id = ?",
            (gift_id,)
        )
        return await cursor.fetchone()


async def decrease_gift(gift_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE gifts SET qty = qty - 1 WHERE id = ? AND qty > 0",
            (gift_id,)
        )
        await db.commit()


async def create_order(
    telegram_user_id: int,
    username: str,
    telegram_full_name: str,
    full_name: str,
    xj_id: str,
    gift_id: int,
    gift_name: str,
    phone: str,
    address: str
):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
        INSERT INTO orders (
            telegram_user_id, username, telegram_full_name,
            full_name, xj_id, gift_id, gift_name, phone, address
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            telegram_user_id, username, telegram_full_name,
            full_name, xj_id, gift_id, gift_name, phone, address
        ))

        await db.commit()
        return cursor.lastrowid
