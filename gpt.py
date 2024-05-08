import requests
import logging

from database import get_history, set_answer, set_tokens
from limits import MAX_GPT_TOKENS
from config import IAM_TOKEN, FOLDER_ID
from limitation import count_tokens


def post_request(messages):
    url = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'
    headers = {
        'Authorization': f'Bearer {IAM_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        'modelUri': f'gpt://{FOLDER_ID}/yandexgpt-lite',
        'completionOptions': {
            'stream': False,
            'temperature': 0.5,
            'maxTokens': MAX_GPT_TOKENS
        },
        'messages': messages
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        text = response.json()['result']['alternatives'][0]['message']['text']
    else:
        error_message = response.text
        logging.error(f'Ошибка GPT - {error_message}')
        text = ''
    return text


def ask_gpt(user_id, question):
    system_prompt = ('Ты вежливо и участливо отвечаешь на вопросы пользователя, можешь продолжить диалог исходя '
                     'из истории переписки с ним.')
    messages = [{'role': 'system', 'text': system_prompt}]
    history = get_history(user_id)[:-1]
    for i in history:
        messages.append({'role': 'user', 'text': i[0]})
        messages.append({'role': 'assistant', 'text': i[1]})
    messages.append({'role': 'user', 'text': question})
    print(messages)
    answer = post_request(messages)
    if answer:
        set_tokens(user_id, count_tokens(answer))
    else:
        answer = 'В YandexGPT произошла ошибка. Попробуй снова чуть позже'
    set_answer(user_id, answer)
    return answer
