import requests

from database import count_gpt_tokens, count_user_images, count_speechkit_symbols, count_speechkit_blocks
from limits import MAX_TOKENS_FOR_USER, MAX_IMAGES_FOR_USER, MAX_SYMBOLS_FOR_USER, MAX_BLOCKS_FOR_USER, MAX_GPT_TOKENS
from constants import tables
from config import IAM_TOKEN, FOLDER_ID


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


def get_from_list(value):
    try:
        result = value[0][0]
        if not result:
            result = 0
    except IndexError:
        result = 0
    return result


def all_gpt_tokens(user_id):
    tokens = count_gpt_tokens(user_id)
    return get_from_list(tokens)


def check_gpt_limit(user_id):
    tokens = all_gpt_tokens(user_id)
    return MAX_TOKENS_FOR_USER - tokens >= MAX_GPT_TOKENS


def all_user_images(user_id):
    images = count_user_images(user_id)
    return get_from_list(images)


def check_kandinsky_limits(user_id):
    images = all_user_images(user_id)
    return images < MAX_IMAGES_FOR_USER


def all_speechkit_symbols(user_id):
    symbols = 0
    for t in tables:
        s = count_speechkit_symbols(user_id, t)
        symbols += get_from_list(s)
    return symbols


def check_tts_limits(user_id):
    symbols = all_speechkit_symbols(user_id)
    return MAX_SYMBOLS_FOR_USER - symbols >= MAX_GPT_TOKENS


def all_speechkit_blocks(user_id):
    blocks = 0
    for t in tables:
        b = count_speechkit_blocks(user_id, t)
        blocks += get_from_list(b)
    return blocks


def check_stt_limits(user_id):
    blocks = all_speechkit_blocks(user_id)
    return blocks < MAX_BLOCKS_FOR_USER


def get_user_balance(user_id):
    gpt_tokens = all_gpt_tokens(user_id)
    images = all_user_images(user_id)
    symbols = all_speechkit_symbols(user_id)
    blocks = all_speechkit_blocks(user_id)
    return [
        (gpt_tokens, MAX_TOKENS_FOR_USER),
        (images, MAX_IMAGES_FOR_USER),
        (symbols, MAX_SYMBOLS_FOR_USER),
        (blocks, MAX_BLOCKS_FOR_USER)
    ]
