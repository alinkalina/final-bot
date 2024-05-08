import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from config import BOT_TOKEN
import logging
from database import add_user, start_request, get_all_user_texts, get_voice, table, set_tts_expenses, set_stt_expenses
from speechkit import text_to_speech, speech_to_text
from gpt import ask_gpt
from limits import modes, MAX_SYMBOLS_FOR_USER, MAX_BLOCKS_IN_MESSAGE, SECONDS_IN_BLOCK, MAX_LEN_OF_MESSAGE
from limitation import check_gpt_limit, check_tts_limits, check_stt_limits, check_kandinsky_limits
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
        bot.send_message(message.chat.id, 'Привет! Ну что, готов приступить к твоей первой истории, написанной вместе '
                                          'с нейросетью? Тогда, ПОЕХАЛИ! Только сначала прочитай инструкцию '
                                          'по использованию бота - жми /help', reply_markup=ReplyKeyboardRemove())
        print(table())
    else:
        bot.send_message(message.chat.id, 'Извини, но на данный момент все свободные места для пользователей заняты :( '
                                          'Попробуй снова через некоторое время', reply_markup=ReplyKeyboardRemove())
        logging.warning('Достигнут лимит пользователей бота')


@bot.message_handler(commands=['help'])
def send_help_message(message):
    if add_user(message.chat.id, message.from_user.username):
        bot.send_message(message.chat.id, 'help', reply_markup=ReplyKeyboardRemove())
        print(get_all_user_texts(message.chat.id))
    else:
        bot.send_message(message.chat.id, 'Извини, но на данный момент все свободные места для пользователей заняты :( '
                                          'Попробуй снова через некоторое время', reply_markup=ReplyKeyboardRemove())
        logging.warning('Достигнут лимит пользователей бота')


@bot.message_handler(commands=['new'])
def ask(message):
    if add_user(message.chat.id, message.from_user.username):
        bot.send_message(message.chat.id, 'choose', reply_markup=create_markup(modes))
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
                    msg = bot.send_message(message.chat.id, 'too long voice')
                    bot.register_next_step_handler(msg, chat)
                file_info = bot.get_file(message.voice.file_id)
                file = bot.download_file(file_info.file_path)
                text = speech_to_text(file)
                set_stt_expenses(message.chat.id, message.voice.duration)
            else:
                msg = bot.send_message(message.chat.id, 'only text')
                bot.register_next_step_handler(msg, chat)
        elif len(message.text) > MAX_LEN_OF_MESSAGE:
            msg = bot.send_message(message.chat.id, 'too long text')
            bot.register_next_step_handler(msg, chat)
        else:
            text = message.text
        start_request(message.chat.id, text=text)
        answer = ask_gpt(message.chat.id, text)
        if message.content_type == 'voice':
            set_tts_expenses(message.chat.id, len(answer))
            answer = text_to_speech(answer, get_voice(message.chat.id))
            msg = bot.send_audio(message.chat.id, answer)
        else:
            msg = bot.send_message(message.chat.id, answer)
        bot.register_next_step_handler(msg, chat)
    elif not check_gpt_limit(message.chat.id):
        bot.send_message(message.chat.id, 'you can only draw', reply_markup=create_markup(modes))
    else:
        bot.send_message(message.chat.id, 'only text or voice', reply_markup=create_markup(modes))


def draw(message):
    if check_kandinsky_limits(message.chat.id) and ((message.content_type == 'text' and not message.text.startswith('/')) or message.content_type == 'voice'):
        prompt = ''
        if message.content_type == 'voice':
            if check_stt_limits(message.chat.id):
                if message.voice.duration > MAX_BLOCKS_IN_MESSAGE * SECONDS_IN_BLOCK:
                    msg = bot.send_message(message.chat.id, 'too long voice')
                    bot.register_next_step_handler(msg, chat)
                file_info = bot.get_file(message.voice.file_id)
                file = bot.download_file(file_info.file_path)
                prompt = speech_to_text(file)
                set_stt_expenses(message.chat.id, message.voice.duration, modes[1])
            else:
                msg = bot.send_message(message.chat.id, 'only text')
                bot.register_next_step_handler(msg, chat)
        elif len(message.text) > MAX_LEN_OF_MESSAGE:
            msg = bot.send_message(message.chat.id, 'too long text')
            bot.register_next_step_handler(msg, chat)
        else:
            prompt = message.text
        start_request(message.chat.id, text=prompt, mode=modes[1])
        image, style = draw_image(message.chat.id, prompt)
        if image:
            msg = bot.send_photo(message.chat.id, image, f'Изображение в стиле {style}')
        else:
            msg = bot.send_message(message.chat.id, 'error in kandinsky')
        bot.register_next_step_handler(msg, draw)
    elif not check_kandinsky_limits(message.chat.id):
        bot.send_message(message.chat.id, 'you can only chat', reply_markup=create_markup(modes))
    else:
        bot.send_message(message.chat.id, 'only text or voice', reply_markup=create_markup(modes))


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
    if text.content_type != 'text':
        msg = bot.send_message(text.chat.id, 'Нужно отправить текстовое сообщение!', reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, tts)
    elif len(text.text) > MAX_LEN_OF_MESSAGE:
        msg = bot.send_message(text.chat.id, f'В этом сообщении больше {MAX_LEN_OF_MESSAGE} символов. '
                                             f'Отправь что-нибудь покороче :)', reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, tts)
    else:
        # set_text(text.chat.id, text.text)
        response = text_to_speech(text.text, get_voice(text.chat.id))
        if response:
            set_tts_expenses(text.chat.id, len(text.text), modes[2])
            bot.send_audio(text.chat.id, response, reply_markup=ReplyKeyboardRemove())
        else:
            bot.send_message(text.chat.id, 'В SpeechKit произошла ошибка. Попробуй снова чуть позже',
                             reply_markup=ReplyKeyboardRemove())


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
    if audio.content_type != 'voice':
        msg = bot.send_message(audio.chat.id, 'Нужно отправить голосовое сообщение!',
                               reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, stt)
    elif audio.voice.duration > MAX_BLOCKS_IN_MESSAGE * SECONDS_IN_BLOCK:
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
            bot.send_message(audio.chat.id, response, reply_markup=ReplyKeyboardRemove())
        else:
            bot.send_message(audio.chat.id, 'В SpeechKit произошла ошибка. Попробуй снова чуть позже',
                             reply_markup=ReplyKeyboardRemove())


@bot.message_handler(content_types=['text'])
def text_message(message):
    if message.text in modes:
        if message.text == modes[0]:
            if check_gpt_limit(message.chat.id):
                msg = bot.send_message(message.chat.id, 'print question', reply_markup=ReplyKeyboardRemove())
                bot.register_next_step_handler(msg, chat)
            else:
                bot.send_message(message.chat.id, 'you can only draw', reply_markup=create_markup(modes))
        elif message.text == modes[1]:
            if check_kandinsky_limits(message.chat.id):
                msg = bot.send_message(message.chat.id, 'print prompt', reply_markup=ReplyKeyboardRemove())
                bot.register_next_step_handler(msg, draw)
            else:
                bot.send_message(message.chat.id, 'you can only chat', reply_markup=create_markup(modes))
        elif message.text == modes[2]:
            tts_limit = check_tts_limits(message.chat.id)
            stt_limit = check_stt_limits(message.chat.id)
            if tts_limit and stt_limit:
                available_modes = []
                if tts_limit:
                    available_modes.append('/tts')
                if stt_limit:
                    available_modes.append('/stt')
                bot.send_message(message.chat.id, 'choose mode', reply_markup=create_markup(available_modes))
            else:
                bot.send_message(message.chat.id, 'no tts and stt', reply_markup=create_markup(modes))
    else:
        bot.send_message(message.chat.id,
                         'Тебе следует воспользоваться командой или кнопкой, другого бот не понимает :(',
                         reply_markup=ReplyKeyboardRemove())


logging.info('starting')
bot.polling()
