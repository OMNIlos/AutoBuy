import json
from src.config_constants import (CONFIG_PATH, SELECTOR_PATH, VARIANT_SELECTOR, BUY_BUTTON_SELECTOR)

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def load_gift_selector():
    with open(SELECTOR_PATH, 'r') as f:
        data = json.load(f)
        return data.get('gift_selector', None)

def save_gift_selector(selector):
    with open(SELECTOR_PATH, 'w') as f:
        json.dump({'gift_selector': selector}, f, ensure_ascii=False, indent=2)

def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)