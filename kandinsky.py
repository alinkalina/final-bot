import requests
import json
import time
import base64
import random
import logging
from database import set_answer
from constants import modes
from config import X_KEY, X_SECRET


def get_model(headers):
    response = requests.get('https://api-key.fusionbrain.ai/key/api/v1/models', headers=headers)
    data = response.json()
    return data[0]['id']


def get_styles():
    response = requests.get('http://cdn.fusionbrain.ai/static/styles/api')
    return response.json()


def generate_image(prompt, headers):
    styles = get_styles()
    style = random.choice(styles)
    url = 'https://api-key.fusionbrain.ai/key/api/v1/text2image/run'
    params = {
        'type': 'GENERATE',
        'style': style['name'],
        'numImages': 1,
        'width': 1024,
        'height': 1024,
        'generateParams': {
            'query': prompt
        }
    }
    data = {
        'model_id': (None, get_model(headers)),
        'params': (None, json.dumps(params), 'application/json')
    }

    response = requests.post(url, headers=headers, files=data)
    return response.json()['uuid'], style['title']


def check_generation(request_id, headers):
    attempts = 20
    delay = 10
    while attempts > 0:
        response = requests.get('https://api-key.fusionbrain.ai/key/api/v1/text2image/status/' + request_id,
                                headers=headers)
        data = response.json()
        if data['status'] == 'DONE':
            return data['images'][0]
        attempts -= 1
        time.sleep(delay)
    logging.error('Слишком долгая генерация в Kandinsky')
    return ''


def draw_image(user_id, prompt):
    headers = {
        'X-Key': f'Key {X_KEY}',
        'X-Secret': f'Secret {X_SECRET}',
    }
    uuid, style = generate_image(prompt, headers)
    code = check_generation(uuid, headers)
    set_answer(user_id, code, modes[1], style)
    if code:
        image = base64.b64decode(code)
        return image, style
    return False, ''
