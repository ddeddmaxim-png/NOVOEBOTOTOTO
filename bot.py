import asyncio
import logging
import os
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery

# =====================================================================
# ⚙️ НАСТРОЙКИ (КОНФИГ)
# =====================================================================
# Токены берутся из переменных окружения вашего хостинга (BotHost)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CRYPTO_BOT_TOKEN = os.getenv("CRYPTO_BOT_TOKEN")

# ⚠️ ВПИШИТЕ СЮДА ВАШ TELEGRAM ID (Узнать можно у бота @userinfobot)
# Обязательно замените 123456789 на ваши цифры, иначе админка не откроется!
ADMIN_ID = 123456789  

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# =====================================================================
# 📦 БАЗА ДАННЫХ (SQLite)
# =====================================================================
def init_db():
    conn = sqlite3.connect("tariffs.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tariffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price_stars INTEGER NOT NULL,
            price_crypto REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# Инициализируем базу данных при запуске
init_db()

# =====================================================================
# 🔔 СИСТЕМА УВЕДОМЛЕНИЙ ДЛЯ АДМИНИСТРАТОРА
# =====================================================================
async def log_to_admin(message_text: str):
    """Отправляет безопасное HTML-уведомление админу в личные сообщения"""
    try:
        await bot.send_message(ADMIN_ID, f"🔔 <b>LOG:</b>\n{message_text}", parse_mode="HTML")
    except Exception as e:
        logging.error(f"Failed to send log to admin: {e}")

# =====================================================================
# 🎭 СОСТОЯНИЯ ДЛЯ АДМИН-ПАНЕЛИ (FSM)
# =====================================================================
class AdminStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_stars = State()
    waiting_for_crypto = State()

# =====================================================================
# ⌨️ КЛАВИАТУРЫ
# =====================================================================
def get_main_menu(user_id: int):
    kb = [
        [types.KeyboardButton(text="💎 Buy Tariff")],
        [types.KeyboardButton(text="👨‍💻 Support"), types.KeyboardButton(text="⭐ Reviews")]
    ]
    # Если боту пишет админ, добавляем кнопку панели управления
    if user_id == ADMIN_ID:
        kb.append([types.KeyboardButton(text="⚙️ Admin Panel")])
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# =====================================================================
# 👤 ПОЛЬЗОВАТЕЛЬСКАЯ ЧАСТЬ (ИНТЕРФЕЙС НА АНГЛИЙСКОМ)
# =====================================================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    # Логируем вход пользователя
    await log_to_admin(f"👤 User <b>@{user.username}</b> (ID: {user.id}) started the bot.")
    
    await message.answer(
        "👋 Welcome! In this bot you can purchase our premium tariffs.\nSelect a section below:",
        reply_markup=get_main_menu(user.id)
    )

@dp.message(F.text == "👨‍💻 Support")
async def tech_support(message: types.Message):
    # Логируем нажатие кнопки поддержки
    await log_to_admin(f"❓ User <b>@{message.from_user.username}</b> clicked Support.")
    await message.answer("📝 For any questions, please contact our manager: @Your_Support_Username")

@dp.message(F.text == "⭐ Reviews")
async def reviews(message: types.Message):
    # Логируем просмотр отзывов
    await log_to_admin(f"📝 User <b>@{message.from_user.username}</b> opened Reviews.")
    await message.answer("💬 Read reviews or leave your own in our channel: [Link to Channel]", parse_mode="Markdown")

@dp.message(F.text == "💎 Buy Tariff")
async def buy_tariff(message: types.Message):
    # Логируем открытие меню тарифов
    await log_to_admin(f"🛒 User <b>@{message.from_user.username}</b> is browsing tariffs.")
    
    conn = sqlite3.connect("tariffs.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tariffs")
    tariffs = cursor.fetchall()
    conn.close()

    if not tariffs:
        await message.answer("😔 Sorry, there are no active tariffs available at the moment.")
        return

    inline_kb = []
    for tariff in tariffs:
        t_id, name, stars, crypto = tariff
        inline_kb.append([InlineKeyboardButton(text=f"{name} (${crypto} / {stars} 🌟)", callback_data=f"select_{t_id}")])
    
    await message.answer("💵 Select a tariff you want to purchase:", reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_kb))

@dp.callback_query(F.data.startswith("select_"))
async def select_payment_method(callback: types.CallbackQuery):
    await callback.answer()
    tariff_id = int(callback.data.split("_")[1])
    
    # Логируем выбор конкретного тарифа
    await log_to_admin(f"📍 User <b>@{callback.from_user.username}</b> selected tariff ID: {tariff_id}")
    
    conn = sqlite3.connect("tariffs.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tariffs WHERE id = ?", (tariff_id,))
    tariff = cursor.fetchone()
    conn.close()

    if not tariff:
        await callback.message.answer("Tariff not found.")
        return

    t_id, name, stars, crypto = tariff
    
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🌟 Pay with Telegram Stars ({stars} XTR)", callback_data=f"stars_{t_id}")],
        [InlineKeyboardButton(text=f"⚡ Pay with CryptoBot (${crypto})", callback_data=f"crypto_{t_id}")]
    ])
    await callback.message.edit_text(f"📊 You selected: <b>{name}</b>\nChoose your payment method:", parse_mode="HTML", reply_markup=inline_kb)

# --- ОПЛАТА ЗВЕЗДАМИ (TELEGRAM STARS) ---
@dp.callback_query(F.data.startswith("stars_"))
async def process_pay_stars(callback: types.CallbackQuery):
    await callback.answer()
    tariff_id = int(callback.data.split("_")[1])
    
    # Логируем попытку оплаты звездами
    await log_to_admin(f"💳 User <b>@{callback.from_user.username}</b> requested Stars invoice for tariff ID: {tariff_id}")
    
    conn = sqlite3.connect("tariffs.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tariffs WHERE id = ?", (tariff_id,))
    tariff = cursor.fetchone()
    conn.close()

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"Tariff: {tariff[1]}",
        description="Access to premium bot features",
        payload=f"pay_stars_{tariff_id}",
        provider_token="", 
        currency="XTR",
        prices=[LabeledPrice(label=tariff[1], amount=int(tariff[2]))]
    )

@dp.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
    amount = message.successful_payment.total_amount
    # Логируем успешную покупку звезд
    await log_to_admin(f"✅ <b>SUCCESS!</b> User <b>@{message.from_user.username}</b> successfully paid <b>{amount} Stars</b>!")
    await message.answer("🎉 Payment via Telegram Stars successful! Your tariff has been activated.")

# --- ОПЛАТА ЧЕРЕЗ CRYPTOBOT ---
@dp.callback_query(F.data.startswith("crypto_"))
async def process_pay_crypto(callback: types.CallbackQuery):
    await callback.answer()
    tariff_id = int(callback.data.split("_")[1])
    
    # Логируем попытку оплаты через Криптобота
    await log_to_admin(f"⚡ User <b>@{callback.from_user.username}</b> requested CryptoBot invoice for tariff ID: {tariff_id}")
    
    conn = sqlite3.connect("tariffs.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tariffs WHERE id = ?", (tariff_id,))
    tariff = cursor.fetchone()
    conn.close()

    # Демо-ссылка. В продакшене здесь делается запрос к API CryptoBot для получения ссылки
    pay_url = "https://t.me/CryptoBot?start=invoice_DEMO" 
    
    crypto_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💸 Pay ${tariff[3]} via CryptoBot", url=pay_url)],
        [InlineKeyboardButton(text="✅ Check Payment", callback_data=f"check_{tariff_id}")]
    ])
    await callback.message.answer("Invoice link created! Pay via CryptoBot and click the check button below.", reply_markup=crypto_kb)

@dp.callback_query(F.data.startswith("check_"))
async def check_crypto_payment(callback: types.CallbackQuery):
    # Логируем проверку оплаты пользователем
    await log_to_admin(f"🔍 User <b>@{callback.from_user.username}</b> clicked 'Check Payment' (ID: {callback.data})")
    await callback.answer("⏳ Checking payment status (Demo Mode)...", show_alert=True)


# =====================================================================
# ⚙️ АДМИН-ПАНЕЛЬ (УПРАВЛЕНИЕ ТАРИФАМИ)
# =====================================================================

@dp.message(F.text == "⚙️ Admin Panel")
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID: 
        return
    
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add New Tariff", callback_data="admin_add")],
        [InlineKeyboardButton(text="❌ Delete Tariff", callback_data="admin_delete_list")]
    ])
    await message.answer("🎛 Welcome to the Admin Panel. Manage your tariffs here:", reply_markup=admin_kb)

# --- ДОБАВЛЕНИЕ ТАРИФА ---
@dp.callback_query(F.data == "admin_add")
async def admin_add_tariff(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await callback.answer()
    await callback.message.answer("📝 Enter the <b>Name</b> of the new tariff (e.g., VIP Monthly):", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_name)

@dp.message(AdminStates.waiting_for_name)
async def admin_name_received(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("🌟 Enter the price in <b>Telegram Stars</b> (integer number, e.g., 150):", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_stars)

@dp.message(AdminStates.waiting_for_stars)
async def admin_stars_received(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Please enter a valid integer number:")
        return
    await state.update_data(stars=int(message.text))
    await message.answer("⚡ Enter the price in <b>USD/USDT</b> for CryptoBot (e.g., 4.99):", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_crypto)

@dp.message(AdminStates.waiting_for_crypto)
async def admin_crypto_received(message: types.Message, state: FSMContext):
    try:
        crypto_price = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("❌ Please enter a valid price (e.g., 5.00 or 4.99):")
        return
    
    user_data = await state.get_data()
    
    # Сохраняем новый тариф в БД
    conn = sqlite3.connect("tariffs.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tariffs (name, price_stars, price_crypto) VALUES (?, ?, ?)",
        (user_data['name'], user_data['stars'], crypto_price)
    )
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer(f"✅ Tariff <b>{user_data['name']}</b> successfully added!", parse_mode="HTML", reply_markup=get_main_menu(message.from_user.id))

# --- УДАЛЕНИЕ ТАРИФА ---
@dp.callback_query(F.data == "admin_delete_list")
async def admin_delete_list(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    await callback.answer()
    
    conn = sqlite3.connect("tariffs.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM tariffs")
    tariffs = cursor.fetchall()
    conn.close()

    if not tariffs:
        await callback.message.answer("There are no tariffs to delete.")
        return

    delete_kb = []
    for tariff in tariffs:
        t_id, name = tariff
        delete_kb.append([InlineKeyboardButton(text=f"🗑 Delete {name}", callback_data=f"del_{t_id}")])
    
    await callback.message.answer("Select a tariff you want to remove permanently:", reply_markup=InlineKeyboardMarkup(inline_keyboard=delete_kb))

@dp.callback_query(F.data.startswith("del_"))
async def admin_delete_execute(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    tariff_id = int(callback.data.split("_")[1])
    
    conn = sqlite3.connect("tariffs.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tariffs WHERE id = ?", (tariff_id,))
    conn.commit()
    conn.close()
    
    await callback.answer("Tariff deleted successfully!", show_alert=True)
    await callback.message.edit_text("✅ Tariff has been deleted from the database.")


# =====================================================================
# 🚀 ЗАПУСК БОТА
# =====================================================================
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())