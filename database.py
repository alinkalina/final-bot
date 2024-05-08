import sqlite3
import logging

from limits import MAX_USERS, MAX_TOKENS_FOR_USER, SECONDS_IN_BLOCK, MAX_MESSAGES_IN_HISTORY
from constants import modes, tables, voices


def open_db():
    con = sqlite3.connect('db.sqlite', check_same_thread=False)
    cur = con.cursor()
    return con, cur


def create_tables():
    connection, cursor = open_db()

    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL UNIQUE,
        tg_username TEXT NOT NULL,
        chat BOOL DEFAULT False,
        voice TEXT DEFAULT "{voices.get('Мужской')}",
        tokens INTEGER DEFAULT {MAX_TOKENS_FOR_USER}
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS questions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        stt_blocks INTEGER DEFAULT 0,
        answer TEXT DEFAULT "",
        tokens INTEGER DEFAULT "",
        tts_symbols INTEGER DEFAULT 0,
        FOREIGN KEY (author_id) REFERENCES users (id)
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS images(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author_id INTEGER NOT NULL,
        prompt TEXT NOT NULL,
        stt_blocks INTEGER DEFAULT 0,
        image TEXT DEFAULT "",
        style TEXT DEFAULT "",
        FOREIGN KEY (author_id) REFERENCES users (id)
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS speechkit(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author_id INTEGER NOT NULL,
        tts_symbols INTEGER DEFAULT 0,
        stt_blocks INTEGER DEFAULT 0,
        FOREIGN KEY (author_id) REFERENCES users (id)
    );
    ''')

    cursor.close()
    connection.commit()
    connection.close()

    logging.info('Созданы таблицы')


def change_db(sql):
    connection, cursor = open_db()
    cursor.execute(sql)
    cursor.close()
    connection.commit()
    connection.close()


def get_from_db(sql):
    connection, cursor = open_db()
    cursor.execute(sql)
    result = cursor.fetchall()
    cursor.close()
    connection.close()
    return result


def user_in_db(user_id):
    res = get_from_db(f'SELECT * FROM users WHERE chat_id = {user_id};')
    return res


def add_user(user_id, username):
    if not user_in_db(user_id):
        if len(get_from_db('SELECT * FROM users')) < MAX_USERS:
            change_db(f'INSERT INTO users (chat_id, tg_username) VALUES ({user_id}, "{username}");')
            logging.info(f'Добавлен пользователь {get_username(user_id)}')
        else:
            logging.warning(f'В базе уже {MAX_USERS} пользователей')
            return False
    return True


def get_username(user_id):
    return get_from_db(f'SELECT tg_username FROM users WHERE chat_id = {user_id};')


def get_id_by_chat_id(user_id):
    return get_from_db(f'SELECT id FROM users WHERE chat_id = {user_id};')[0][0]


def start_request(user_id, text='', mode=modes[0]):
    if mode == modes[0]:
        change_db(f'INSERT INTO questions (author_id, text) VALUES ({get_id_by_chat_id(user_id)}, "{text}");')
    elif mode == modes[1]:
        change_db(f'INSERT INTO images (author_id, prompt) VALUES ({get_id_by_chat_id(user_id)}, "{text}");')
    elif mode == modes[2]:
        change_db(f'INSERT INTO speechkit (author_id) VALUES ({get_id_by_chat_id(user_id)});')


def set_answer(user_id, answer, mode=modes[0], param=''):
    if mode == modes[0]:
        change_db(f'UPDATE questions SET answer = "{answer}" '
                  f'WHERE id = (SELECT MAX(id) FROM questions WHERE author_id = {get_id_by_chat_id(user_id)});')
    elif mode == modes[1]:
        change_db(f'UPDATE images SET image = "{answer}", style = "{param}" '
                  f'WHERE id = (SELECT MAX(id) FROM images WHERE author_id = {get_id_by_chat_id(user_id)});')


def set_tokens(user_id, tokens):
    change_db(f'UPDATE questions SET tokens = "{tokens}" '
              f'WHERE id = (SELECT MAX(id) FROM questions WHERE author_id = {get_id_by_chat_id(user_id)});')


def set_tts_expenses(user_id, tts_symbols, mode=modes[0]):
    table_name = tables[modes.index(mode)]
    change_db(f'UPDATE {table_name} SET tts_symbols = {tts_symbols} '
              f'WHERE id = (SELECT MAX(id) FROM {table_name} WHERE author_id = {get_id_by_chat_id(user_id)});')


def set_stt_expenses(user_id, stt_seconds, mode=modes[0]):
    stt_blocks = stt_seconds // SECONDS_IN_BLOCK + 1
    table_name = tables[modes.index(mode)]
    change_db(f'UPDATE {table_name} SET stt_blocks = {stt_blocks} '
              f'WHERE id = (SELECT MAX(id) FROM {table_name} WHERE author_id = {get_id_by_chat_id(user_id)});')


def get_history(user_id):
    return get_from_db(f'SELECT text, answer FROM questions '
                       f'WHERE author_id = {get_id_by_chat_id(user_id)} AND answer != "" '
                       f'ORDER BY id DESC LIMIT {MAX_MESSAGES_IN_HISTORY};')


def count_gpt_tokens(user_id):
    return get_from_db(f'SELECT SUM(tokens) FROM questions WHERE author_id = {get_id_by_chat_id(user_id)};')


def count_user_images(user_id):
    return get_from_db(f'SELECT COUNT(*) FROM images WHERE author_id = {get_id_by_chat_id(user_id)};')


def count_speechkit_blocks(user_id, table_name):
    try:
        return get_from_db(f'SELECT SUM(stt_blocks) FROM {table_name} WHERE author_id = {get_id_by_chat_id(user_id)};')
    except sqlite3.OperationalError:
        return [(None,)]


def count_speechkit_symbols(user_id, table_name):
    try:
        return get_from_db(f'SELECT SUM(tts_symbols) FROM {table_name} WHERE author_id = {get_id_by_chat_id(user_id)};')
    except sqlite3.OperationalError:
        return [(None,)]


def set_voice(user_id, voice):
    change_db(f'UPDATE users SET voice = "{voice}" WHERE chat_id = {user_id};')


def get_voice(user_id):
    return get_from_db(f'SELECT voice FROM users WHERE chat_id = {user_id};')


create_tables()
