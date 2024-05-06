from database import count_gpt_tokens, count_speechkit_blocks, count_speechkit_symbols, count_user_images
from limits import MAX_SYMBOLS_FOR_USER, MAX_TOKENS_FOR_USER, MAX_GPT_TOKENS, MAX_BLOCKS_FOR_USER, modes, MAX_IMAGES_FOR_USER
from config import IAM_TOKEN, FOLDER_ID
import requests


def count_tokens(text):
    url = 'https://llm.api.cloud.yandex.net/foundationModels/v1/tokenize'
    headers = {
        'Authorization': f'Bearer {IAM_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        'modelUri': f'gpt://{FOLDER_ID}/yandexgpt/latest',
        'maxTokens': MAX_GPT_TOKENS,
        'text': text
    }
    response = requests.post(url, headers=headers, json=data)
    return len(response.json()['tokens'])


def check_gpt_limit(user_id):
    try:
        tokens = count_gpt_tokens(user_id)[0][0]
        if not tokens:
            tokens = 0
    except IndexError:
        tokens = 0
    return MAX_TOKENS_FOR_USER - tokens >= MAX_GPT_TOKENS


def check_speechkit_limits(user_id):
    try:
        blocks = count_speechkit_blocks(user_id)[0][0]
        symbols = count_speechkit_symbols(user_id)[0][0]
        if not blocks:
            blocks = 0
        if not symbols:
            symbols = 0
    except IndexError:
        blocks, symbols = 0, 0
    return (blocks < MAX_BLOCKS_FOR_USER) and (MAX_SYMBOLS_FOR_USER - symbols >= MAX_GPT_TOKENS)


def check_kandinsky_limits(user_id):
    try:
        images = count_user_images(user_id)[0][0]
        if not images:
            images = 0
    except IndexError:
        images = 0
    return images < MAX_IMAGES_FOR_USER


def check_stt_limits(user_id):
    try:
        blocks = count_speechkit_blocks(user_id, modes[1])[0][0]
        if not blocks:
            blocks = 0
    except IndexError:
        blocks = 0
    return blocks < MAX_BLOCKS_FOR_USER


# def available_blocks(user_id):
#     blocks = count_stt_request(user_id)
#
#
# def available_symbols(user_id):
#     symbols = check_tts_limits(user_id)[1]
#     if MAX_SYMBOLS_FOR_USER - symbols >= MAX_SYMBOLS_IN_MESSAGE:
#         return MAX_SYMBOLS_IN_MESSAGE
#     return MAX_SYMBOLS_FOR_USER - symbols
