import psycopg2
from src.familiarbot.config import DB_NAME, DB_USERNAME, DB_PASSWORD, DB_HOST, DB_PORT

def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME, user=DB_USERNAME, password=DB_PASSWORD, 
        host=DB_HOST, port=DB_PORT
    )

def setup_database():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            username VARCHAR(255),
            language VARCHAR(10) DEFAULT 'en',
            timezone VARCHAR(50) DEFAULT 'UTC'
        );
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            notes TEXT,
            due_date TIMESTAMP NOT NULL,
            reminder_offset_hours FLOAT,
            remind_at TIMESTAMP NOT NULL,
            status BOOLEAN DEFAULT FALSE,
            notified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    conn.commit()
    cur.close()
    conn.close()
    print("Database setup complete.")

def add_user(telegram_id, username, language_code):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO users (telegram_id, username, language)
        VALUES (%s, %s, %s)
        ON CONFLICT (telegram_id) DO UPDATE 
        SET username = EXCLUDED.username,
            language = EXCLUDED.language;
    ''', (telegram_id, username, language_code))
    conn.commit()
    cur.close()
    conn.close()

def get_user_language(telegram_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT language FROM users WHERE telegram_id = %s;', (telegram_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else 'en'

def add_task(telegram_id, title, notes, due_date, offset_hours, remind_at):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        INSERT INTO tasks (user_id, title, notes, due_date, reminder_offset_hours, remind_at)
        VALUES (
            (SELECT id FROM users WHERE telegram_id = %s),
            %s, %s, %s, %s, %s
        );
    ''', (telegram_id, title, notes, due_date, offset_hours, remind_at))

    conn.commit()
    cur.close()
    conn.close()

def get_username(telegram_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
                SELECT username FROM users WHERE telegram_id = %s;
                ''', (telegram_id,))
    result = cur.fetchone()

    cur.close()
    conn.close()

    if result:
        return result[0]
    else:
        return None
    
def update_language(telegram_id, new_language):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        UPDATE users
        SET language = %s
        WHERE telegram_id = %s;
    ''', (new_language, telegram_id))
    conn.commit()
    cur.close()
    conn.close()

def get_pending_reminders():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        SELECT t.id, u.telegram_id, t.title, t.notes, u.language, t.due_date 
        FROM tasks t
        JOIN users u ON t.user_id = u.id
        WHERE t.remind_at <= (NOW() AT TIME ZONE u.timezone) AND t.notified = FALSE AND t.status = FALSE;
    ''')
    reminders = cur.fetchall()

    cur.close()
    conn.close()
    return reminders

def mark_reminder_notified(task_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE tasks SET notified = TRUE WHERE id = %s;', (task_id,))
    conn.commit()
    cur.close()
    conn.close()

def get_user_reminders(telegram_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT title, remind_at, notified 
        FROM tasks 
        WHERE user_id = (SELECT id FROM users WHERE telegram_id = %s)
        ORDER BY remind_at ASC;
    ''', (telegram_id,))
    reminders = cur.fetchall()
    cur.close()
    conn.close()
    return reminders

def update_timezone(telegram_id, timezone_str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        UPDATE users
        SET timezone = %s
        WHERE telegram_id = %s;
    ''', (timezone_str, telegram_id))
    conn.commit()
    cur.close()
    conn.close()