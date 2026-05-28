import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery

# Токены (на BotHost мы вынесем их в Переменные Окружения / Environment Variables)
import os
BOT_TOKEN = os.getenv("BOT_TOKEN")
# Для CryptoBot используйте официальный API-токен от @CryptoBot (@CryptoPay_bot)
CRYPTO_BOT_TOKEN = os.getenv("CRYPTO_BOT_TOKEN") 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Главное меню (Клавиатура)
def get_main_menu():
    kb = [
        [types.KeyboardButton(text="💎 Купить тариф")],
        [types.KeyboardButton(text="👨‍💻 Тех. поддержка"), types.KeyboardButton(text="⭐ Отзывы")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! В этом боте ты можешь приобрести тарифы.\nВыбери нужный раздел ниже:",
        reply_markup=get_main_menu()
    )

# Кнопки поддержки и отзывов
@dp.message(F.text == "👨‍💻 Тех. поддержка")
async def tech_support(message: types.Message):
    await message.answer("📝 По всем вопросам пишите нашему менеджеру: @Ваш_Логин_Поддержки")

@dp.message(F.text == "⭐ Отзывы")
async def reviews(message: types.Message):
    await message.answer("💬 Почитать отзывы и оставить свой можно в нашем канале: [Ссылка на канал]", parse_mode="Markdown")

# Выбор тарифа и способа оплаты
@dp.message(F.text == "💎 Купить тариф")
async def buy_tariff(message: types.Message):
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌟 Оплатить Звездами (XTR)", callback_data="pay_stars")],
        [InlineKeyboardButton(text="⚡ Оплатить через CryptoBot", callback_data="pay_crypto")]
    ])
    await message.answer("💵 Выберите удобный способ оплаты для **Тарифа VIP (100 XTR / 2$)**:", parse_mode="Markdown", reply_markup=inline_kb)

# --- СПОСОБ 1: Telegram Stars ---
@dp.callback_query(F.data == "pay_stars")
async def process_pay_stars(callback: types.CallbackQuery):
    await callback.answer()
    
    # Генерация инвойса для Telegram Stars. Валюта строго 'XTR'
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="VIP Тариф",
        description="Доступ к закрытым функциям бота",
        payload="vip_tariff_stars",
        provider_token="", # Для звезд это поле ВСЕГДА остается пустым
        currency="XTR",
        prices=[LabeledPrice(label="VIP Тариф", amount=100)] # 100 звезд
    )

# Обязательное подтверждение перед списанием Звезд
@dp.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# Успешная оплата Звездами
@dp.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
    await message.answer("🎉 Оплата Звездами прошла успешно! Ваш VIP-тариф активирован.")

# --- СПОСОБ 2: CryptoBot ---
@dp.callback_query(F.data == "pay_crypto")
async def process_pay_crypto(callback: types.CallbackQuery):
    await callback.answer()
    
    # В реальном проекте используем aiohttp/aiocryptopay для запроса к CryptoPay API.
    # Ниже — упрощенная схема логики генерации счета.
    # Запрос отправляется на https://pay.cryptomus.com/ или @CryptoBot API:
    # Метод createInvoice(asset="USDT", amount="2.00") вернет pay_url.
    
    pay_url = "https://t.me/CryptoBot?start=invoice_TEST" # Здесь будет реальная ссылка из API
    
    crypto_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Перейти к оплате (2 USDT)", url=pay_url)],
        [InlineKeyboardButton(text="✅ Проверить оплату", callback_data="check_crypto")]
    ])
    
    await callback.message.answer("Ссылка на оплату создана! Оплатите счет в CryptoBot и нажмите кнопку проверки.", reply_markup=crypto_kb)

@dp.callback_query(F.data == "check_crypto")
async def check_crypto_payment(callback: types.CallbackQuery):
    # Тут должна быть проверка статуса инвойса через API Криптобота
    # Если статус paid -> выдаем тариф
    await callback.answer("⏳ Платеж проверяется (или демо-режим)", show_alert=True)

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())