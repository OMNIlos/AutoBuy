import json

CONFIG_PATH = 'config/config.json'
SELECTOR_PATH = 'config/gift_selector.json'
VARIANT_SELECTOR = '#portals > div:nth-child(2) > div > div > div.modal-dialog > div > div.Transition.pP8TxefR > div.Transition_slide.Transition_slide-active > div > div > div.Transition_slide.Transition_slide-active > div > div:nth-child(1)'
BUY_BUTTON_SELECTOR = '#portals > div:nth-child(3) > div > div.modal-container > div.modal-dialog > div.modal-content.custom-scroll.KYHkJ9Qf > div.bho0GTYt > button'  # замените на реальный селектор кнопки покупки


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

MENU_SELECTOR = '#LeftMainHeader > div.DropdownMenu.main-menu > button'
SETTINGS_SELECTOR = '#LeftMainHeader > div.DropdownMenu.main-menu > div > div.bubble.menu-container.custom-scroll.with-footer.opacity-transition.fast.left.top.shown.open > div:nth-child(9)'
SEND_GIFT = '#Settings > div > div.settings-content.custom-scroll.scrolled > div:nth-child(3) > div:nth-child(3) > div'
TARGET_CONTACT = '#portals > div:nth-child(2) > div > div > div.modal-dialog > div.modal-content.custom-scroll.FuFYE0AA > div > div.yLCbiItq.bXzIGw8s.custom-scroll > div:nth-child(1)'
TARGET_TYPE_GIFT = '#portals > div:nth-child(2) > div > div > div.modal-dialog > div > div.Transition.pP8TxefR > div > div > div.Transition.kB6IyXqS > div > div > div:nth-child(14)'
TARGET_GIFT = '#portals > div:nth-child(2) > div > div > div.modal-dialog > div > div.Transition.pP8TxefR > div.Transition_slide.Transition_slide-active > div > div > div.Transition_slide.Transition_slide-active > div > div:nth-child(1)'
TARGET_PRICE = '#portals > div:nth-child(2) > div > div > div.modal-dialog > div > div.Transition.pP8TxefR > div.Transition_slide.Transition_slide-active > div > div > div.Transition_slide.Transition_slide-active > div > div:nth-child(1) > button > i'
SECOND_PRICE = '#portals > div:nth-child(2) > div > div > div.modal-dialog > div > div.Transition.pP8TxefR > div.Transition_slide.Transition_slide-active > div > div > div.Transition_slide.Transition_slide-active > div > div:nth-child(2) > button > i'
THIRD_PRICE = '#portals > div:nth-child(2) > div > div > div.modal-dialog > div > div.Transition.pP8TxefR > div.Transition_slide.Transition_slide-active > div > div > div.Transition_slide.Transition_slide-active > div > div:nth-child(3) > button > i'
RETURN_TO_TYPE_GIFT_BUTTON = '#portals > div:nth-child(2) > div > div > div.modal-dialog > div > button'
PAY_BUTTON_FOR_TARGET_GIFT = '#portals > div:nth-child(3) > div > div.modal-container > div.modal-dialog > div.modal-content.custom-scroll.KYHkJ9Qf > div.bho0GTYt > button'
EXIT_FROM_PAYING_GIFT_BUTTON = '#portals > div:nth-child(3) > div > div.modal-container > div.modal-dialog > div.ie9tImaj > div > div.WA0INleU.rJOB1u5Q'
