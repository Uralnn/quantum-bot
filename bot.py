import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
import requests
import json

# --- НАСТРОЙКИ ---
BOT_TOKEN = '9250666051:AAGJO4fJQOnRNIFK-tNmaTvVeZkG3fgPeKE'
ADMIN_ID = '1192292768'

# Настройки ЮKassa (пока пустые, заполним позже)
YOOKASSA_SHOP_ID = '' 
YOOKASSA_SECRET_KEY = ''

bot = telebot.TeleBot(BOT_TOKEN)

# Временное хранилище для ID клиентов
user_pending_ids = {}

# --- ФУНКЦИЯ ГЕНЕРАЦИИ КЛЮЧА ---
def generate_key(device_id):
    try:
        return str((int(device_id) + 54321) * 3)
    except ValueError:
        return None

# --- ОБРАБОТЧИК КОМАНДЫ /start ---
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(
        message.chat.id,
        "👋 Привет! Я бот для выдачи лицензионных ключей.\n\n"
        "Отправьте мне **ID вашего оборудования** (цифры, которые вы видите на экране программы):",
        parse_mode='Markdown'
    )

# --- ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ (ID) ---
@bot.message_handler(content_types=['text'])
def handle_id(message):
    text = message.text.strip()
    
    if text.isdigit():
        device_id = text
        user_pending_ids[message.from_user.id] = device_id
        
        # Создаем кнопки выбора оплаты
        markup = InlineKeyboardMarkup()
        btn_stars = InlineKeyboardButton("⭐ Оплатить звёздами", callback_data="pay_stars")
        btn_card = InlineKeyboardButton("💳 Оплатить картой", callback_data="pay_card")
        markup.add(btn_stars, btn_card)
        
        bot.send_message(
            message.chat.id,
            f"✅ ID `{device_id}` принят.\n"
            f"Выберите удобный способ оплаты:",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    else:
        bot.send_message(
            message.chat.id, 
            "⚠️ Пожалуйста, отправьте только цифры (ID оборудования)."
        )

# --- ОБРАБОТЧИК КНОПОК (ЗВЕЗДЫ ИЛИ КАРТА) ---
@bot.callback_query_handler(func=lambda call: call.data in ['pay_stars', 'pay_card'])
def handle_payment_choice(call):
    user_id = call.from_user.id
    
    if call.data == 'pay_stars':
        # Логика оплаты Stars
        bot.answer_callback_query(call.id, "Выбрана оплата звёздами")
        bot.send_invoice(
            chat_id=user_id,
            title="Лицензия Quantum Terminal",
            description="Активация Pro-версии калькулятора",
            invoice_payload="license_payload",
            provider_token="",  # Для Stars это поле должно быть пустым
            currency="XTR",     # XTR - это код валюты Telegram Stars
            prices=[LabeledPrice(label="Лицензия", amount=100)] # 100 Stars (можете изменить)
        )
    
    elif call.data == 'pay_card':
        # Логика оплаты картой (ЮKassa)
        if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
            # Если ключи ЮKassa еще не вписаны
            bot.answer_callback_query(call.id, "Оплата картой временно недоступна. Используйте звёзды.", show_alert=True)
        else:
            # Здесь будет код создания платежа в ЮKassa (добавим позже)
            bot.answer_callback_query(call.id, "Перенаправление на оплату картой...")
            # Временная заглушка
            bot.send_message(user_id, "Функция оплаты картой находится в разработке.")

# --- ОБРАБОТЧИК ПРЕДВАРИТЕЛЬНОЙ ПРОВЕРКИ (ДЛЯ STARS) ---
@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# --- ОБРАБОТЧИК УСПЕШНОЙ ОПЛАТЫ STARS ---
@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    user_id = message.from_user.id
    
    if user_id in user_pending_ids:
        device_id = user_pending_ids[user_id]
        key = generate_key(device_id)
        
        if key:
            bot.send_message(
                user_id,
                f"✅ Оплата прошла! Ваш ключ активации для ID `{device_id}`:\n\n"
                f"👉 **{key}**\n\n"
                f"Введите его в программе.",
                parse_mode='Markdown'
            )
            
            # Уведомление админу
            bot.send_message(
                ADMIN_ID,
                f"💰 Оплата Stars получена!\n"
                f"ID: {device_id}\n"
                f"Ключ: {key}\n"
                f"Сумма: {message.successful_payment.total_amount} Stars"
            )
            
            del user_pending_ids[user_id]
        else:
            bot.send_message(user_id, "❌ Ошибка генерации ключа. Свяжитесь с поддержкой.")
    else:
        bot.send_message(user_id, "❌ Не удалось найти ваш ID. Отправьте его заново.")

# --- ЗАПУСК БОТА ---
if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()


