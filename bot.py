import os
import time
from flask import Flask, request, abort, jsonify

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice

# --- НАСТРОЙКИ ---
# На Render лучше задать эти значения в разделе Environment Variables
BOT_TOKEN = os.environ.get('BOT_TOKEN', '9250666051:AAHbnlh8pf6aZBArzFDeNvfmNTS90n6IGQc')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 1192292768))  # Замените на ваш числовой ID

YOOKASSA_SHOP_ID = os.environ.get('YOOKASSA_SHOP_ID', '')
YOOKASSA_SECRET_KEY = os.environ.get('YOOKASSA_SECRET_KEY', '')

# Render автоматически создает переменную RENDER_EXTERNAL_URL (например, https://onrender.com)
RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL')

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.after_request
def add_cors_headers(response):        
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response

user_pending_ids = {}

# --- ФУНКЦИЯ ГЕНЕРАЦИИ КЛЮЧА ---
def generate_key(device_id):
    try:
        return str((int(device_id) + 54321) * 3)
    except ValueError:
        return None

# --- ССЫЛКА НА УСТАНОВЩИК ---
PC_DOWNLOAD_URL = "https://github.com/Uralnn/quantum-bot/releases/download/v1.0/QuantumTerminal_Setup.exe"

# --- ОБРАБОТЧИКИ СООБЩЕНИЙ ---
@bot.message_handler(commands=['start'])
def start_message(message):
    markup = InlineKeyboardMarkup(row_width=1)
    btn_pc = InlineKeyboardButton("💻 Скачать для ПК (Windows)", url=PC_DOWNLOAD_URL)
    markup.add(btn_pc)

    bot.send_message(
        message.chat.id,
        "👋 Привет! Я бот для установки и активации калькулятора.\n\n"
        "1. Нажмите кнопку ниже, чтобы скачать установочный файл для компьютера.\n"
        "2. Установите и запустите программу.\n"
        "3. Отправьте мне **ID вашего оборудования** (цифры с экрана) для получения ключа:",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.message_handler(content_types=['text'])
def handle_id(message):
    text = message.text.strip()
    
    if text.isdigit():
        device_id = text
        user_pending_ids[message.from_user.id] = device_id
        
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

@bot.callback_query_handler(func=lambda call: call.data in ['pay_stars', 'pay_card'])
def handle_payment_choice(call):
    user_id = call.from_user.id
    
    if call.data == 'pay_stars':
        bot.answer_callback_query(call.id, "Выбрана оплата звёздами")
        bot.send_invoice(
            chat_id=user_id,
            title="Лицензия Quantum Terminal",
            description="Активация Pro-версии калькулятора",
            invoice_payload="license_payload",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Лицензия", amount=235)]
        )
    
    elif call.data == 'pay_card':
        if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
            bot.answer_callback_query(call.id, "Оплата картой временно недоступна. Используйте звёзды.", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "Перенаправление на оплату картой...")
            bot.send_message(user_id, "Функция оплаты картой находится в разработке.")

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

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

# --- ВЕБХУКИ И ПРОВЕРКА ЛИЦЕНЗИИ ---
@app.route('/')
def home():
    return "Bot is running via Webhooks!", 200

@app.route('/validate', methods=['POST', 'OPTIONS'])
def validate_license():
    # Разрешаем запросы с любых устройств и локальных файлов (CORS)
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response

    data = request.get_json(silent=True) or {}
    device_id = str(data.get('id', '')).strip()
    user_key = str(data.get('key', '')).strip()

    expected_key = generate_key(device_id)
    is_valid = (expected_key is not None and user_key == expected_key)

    response = jsonify({'activated': is_valid})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        abort(403)

# Настройка вебхука при запуске
if RENDER_URL:
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{RENDER_URL}/{BOT_TOKEN}")
    print(f"Вебхук успешно установлен на {RENDER_URL}")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
