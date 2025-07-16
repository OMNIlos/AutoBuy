import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from datetime import datetime
from src.config import MENU_SELECTOR, SEND_GIFT, TARGET_CONTACT, SETTINGS_SELECTOR


class TelegramWebNavigator:
    def __init__(self, driver=None):
        self.driver = driver or webdriver.Firefox()
        self.wait = WebDriverWait(self.driver, 30)

    def open_and_auth(self):
        self.driver.maximize_window()
        self.driver.get('https://web.telegram.org')
        time.sleep(2)  # Дать время браузеру открыться
        print("Пожалуйста, авторизуйтесь через QR-код в браузере Telegram Web...")
        time.sleep(10)
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[aria-label*="menu"], button[title*="menu"]')))
        print("Авторизация завершена.")
        time.sleep(2)

    def go_to_gift_menu(self):
        # Открыть меню (гамбургер)
        menu_btn = WebDriverWait(self.driver, 30).until(EC.element_to_be_clickable((By.CSS_SELECTOR, MENU_SELECTOR)))
        menu_btn.click()
        time.sleep(0.5)
        print("Burger Меню открыто.")
        # Открыть Settings по тексту
        settings_btn = WebDriverWait(self.driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '//div[contains(text(), "Settings")]'))
        )
        settings_btn.click()
        time.sleep(0.5)
        print("Settings открыто.")

        # Прокрутка меню Settings вниз
        try:
            settings_menu_container = self.driver.find_element(By.ID, 'Settings')
            self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", settings_menu_container)
            time.sleep(0.5)
        except Exception as e:
            print(f"Не удалось прокрутить меню Settings: {e}")

        # Send a Gift
        send_gift_btn = WebDriverWait(self.driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '//div[contains(text(), "Send a Gift")]'))
        )
        send_gift_btn.click()
        time.sleep(0.5)
        print("Send a Gift открыто.")

        # Выбрать первый контакт
        first_contact = WebDriverWait(self.driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '//div[contains(text(), "First contact")]'))
        )
        first_contact.click()
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