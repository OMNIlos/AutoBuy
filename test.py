import cv2
import numpy as np
import time
import re
import pytesseract
import pyautogui
import logging
import os
from PIL import ImageChops, Image
import matplotlib.pyplot as plt
import pygetwindow as gw
import sys


# Константы
WIDTH = 350  # Ширина региона меню
HEIGHT = 450  # Высота региона меню
MENU_X_OFFSET = 0  # Смещение X внутри окна
MENU_Y_OFFSET = 20  # Смещение Y внутри окна
MAX_SCROLL_ATTEMPTS = 50
SCROLL_STEP = -10
THRESHOLD = 0.8

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def capture():
    """Захват скриншота без сохранения."""
    return pyautogui.screenshot()

def images_are_same(img1, img2):
    """Сравнение двух изображений на идентичность."""
    diff = ImageChops.difference(img1, img2)
    return diff.getbbox() is None

def capture_screen():
    """Захват экрана и сохранение в файл."""
    folder = '/Users/ilagulakin/Desktop/script/Script_Telegram_2'
    os.makedirs(folder, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(folder, f'screenshot_{timestamp}.png')
    screenshot = pyautogui.screenshot()
    screenshot.save(path)
    logger.info("Снимок экрана сохранен в %s", path)
    return path, np.array(screenshot)

def is_valid_region(x, y, width, height):
    """Проверка, находится ли регион в пределах экрана."""
    screen_width, screen_height = pyautogui.size()
    return (x >= 0 and y >= 0 and x + width <= screen_width and y + height <= screen_height)

def activate_telegram():
    if sys.platform == "win32":
        import pygetwindow as gw
        titles = gw.getAllTitles()
        for title in titles:
            if "Telegram" in title:
                logger.info("Найден заголовок Telegram: %s", title)
                win = gw.getWindowsWithTitle(title)[0]
                win.activate()
                time.sleep(0.5)
                return win.left, win.top, win.width, win.height
        logger.warning("Окно Telegram не найдено.")
        return None, None, None, None

    elif sys.platform == "darwin":
        import subprocess

        def try_app(app_name):
            script = f'''
            tell application "{app_name}" to activate
            delay 0.5
            tell application "System Events"
                set appName to "{app_name}"
                try
                    set appProc to first application process whose name is appName
                    set win to first window of appProc
                    set pos to position of win
                    set sz to size of win
                    return (item 1 of pos as text) & "," & (item 2 of pos as text) & "," & (item 1 of sz as text) & "," & (item 2 of sz as text)
                on error errMsg
                    return "ERROR:" & errMsg
                end try
            end tell
            '''
            result = subprocess.check_output(['osascript', '-e', script])
            decoded = result.decode().strip()
            if decoded.startswith("ERROR:"):
                return None
            return [int(x) for x in decoded.split(',')]

        # Пробуем оба варианта названия приложения
        for app_name in ["Telegram", "Telegram Desktop"]:
            res = try_app(app_name)
            if res:
                logger.info(f"Окно {app_name} найдено.")
                return tuple(res)
        logger.warning("Окно Telegram не найдено.")
        return None, None, None, None

    else:
        logger.error("ОС не поддерживается этим скриптом.")
        return None, None, None, None


def find_and_purchase_gift():
    template_path = 'templates/gift4.png'
    template = cv2.imread(template_path, 0)
    if template is None:
        logger.error("Шаблон подарка не найден по пути: %s", template_path)
        return False

    max_scroll_attempts = MAX_SCROLL_ATTEMPTS
    scroll_step = SCROLL_STEP
    threshold = THRESHOLD
    template_height, template_width = template.shape

    # Получение координат окна Telegram
    win_x, win_y, win_width, win_height = activate_telegram()
    print("win_x, win_y, win_width, win_height:", win_x, win_y, win_width, win_height)
    if win_x is None:
        logger.error("Не удалось получить координаты окна Telegram, используется ручная настройка.")
        win_x, win_y = 0, 38  # Ручные значения из [0, 38, 1470, 839]
        win_width, win_height = 1470, 839
    logger.info("Координаты окна Telegram: (%d, %d), размер: %dx%d", win_x, win_y, win_width, win_height)

    # Определение региона меню внутри окна, начиная от точки (640, 340)
    base_x = 562  # Базовая X-координата клика внутри окна
    base_y = 340  # Базовая Y-координата клика внутри окна
    menu_x = base_x # Смещение от левого края окна win_x + base_x + MENU_X_OFFSET
    menu_y = win_y + base_y + MENU_Y_OFFSET  # Смещение от верхнего края окна
    menu_width, menu_height = WIDTH, HEIGHT
    if not is_valid_region(menu_x, menu_y, menu_width, menu_height):
        logger.error("Регион (%d, %d, %d, %d) выходит за пределы экрана. Корректировка...",
                     menu_x, menu_y, menu_width, menu_height)
        menu_y = max(win_y, min(menu_y, win_y + win_height - menu_height))
        logger.info("Используется скорректированный регион: (%d, %d, %d, %d)", menu_x, menu_y, menu_width, menu_height)

    for attempt in range(max_scroll_attempts):
        logger.info("Попытка %d: поиск подарка...", attempt + 1)
        try:
            region = pyautogui.screenshot(region=(menu_x, menu_y, menu_width, menu_height))
            region.save('region.png')  # Сохраняем регион для отладки
            screen = cv2.cvtColor(np.array(region), cv2.COLOR_RGB2GRAY)
            result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= threshold)

            if len(locations[0]) > 0:
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                y, x = max_loc
                # Переводим координаты в глобальные относительно исходного региона
                center_x = menu_x + x + template_width // 2
                center_y = menu_y + y + template_height // 2
                logger.info("Подарок найден в позиции (центр: %d, %d) с уверенностью %f", center_x, center_y, max_val)
                logger.info("Локальные координаты: x=%d, y=%d", x, y)

                pyautogui.moveTo(center_x, center_y)
                time.sleep(0.5)
                pyautogui.click()
                logger.info("Клик выполнен по центру подарка в (%d, %d)", center_x, center_y)
                time.sleep(2)
                return True
        except Exception as e:
            logger.error("Ошибка при захвате региона: %s", e)
            break

        logger.info("Подарок не найден, выполняем прокрутку...")
        pyautogui.moveTo(menu_x + menu_width // 2, menu_y + menu_height - 50)
        pyautogui.scroll(scroll_step)
        time.sleep(1)

    logger.warning("Подарок не найден после %d попыток прокрутки", max_scroll_attempts)
    return False

def navigate_to_gifts():
    try:
        win_x, win_y, win_width, win_height = activate_telegram()
        if win_x is not None:
            time.sleep(0.5)
        else:
            logger.warning("Не удалось активировать окно Telegram — убедитесь, что оно открыто.")
    except Exception as e:
        logger.warning("Ошибка активации окна Telegram: %s", e)
    logger.info("Начинаем навигацию в меню подарков.")
    pyautogui.moveTo(403, 856)  # Settings
    pyautogui.click()
    time.sleep(1)
    previous = capture()
    time.sleep(2)
    while True:
        pyautogui.scroll(-500)
        time.sleep(0.5)
        current = capture()
        if images_are_same(previous, current):
            print("Достигнут конец страницы.")
            break
        previous = current

    pyautogui.moveTo(284, 667)  # Send a Gift
    pyautogui.click()
    time.sleep(1)
    pyautogui.moveTo(687, 364)  # Первый контакт
    pyautogui.click()
    time.sleep(1)
    logger.info("Навигация в меню подарков завершена.")
    pyautogui.moveTo(734, 531)  # Предположительно, дополнительный клик
    if find_and_purchase_gift():
        logger.info("Подарок успешно найден и куплен.")
    else:
        logger.warning("Не удалось найти подарок.")

    path, screenshot = capture_screen()
    return path, screenshot

# Задержка перед началом
time.sleep(3)
cortage = navigate_to_gifts()
print(cortage)
if cortage[1] is not None:
    plt.imshow(cortage[1])
    plt.axis('off')
    plt.show()
else:
    logger.error("Не удалось отобразить изображение.")
logger.info("Скриншот сохранен по пути: %s", cortage[0])
logger.info("Ожидание перед завершением скрипта...")
time.sleep(10)