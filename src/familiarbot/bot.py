import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from src.familiarbot import database
from src.familiarbot.config import TELEGRAM_KEY, GEMINI_KEY
from src.familiarbot.i18n import get_text
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
from timezonefinder import TimezoneFinder
from google import genai
from google.genai import types

bot = telebot.TeleBot(TELEGRAM_KEY)
user_states = {}
tf = TimezoneFinder()
client = genai.Client(api_key=GEMINI_KEY)

@bot.message_handler(commands=['start'])
def handle_start(message):
    existing_lang = database.get_user_language(message.from_user.id)
    lang_code = message.from_user.language_code if existing_lang == 'en' else existing_lang
    database.add_user(message.from_user.id, message.from_user.username, lang_code)
    
    reply = get_text(lang_code, "welcome_message")
    bot.send_message(message.chat.id, reply)

    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    location_btn = KeyboardButton(text=get_text(lang_code, "btn_share_location"), request_location=True)
    manual_btn = KeyboardButton(text=get_text(lang_code, "btn_set_manually"))
    markup.add(location_btn, manual_btn)

    msg = bot.send_message(message.chat.id, get_text(lang_code, "ask_timezone_setup"), reply_markup=markup)
    bot.register_next_step_handler(msg, process_timezone_setup, lang_code)


def process_timezone_setup(message, lang):
    if message.location:
        lat = message.location.latitude
        lon = message.location.longitude
        user_timezone = tf.timezone_at(lng=lon, lat=lat)
        if user_timezone:
            database.update_timezone(message.from_user.id, user_timezone)
            bot.send_message(message.chat.id, get_text(lang, "timezone_set_success", timezone=user_timezone), reply_markup=ReplyKeyboardRemove())
        else:
            bot.send_message(message.chat.id, get_text(lang, "timezone_fail"), reply_markup=ReplyKeyboardRemove())
    elif message.text == get_text(lang, "btn_set_manually"):
        remove_msg = bot.send_message(message.chat.id, get_text(lang, "loading_timezones"), reply_markup=ReplyKeyboardRemove())
        bot.delete_message(message.chat.id, remove_msg.message_id)

        timezones = [
            "Pacific/Midway", "Pacific/Honolulu", "America/Anchorage", "America/Los_Angeles",
            "America/Denver", "America/Chicago", "America/New_York", "America/Caracas",
            "America/Halifax", "America/St_Johns", "America/Sao_Paulo", "Atlantic/South_Georgia",
            "Europe/London", "Europe/Paris", "Europe/Athens", "Europe/Moscow",
            "Asia/Dubai", "Asia/Karachi", "Asia/Dhaka", "Asia/Bangkok",
            "Asia/Singapore", "Asia/Tokyo", "Australia/Sydney", "Pacific/Auckland"
        ]
        
        markup = InlineKeyboardMarkup()
        for i in range(0, len(timezones), 2):
            row = []
            row.append(InlineKeyboardButton(timezones[i].split('/')[-1].replace('_', ' '), callback_data=f"tz_{timezones[i]}"))
            if i + 1 < len(timezones):
                row.append(InlineKeyboardButton(timezones[i+1].split('/')[-1].replace('_', ' '), callback_data=f"tz_{timezones[i+1]}"))
            markup.row(*row)

        bot.send_message(message.chat.id, get_text(lang, "ask_timezone_selection"), reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('tz_'))
def handle_timezone_callback(call):
    selected_tz = call.data.replace('tz_', '')
    telegram_id = call.from_user.id
    lang = database.get_user_language(telegram_id)
    
    database.update_timezone(telegram_id, selected_tz)
    
    bot.answer_callback_query(call.id, text=get_text(lang, "timezone_set_success", timezone=selected_tz))
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=get_text(lang, "timezone_set_success", timezone=selected_tz)
    )

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
    
    user_states[message.from_user.id] = {}
    
    if text:
        user_states[message.from_user.id]['title'] = text
        msg = bot.reply_to(message, get_text(lang, "ask_notes"))
        bot.register_next_step_handler(msg, process_notes_step, lang)
    else:
        msg = bot.reply_to(message, get_text(lang, "ask_title"))
        bot.register_next_step_handler(msg, process_title_step, lang)

def process_title_step(message, lang):
    if message.text.startswith('/'):
        bot.reply_to(message, get_text(lang, "cancel_reminder"))
        return
    user_states[message.from_user.id]['title'] = message.text.strip()
    msg = bot.reply_to(message, get_text(lang, "ask_notes"))
    bot.register_next_step_handler(msg, process_notes_step, lang)

def process_notes_step(message, lang):
    if message.text.startswith('/'):
        bot.reply_to(message, get_text(lang, "cancel_reminder"))
        return
    user_states[message.from_user.id]['notes'] = message.text.strip()
    
    calendar, step = DetailedTelegramCalendar().build()
    bot.send_message(message.chat.id, get_text(lang, f"select_{step}"), reply_markup=calendar)

@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def calendar_callback(call):
    lang = database.get_user_language(call.from_user.id)
    result, key, step = DetailedTelegramCalendar().process(call.data)
    
    if not result and key:
        bot.edit_message_text(get_text(lang, f"select_{step}"),
                              call.message.chat.id,
                              call.message.message_id,
                              reply_markup=key)
    elif result:
        bot.edit_message_text(get_text(lang, "date_selected", date=result),
                              call.message.chat.id,
                              call.message.message_id)
        user_states[call.from_user.id]['date'] = result
        msg = bot.send_message(call.message.chat.id, get_text(lang, "ask_time"))
        bot.register_next_step_handler(msg, process_time_step, lang)

def process_time_step(message, lang):
    if message.text.startswith('/'):
        bot.reply_to(message, get_text(lang, "cancel_reminder"))
        return
    try:
        time_obj = datetime.datetime.strptime(message.text.strip(), '%H:%M').time()
        user_states[message.from_user.id]['time'] = time_obj
        msg = bot.reply_to(message, get_text(lang, "ask_offset"))
        bot.register_next_step_handler(msg, process_offset_step, lang)
    except ValueError:
        msg = bot.reply_to(message, get_text(lang, "invalid_time"))
        bot.register_next_step_handler(msg, process_time_step, lang)

def process_offset_step(message, lang):
    if message.text.startswith('/'):
        bot.reply_to(message, get_text(lang, "cancel_reminder"))
        return
    try:
        offset_hours = float(message.text.strip())
        user_id = message.from_user.id
        state = user_states.get(user_id, {})
        due_date = datetime.datetime.combine(state['date'], state['time'])
        remind_at = due_date - datetime.timedelta(hours=offset_hours)

        database.add_task(user_id, state['title'], state['notes'], due_date, offset_hours, remind_at)
        bot.reply_to(message, get_text(lang, "reminder_saved", text=state['title']))

        if user_id in user_states:
            del user_states[user_id]
    except ValueError:
        msg = bot.reply_to(message, get_text(lang, "invalid_offset"))
        bot.register_next_step_handler(msg, process_offset_step, lang)
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
    bot.answer_callback_query(call.id, text=get_text(new_lang, "language_changed_popup"))
    bot.edit_message_text(chat_id=call.message.chat.id,message_id=call.message.message_id,text=get_text(new_lang, "language_updated"))

def get_ai_reminder_text(username, title, notes, due_date, lang):

    system_prompt = f"You are a helpful personal familiar. Your master, {username}, asked you to remind them of a task. Write a short, creative, and personalized reminder message. You MUST write the response in the language corresponding to this ISO code: {lang}. Do not use any markdown formatting like bolding or italics."
    user_prompt = f"Task Title: {title}\nDue Date: {due_date}\nTask Notes: {notes}"
    
    try:
        response = client.models.generate_content(model='gemini-2.5-flash-lite', config=types.GenerateContentConfig(system_instruction=system_prompt), contents=user_prompt)
        return response.text.strip()
    except Exception as e:
        print(f"AI Generation failed: {e}")
        return None

def check_and_send_reminders():
    pending = database.get_pending_reminders()
    
    for task in pending:
        task_id, telegram_id, title, notes, lang, due_date = task
        try:
            due_date_str = due_date.strftime("%Y-%m-%d %H:%M")
            username = database.get_username(telegram_id) or "Master"
            final_text = get_ai_reminder_text(username, title, notes, due_date_str, lang)
            
            if not final_text:
                final_text = get_text(lang, "reminder_sent", title=title, due_date=due_date_str, notes=notes)

            bot.send_message(telegram_id, final_text)
            database.mark_reminder_notified(task_id)
            
        except Exception as e:
            print(f"Failed to send reminder to {telegram_id}: {e}")

@bot.message_handler(commands=['myreminders'])
def handle_myreminders(message):
    telegram_id = message.from_user.id
    lang = database.get_user_language(telegram_id)
    reminders = database.get_user_reminders(telegram_id)
    
    if not reminders:
        bot.reply_to(message, get_text(lang, "no_reminders"))
        return
        
    reply_text = get_text(lang, "your_reminders") + "\n\n"
    
    for title, remind_at, notified in reminders:
        time_str = remind_at.strftime("%Y-%m-%d %H:%M")
        status_key = "status_sent" if notified else "status_pending"
        status_text = get_text(lang, status_key)
        reply_text += get_text(lang, "reminder_item", title=title, time_str=time_str, status=status_text)
        
    bot.reply_to(message, reply_text)

def run_bot():
    database.setup_database()
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_and_send_reminders, 'interval', minutes=1)
    scheduler.start()
    
    print("Bot is up and running...")
    bot.polling(non_stop=True, interval=0)