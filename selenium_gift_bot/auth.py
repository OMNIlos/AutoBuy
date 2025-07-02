import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from datetime import datetime
from selenium_gift_bot.config import MENU_SELECTOR, SEND_GIFT, TARGET_CONTACT

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), 'screenshots')

def save_screenshot(driver, step_name):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(SCREENSHOT_DIR, f'{step_name}_{ts}.png')
    driver.save_screenshot(path)
    print(f'Скриншот сохранён: {path}')

class TelegramWebNavigator:
    def __init__(self, driver=None):
        self.driver = driver or webdriver.Safari()
        self.wait = WebDriverWait(self.driver, 20)

    def open_and_auth(self):
        self.driver.get('https://web.telegram.org')
        save_screenshot(self.driver, 'open_telegram')
        print("Пожалуйста, авторизуйтесь через QR-код и нажмите Enter...")
        input()
        save_screenshot(self.driver, 'after_auth')
        print("Авторизация завершена.")

    def go_to_gift_menu(self):
        # Открыть меню (гамбургер)
        menu_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, MENU_SELECTOR)))
        menu_btn.click()
        save_screenshot(self.driver, 'menu_opened')
        time.sleep(0.5)
        # Открыть Settings по тексту
        menu_items = self.wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[role="menuitem"].MenuItem.compact'))
        )
        settings_btn = None
        for item in menu_items:
            if "Settings" in item.text:
                settings_btn = item
                break
        if not settings_btn:
            raise Exception("Settings menu item not found!")
        settings_btn.click()
        save_screenshot(self.driver, 'settings_opened')
        time.sleep(0.5)
        # Send a Gift
        send_gift_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, SEND_GIFT)))
        send_gift_btn.click()
        save_screenshot(self.driver, 'send_gift_opened')
        time.sleep(0.5)
        # Первый контакт
        first_contact = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, TARGET_CONTACT)))
        first_contact.click()
        save_screenshot(self.driver, 'first_contact_selected')
        time.sleep(0.5)
        print("Меню подарков открыто. Можно продолжать.")

    def close(self):
        self.driver.quit()

if __name__ == '__main__':
    nav = TelegramWebNavigator()
    nav.open_and_auth()
    nav.go_to_gift_menu()
    input("Проверьте, что меню подарков открыто. Нажмите Enter для выхода...")
    nav.close() 