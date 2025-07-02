#portals > div:nth-child(2) > div > div > div.modal-dialog > div > button <- кнопка назад
# #portals > div:nth-child(2) > div > div > div.modal-dialog > div > div.Transition.pP8TxefR > div.Transition_slide.Transition_slide-active > div > div > div.Transition_slide.Transition_slide-active > div > div:nth-child(2) > button 

#LeftMainHeader > div.DropdownMenu.main-menu > button  <- меню
#LeftMainHeader > div.DropdownMenu.main-menu > div > div.bubble.menu-container.custom-scroll.with-footer.opacity-transition.fast.left.top.shown.open > div:nth-child(9)  <- Settings
#Settings > div > div.settings-content.custom-scroll.scrolled > div:nth-child(3) > div:nth-child(3)  <- send a gift
#portals > div:nth-child(2) > div > div > div.modal-dialog > div.modal-content.custom-scroll.FuFYE0AA > div > div.yLCbiItq.bXzIGw8s.custom-scroll > div:nth-child(1)  <- Me
#portals > div:nth-child(2) > div > div > div.modal-dialog > div > div.Transition.pP8TxefR > div.Transition_slide.Transition_slide-active > div > div.Transition.kB6IyXqS > div > div > div:nth-child(12) > button  <- single gift
#portals > div:nth-child(2) > div > div > div.modal-dialog > div > div.Transition.pP8TxefR > div.Transition_slide.Transition_slide-active > div > div > div.Transition_slide.Transition_slide-active > div > div:nth-child(1) > button  <- target gift price

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging

PASSWORD=18082008

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_driver():
    driver = webdriver.Safari()
    driver.maximize_window()
    return driver

def login_telegram(driver):
    logger.info("Переход на Telegram Web...")
    driver.get("https://web.telegram.org")
    time.sleep(5)  # Время на загрузку и ручную авторизацию
    logger.info("Пожалуйста, выполните ручную авторизацию. Нажмите Enter после входа...")
    input()
    logger.info("Авторизация завершена.") 
    menu_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#LeftMainHeader > div.DropdownMenu.main-menu > button"))  
    )
    menu_button.click()
    settings_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#LeftMainHeader > div.DropdownMenu.main-menu > div > div.bubble.menu-container.custom-scroll.with-footer.opacity-transition.fast.left.top.shown.open > div:nth-child(9)"))  
    )
    settings_button.click()
    send_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#Settings > div > div.settings-content.custom-scroll.scrolled > div:nth-child(3) > div:nth-child(3)")) 
    )
    send_button.click()
    me_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#portals > div:nth-child(2) > div > div > div.modal-dialog > div.modal-content.custom-scroll.FuFYE0AA > div > div.yLCbiItq.bXzIGw8s.custom-scroll > div:nth-child(1)")) 
    )
    me_button.click()
    single_gift_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#portals > div:nth-child(2) > div > div > div.modal-dialog > div > div.Transition.pP8TxefR > div.Transition_slide.Transition_slide-active > div > div.Transition.kB6IyXqS > div > div > div:nth-child(12) > button")) 
    )
    single_gift_button.click() 
    target_gift_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#portals > div:nth-child(2) > div > div > div.modal-dialog > div > div.Transition.pP8TxefR > div.Transition_slide.Transition_slide-active > div > div > div.Transition_slide.Transition_slide-active > div > div:nth-child(1) > button")) 
    )
    prices = []
    for element in target_gift_button:
        price_text = element.text
        price_match = re.search(r'\d+\.\d{2}', price_text)
        if price_match:
            prices.append(float(price_match.group()))
    logger.info("Извлеченные цены: %s", prices)
    return prices


def extract_prices(driver, gift_selector):
    prices = []
    try:
        gift_elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, gift_selector))
        )[:3]
        for element in gift_elements:
            price_text = element.text
            price_match = re.search(r'\d+\.\d{2}', price_text)
            if price_match:
                prices.append(float(price_match.group()))
        logger.info("Извлеченные цены: %s", prices)
        return prices
    except Exception as e:
        logger.error("Ошибка при извлечении цен: %s", e)
        return []

def process_gifts():
    driver = setup_driver()
    login_telegram(driver)

    logger.info("Пожалуйста, выберите тип подарка и откройте меню версий вручную. Нажмите Enter...")
    input()

    gift_selector = "portals > div:nth-child(2) > div > div > div.modal-dialog > div > div.Transition.pP8TxefR > div.Transition_slide.Transition_slide-active > div > div > div.Transition_slide.Transition_slide-active > div > div:nth-child(2) > button"  # Замените на реальный селектор из Safari
    initial_prices = extract_prices(driver, gift_selector)
    if len(initial_prices) < 3:
        logger.warning("Не удалось извлечь достаточно цен, найдено: %d", len(initial_prices))
        driver.quit()
        return

    average_price = sum(initial_prices) / 3
    logger.info("Средняя цена первых трех подарков: %.2f", average_price)

    close_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "portals > div:nth-child(2) > div > div > div.modal-dialog > div > button"))  # Замените на реальный селектор
    )
    close_button.click()
    time.sleep(1)

    logger.info("Снова выберите тип подарка вручную. Нажмите Enter...")
    input()

    new_prices = extract_prices(driver, gift_selector)
    if len(new_prices) > 0 and new_prices[0] < average_price:
        logger.info("Новый первый подарок с ценой %.2f ниже среднего %.2f", new_prices[0], average_price)
        first_gift = driver.find_elements(By.CSS_SELECTOR, gift_selector)[0]
        first_gift.click()
        logger.info("Подарок куплен.")
    else:
        logger.warning("Новый первый подарок не найден или цена выше среднего (%.2f)", average_price)

    time.sleep(2)
    driver.quit()

if __name__ == "__main__":
    import re
    driver = setup_driver()
    login_telegram(driver)