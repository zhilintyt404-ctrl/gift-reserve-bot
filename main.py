import sqlite3
from aiogram import Bot, Dispatcher, executor, types

TOKEN = "8514112185:AAHKGUgvQVyEjRc1zW9o4ROd9H24k9BddNw"
ADMIN_ID = 1020075016  # твой Telegram ID

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

conn = sqlite3.connect("gifts.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS gifts (
    message_id INTEGER PRIMARY KEY,
    owner_id INTEGER,
    reserved_by INTEGER,
    text TEXT
)
""")
conn.commit()

def get_gift(message_id):
    cursor.execute("SELECT * FROM gifts WHERE message_id=?", (message_id,))
    return cursor.fetchone()

def save_gift(message_id, owner_id, text):
    cursor.execute(
        "INSERT OR IGNORE INTO gifts VALUES (?, ?, ?, ?)",
        (message_id, owner_id, None, text)
    )
    conn.commit()

def reserve_gift(message_id, user_id):
    cursor.execute(
        "UPDATE gifts SET reserved_by=? WHERE message_id=?",
        (user_id, message_id)
    )
    conn.commit()

def cancel_reserve(message_id):
    cursor.execute(
        "UPDATE gifts SET reserved_by=NULL WHERE message_id=?",
        (message_id,)
    )
    conn.commit()

@dp.message_handler(lambda m: m.text and "http" in m.text)
async def handle_link(message: types.Message):
    save_gift(message.message_id, message.from_user.id, message.text)

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "🎁 Забронировать",
        callback_data=f"reserve:{message.message_id}"
    ))

    await message.reply("🎄 Подарок:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("reserve"))
async def reserve(call: types.CallbackQuery):
    msg_id = int(call.data.split(":")[1])
    gift = get_gift(msg_id)

    if not gift:
        await call.answer("Подарок не найден", show_alert=True)
        return

    _, owner_id, reserved_by, text = gift

    if call.from_user.id == owner_id:
        await call.answer("Нельзя бронировать свой подарок", show_alert=True)
        return

    if reserved_by:
        await call.answer("Уже забронировано", show_alert=True)
        return

    reserve_gift(msg_id, call.from_user.id)

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "🔄 Отменить бронь",
        callback_data=f"cancel:{msg_id}"
    ))

    await call.message.edit_text(
        call.message.text + "\n\n🎁 Забронировано",
        reply_markup=kb
    )

    await bot.send_message(
        ADMIN_ID,
        f"🎁 Забронировано\n\n{text}"
    )

    await call.answer("Подарок забронирован")

@dp.callback_query_handler(lambda c: c.data.startswith("cancel"))
async def cancel(call: types.CallbackQuery):
    msg_id = int(call.data.split(":")[1])
    gift = get_gift(msg_id)

    if not gift:
        await call.answer("Брони нет", show_alert=True)
        return

    _, _, reserved_by, _ = gift

    if call.from_user.id not in (reserved_by, ADMIN_ID):
        await call.answer("Ты не можешь отменить бронь", show_alert=True)
        return

    cancel_reserve(msg_id)

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "🎁 Забронировать",
        callback_data=f"reserve:{msg_id}"
    ))

    await call.message.edit_text(
        call.message.text.replace("\n\n🎁 Забронировано", ""),
        reply_markup=kb
    )

    await call.answer("Бронь отменена")

executor.start_polling(dp)
