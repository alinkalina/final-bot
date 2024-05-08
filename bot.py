import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from config import BOT_TOKEN
import logging
from database import add_user, start_request, get_all_user_texts, get_voice, table, set_tts_expenses, set_stt_expenses, set_voice
from speechkit import text_to_speech, speech_to_text
from gpt import ask_gpt
from limits import modes, MAX_BLOCKS_IN_MESSAGE, SECONDS_IN_BLOCK, MAX_LEN_OF_MESSAGE, voices
from limitation import check_gpt_limit, check_tts_limits, check_stt_limits, check_kandinsky_limits, get_user_balance
from kandinsky import draw_image


bot = telebot.TeleBot(BOT_TOKEN)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='logs.txt', filemode='w')


def create_markup(buttons: list[str]):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    for i in range(len(buttons)):
        if i % 2 == 0:
            try:
                markup.row(KeyboardButton(buttons[i]), KeyboardButton(buttons[i + 1]))
            except IndexError:
                markup.row(KeyboardButton(buttons[i]))
    return markup


@bot.message_handler(commands=['start'])
def send_start_message(message):
    if add_user(message.chat.id, message.from_user.username):
        bot.send_message(message.chat.id, 'Привет! Я Женя, друг на все времена. Ты можешь задавать мне вопросы, просить'
                                          ' меня нарисовать что-нибудь... И ещё несколько прикольных вещей! Только '
                                          'сначала прочитай инструкцию по использованию бота - жми /help',
                         reply_markup=ReplyKeyboardRemove())
        print(table())
    else:
        bot.send_message(message.chat.id, 'Извини, но на данный момент все свободные места для пользователей заняты :( '
                                          'Попробуй снова через некоторое время', reply_markup=ReplyKeyboardRemove())
        logging.warning('Достигнут лимит пользователей бота')


@bot.message_handler(commands=['help'])
def send_help_message(message):
    if add_user(message.chat.id, message.from_user.username):
        bot.send_message(message.chat.id, '*Инструкция*\n\nНажми на кнопку Меню внизу слева. Там ты увидишь список '
                                          'моих команд. Нажав на /new, ты сможешь выбрать один из режимов:'
                                          '\nПообщаться - последовательно задавай вопросы и получай ответ от нейросети.'
                                          '\nПорисовать - описывай то, что хочешь увидеть на картинке, и тебе придёт '
                                          'результат от Kandinsky в случайном стиле.'
                                          '\nПоговорить - выбирай режим (текст в голос - /tts, голос в текст - /stt), '
                                          'а нейросеть выполнит преобразование.'
                                          '\nВсе режимы работают в формате диалога (не нужно заново запускать команду, '
                                          'просто продолжай спрашивать). Кстати, тебе не обязательно печатать текст! '
                                          'Во всех 3 режимах ты можешь отправлять мне голосовые. Тогда ответ '
                                          '(если это возможно) тоже придёт тебе голосом. В настройках (/settings) '
                                          'ты можешь выбрать голос.'
                                          '\n\n*Лимиты*\n\nКаждому пользователю предоставлено ограниченное количество '
                                          'токенов при общении с нейросетью (на её ответы), генерируемых изображений, '
                                          f'символов на перевод из текста в речь и блоков аудио по {SECONDS_IN_BLOCK} '
                                          'секунд на перевод из речи в текст. Когда лимит будет превышен, мои функции '
                                          'перестанут работать (но тебя об этом я конечно же предупрежу!). Свой '
                                          'баланс и ограничения можно посмотреть по команде /balance.',
                         reply_markup=ReplyKeyboardRemove(), parse_mode='Markdown')
        print(get_all_user_texts(message.chat.id))
    else:
        bot.send_message(message.chat.id, 'Извини, но на данный момент все свободные места для пользователей заняты :( '
                                          'Попробуй снова через некоторое время', reply_markup=ReplyKeyboardRemove())
        logging.warning('Достигнут лимит пользователей бота')


@bot.message_handler(commands=['new'])
def ask(message):
    if add_user(message.chat.id, message.from_user.username):
        bot.send_message(message.chat.id, 'Выбери режим', reply_markup=create_markup(modes))
    else:
        bot.send_message(message.chat.id, 'Извини, но на данный момент все свободные места для пользователей заняты :( '
                                          'Попробуй снова через некоторое время', reply_markup=ReplyKeyboardRemove())
        logging.warning('Достигнут лимит пользователей бота')


def chat(message):
    if check_gpt_limit(message.chat.id) and ((message.content_type == 'text' and not message.text.startswith('/')) or message.content_type == 'voice'):
        text = ''
        if message.content_type == 'voice':
            if check_tts_limits(message.chat.id) and check_stt_limits(message.chat.id):
                if message.voice.duration > MAX_BLOCKS_IN_MESSAGE * SECONDS_IN_BLOCK:
                    msg = bot.send_message(message.chat.id, f'Это аудио дольше '
                                                            f'{MAX_BLOCKS_IN_MESSAGE * SECONDS_IN_BLOCK} секунд. '
                                                            f'Отправь что-нибудь покороче :)',
                                           reply_markup=ReplyKeyboardRemove())
                    bot.register_next_step_handler(msg, chat)
                file_info = bot.get_file(message.voice.file_id)
                file = bot.download_file(file_info.file_path)
                text = speech_to_text(file)
                set_stt_expenses(message.chat.id, message.voice.duration)
            else:
                msg = bot.send_message(message.chat.id, 'К сожалению, у тебя закончились все блоки для распознавания '
                                                        'речи. Задай вопрос текстом',
                                       reply_markup=ReplyKeyboardRemove())
                bot.register_next_step_handler(msg, chat)
        elif len(message.text) > MAX_LEN_OF_MESSAGE:
            msg = bot.send_message(message.chat.id, f'В этом сообщении больше {MAX_LEN_OF_MESSAGE} символов. Отправь '
                                                    f'что-нибудь покороче :)', reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, chat)
        else:
            text = message.text
        start_request(message.chat.id, text=text)
        answer = ask_gpt(message.chat.id, text)
        if message.content_type == 'voice':
            set_tts_expenses(message.chat.id, len(answer))
            answer = text_to_speech(answer, get_voice(message.chat.id))
            msg = bot.send_audio(message.chat.id, answer, reply_markup=ReplyKeyboardRemove())
        else:
            msg = bot.send_message(message.chat.id, answer, reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, chat)
    elif not check_gpt_limit(message.chat.id):
        bot.send_message(message.chat.id, 'К сожалению, у тебя закончились все токены для общения с нейросетью',
                         reply_markup=create_markup(modes))
    elif not message.text.startswith('/'):
        msg = bot.send_message(message.chat.id, 'Нужно отправить текстовое или голосовое сообщение!',
                               reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, chat)
    else:
        bot.send_message(message.chat.id, 'Пожалуйста, повтори команду', reply_markup=ReplyKeyboardRemove())


def draw(message):
    if check_kandinsky_limits(message.chat.id) and ((message.content_type == 'text' and not message.text.startswith('/')) or message.content_type == 'voice'):
        prompt = ''
        if message.content_type == 'voice':
            if check_stt_limits(message.chat.id):
                if message.voice.duration > MAX_BLOCKS_IN_MESSAGE * SECONDS_IN_BLOCK:
                    msg = bot.send_message(message.chat.id, f'Это аудио дольше '
                                                            f'{MAX_BLOCKS_IN_MESSAGE * SECONDS_IN_BLOCK} секунд. '
                                                            f'Отправь что-нибудь покороче :)',
                                           reply_markup=ReplyKeyboardRemove())
                    bot.register_next_step_handler(msg, draw)
                file_info = bot.get_file(message.voice.file_id)
                file = bot.download_file(file_info.file_path)
                prompt = speech_to_text(file)
                set_stt_expenses(message.chat.id, message.voice.duration, modes[1])
            else:
                msg = bot.send_message(message.chat.id, 'К сожалению, у тебя закончились все блоки для распознавания '
                                                        'речи. Напиши промпт текстом',
                                       reply_markup=ReplyKeyboardRemove())
                bot.register_next_step_handler(msg, draw)
        elif len(message.text) > MAX_LEN_OF_MESSAGE:
            msg = bot.send_message(message.chat.id, f'В этом сообщении больше {MAX_LEN_OF_MESSAGE} символов. Отправь '
                                                    f'что-нибудь покороче :)', reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, draw)
        else:
            prompt = message.text
        start_request(message.chat.id, text=prompt, mode=modes[1])
        image, style = draw_image(message.chat.id, prompt)
        if image:
            msg = bot.send_photo(message.chat.id, image, f'Изображение в стиле {style}',
                                 reply_markup=ReplyKeyboardRemove())
        else:
            msg = bot.send_message(message.chat.id, 'В Kandinsky произошла ошибка. Попробуй снова чуть позже',
                                   reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, draw)
    elif not check_kandinsky_limits(message.chat.id):
        bot.send_message(message.chat.id, 'К сожалению, у тебя закончились все изображения для генерации',
                         reply_markup=create_markup(modes))
    elif not message.text.startswith('/'):
        msg = bot.send_message(message.chat.id, 'Нужно отправить текстовое или голосовое сообщение!',
                               reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, draw)
    else:
        bot.send_message(message.chat.id, 'Пожалуйста, повтори команду', reply_markup=ReplyKeyboardRemove())


@bot.message_handler(commands=['tts'])
def tts_command(message):
    if check_tts_limits(message.chat.id):
        start_request(message.chat.id, mode=modes[2])
        msg = bot.send_message(message.chat.id, f'Напиши текст не более {MAX_LEN_OF_MESSAGE} символов',
                               reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, tts)
        # start_tts_text(message.chat.id)
        # bot.send_message(message.chat.id, 'Выбери голос', reply_markup=create_markup(list(voices.keys())))
    else:
        bot.send_message(message.chat.id, 'К сожалению, у тебя закончились все символы для синтеза речи',
                         reply_markup=ReplyKeyboardRemove())


def tts(text):
    if check_tts_limits(text.chat.id) and text.content_type == 'text' and not text.text.startswith('/'):
        if len(text.text) > MAX_LEN_OF_MESSAGE:
            msg = bot.send_message(text.chat.id, f'В этом сообщении больше {MAX_LEN_OF_MESSAGE} символов. '
                                                 f'Отправь что-нибудь покороче :)', reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, tts)
        else:
            # set_text(text.chat.id, text.text)
            response = text_to_speech(text.text, get_voice(text.chat.id))
            if response:
                set_tts_expenses(text.chat.id, len(text.text), modes[2])
                msg = bot.send_audio(text.chat.id, response, reply_markup=ReplyKeyboardRemove())
            else:
                msg = bot.send_message(text.chat.id, 'В SpeechKit произошла ошибка. Попробуй снова чуть позже',
                                       reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, tts)
    elif not check_tts_limits(text.chat.id):
        bot.send_message(text.chat.id, 'К сожалению, у тебя закончились все символы для синтеза речи',
                         reply_markup=ReplyKeyboardRemove())
    elif not text.text.startswith('/'):
        msg = bot.send_message(text.chat.id, 'Нужно отправить текстовое сообщение!', reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, tts)
    else:
        bot.send_message(text.chat.id, 'Пожалуйста, повтори команду', reply_markup=ReplyKeyboardRemove())


@bot.message_handler(commands=['stt'])
def stt_command(message):
    if check_stt_limits(message.chat.id):
        start_request(message.chat.id, mode=modes[2])
        msg = bot.send_message(message.chat.id, f'Отправь голосовое сообщение не длиннее '
                                                f'{MAX_BLOCKS_IN_MESSAGE * SECONDS_IN_BLOCK} секунд',
                               reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, stt)
    else:
        bot.send_message(message.chat.id, 'К сожалению, у тебя закончились все блоки для распознавания речи',
                         reply_markup=ReplyKeyboardRemove())


def stt(audio):
    if check_stt_limits(audio.chat.id) and audio.content_type == 'voice':
        if audio.voice.duration > MAX_BLOCKS_IN_MESSAGE * SECONDS_IN_BLOCK:
            msg = bot.send_message(audio.chat.id, f'Это аудио длиннее {MAX_BLOCKS_IN_MESSAGE * SECONDS_IN_BLOCK} секунд. '
                                                  f'Отправь что-нибудь покороче :)', reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, stt)
        else:
            # set_blocks(audio.chat.id, audio.voice.duration)
            file_info = bot.get_file(audio.voice.file_id)
            file = bot.download_file(file_info.file_path)
            response = speech_to_text(file)
            if response:
                set_stt_expenses(audio.chat.id, audio.voice.duration, modes[2])
                msg = bot.send_message(audio.chat.id, response, reply_markup=ReplyKeyboardRemove())
            else:
                msg = bot.send_message(audio.chat.id, 'В SpeechKit произошла ошибка. Попробуй снова чуть позже',
                                       reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, stt)
    elif not check_stt_limits(audio.chat.id):
        bot.send_message(audio.chat.id, 'К сожалению, у тебя закончились все блоки для распознавания речи',
                         reply_markup=ReplyKeyboardRemove())
    else:
        msg = bot.send_message(audio.chat.id, 'Нужно отправить голосовое сообщение!',
                               reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, stt)


@bot.message_handler(commands=['balance'])
def send_balance(message):
    if add_user(message.chat.id, message.from_user.username):
        gpt_tokens, images, symbols, blocks = get_user_balance(message.chat.id)
        bot.send_message(message.chat.id, f'Потрачено:'
                                          f'\n{gpt_tokens[0]} из {gpt_tokens[1]} токенов'
                                          f'\n{images[0]} из {images[1]} изображений'
                                          f'\n{symbols[0]} из {symbols[1]} символов'
                                          f'\n{blocks[0]} из {blocks[1]} блоков',
                         reply_markup=ReplyKeyboardRemove())
    else:
        bot.send_message(message.chat.id, 'Извини, но на данный момент все свободные места для пользователей заняты :( '
                                          'Попробуй снова через некоторое время', reply_markup=ReplyKeyboardRemove())
        logging.warning('Достигнут лимит пользователей бота')


@bot.message_handler(commands=['settings'])
def change_settings(message):
    if add_user(message.chat.id, message.from_user.username):
        # gpt_tokens, images, symbols, blocks = get_user_balance(message.chat.id)
        bot.send_message(message.chat.id, 'Выбери голос', reply_markup=create_markup(list(voices.keys())))
    else:
        bot.send_message(message.chat.id, 'Извини, но на данный момент все свободные места для пользователей заняты :( '
                                          'Попробуй снова через некоторое время', reply_markup=ReplyKeyboardRemove())
        logging.warning('Достигнут лимит пользователей бота')


@bot.message_handler(commands=['debug'])
def send_logs(message):
    if add_user(message.chat.id, message.from_user.username):
        with open('logs.txt', 'r') as f:
            bot.send_document(message.chat.id, f, reply_markup=ReplyKeyboardRemove())
        f.close()
    else:
        bot.send_message(message.chat.id, 'Извини, но на данный момент все свободные места для пользователей заняты :( '
                                          'Попробуй снова через некоторое время', reply_markup=ReplyKeyboardRemove())
        logging.warning('Достигнут лимит пользователей бота')


@bot.message_handler(content_types=['text'])
def text_message(message):
    if message.text in modes:
        if message.text == modes[0]:
            if check_gpt_limit(message.chat.id):
                msg = bot.send_message(message.chat.id, 'Задай вопрос', reply_markup=ReplyKeyboardRemove())
                bot.register_next_step_handler(msg, chat)
            else:
                bot.send_message(message.chat.id, 'К сожалению, у тебя закончились все токены для общения с нейросетью',
                                 reply_markup=create_markup(modes))
        elif message.text == modes[1]:
            if check_kandinsky_limits(message.chat.id):
                msg = bot.send_message(message.chat.id, 'Опиши, что должно быть на картинке',
                                       reply_markup=ReplyKeyboardRemove())
                bot.register_next_step_handler(msg, draw)
            else:
                bot.send_message(message.chat.id, 'К сожалению, у тебя закончились все изображения для генерации',
                                 reply_markup=create_markup(modes))
        elif message.text == modes[2]:
            tts_limit = check_tts_limits(message.chat.id)
            stt_limit = check_stt_limits(message.chat.id)
            if tts_limit or stt_limit:
                available_modes = []
                if tts_limit:
                    available_modes.append('/tts')
                if stt_limit:
                    available_modes.append('/stt')
                bot.send_message(message.chat.id, 'Выбери режим', reply_markup=create_markup(available_modes))
            else:
                bot.send_message(message.chat.id, 'К сожалению, у тебя закончились все символы для синтеза речи и все '
                                                  'блоки для распознавания речи', reply_markup=create_markup(modes))
    elif message.text in voices.keys():
        set_voice(message.chat.id, voices.get(message.text))
    else:
        bot.send_message(message.chat.id,
                         'Тебе следует воспользоваться командой или кнопкой, другого бот не понимает :(',
                         reply_markup=ReplyKeyboardRemove())


@bot.message_handler(content_types=['photo', 'audio', 'document', 'sticker', 'video', 'voice', 'location', 'contact'])
def error_message(message):
    bot.send_message(message.chat.id, 'Тебе следует воспользоваться командой или кнопкой, другого бот не понимает :(',
                     reply_markup=ReplyKeyboardRemove())


try:
    logging.info('Бот запущен')
    bot.polling()
except Exception as e:
    logging.critical(f'Ошибка - {e}')
