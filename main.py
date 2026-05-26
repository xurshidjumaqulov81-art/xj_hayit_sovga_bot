from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
import asyncio
import os

from gifts import GIFTS

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

used_users = set()

@dp.message(CommandStart())
async def start_handler(message: Message):

    if message.from_user.id in used_users:
        await message.answer(
            "❌ Сиз аввал совға танлагансиз."
        )
        return

    text = """
🌙 Ассалому алайкум!

Ҳайит байрами муносабати билан
сиз учун махсус совғалар тайёрладик 🎁

Қуйидаги каталогдан совғани танланг.
"""

    builder = InlineKeyboardBuilder()

    for gift in GIFTS:

        if gift["qty"] > 0:
            builder.button(
                text=f"{gift['name']} ({gift['qty']} та)",
                callback_data=f"gift_{gift['id']}"
            )
        else:
            builder.button(
                text=f"{gift['name']} ❌",
                callback_data="empty"
            )

    builder.adjust(1)

    await message.answer(
        text,
        reply_markup=builder.as_markup()
    )

@dp.callback_query()
async def gift_handler(callback: types.CallbackQuery):

    if callback.data == "empty":
        await callback.answer(
            "Бу совға қолмаган ❌",
            show_alert=True
        )
        return

    gift_id = int(callback.data.split("_")[1])

    selected_gift = None

    for gift in GIFTS:
        if gift["id"] == gift_id:
            selected_gift = gift
            break

    if selected_gift["qty"] <= 0:
        await callback.message.answer(
            "❌ Бу совға қолмаган."
        )
        return

    selected_gift["qty"] -= 1

    used_users.add(callback.from_user.id)

    username = callback.from_user.username

    if username:
        username_text = f"@{username}"
    else:
        username_text = "Username йўқ"

    admin_text = f"""
🎁 ЯНГИ СОВҒА

👤 Фойдаланувчи:
{callback.from_user.full_name}

🎁 Совға:
{selected_gift['name']}

📲 Username:
{username_text}

🆔 Telegram ID:
{callback.from_user.id}
"""

    await bot.send_message(
        ADMIN_ID,
        admin_text
    )

    await callback.message.answer(
        f"""
✅ Табриклаймиз!

Сиз танлаган совға:

🎁 {selected_gift['name']}

Ҳайит байрамингиз муборак бўлсин 🌙
"""
    )

async def main():
    print("BOT ISHLADI")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
