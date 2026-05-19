import datetime

import telebot
from apscheduler.schedulers.background import BackgroundScheduler
from google import genai
from google.genai import types
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram_bot_calendar import DetailedTelegramCalendar
from timezonefinder import TimezoneFinder

import src.familiarbot.logger as logger
from src.familiarbot import database
from src.familiarbot.config import ADMIN_PASS, GEMINI_KEY, TELEGRAM_KEY
from src.familiarbot.i18n import get_text

# Various initializations
bot = telebot.TeleBot(TELEGRAM_KEY)
user_states = {}
tf = TimezoneFinder()
client = genai.Client(api_key=GEMINI_KEY)
logger.init()

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

        state = user_states.get(message.from_user.id, {})
        if state.get('update_mode'):
            ask_upd_offset(message.chat.id, message.from_user.id, lang)
        else:
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

        if 'date' in state and 'time' in state:
            due_date = datetime.datetime.combine(state['date'], state['time'])
        else:
            due_date = state['due_date']

        remind_at = due_date - datetime.timedelta(hours=offset_hours)

        if state.get('update_mode'):
            database.update_task(state['task_id'], state['title'], state['notes'], due_date, offset_hours, remind_at)
            bot.reply_to(message, get_text(lang, "reminder_updated"))
        else:
            database.add_task(user_id, state['title'], state['notes'], due_date, offset_hours, remind_at)
            bot.reply_to(message, get_text(lang, "reminder_saved", text=state['title']))

        if user_id in user_states:
            del user_states[user_id]

    except ValueError:
        msg = bot.reply_to(message, get_text(lang, "invalid_offset"))
        bot.register_next_step_handler(msg, process_offset_step, lang)
    except Exception as e:
        logger.log_and_reply(bot, message, lang, e, "Failed to save reminder")

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

    system_prompt = f"You are a helpful personal familiar. Your master, {username}, asked you to remind them of a task. Write a short, creative, and personalized reminder message. You MUST write the response in the language corresponding to this ISO code: {lang}. Always mention the date and time from {due_date}. Do not use any markdown formatting like bolding or italics."
    user_prompt = f"Task Title: {title}\nDue Date: {due_date}\nTask Notes: {notes}"

    try:
        response = client.models.generate_content(model='gemini-2.5-flash-lite', config=types.GenerateContentConfig(system_instruction=system_prompt), contents=user_prompt)
        return response.text.strip()
    except Exception as e:
        logger.log_exception(e, f"Failed to generate AI text for {username}")
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

            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(get_text(lang, "reminder_complete"), callback_data=f"comp_task_{task_id}"))
            markup.add(InlineKeyboardButton(get_text(lang, "reminder_postpone"), callback_data=f"post_task_{task_id}"))
            bot.send_message(telegram_id, final_text, reply_markup=markup)
            database.mark_reminder_notified(task_id)

        except Exception as e:
            logger.log_exception(e, f"Failed to send reminder {task_id} to {telegram_id}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('comp_task_'))
def handle_complete_callback(call):
    task_id = call.data.split('_')[2]
    lang = database.get_user_language(call.from_user.id)

    database.remove_reminder(task_id)

    bot.answer_callback_query(call.id, text=get_text(lang, "reminder_completed_popup", default="Task completed!"))

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"{call.message.text}\n\nCompleted!",
        reply_markup=None
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('post_task_'))
def handle_postpone_callback(call):
    task_id = call.data.split('_')[2]
    lang = database.get_user_language(call.from_user.id)

    user_states[call.from_user.id] = {'postpone_task_id': task_id, 'msg_to_edit': call.message.message_id}

    msg = bot.send_message(
        call.message.chat.id,
        get_text(lang, "ask_postpone_hours", default="How many hours do you want to postpone this task?")
    )
    bot.register_next_step_handler(msg, process_postpone_step, lang)

def process_postpone_step(message, lang):
    if message.text.startswith('/'):
        bot.reply_to(message, get_text(lang, "cancel_reminder"))
        return
    try:
        offset_hours = float(message.text.strip())
        user_id = message.from_user.id
        state = user_states.get(user_id, {})
        task_id = state.get('postpone_task_id')
        if not task_id:
            bot.reply_to(message, "Error: Could not find the task.")
            return
        new_remind_at = datetime.datetime.now() + datetime.timedelta(hours=offset_hours)
        database.postpone_task(task_id, new_remind_at)
        bot.reply_to(message, get_text(lang, "task_postponed", default=f"Task postponed by {offset_hours} hours."))
        if 'msg_to_edit' in state:
            try:
                bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=state['msg_to_edit'], reply_markup=None)
            except Exception:
                pass
        if user_id in user_states:
            del user_states[user_id]
    except ValueError:
        msg = bot.reply_to(message, get_text(lang, "invalid_offset"))
        bot.register_next_step_handler(msg, process_postpone_step, lang)

@bot.message_handler(commands=['myreminders'])
def handle_myreminders(message):
    telegram_id = message.from_user.id
    lang = database.get_user_language(telegram_id)
    reminders = database.get_user_reminders(telegram_id)

    if not reminders:
        bot.reply_to(message, get_text(lang, "no_reminders"))
        return
    reply_text = get_text(lang, "your_reminders") + "\n\n"
    for task_id, title, remind_at, notified in reminders:
        time_str = remind_at.strftime("%Y-%m-%d %H:%M")
        status_key = "status_sent" if notified else "status_pending"
        status_text = get_text(lang, status_key)
        reply_text += get_text(lang, "reminder_item", title=title, time_str=time_str, status=status_text)

    bot.reply_to(message, reply_text)

@bot.message_handler(commands=['removereminder'])
def handle_removereminder(message):
    telegram_id = message.from_user.id
    lang = database.get_user_language(telegram_id)
    reminders = database.get_user_reminders(telegram_id)

    if not reminders:
        bot.reply_to(message, get_text(lang, "no_reminders"))
        return
    reply_text = get_text(lang, "choose_reminder_to_remove")
    markup = InlineKeyboardMarkup()
    for task_id, title, remind_at, notified in reminders:
        time_str = remind_at.strftime("%Y-%m-%d %H:%M")
        status_key = "status_sent" if notified else "status_pending"
        status_text = get_text(lang, status_key)
        reminder = get_text(lang, "reminder_item", title=title, time_str=time_str, status=status_text)
        markup.add(InlineKeyboardButton(f"{reminder}", callback_data=f"rm_task_{task_id}"))

    bot.send_message(message.chat.id, reply_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('rm_task_'))
def handle_remove_callback(call):
    task_id = call.data.split('_')[2]
    lang = database.get_user_language(call.from_user.id)
    database.remove_reminder(task_id)
    bot.answer_callback_query(call.id, text=get_text(lang, "reminder_removed_popup", default="Reminder removed!"))
    bot.edit_message_text(chat_id=call.message.chat.id,message_id=call.message.message_id,text=get_text(lang, "reminder_removed_text", default="Reminder successfully removed."))

@bot.message_handler(commands=['updatereminder'])
def handle_updatereminder(message):
    telegram_id = message.from_user.id
    lang = database.get_user_language(telegram_id)
    reminders = database.get_user_reminders(telegram_id)

    if not reminders:
        bot.reply_to(message, get_text(lang, "no_reminders"))
        return

    reply_text = get_text(lang, "choose_reminder_to_update")

    markup = InlineKeyboardMarkup()
    for task_id, title, remind_at, notified in reminders:
        time_str = remind_at.strftime("%Y-%m-%d %H:%M")
        status_key = "status_sent" if notified else "status_pending"
        status_text = get_text(lang, status_key)
        reminder = get_text(lang, "reminder_item", title=title, time_str=time_str, status=status_text)
        markup.add(InlineKeyboardButton(f"{reminder}", callback_data=f"upd_task_{task_id}"))

    bot.send_message(message.chat.id, reply_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('upd_task_'))
def handle_update_callback(call):
    task_id = call.data.split('_')[2]
    lang = database.get_user_language(call.from_user.id)

    task_data = database.get_task(task_id)
    if not task_data:
        bot.answer_callback_query(call.id, text=get_text(lang, "error_saving"))
        return

    user_states[call.from_user.id] = {'update_mode': True, 'task_id': task_id, 'title': task_data[0], 'notes': task_data[1], 'due_date': task_data[2], 'offset_hours': task_data[3]}

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(get_text(lang, "btn_skip"), callback_data="skip_upd_title"))

    msg = bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=get_text(lang, "ask_title"),
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, process_upd_title_step, lang)

# | TITLE STEP |
def process_upd_title_step(message, lang):
    if message.text.startswith('/'):
        bot.reply_to(message, get_text(lang, "cancel_reminder"))
        return
    user_states[message.from_user.id]['title'] = message.text.strip()
    ask_upd_notes(message.chat.id, message.from_user.id, lang)

@bot.callback_query_handler(func=lambda call: call.data == 'skip_upd_title')
def handle_skip_upd_title(call):
    lang = database.get_user_language(call.from_user.id)
    bot.clear_step_handler_by_chat_id(call.message.chat.id) # Stops waiting for text
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    ask_upd_notes(call.message.chat.id, call.from_user.id, lang)

# | NOTES STEP |
def ask_upd_notes(chat_id, user_id, lang):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(get_text(lang, "btn_skip"), callback_data="skip_upd_notes"))
    msg = bot.send_message(chat_id, get_text(lang, "ask_notes"), reply_markup=markup)
    bot.register_next_step_handler(msg, process_upd_notes_step, lang)

def process_upd_notes_step(message, lang):
    if message.text.startswith('/'):
        bot.reply_to(message, get_text(lang, "cancel_reminder"))
        return
    user_states[message.from_user.id]['notes'] = message.text.strip()
    ask_upd_datetime_choice(message.chat.id, message.from_user.id, lang)

@bot.callback_query_handler(func=lambda call: call.data == 'skip_upd_notes')
def handle_skip_upd_notes(call):
    lang = database.get_user_language(call.from_user.id)
    bot.clear_step_handler_by_chat_id(call.message.chat.id)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    ask_upd_datetime_choice(call.message.chat.id, call.from_user.id, lang)

# | DATE STEP |
def ask_upd_datetime_choice(chat_id, user_id, lang):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(get_text(lang, "btn_yes"), callback_data="do_upd_datetime"),
        InlineKeyboardButton(get_text(lang, "btn_skip"), callback_data="skip_upd_datetime")
    )
    bot.send_message(chat_id, get_text(lang, "ask_update_datetime"), reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'do_upd_datetime')
def handle_do_upd_datetime(call):
    lang = database.get_user_language(call.from_user.id)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    calendar, step = DetailedTelegramCalendar().build()
    bot.send_message(call.message.chat.id, get_text(lang, f"select_{step}"), reply_markup=calendar)

@bot.callback_query_handler(func=lambda call: call.data == 'skip_upd_datetime')
def handle_skip_upd_datetime(call):
    lang = database.get_user_language(call.from_user.id)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    ask_upd_offset(call.message.chat.id, call.from_user.id, lang)

# | OFFSET STEP |
def ask_upd_offset(chat_id, user_id, lang):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(get_text(lang, "btn_skip"), callback_data="skip_upd_offset"))
    msg = bot.send_message(chat_id, get_text(lang, "ask_offset"), reply_markup=markup)
    bot.register_next_step_handler(msg, process_offset_step, lang)

@bot.callback_query_handler(func=lambda call: call.data == 'skip_upd_offset')
def handle_skip_upd_offset(call):
    user_id = call.from_user.id
    lang = database.get_user_language(user_id)
    bot.clear_step_handler_by_chat_id(call.message.chat.id)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    state = user_states.get(user_id, {})
    if not state:
        return

    due_date = state.get('due_date')
    if 'date' in state and 'time' in state:
        due_date = datetime.datetime.combine(state['date'], state['time'])

    offset_hours = state['offset_hours']
    remind_at = due_date - datetime.timedelta(hours=offset_hours)

    database.update_task(state['task_id'], state['title'], state['notes'], due_date, offset_hours, remind_at)
    bot.send_message(call.message.chat.id, get_text(lang, "reminder_updated"))
    if user_id in user_states:
        del user_states[user_id]

@bot.message_handler(commands=['debug'])
def handle_debug(message):
    msg = bot.reply_to(message, "Enter the admin password:")
    bot.register_next_step_handler(msg, verify_adm_pass)

def verify_adm_pass(message):
    if message.text == ADMIN_PASS:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("Quit Debug Mode"))

        msg = bot.send_message(message.chat.id, "Access granted. You are now in debug mode. \nEnter your raw SQL commands:", reply_markup=markup)
        bot.register_next_step_handler(msg, debug_loop)
    else:
        bot.send_message(message.chat.id, "Nuh-uh.")

def debug_loop(message):
    if message.text == "Quit Debug Mode":
        bot.send_message(message.chat.id, "Quit debug mode.", reply_markup=ReplyKeyboardRemove())
        return

    result = database.exec_admin_cmd(message.text)
    msg = bot.send_message(message.chat.id, f"Result:\n\\```\n{result}\n```", parse_mode='Markdown')
    bot.register_next_step_handler(msg, debug_loop)

def run_bot():
    database.setup_database()
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_and_send_reminders, 'interval', minutes=1)
    scheduler.start()

    print("Bot is up and running...")
    bot.polling(non_stop=True, interval=0)
