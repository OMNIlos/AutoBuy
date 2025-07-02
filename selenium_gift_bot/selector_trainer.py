import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

CONFIG_PATH = 'config/gift_selector.json'


def save_selector(selector):
    with open(CONFIG_PATH, 'w') as f:
        json.dump({'gift_selector': selector}, f, ensure_ascii=False, indent=2)
    print(f"Селектор сохранён: {selector}")

def main():
    driver = webdriver.Safari()
    driver.maximize_window()
    driver.get('https://web.telegram.org')
    print("Пожалуйста, авторизуйтесь через QR-код и нажмите Enter...")
    input()
    print("Навигируйте вручную до меню с подарками, затем нажмите Enter...")
    input()
    print("Наведите мышь на нужный подарок и кликните по нему в окне браузера. Селектор будет определён автоматически.")

    # Вставляем JS для отслеживания клика и получения селектора
    js = '''
    window._gift_selector = null;
    document.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        let el = e.target;
        function getSelector(el) {
            if (el.id) return '#' + el.id;
            if (el.className && typeof el.className === 'string') {
                return el.tagName.toLowerCase() + '.' + el.className.trim().replace(/\s+/g, '.');
            }
            return el.tagName.toLowerCase();
        }
        let path = [];
        while (el && el.nodeType === 1 && el !== document.body) {
            path.unshift(getSelector(el));
            el = el.parentElement;
        }
        window._gift_selector = path.join(' > ');
    }, {once: true});
    '''
    driver.execute_script(js)
    print("Сделайте клик по нужному подарку в браузере...")
    # Ждем, пока JS не запишет селектор
    selector = None
    for _ in range(60):
        selector = driver.execute_script('return window._gift_selector;')
        if selector:
            break
        time.sleep(1)
    if selector:
        save_selector(selector)
    else:
        print("Не удалось определить селектор. Попробуйте снова.")
    driver.quit()

if __name__ == '__main__':
    main() 