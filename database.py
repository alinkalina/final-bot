import sqlite3
import logging

from limits import MAX_USERS, MAX_TOKENS_FOR_USER, voices, modes, MAX_MESSAGES_IN_HISTORY, SECONDS_IN_BLOCK


def table():
    return get_from_db('SELECT * FROM questions;')


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


# users


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


# start (both)


def start_request(user_id, mode, text):
    if mode == modes[0]:
        change_db(f'INSERT INTO questions (author_id, text) '
                  f'VALUES ({get_id_by_chat_id(user_id)}, "{text}");')
    elif mode == modes[1]:
        change_db(f'INSERT INTO images (author_id, prompt) '
                  f'VALUES ({get_id_by_chat_id(user_id)}, "{text}");')


# add answer (both)


def set_answer(user_id, mode, answer, param=''):
    if mode == modes[0]:
        change_db(f'UPDATE questions SET answer = "{answer}" '
                  f'WHERE id = (SELECT MAX(id) FROM questions WHERE author_id = {get_id_by_chat_id(user_id)});')
    elif mode == modes[1]:
        change_db(f'UPDATE images SET image = "{answer}", style = "{param}" '
                  f'WHERE id = (SELECT MAX(id) FROM images WHERE author_id = {get_id_by_chat_id(user_id)});')
    # logging.info(f'Пользователю {get_username(user_id)} в историю добавлен новый кусочек:\n{new_answer}')


# set tokens of answer, only for gpt questions


def set_tokens(user_id, tokens):
    change_db(f'UPDATE questions SET tokens = "{tokens}" '
              f'WHERE id = (SELECT MAX(id) FROM questions WHERE author_id = {get_id_by_chat_id(user_id)});')


# speechkit stt, tts (can be both)


def set_speechkit_expenses(user_id, stt_seconds, tts_symbols):
    stt_blocks = stt_seconds // SECONDS_IN_BLOCK + 1
    change_db(f'UPDATE questions SET stt_blocks = {stt_blocks}, tts_symbols = {tts_symbols} '
              f'WHERE id = (SELECT MAX(id) FROM questions WHERE author_id = {get_id_by_chat_id(user_id)});')


def set_stt_expenses(user_id, stt_seconds):
    stt_blocks = stt_seconds // SECONDS_IN_BLOCK + 1
    change_db(f'UPDATE images SET stt_blocks = {stt_blocks} '
              f'WHERE id = (SELECT MAX(id) FROM images WHERE author_id = {get_id_by_chat_id(user_id)});')


# history for gpt


def get_history(user_id):
    return get_from_db(f'SELECT text, answer FROM questions '
                       f'WHERE author_id = {get_id_by_chat_id(user_id)} AND answer != "" '
                       f'ORDER BY id DESC LIMIT {MAX_MESSAGES_IN_HISTORY};')


# can user ask gpt or not


def count_gpt_tokens(user_id):
    return get_from_db(f'SELECT SUM(tokens) FROM questions WHERE author_id = {get_id_by_chat_id(user_id)};')


# can user draw or not


def count_user_images(user_id):
    return get_from_db(f'SELECT COUNT(*) FROM images WHERE author_id = {get_id_by_chat_id(user_id)};')


# can user send voice or not (can be both)


def count_speechkit_blocks(user_id, mode=modes[0]):
    table_name = 'questions'
    if mode == modes[1]:
        table_name = 'images'
    return get_from_db(f'SELECT SUM(stt_blocks) FROM {table_name} WHERE author_id = {get_id_by_chat_id(user_id)};')


def count_speechkit_symbols(user_id):
    return get_from_db(f'SELECT SUM(tts_symbols) FROM questions WHERE author_id = {get_id_by_chat_id(user_id)};')


# change voice in settings


def set_voice(user_id, voice):
    change_db(f'UPDATE users SET voice = "{voice}" WHERE chat_id = {user_id};')


# get voice for tts


def get_voice(user_id):
    return get_from_db(f'SELECT voice FROM users WHERE chat_id = {user_id};')


# debug


def get_all_user_texts(user_id):
    return get_from_db(f'SELECT * FROM questions WHERE author_id = {get_id_by_chat_id(user_id)};'), \
           get_from_db(f'SELECT * FROM images WHERE author_id = {get_id_by_chat_id(user_id)};')


# def get_user_tokens_data(user_id, param):
#     return get_from_db(f'SELECT {param} FROM users WHERE chat_id = {user_id};')
#
#
# def update_sessions(user_id, sessions):
#     change_db(f'UPDATE users SET sessions = {sessions}, tokens = {MAX_TOKENS_IN_SESSION} WHERE chat_id = {user_id};')
#
#
# def update_tokens(user_id, tokens):
#     change_db(f'UPDATE users SET tokens = {get_user_tokens_data(user_id, "tokens")[0][0] - tokens} '
#               f'WHERE chat_id = {user_id};')
#
#
# def start_tts_text(user_id):
#     change_db(f'INSERT INTO texts (author_id) VALUES ({get_id_by_chat_id(user_id)});')


# def set_text(user_id, text):
#     change_db(f'UPDATE texts SET text = "{text}" '
#               f'WHERE id = (SELECT MAX(id) FROM texts WHERE author_id = {get_id_by_chat_id(user_id)});')
#
#
# def start_stt_text(user_id):
#     change_db(f'INSERT INTO audio (author_id) VALUES ({get_id_by_chat_id(user_id)});')
#
#
# def set_blocks(user_id, duration):
#     blocks = (duration // SECONDS_IN_BLOCK) + 1
#     change_db(f'UPDATE audio SET blocks = {blocks} '
#               f'WHERE id = (SELECT MAX(id) FROM audio WHERE author_id = {get_id_by_chat_id(user_id)});')
#
#
# def get_user_blocks(user_id):
#     return get_from_db(f'SELECT blocks FROM audio WHERE author_id = {get_id_by_chat_id(user_id)};')


# def get_story_settings(user_id):
#     return get_from_db(f'SELECT genre, main_character, setting, info FROM stories '
#                        f'WHERE author_id = (SELECT id FROM users WHERE chat_id = {user_id}) '
#                        f'ORDER BY id DESC LIMIT 1;')


create_tables()
