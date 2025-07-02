import pyautogui as pi
import time 
import pygetwindow as gw
import logging
import subprocess
from pynput import keyboard 
from threading import Thread
import json
import cv2
import numpy as np
from PIL import Image

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

with open('config/tmp.json', 'r') as f:
    config = json.load(f)

def debug_image(image, filename="debug.png"):
    """Сохраняет изображение для отладки"""
    if image is not None:
        Image.fromarray(image).save(filename)
        logger.info(f"Изображение сохранено как {filename}")

def clicking():
    try:
        # Добавим проверку координат
        logger.info(f"Конфигурация: {config}")
        
        pi.moveTo(850, 616)
        pi.click()
        logger.info("Подарок найден и кликнут.")
        
        pi.moveTo(556, 382)
        time.sleep(3)
        pi.moveTo(911, 238)
        logger.info("Размер региона продемонстрирован")
        time.sleep(3)
        
        # Исправляем двойной вызов capturing()
        cv_region, pil_region = capturing()
        np_region = np.array(pil_region)
        
        # Сохраняем для отладки
        debug_image(np_region, 'region_capture.png')
        
        if np_region.size == 0:
            logger.error("Захвачен пустой регион!")
            return
            
        pil_region.save('region.png')
        
        thresh = get_price_region(np_region)
        if thresh is not None:
            debug_image(thresh, 'threshold.png')
            print(thresh)
        else:
            logger.error("Не удалось получить пороговое изображение")
        
        time.sleep(2)
        pi.moveTo(576, 164)
        pi.click()
        logger.info("Возврат к типу подарка выполнен.")
        time.sleep(1)
        pi.moveTo(850, 616)
        pi.click()
        logger.info("Меню версий подарка обновлено.")
        
    except Exception as e:
        logger.error(f"Ошибка в функции clicking: {str(e)}", exc_info=True)

def capturing(x=None, y=None, width=None, height=None):
    try:
        # Используем значения по умолчанию, если не переданы
        x = x if x is not None else config["MENU_X"]
        y = y if y is not None else config["MENU_Y"]
        width = width if width is not None else config["MENU_WIDTH"]
        height = height if height is not None else config["MENU_HEIGHT"]
        
        logger.info(f"Захват региона: x={x}, y={y}, width={width}, height={height}")
        
        region = pi.screenshot(region=(x, y, width, height))
        
        # Добавим проверку размера
        if region.size[0] == 0 or region.size[1] == 0:
            logger.error("Захвачен пустой регион!")
            return None, None
            
        cv_image = cv2.cvtColor(np.array(region), cv2.COLOR_RGB2BGR)
        return cv_image, region
        
    except Exception as e:
        logger.error(f"Ошибка в функции capturing: {str(e)}", exc_info=True)
        return None, None

def get_price_region(screen):
    try:
        if screen is None or screen.size == 0:
            logger.error("Передано пустое изображение в get_price_region")
            return None
            
        cfg = config['PRICE_DETECTION']
        logger.info(f"Конфигурация ценового региона: {cfg}")
        
        # Корректировка координат с учетом динамического разрешения
        x_start = cfg["MENU_X"]
        y_start = cfg['MENU_Y']
        
        # Проверка выхода за границы изображения
        if (y_start + cfg['MENU_HEIGHT'] > screen.shape[0] or 
            x_start + cfg['MENU_WIDTH'] > screen.shape[1]):
            logger.error(f"Регион цены выходит за границы изображения. Screen: {screen.shape}, Region: {cfg}")
            return None
            
        region = screen[y_start:y_start+cfg['MENU_HEIGHT'], x_start:x_start+cfg['MENU_WIDTH']]
        
        if region.size == 0:
            logger.error("Выделен пустой ценовой регион!")
            return None
            
        debug_image(region, 'price_region_raw.png')
        
        image = Image.fromarray(region)
        image.save('price_region.png')
        
        logger.debug("Извлечена область с ценой в позиции (%d, %d) с размерами (%d, %d)", 
                    x_start, y_start, cfg['MENU_WIDTH'], cfg['MENU_HEIGHT'])
        
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        return thresh
        
    except Exception as e:
        logger.error(f"Ошибка в функции get_price_region: {str(e)}", exc_info=True)
        return None

def activate_telegram():
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

if __name__ == "__main__":
    try:
        logger.info("Запуск скрипта...")
        time.sleep(2)
        activate_telegram()
        clicking()
        logger.info("Скрипт завершен успешно")
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)