import requests
import time
import json

# Загрузка токена из config/config.json
with open('config/config.json', 'r') as f:
    config = json.load(f)
TOKEN = config.get('telegram_bot_token')
if not TOKEN:
    print('Не найден telegram_bot_token в config/config.json!')
    exit(1)

URL = f'https://api.telegram.org/bot{TOKEN}/'

def get_updates(offset=None):
    params = {'timeout': 100, 'offset': offset}
    resp = requests.get(URL + 'getUpdates', params=params)
    return resp.json()

def send_message(chat_id, text):
    params = {'chat_id': chat_id, 'text': text}
    requests.post(URL + 'sendMessage', params=params)

def main():
    print('Бот для выдачи chat_id запущен. Ожидает команду /get_chat_id...')
    last_update_id = None
    while True:
        updates = get_updates(last_update_id)
        for update in updates.get('result', []):
            last_update_id = update['update_id'] + 1
            message = update.get('message')
            if not message:
                continue
            text = message.get('text', '')
            chat_id = message['chat']['id']
            if text == '/get_chat_id':
                send_message(chat_id, f'Ваш chat_id: {chat_id}')
        time.sleep(1)

if __name__ == '__main__':
    try:
        main() 
    except KeyboardInterrupt:
        print('Бот остановлен пользователем.') 