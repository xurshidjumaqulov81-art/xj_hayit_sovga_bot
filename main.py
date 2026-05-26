import asyncio
import os
import re
from aiohttp import web
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    FSInputFile
)

from database import (
    init_db,
    user_has_order,
    xj_id_exists,
    get_gifts,
    get_gift,
    decrease_gift,
    create_order
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "199169309"))
PORT = int(os.getenv("PORT", "10000"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class OrderState(StatesGroup):
    full_name = State()
    xj_id = State()
    gift = State()
    phone = State()
    address = State()
    confirm = State()


def phone_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Телефон рақамни юбориш", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def confirm_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Тасдиқлаш", callback_data="confirm_order"),
                InlineKeyboardButton(text="❌ Бекор қилиш", callback_data="cancel_order")
            ]
        ]
    )


def gifts_keyboard(gifts):
    buttons = []

    for gift_id, name, qty, photo in gifts:
        if qty > 0:
            text = f"🎁 {name} — қолди: {qty} та"
            callback = f"gift_{gift_id}"
        else:
            text = f"❌ {name} — қолмаган"
            callback = "gift_empty"

        buttons.append([InlineKeyboardButton(text=text, callback_data=callback)])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def valid_xj_id(text: str) -> bool:
    return bool(re.fullmatch(r"00\d{5}", text))


def valid_phone(text: str) -> bool:
    clean = text.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    return bool(re.fullmatch(r"(\+998|998|8|9)\d{8,12}", clean))


@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    if await user_has_order(message.from_user.id):
        await message.answer(
            "🎁 Сиз совғани аввал танлаб бўлгансиз.\n\n"
            "🌙 Ҳайит байрамингиз муборак бўлсин!"
        )
        return

    await message.answer(
        "🌙 Ассалому алайкум!\n\n"
        "Ҳайит байрами муносабати билан XJ ҳамкорлари ва мижозлари учун "
        "махсус совғалар тайёрланди 🎁\n\n"
        "Совғани олиш учун маълумотларни тўғри киритинг.\n\n"
        "👤 Илтимос, исм-фамилиянгизни киритинг.\n\n"
        "Намуна:\n"
        "Али Валиев"
    )

    await state.set_state(OrderState.full_name)


@dp.message(OrderState.full_name)
async def get_full_name(message: Message, state: FSMContext):
    full_name = message.text.strip()

    if len(full_name.split()) < 2:
        await message.answer(
            "❌ Илтимос, исм ва фамилияни тўлиқ киритинг.\n\n"
            "Намуна:\n"
            "Али Валиев"
        )
        return

    await state.update_data(full_name=full_name)

    await message.answer(
        "🆔 Энди XJ ID рақамингизни киритинг.\n\n"
        "ID рақам 7 хонали бўлиши керак.\n"
        "Бошида 2 та нол бўлади.\n\n"
        "Намуна:\n"
        "0012345"
    )

    await state.set_state(OrderState.xj_id)


@dp.message(OrderState.xj_id)
async def get_xj_id(message: Message, state: FSMContext):
    xj_id = message.text.strip()

    if not valid_xj_id(xj_id):
        await message.answer(
            "❌ ID рақам нотўғри киритилди.\n\n"
            "Тўғри формат:\n"
            "00xxxxx\n\n"
            "Намуна:\n"
            "0012345"
        )
        return

    if await xj_id_exists(xj_id):
        await message.answer(
            "❌ Бу ID рақам орқали аввал совға олинган.\n\n"
            "Илтимос, тўғри ID рақам киритинг."
        )
        return

    await state.update_data(xj_id=xj_id)

    gifts = await get_gifts()

    await message.answer(
        "🎁 Совғалар каталоги\n\n"
        "Илтимос, қуйидаги совғалардан бирини танланг.\n"
        "Ҳар бир совға ёнида қолган сони кўрсатилган:",
        reply_markup=gifts_keyboard(gifts)
    )

    await state.set_state(OrderState.gift)


@dp.callback_query(OrderState.gift, F.data == "gift_empty")
async def gift_empty(callback: CallbackQuery):
    await callback.answer("❌ Бу совға қолмаган.", show_alert=True)


@dp.callback_query(OrderState.gift, F.data.startswith("gift_"))
async def choose_gift(callback: CallbackQuery, state: FSMContext):
    gift_id = int(callback.data.split("_")[1])
    gift = await get_gift(gift_id)

    if not gift:
        await callback.answer("Совға топилмади.", show_alert=True)
        return

    gift_id, name, qty, photo = gift

    if qty <= 0:
        await callback.answer("❌ Бу совға қолмаган.", show_alert=True)
        return

    await state.update_data(gift_id=gift_id, gift_name=name)

    caption = (
        f"🎁 Сиз танлаган совға:\n\n"
        f"{name}\n\n"
        f"Қолди: {qty} та\n\n"
        f"Энди телефон рақамингизни юборинг.\n\n"
        f"Намуна:\n"
        f"+998901234567"
    )

    try:
        if photo and os.path.exists(photo):
            await callback.message.answer_photo(
                photo=FSInputFile(photo),
                caption=caption,
                reply_markup=phone_keyboard()
            )
        else:
            await callback.message.answer(
                caption,
                reply_markup=phone_keyboard()
            )
    except Exception:
        await callback.message.answer(
            caption,
            reply_markup=phone_keyboard()
        )

    await callback.answer()
    await state.set_state(OrderState.phone)


@dp.message(OrderState.phone)
async def get_phone(message: Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text.strip()

    if not valid_phone(phone):
        await message.answer(
            "❌ Телефон рақам нотўғри киритилди.\n\n"
            "Илтимос, рақамни тўғри киритинг ёки пастдаги тугма орқали юборинг.\n\n"
            "Намуна:\n"
            "+998901234567",
            reply_markup=phone_keyboard()
        )
        return

    await state.update_data(phone=phone)

    await message.answer(
        "📍 Энди совғани етказиб бериш учун манзилингизни киритинг.\n\n"
        "Манзилни тўлиқ ёзинг: шаҳар, туман, кўча, уй.\n\n"
        "Намуна:\n"
        "Тошкент шаҳри, Юнусобод тумани, Амир Темур кўчаси, 25-уй",
        reply_markup=ReplyKeyboardRemove()
    )

    await state.set_state(OrderState.address)


@dp.message(OrderState.address)
async def get_address(message: Message, state: FSMContext):
    address = message.text.strip()

    if len(address) < 10:
        await message.answer(
            "❌ Манзил жуда қисқа киритилди.\n\n"
            "Илтимос, тўлиқ манзилни киритинг.\n\n"
            "Намуна:\n"
            "Тошкент шаҳри, Юнусобод тумани, Амир Темур кўчаси, 25-уй"
        )
        return

    await state.update_data(address=address)
    data = await state.get_data()

    text = (
        "✅ Маълумотларни текширинг:\n\n"
        f"👤 Исм-фамилия:\n{data['full_name']}\n\n"
        f"🆔 ID рақам:\n{data['xj_id']}\n\n"
        f"🎁 Совға:\n{data['gift_name']}\n\n"
        f"📞 Телефон:\n{data['phone']}\n\n"
        f"📍 Манзил:\n{data['address']}\n\n"
        "Ҳаммаси тўғрими?"
    )

    await message.answer(text, reply_markup=confirm_keyboard())
    await state.set_state(OrderState.confirm)


@dp.callback_query(OrderState.confirm, F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(
        "❌ Буюртма бекор қилинди.\n\n"
        "Қайта бошлаш учун /start босинг."
    )
    await callback.answer()


@dp.callback_query(OrderState.confirm, F.data == "confirm_order")
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    if await user_has_order(callback.from_user.id):
        await callback.message.answer(
            "❌ Сиз аввал совға танлагансиз."
        )
        await state.clear()
        return

    data = await state.get_data()
    gift = await get_gift(data["gift_id"])

    if not gift:
        await callback.message.answer("❌ Совға топилмади.")
        await state.clear()
        return

    gift_id, gift_name, qty, photo = gift

    if qty <= 0:
        await callback.message.answer(
            "❌ Афсуски, сиз танлаган совға тугаган.\n\n"
            "Қайта /start босиб бошқа совға танланг."
        )
        await state.clear()
        return

    username = callback.from_user.username
    username_text = f"@{username}" if username else "Username йўқ"

    order_id = await create_order(
        telegram_user_id=callback.from_user.id,
        username=username_text,
        telegram_full_name=callback.from_user.full_name,
        full_name=data["full_name"],
        xj_id=data["xj_id"],
        gift_id=gift_id,
        gift_name=gift_name,
        phone=data["phone"],
        address=data["address"]
    )

    await decrease_gift(gift_id)

    admin_text = (
        f"🎁 #{order_id} ЯНГИ СОВҒА БУЮРТМАСИ\n\n"
        f"👤 Мижоз:\n{data['full_name']}\n\n"
        f"🆔 ID рақам:\n{data['xj_id']}\n\n"
        f"🎁 Танланган совға:\n{gift_name}\n\n"
        f"📞 Телефон:\n{data['phone']}\n\n"
        f"📍 Манзил:\n{data['address']}\n\n"
        f"📲 Telegram:\n{username_text}\n\n"
        f"🆔 Telegram ID:\n{callback.from_user.id}\n\n"
        f"👥 Telegram исми:\n{callback.from_user.full_name}"
    )

    await bot.send_message(ADMIN_ID, admin_text)

    await callback.message.answer(
        "🎉 Табриклаймиз!\n\n"
        "Сизнинг совға буюртмангиз қабул қилинди.\n"
        "Тез орада совғангиз кўрсатилган манзилга етказилади.\n\n"
        f"🎁 Танланган совға:\n{gift_name}\n\n"
        "🌙 Ҳайит байрамингиз муборак бўлсин!"
    )

    await state.clear()
    await callback.answer()


async def health(request):
    return web.Response(text="Bot is running")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()


async def main():
    await init_db()
    await start_web_server()

    print("XJ Hayit Sovga Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
