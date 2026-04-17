import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.familiarbot import database
from src.familiarbot.config import TOKEN
from src.familiarbot.i18n import get_text

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def handle_start(message):
    existing_lang = database.get_user_language(message.from_user.id)
    lang_code = message.from_user.language_code if existing_lang == 'en' else existing_lang
    database.add_user(message.from_user.id, message.from_user.username, lang_code)
    reply = get_text(lang_code, "welcome_message")
    bot.send_message(message.chat.id, reply)

@bot.message_handler(commands=['help'])
def handle_help(message):
    lang = database.get_user_language(message.from_user.id)
    reply = get_text(lang, "helper_message")
    bot.send_message(message.from_user.id, reply)

@bot.message_handler(commands=['me'])
def handle_me_request(message):
    lang = database.get_user_language(message.from_user.id)
    username = database.get_username(message.from_user.id)
    
    if username:
        bot.reply_to(message, get_text(lang, "username_query", username=username))
    else:
        bot.reply_to(message, get_text(lang, "unknown_user"))

@bot.message_handler(commands=['newreminder'])
def handle_newreminder(message):
    lang = database.get_user_language(message.from_user.id)
    text = message.text.replace('/newreminder', '').strip()
    
    if text:
        save_reminder(message, text, lang)
    else:
        msg = bot.reply_to(message, get_text(lang, "ask_reminder"))
        bot.register_next_step_handler(msg, process_reminder_step, lang)

def process_reminder_step(message, lang):
    if message.text.startswith('/'):
        bot.reply_to(message, get_text(lang, "cancel_reminder"))
        return
    text = message.text.strip()
    save_reminder(message, text, lang)

def save_reminder(message, text, lang):
    try:
        user_lang = message.from_user.language_code or 'en'
        database.add_user(message.from_user.id, message.from_user.username, user_lang)
        
        database.add_task(message.from_user.id, text)
        bot.reply_to(message, get_text(lang, "reminder_saved", text=text))
    except Exception as e:
        bot.reply_to(message, get_text(lang, "error_saving"))
        print(f"Error: {e}")

@bot.message_handler(commands=['language', 'lang'])
def handle_language(message):
    lang = database.get_user_language(message.from_user.id)
    text = get_text(lang, "choose_language")
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇺🇦 Українська", callback_data="lang_ua")
    )
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def handle_language_callback(call):
    new_lang = call.data.split('_')[1] 
    telegram_id = call.from_user.id
    
    database.update_language(telegram_id, new_lang)
    
    bot.answer_callback_query(call.id, text="Language changed!")
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=get_text(new_lang, "language_updated")
    )



def run_bot():
    database.setup_database()
    print("Bot is up and running...")
    bot.polling(non_stop=True, interval=0)