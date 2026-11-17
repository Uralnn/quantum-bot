import os
import time
from flask import Flask, request, abort, jsonify

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice

# --- НАСТРОЙКИ ТОКЕНОВ И СЕРВЕРА ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

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

# --- НАСТРОЙКИ ССЫЛОК И ЦЕН ---
PC_DOWNLOAD_URL = "https://github.com" + "quantum-bot/releases/download/v1.0/" + "QuantumTerminal_Setup.exe"
SUPPORT_LINK = "@Dmitryshir"  # Можете заменить на @ваш_канал или https://t.me
PRICE_RUB = 260
PRICE_STARS = 235

# --- ОБРАБОТЧИКИ СООБЩЕНИЙ ---
@bot.message_handler(commands=['start'])
def start_message(message):
    markup = InlineKeyboardMarkup(row_width=1)
    btn_pc = InlineKeyboardButton("💻 Скачать для ПК (Windows)", url=PC_DOWNLOAD_URL)
    markup.add(btn_pc)

    bot.send_message(
        message.chat.id,
        "👋 Привет! Я официальный бот активации калькулятора.\n\n"
        "📦 **Товар:** Лицензионный ключ активации (бессрочный доступ).\n"
        f"💰 **Стоимость:** {PRICE_RUB} ₽ (или {PRICE_STARS} Telegram Stars).\n\n"
        "**Как получить доступ:**\n"
        "1. Скачайте и установите программу по кнопке ниже.\n"
        "2. Откройте калькулятор и скопируйте ваш цифровой **ID оборудования**.\n"
        "3. Отправьте цифры ID в этот чат и оплатите лицензию.\n\n"
        f"🆘 **Техподдержка:** {SUPPORT_LINK}",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.message_handler(content_types=['text'])
def handle_id(message):
    text = message.text.strip()
    if text.isdigit():
        user_pending_ids[message.from_user.id] = text
        markup = InlineKeyboardMarkup(row_width=1)
        btn_card = InlineKeyboardButton(f"💳 Оплатить картой / СБП ({PRICE_RUB} ₽)", callback_data="pay_card")
        btn_stars = InlineKeyboardButton(f"⭐ Оплатить звёздами ({PRICE_STARS} Stars)", callback_data="pay_stars")
        markup.add(btn_card, btn_stars)

        bot.send_message(
            message.chat.id,
            f"✅ **ID оборудования принят:** `{text}`\n"
            f"📦 **Товар:** Лицензионный ключ активации\n"
            f"💰 **Итого к оплате:** {PRICE_RUB} ₽\n\n"
            "Выберите удобный способ оплаты:",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    else:
        bot.send_message(
            message.chat.id,
            f"⚠️ Пожалуйста, отправьте только цифры (ID оборудования).\n"
            f"Если возникли вопросы, напишите в поддержку: {SUPPORT_LINK}"
        )

@bot.callback_query_handler(func=lambda call: call.data in ['pay_card', 'pay_stars'])
def handle_payment_choice(call):
    user_id = call.from_user.id
    device_id = user_pending_ids.get(user_id)

    if not device_id:
        bot.answer_callback_query(call.id, "Сначала отправьте ID оборудования!")
        return

    if call.data == 'pay_stars':
        bot.answer_callback_query(call.id, "Выбрана оплата звёздами")
        bot.send_invoice(
            chat_id=user_id,
            title="Лицензионный ключ активации",
            description=f"Активация полной версии для ID: {device_id}",
            invoice_payload="license_payload",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Лицензия", amount=PRICE_STARS)]
        )

    elif call.data == 'pay_card':
        bot.answer_callback_query(call.id, "Формируем счёт ЮKassa...")
        bot.send_message(
            chat_id=user_id,
            text=(
                f"🧾 **Счёт на оплату через ЮKassa**\n\n"
                f"📦 **Товар:** Лицензионный ключ активации\n"
                f"🔑 **ID оборудования:** `{device_id}`\n"
                f"💳 **Сумма к оплате:** {PRICE_RUB} ₽\n\n"
                f"⏳ *Оплата банковской картой и по СБП находится на финальной стадии подключения. "
                f"Для оплаты или по вопросам работы сервиса обращайтесь в поддержку: {SUPPORT_LINK}*"
            ),
            parse_mode='Markdown'
        )
# --- ПОДТВЕРЖДЕНИЕ ОПЛАТЫ И ВЫДАЧА КЛЮЧА ---
@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(
        pre_checkout_query.id,
        ok=True
    )

@bot.message_handler(content_types=['successful_payment'])
def process_successful_payment(message):
    user_id = message.from_user.id
    device_id = user_pending_ids.get(user_id)

    if device_id:
        key = generate_key(device_id)
        bot.send_message(
            message.chat.id,
            f"🎉 **Оплата прошла успешно!**\n\n"
            f"🔑 **Ваш ключ активации:** `{key}`\n"
            f"Введите его в окно программы.",
            parse_mode='Markdown'
        )
        del user_pending_ids[user_id]
    else:
        bot.send_message(
            message.chat.id,
            f"⚠️ Оплата получена, но ID не найден.\n"
            f"Напишите в поддержку: {SUPPORT_LINK}"
        )

# --- ВЕБХУКИ И ПРОВЕРКА ЛИЦЕНЗИИ ---
@app.route('/')
def home():
    return "Bot is running via Webhooks!", 200

@app.route('/validate', methods=['POST', 'OPTIONS'])
def validate_license():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    data = request.get_json(silent=True) or {}
    device_id = str(data.get('id', '')).strip()
    user_key = str(data.get('key', '')).strip()

    expected_key = generate_key(device_id)
    is_valid = (
        expected_key is not None
        and user_key == expected_key
    )

    return jsonify({'activated': is_valid}), 200

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        abort(403)

if __name__ == '__main__':
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

