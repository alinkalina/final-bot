import requests
from config import X_KEY, X_SECRET
import json
import time
import base64
from database import set_answer
from limits import modes
import random


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
        print(data)
        if data['status'] == 'DONE':
            print('done')
            return data['images'][0]
        attempts -= 1
        time.sleep(delay)
    print('fail')
    return ''


def draw_image(user_id, prompt):
    print('start')
    headers = {
        'X-Key': f'Key {X_KEY}',
        'X-Secret': f'Secret {X_SECRET}',
    }
    uuid, style = generate_image(prompt, headers)
    print(style)
    code = check_generation(uuid, headers)
    set_answer(user_id, code, modes[1], style)
    if code:
        image = base64.b64decode(code)
        with open('test.jpg', 'wb') as f:
            f.write(image)
        f.close()
        return image, style
    return False, ''
