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
            language VARCHAR(10) DEFAULT 'en'
        );
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            status BOOLEAN DEFAULT FALSE,
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

def add_task(telegram_id, title):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        INSERT INTO tasks (user_id, title)
        VALUES (
            (SELECT id FROM users WHERE telegram_id = %s),
            %s
        );
    ''', (telegram_id, title))

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