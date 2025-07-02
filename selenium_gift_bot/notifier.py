import requests
from selenium_gift_bot.config import load_config

def send_telegram_notification(message):
    config = load_config()
    token = config.get('telegram_bot_token')
    chat_id = config.get('telegram_chat_id')
    if not token or not chat_id:
        print('Не указан токен или chat_id для Telegram!')
        return
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = {'chat_id': chat_id, 'text': message}
    try:
        resp = requests.post(url, data=payload, timeout=10)
        if not resp.ok:
            print(f'Ошибка отправки уведомления: {resp.text}')
    except Exception as e:
        print(f'Ошибка отправки уведомления: {e}') 