import time
import re
import os
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_gift_bot.config import (
    load_gift_selector, TARGET_TYPE_GIFT, TARGET_GIFT, TARGET_PRICE, SECOND_PRICE, THIRD_PRICE,
    RETURN_TO_TYPE_GIFT_BUTTON, PAY_BUTTON_FOR_TARGET_GIFT, EXIT_FROM_PAYING_GIFT_BUTTON
)
from selenium_gift_bot.notifier import send_telegram_notification

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), 'screenshots')

def save_screenshot(driver, step_name):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(SCREENSHOT_DIR, f'{step_name}_{ts}.png')
    driver.save_screenshot(path)
    print(f'Скриншот сохранён: {path}')

class GiftBuyer:
    def __init__(self, driver, wait=None):
        self.driver = driver
        self.wait = wait or WebDriverWait(driver, 40)
        self.type_gift_selector = load_gift_selector() or TARGET_TYPE_GIFT

    def open_type_gift(self):
        type_gift = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, self.type_gift_selector)))
        type_gift.click()
        time.sleep(0.5)
        save_screenshot(self.driver, 'type_gift_opened')

    def get_prices(self):
        # Получить цены первых трёх вариантов подарка
        price1 = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, TARGET_PRICE))).text
        price2 = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, SECOND_PRICE))).text
        price3 = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, THIRD_PRICE))).text
        def parse_price(text):
            match = re.search(r'[\d,]+', text.replace('\u202f', '').replace(' ', ''))
            return int(match.group().replace(',', '')) if match else 0
        return [parse_price(price1), parse_price(price2), parse_price(price3)]

    def buy_gift_if_profitable(self):
        while True:
            self.open_type_gift()
            save_screenshot(self.driver, 'variants_list')
            try:
                prices = self.get_prices()
            except Exception as e:
                print(f'Ошибка получения цен: {e}')
                self.close_variant_menu()
                continue
            if len(prices) < 3:
                print('Не удалось получить цены трёх вариантов. Повтор...')
                self.close_variant_menu()
                continue
            avg = sum(prices) / 3
            print(f'Цены: {prices}, среднее: {avg:.2f}')
            if prices[0] < avg:
                print(f'Первая цена {prices[0]} ниже среднего. Покупаем!')
                # Клик по первому варианту подарка
                first_gift = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, TARGET_GIFT)))
                first_gift.click()
                time.sleep(0.5)
                save_screenshot(self.driver, 'variant_selected')
                # Кнопка покупки
                buy_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, PAY_BUTTON_FOR_TARGET_GIFT)))
                buy_btn.click()
                save_screenshot(self.driver, 'after_buy_click')
                send_telegram_notification(f'Подарок куплен за {prices[0]} ⭐')
                time.sleep(2)
                # Закрыть окно оплаты, если оно появилось
                try:
                    exit_btn = self.driver.find_element(By.CSS_SELECTOR, EXIT_FROM_PAYING_GIFT_BUTTON)
                    exit_btn.click()
                    save_screenshot(self.driver, 'exit_from_paying_gift')
                except Exception:
                    pass
            else:
                print('Цена невыгодна, перезапуск меню вариантов...')
                self.close_variant_menu()
            time.sleep(1)

    def close_variant_menu(self):
        close_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, RETURN_TO_TYPE_GIFT_BUTTON)))
        close_btn.click()
        time.sleep(0.5)
        save_screenshot(self.driver, 'variant_menu_closed')