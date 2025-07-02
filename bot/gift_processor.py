import cv2
import numpy as np
import time
import re
import pytesseract
import pyautogui
import logging
from bot.enums import FilterType

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GiftProcessor:
    def __init__(self, config, filters, error_logger, stop_event):
        self.config = config
        self.filters = filters
        self.templates = {
            'gift': cv2.imread('templates/gift.png', 0)
        }
        self.stop_event = stop_event
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info("Размеры экрана: %dx%d", self.screen_width, self.screen_height)
        logger.info("GiftProcessor инициализирован с конфигурацией: %s", self.config)

    def capture_screen(self):
        screenshot = pyautogui.screenshot()
        logger.debug("Снимок экрана сделан.")
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    def detect_gifts(self, screen):
        detected = []
        logger.debug("Поиск подарков на экране.")
        for name, template in self.templates.items():
            if template is None:
                logger.warning("Шаблон для '%s' не найден, пропускаем.", name)
                continue
            try:
                if template.shape[0] > screen.shape[0] or template.shape[1] > screen.shape[1]:
                    logger.debug("Размер шаблона больше экрана, пропускаем.")
                    continue
                res = cv2.matchTemplate(cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY), template, cv2.TM_CCOEFF_NORMED)
                loc = np.where(res >= self.config['template_threshold'])
                for pt in zip(*loc[::-1]):
                    detected.append({'position': pt, 'type': name, 'confidence': res[pt[1], pt[0]]})
                    logger.debug("Подарок найден в позиции %s с уверенностью %f", pt, res[pt[1], pt[0]])
            except Exception as e:
                logger.error("Ошибка при сопоставлении шаблона для %s: %s", name, e)
        detected = self.remove_duplicates(detected)
        logger.debug("Обнаруженные подарки после удаления дубликатов: %d", len(detected))
        return detected

    def extract_gift_details(self, screen, gift):
        details = {'price': None, 'timestamp': time.time()}
        logger.debug("Извлечение деталей подарка в позиции %s", gift['position'])
        
        if self.filters[FilterType.PRICE]:
            price_region = self.get_price_region(screen, gift['position'])
            extracted_price = self.parse_price(price_region)
            details['price'] = extracted_price if extracted_price is not None else 15
        
        if self.filters[FilterType.NOVELTY]:
            details['novelty_score'] = self.calculate_novelty(gift['position'])
        
        logger.debug("Извлеченные детали подарка: %s", details)
        return {**gift, **details}


    def get_price_region(self, screen, position):
        x, y = position
        cfg = self.config['price_detection']
        # Корректировка координат с учетом динамического разрешения
        max_x = self.screen_width - cfg['width']
        max_y = self.screen_height - cfg['height']
        x_start = max(0, min(x + cfg['x_offset'], max_x))
        y_start = max(0, min(y + cfg['y_offset'], max_y))
        region = screen[y_start:y_start + cfg['height'], x_start:x_start + cfg['width']]
        if region.size == 0:
            logger.warning("Область цены выходит за пределы экрана, позиция: (%d, %d)", x, y)
            return np.zeros((cfg['height'], cfg['width']), dtype=np.uint8)
        logger.debug("Извлечена область с ценой в позиции (%d, %d) с размерами (%d, %d)", x_start, y_start, cfg['width'], cfg['height'])
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        return thresh

    def parse_price(self, image):
        try:
            config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
            text = pytesseract.image_to_string(image, config=config)
            logger.debug("Извлеченный текст OCR: '%s'", text)  # Логируем текст
            if not text.strip():
                cv2.imwrite(f"error_price_{time.time()}.png", image)  # Сохраняем изображение
                logger.warning("OCR вернул пустой текст")
                return None
            price = int(re.search(r'\d+', text).group())
            logger.debug("Цена, извлеченная с изображения: %d", price)
            return price
        except Exception as e:
            cv2.imwrite(f"error_price_{time.time()}.png", image)  # Сохраняем при ошибке
            logger.warning("Не удалось извлечь цену: %s", e)
            return None

    def calculate_novelty(self, position):
        x, y = position
        novelty = 1 - (max(0, min(x, self.screen_width)) / self.screen_width)
        logger.debug("Рассчитана новизна для позиции %s: %f", position, novelty)
        return novelty

    def remove_duplicates(self, gifts):
        unique = []
        logger.debug("Удаляем дубликаты среди найденных подарков.")
        for gift in sorted(gifts, key=lambda x: -x['confidence']):
            if not any(self.is_same_gift(gift, u) for u in unique):
                unique.append(gift)
                logger.debug("Добавлен подарок в уникальный список: %s", gift)
        logger.debug("Уникальные подарки после удаления дубликатов: %d", len(unique))
        return unique

    def is_same_gift(self, g1, g2):
        dist = np.sqrt((g1['position'][0] - g2['position'][0]) ** 2 + (g1['position'][1] - g2['position'][1]) ** 2)
        same = dist < self.config['duplicate_threshold']
        logger.debug("Проверка, являются ли подарки одинаковыми: %s vs %s, результат: %s", g1, g2, same)
        return same

    def apply_filters(self, gifts):
        filtered = []
        logger.debug("Применяем фильтры к подаркам.")
        for gift in gifts:
            if self.filters[FilterType.PRICE] and not self.is_price_valid(gift.get('price')):
                logger.debug("Подарок %s не прошел фильтр по цене.", gift)
                continue
            if gift['confidence'] < self.config['template_threshold']:
                logger.debug("Подарок %s не прошел фильтр по уверенности.", gift)
                continue
            filtered.append(gift)

        if self.filters[FilterType.NOVELTY]:
            filtered.sort(key=lambda x: (-x.get('novelty_score', 0), x.get('price', float('inf'))))
        else:
            filtered.sort(key=lambda x: x.get('price', float('inf')))
        
        logger.debug("Количество отфильтрованных подарков: %d", len(filtered))
        return filtered[:self.config['max_gifts_per_scan']]

    def is_price_valid(self, price):
        if price is None:
            logger.debug("Цена не указана: %s", price)
            return False
        valid = self.config['gift_price_min'] <= price <= self.config['gift_price_max']
        logger.debug("Проверка, валидна ли цена %d: %s", price, valid)
        return valid

    def purchase_gift(self, gift):
        try:
            x, y = gift['position']
            screen_width, screen_height = pyautogui.size()

            x = int(x * screen_width / self.config['screen_resolution'][1])
            y = int(y * screen_height / self.config['screen_resolution'][0])

            if 0 <= x < screen_width and 0 <= y < screen_height:
                pyautogui.moveTo(x, y)
                pyautogui.click(x, y)
                logger.info(f"Клик по подарку в позиции ({x}, {y}).")

                time.sleep(1)

                screen = pyautogui.screenshot()
                screen_np = np.array(screen)
                gray = cv2.cvtColor(screen_np, cv2.COLOR_RGB2GRAY)

                data = pytesseract.image_to_data(gray, lang='rus', output_type=pytesseract.Output.DICT)

                for i, word in enumerate(data['text']):
                    if word.lower().startswith('купить'):
                        x_btn = data['left'][i] + data['width'][i] // 2
                        y_btn = data['top'][i] + data['height'][i] // 2
                        pyautogui.moveTo(x_btn, y_btn)
                        pyautogui.click()
                        logger.info(f"Клик по кнопке '{word}' в позиции ({x_btn}, {y_btn}).")
                        return

                logger.warning("Кнопка 'Купить подарок' не найдена на экране.")
            else:
                logger.warning(f"Координаты ({x}, {y}) выходят за пределы экрана.")
        except Exception as e:
            logger.error(f"Ошибка при попытке купить подарок: {e}")

    def monitor_and_process(self):
        logger.info("Начинаем мониторинг и обработку.")
        while not self.stop_event.is_set():
            screen = self.capture_screen()
            gifts = self.detect_gifts(screen)
            processed_gifts = []

            for gift in gifts:
                gift_details = self.extract_gift_details(screen, gift)
                processed_gifts.append(gift_details)

            filtered_gifts = self.apply_filters(processed_gifts)
            self.log_filtered_gifts(filtered_gifts)

            for gift in filtered_gifts:
                self.purchase_gift(gift)

            for _ in range(self.config['monitor_interval']):
                if self.stop_event.is_set():
                    logger.info("Мониторинг остановлен.")
                    return
                time.sleep(1)

            logger.debug("Ожидаем %d секунд до следующего сканирования.", self.config['monitor_interval'])

        logger.info("Мониторинг завершён.")

    def log_filtered_gifts(self, gifts):
        for gift in gifts:
            logger.info("Обработанный подарок: %s", gift)