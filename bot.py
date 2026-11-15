import telebot

# --- НАСТРОЙКИ ---
BOT_TOKEN = '9250666051:AAHwJ_vugRpbb3YRujzPvZSqC0Wf9lyUj98'
ADMIN_ID = '1192292768' 

bot = telebot.TeleBot(BOT_TOKEN)

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
    
    # Проверяем, что клиент прислал именно цифры
    if text.isdigit():
        device_id = text
        key = generate_key(device_id)
        
        if key:
            # 1. Отправляем ключ клиенту
            bot.send_message(
                message.chat.id,
                f"✅ Отлично! Для ID `{device_id}` ваш ключ активации:\n\n"
                f"👉 **{key}**\n\n"
                f"Введите его в программе для активации.",
                parse_mode='Markdown'
            )
            
            # 2. Отправляем уведомление вам (админу)
            try:
                bot.send_message(
                    ADMIN_ID,
                    f"🔑 Выдан новый ключ!\nID: {device_id}\nКлюч: {key}"
                )
            except Exception as e:
                print(f"Не удалось отправить уведомление админу: {e}")
                
        else:
            bot.send_message(message.chat.id, "❌ Ошибка при генерации ключа. Проверьте ID.")
    else:
        bot.send_message(
            message.chat.id, 
            "⚠️ Пожалуйста, отправьте только цифры (ID оборудования)."
        )

# --- ЗАПУСК БОТА ---
if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()
