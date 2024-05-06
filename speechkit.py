import requests
from config import IAM_TOKEN, FOLDER_ID


def text_to_speech(text, voice):
    headers = {
        'Authorization': f'Bearer {IAM_TOKEN}',
    }
    data = {
        'text': text,
        'lang': 'ru-RU',
        'voice': voice,
        'folderId': FOLDER_ID,
    }

    response = requests.post('https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize', headers=headers, data=data)

    if response.status_code == 200:
        return response.content
    return False


def speech_to_text(audio):
    headers = {
        'Authorization': f'Bearer {IAM_TOKEN}',
    }
    params = '&'.join([
        'topic=general',
        f'folderId={FOLDER_ID}',
        'lang=ru-RU'
    ])

    response = requests.post(
        f'https://stt.api.cloud.yandex.net/speech/v1/stt:recognize?{params}',
        headers=headers,
        data=audio
    )
    answer = response.json()

    if answer.get('error_code') is None:
        return answer.get('result')
    return False
