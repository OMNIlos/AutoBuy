import time
import re
import os
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.config import (
    load_gift_selector, TARGET_TYPE_GIFT, TARGET_GIFT, TARGET_PRICE, SECOND_PRICE, THIRD_PRICE,
    RETURN_TO_TYPE_GIFT_BUTTON, PAY_BUTTON_FOR_TARGET_GIFT, EXIT_FROM_PAYING_GIFT_BUTTON
)
from src.notifier import send_telegram_notification
from selenium.common.exceptions import TimeoutException


class GiftBuyer:
    def __init__(self, driver, price_threshold_percent=50.0, gift_elem_number=13, min_price_threshold=1000, log_callback=None, stop_event=None, gift_selector=None, use_absolute=False, absolute_threshold=0.0, chat_id=None):
        self.driver = driver
        self.wait = WebDriverWait(driver, 8)
        self.type_gift_selector = gift_selector or load_gift_selector() or TARGET_TYPE_GIFT
        self.price_threshold_percent = price_threshold_percent  # Процент ниже среднего
        self.min_price_threshold = min_price_threshold  # Минимальная цена для фильтрации
        self.log_callback = log_callback  # Callback для отправки логов в GUI
        self.stop_event = stop_event  # Новый флаг для остановки
        self.gift_selector = gift_selector
        self.gift_elem_number = gift_elem_number
        self.use_absolute = use_absolute  # Использовать абсолютное отклонение
        self.absolute_threshold = absolute_threshold  # Абсолютное отклонение в звездах
        self.chat_id = chat_id  # Новый параметр для индивидуального chat_id
        
    def log(self, message):
        """Отправка сообщения в лог"""
        print(message)
        if self.log_callback:
            self.log_callback(message)

    def open_type_gift(self):
        self.log("Открываем выбранный тип подарка...")
        try:
            # Ищем все типы подарков (блоки)
            type_gift_elems = self.driver.find_elements(By.CSS_SELECTOR, 'div.G1mBmzxs.f5ArEO1S.starGiftItem')
            if not type_gift_elems:
                self.log("❌ Не найдено ни одного типа подарка!")
                return
            
            # Проверяем, что индекс не выходит за границы
            if self.gift_elem_number >= len(type_gift_elems):
                self.log(f"❌ Индекс {self.gift_elem_number} выходит за границы списка (всего {len(type_gift_elems)} подарков)")
                self.gift_elem_number = min(self.gift_elem_number, len(type_gift_elems) - 1)
                self.log(f"Используем индекс {self.gift_elem_number}")
            
            # Выбираем нужный элемент
            type_gift_btn = type_gift_elems[self.gift_elem_number]
            
            # Прокручиваем к элементу с центрированием
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", type_gift_btn)
            time.sleep(0.1)
            
            # Ждем, пока элемент станет кликабельным
            WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.G1mBmzxs.f5ArEO1S.starGiftItem'))
            )
            
            # Пробуем кликнуть с обработкой ошибок
            try:
                type_gift_btn.click()
            except Exception as click_error:
                self.log(f"Обычный клик не сработал: {click_error}")
                # Пробуем через JavaScript
                try:
                    self.driver.execute_script("arguments[0].click();", type_gift_btn)
                except Exception as js_error:
                    self.log(f"JavaScript клик тоже не сработал: {js_error}")
                    # Пробуем найти кнопку внутри элемента
                    try:
                        button_inside = type_gift_btn.find_element(By.TAG_NAME, 'button')
                        button_inside.click()
                    except Exception as button_error:
                        self.log(f"Клик по кнопке внутри элемента не сработал: {button_error}")
                        raise Exception("Не удалось кликнуть по типу подарка всеми способами")
            
            time.sleep(0.1)
            self.log(f"Тип подарка выбран (индекс {self.gift_elem_number}).")
            
            # Ждем появления вариантов подарков
            time.sleep(0.2)
            
            # Продвинутая попытка сортировки по цене
            self.sort_by_price_advanced()
            
        except Exception as e:
            self.log(f"Ошибка при выборе типа подарка: {e}")
            time.sleep(2)

    def analyze_page_structure(self):
        """Анализирует структуру страницы для поиска цен"""
        print("Анализируем структуру страницы...")
        
        # Ищем все элементы с текстом, содержащим цифры и звездочки
        elements_with_stars = self.driver.find_elements(By.XPATH, "//*[contains(text(), '⭐') or contains(text(), '*')]")
        print(f"Найдено {len(elements_with_stars)} элементов")
        
        for i, element in enumerate(elements_with_stars[:10]):  # Показываем первые 10
            try:
                text = element.text.strip()
                tag_name = element.tag_name
                class_name = element.get_attribute('class')
                print(f"  {i+1}. {tag_name} (class: {class_name}): '{text}'")
            except:
                continue
        
        # Ищем все кнопки
        buttons = self.driver.find_elements(By.TAG_NAME, "button")
        print(f"Найдено {len(buttons)} кнопок:")
        
        for i, button in enumerate(buttons[:5]):  # Показываем первые 5
            try:
                text = button.text.strip()
                class_name = button.get_attribute('class')
                print(f"  {i+1}. button (class: {class_name}): '{text}'")
            except:
                continue
    
    def get_gift_elements(self):
        """Возвращает список всех элементов подарков на странице"""
        try:
            gift_elems = self.driver.find_elements(By.CSS_SELECTOR, 'div.G1mBmzxs.f5ArEO1S.starGiftItem')
            # Фильтруем устаревшие элементы
            valid_elems = []
            for elem in gift_elems:
                try:
                    if not self._is_element_stale(elem):
                        valid_elems.append(elem)
                except:
                    continue
            return valid_elems
        except Exception as e:
            self.log(f"Ошибка при получении элементов подарков: {e}")
            return []

    def extract_price_from_gift(self, gift_elem):
        """Быстро извлекает цену из текста gift_elem без вложенных find_elements"""
        try:
            text = gift_elem.text.strip()
            clean_text = re.sub(r'[✦⭐\s\n]+', '', text)
            comma_numbers = re.findall(r'(\d{1,3}(?:,\d{3})*)', clean_text)
            if comma_numbers:
                last_comma_num = comma_numbers[-1]
                price = int(last_comma_num.replace(',', ''))
                if price >= 100:
                    return price
            numbers = re.findall(r'\d+', clean_text)
            if numbers:
                valid_prices = [int(num) for num in numbers if int(num) >= 100]
                if valid_prices:
                    return max(valid_prices)
            return 0
        except Exception as e:
            self.log(f"Ошибка быстрого извлечения цены: {e}")
            return 0
        # --- старые методы для отката ---
        # def _extract_price_from_button(self, ...): ...
        # def _extract_price_from_stars(self, ...): ...
        # def _extract_price_from_text(self, ...): ...
        # def _extract_price_from_children(self, ...): ...
    
    def _is_element_stale(self, element):
        """Проверяет, является ли элемент устаревшим"""
        try:
            # Пытаемся получить любой атрибут элемента
            element.get_attribute('class')
            return False
        except:
            return True
    
    # def _extract_price_from_button(self, gift_elem):
    #     """Извлекает цену из кнопки подарка"""
    #     try:
    #         # Проверяем, что элемент не устарел
    #         if self._is_element_stale(gift_elem):
    #             return 0
                
    #         buttons = gift_elem.find_elements(By.TAG_NAME, 'button')
    #         for button in buttons:
    #             try:
    #                 # Проверяем, что кнопка не устарела
    #                 if self._is_element_stale(button):
    #                     continue
                        
    #                 text = button.text.strip()
                    
    #                 # Очищаем текст от звездочек и других символов
    #                 clean_text = re.sub(r'[✦⭐\s\n]+', '', text)
                    
    #                 # Ищем числа с запятыми (формат 9,300, 10,000 и т.д.)
    #                 comma_numbers = re.findall(r'(\d{1,3}(?:,\d{3})*)', clean_text)
    #                 if comma_numbers:
    #                     # Берем последнее число с запятыми
    #                     last_comma_num = comma_numbers[-1]
    #                     # Убираем запятые и конвертируем в число
    #                     price = int(last_comma_num.replace(',', ''))
    #                     if price >= 100:  # Фильтруем слишком маленькие числа
    #                         return price
                    
    #                 # Если не нашли числа с запятыми, ищем обычные числа
    #                 numbers = re.findall(r'\d+', clean_text)
    #                 if numbers:
    #                     # Берем максимальное число (обычно это цена)
    #                     max_price = max(int(num) for num in numbers)
    #                     if max_price >= 100:  # Фильтруем слишком маленькие числа
    #                         return max_price
    #             except Exception as button_error:
    #                 # Пропускаем проблемную кнопку и продолжаем
    #                 continue
    #     except Exception as e:
    #         self.log(f"Ошибка извлечения цены из кнопки: {e}")
    #     return 0
    
    # def _extract_price_from_stars(self, gift_elem):
    #     """Извлекает цену из иконок звездочек"""
    #     try:
    #         # Проверяем, что элемент не устарел
    #         if self._is_element_stale(gift_elem):
    #             return 0
                
    #         # Ищем элементы с иконками звездочек
    #         star_elements = gift_elem.find_elements(By.XPATH, ".//i[contains(@class, 'star') or contains(@class, 'icon-star')]")
    #         for star in star_elements:
    #             try:
    #                 # Проверяем, что звездочка не устарела
    #                 if self._is_element_stale(star):
    #                     continue
                        
    #                 # Получаем родительский элемент иконки
    #                 parent = star.find_element(By.XPATH, "./..")
                    
    #                 # Проверяем, что родительский элемент не устарел
    #                 if self._is_element_stale(parent):
    #                     continue
                        
    #                 text = parent.text.strip()
                    
    #                 # Очищаем текст от звездочек и других символов
    #                 clean_text = re.sub(r'[✦⭐\s\n]+', '', text)
                    
    #                 # Ищем числа с запятыми (формат 9,300, 10,000 и т.д.)
    #                 comma_numbers = re.findall(r'(\d{1,3}(?:,\d{3})*)', clean_text)
    #                 if comma_numbers:
    #                     # Берем последнее число с запятыми
    #                     last_comma_num = comma_numbers[-1]
    #                     # Убираем запятые и конвертируем в число
    #                     price = int(last_comma_num.replace(',', ''))
    #                     if price >= 100:  # Фильтруем слишком маленькие числа
    #                         return price
                    
    #                 # Если не нашли числа с запятыми, ищем обычные числа
    #                 numbers = re.findall(r'\d+', clean_text)
    #                 if numbers:
    #                     # Берем максимальное число
    #                     max_price = max(int(num) for num in numbers)
    #                     if max_price >= 100:  # Фильтруем слишком маленькие числа
    #                         return max_price
    #             except Exception as star_error:
    #                 # Пропускаем проблемную звездочку и продолжаем
    #                 continue
    #     except Exception as e:
    #         self.log(f"Ошибка извлечения цены из звездочек: {e}")
    #     return 0
    
    # def _extract_price_from_text(self, gift_elem):
    #     """Извлекает цену из текста элемента подарка"""
    #     try:
    #         # Проверяем, что элемент не устарел
    #         if self._is_element_stale(gift_elem):
    #             return 0
                
    #         text = gift_elem.text.strip()
            
    #         # Очищаем текст от звездочек и других символов
    #         clean_text = re.sub(r'[✦⭐\s\n]+', '', text)
            
    #         # Ищем числа с запятыми (формат 9,300, 10,000 и т.д.)
    #         comma_numbers = re.findall(r'(\d{1,3}(?:,\d{3})*)', clean_text)
    #         if comma_numbers:
    #             # Берем последнее число с запятыми
    #             last_comma_num = comma_numbers[-1]
    #             # Убираем запятые и конвертируем в число
    #             price = int(last_comma_num.replace(',', ''))
    #             if price >= 100:  # Фильтруем слишком маленькие числа
    #                 return price
            
    #         # Если не нашли числа с запятыми, ищем обычные числа
    #         numbers = re.findall(r'\d+', clean_text)
    #         if numbers:
    #             # Фильтруем числа по размеру (цены обычно больше 100)
    #             valid_prices = [int(num) for num in numbers if int(num) >= 100]
    #             if valid_prices:
    #                 # Берем максимальное число как цену
    #                 price = max(valid_prices)
    #                 return price
    #     except Exception as e:
    #         self.log(f"Ошибка извлечения цены из текста: {e}")
    #     return 0
    
    # def _extract_price_from_children(self, gift_elem):
    #     """Извлекает цену из дочерних элементов"""
    #     try:
    #         # Проверяем, что элемент не устарел
    #         if self._is_element_stale(gift_elem):
    #             return 0
                
    #         # Ищем все дочерние элементы с текстом
    #         children = gift_elem.find_elements(By.XPATH, ".//*[text()]")
    #         for child in children:
    #             try:
    #                 # Проверяем, что дочерний элемент не устарел
    #                 if self._is_element_stale(child):
    #                     continue
                        
    #                 text = child.text.strip()
    #                 if text and len(text) < 50:  # Ограничиваем длину текста
                        
    #                     # Очищаем текст от звездочек и других символов
    #                     clean_text = re.sub(r'[✦⭐\s\n]+', '', text)
                        
    #                     # Ищем числа с запятыми (формат 9,300, 10,000 и т.д.)
    #                     comma_numbers = re.findall(r'(\d{1,3}(?:,\d{3})*)', clean_text)
    #                     if comma_numbers:
    #                         # Берем последнее число с запятыми
    #                         last_comma_num = comma_numbers[-1]
    #                         # Убираем запятые и конвертируем в число
    #                         price = int(last_comma_num.replace(',', ''))
    #                         if price >= 100:  # Фильтруем слишком маленькие числа
    #                             return price
                        
    #                     # Если не нашли числа с запятыми, ищем обычные числа
    #                     numbers = re.findall(r'\d+', clean_text)
    #                     if numbers:
    #                         # Берем максимальное число
    #                         max_price = max(int(num) for num in numbers)
    #                         if max_price >= 100:  # Фильтруем слишком маленькие числа
    #                             return max_price
    #             except Exception as child_error:
    #                 # Пропускаем проблемный дочерний элемент и продолжаем
    #                 continue
    #     except Exception as e:
    #         self.log(f"Ошибка извлечения цены из дочерних элементов: {e}")
    #     return 0

    def click_gift_element(self, gift_elem):
        """
        --- PATCH: CLICK FIX START ---
        Кликает по родительскому div подарка (starGiftItem), не по вложенной кнопке
        """
        try:
            """
            if self._is_element_stale(gift_elem):
                self.log("Элемент подарка устарел, пробуем получить его заново")
                print("A")
                return False
            # Прокрутка к элементу
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", gift_elem)
                time.sleep(0.3)
                print("B")
            except Exception as e:
                self.log(f"Ошибка прокрутки к элементу: {e}")
            # Явное ожидание кликабельности
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "starGiftItem"))
                )
                print("C")
            except Exception as e:
                self.log(f"Элемент не стал кликабельным: {e}")
            # Обычный клик
            """
            try:
                gift_elem.click()
                print("D")
                return True
            except Exception as e:
                self.log(f"Обычный клик не сработал: {e}")
            # JS-клик
            """
            try:
                self.driver.execute_script("arguments[0].click();", gift_elem)
                print("E")
                return True
            except Exception as e:
                self.log(f"JS-клик не сработал: {e}")
            return False
            """
        except Exception as e:
            self.log(f"Ошибка в click_gift_element: {e}")
            return False
        
        # --- PATCH: CLICK FIX END ---

    def buy_gift_if_profitable(self):
        while not (self.stop_event and self.stop_event.is_set()):
            self.log("\n=== НОВЫЙ ЦИКЛ ПОИСКА ПОДАРКА ===")
            
            # Проверяем флаг остановки перед каждым действием
            if self.stop_event and self.stop_event.is_set():
                self.log("🛑 Получена команда остановки в начале цикла")
                break
                
            self.open_type_gift()
            self.log("Ожидаем появления вариантов подарков...")
            try:
                # Явное ожидание появления хотя бы одного подарка
                WebDriverWait(self.driver, 3).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, 'div.G1mBmzxs.f5ArEO1S.starGiftItem')) > 0
                )
            except TimeoutException:
                self.log("❌ Не удалось найти ни одного подарка за 10 секунд. Пробую снова...")
                self._sleep_with_stop(2)
                continue

            gift_elems = self.get_gift_elements()
            if not gift_elems:
                self.log('❌ Не найдено ни одного подарка. Жду и пробую снова...')
                self._sleep_with_stop(2)
                continue

            gifts = []
            stale_count = 0
            total_count = len(gift_elems)
            
            for i, elem in enumerate(gift_elems):
                # Проверяем флаг остановки на каждой итерации
                if self.stop_event and self.stop_event.is_set():
                    self.log("🛑 Получена команда остановки во время анализа подарков")
                    return
                
                # Проверяем, что элемент не устарел перед обработкой
                if self._is_element_stale(elem):
                    stale_count += 1
                    self.log(f"Подарок №{i+1} стал устаревшим, пропускаем")
                    continue
                
                price = self.extract_price_from_gift(elem)
                    
                if price >= self.min_price_threshold:
                    gifts.append({'elem': elem, 'price': price, 'index': i+1})
            
            # Если слишком много устаревших элементов, перезапускаем поиск
            if stale_count > total_count * 0.5:  # Если больше 50% элементов устарели
                self.log(f"⚠️ Обнаружено много устаревших элементов ({stale_count}/{total_count}), перезапускаем поиск...")
                self._sleep_with_stop(2)
                continue

            if not gifts:
                self.log('❌ Нет подарков с подходящей ценой. Жду и пробую снова...')
                self._sleep_with_stop(2)
                continue

            # Сортируем подарки по цене (от дешевых к дорогим)
            gifts.sort(key=lambda x: x['price'])
            
            self.log(f"Анализируем интересующие подарки...")
            for i, gift in enumerate(gifts[:3]):  # Показываем первые 3
                self.log(f"Подарок №{i+1}. стоимость: {gift['price']}⭐")
            
            best_gift = gifts[0]
            price = best_gift['price']
            
            # Рассчитываем среднюю цену первых 3 подарков
            first_three_prices = [gift['price'] for gift in gifts[:3]]
            average_price = sum(first_three_prices) / len(first_three_prices)
            
            # Рассчитываем порог для покупки
            if self.use_absolute:
                # Абсолютное отклонение от среднего
                threshold = average_price - self.absolute_threshold
                self.log(f'\n🎯 Анализ лучшего подарка:')
                self.log(f'  • Подарок №1: {price}⭐')
                self.log(f'  • Средняя цена (3 подарка): {average_price:.2f}⭐')
                self.log(f'  • Абсолютный порог: {average_price:.2f} - {self.absolute_threshold} = {threshold:.2f}⭐')
                self.log(f'  • Отклонение от среднего: {average_price - price:.2f}⭐')
            else:
                # Процентное отклонение от среднего
                threshold = average_price * (1 - self.price_threshold_percent / 100)
                deviation_percent = ((average_price - price) / average_price) * 100
                self.log(f'\n🎯 Анализ лучшего подарка:')
                self.log(f'  • Подарок №1: {price}⭐')
                self.log(f'  • Средняя цена (3 подарка): {average_price:.2f}⭐')
                self.log(f'  • Процентный порог: {average_price:.2f} * (1 - {self.price_threshold_percent}%) = {threshold:.2f}⭐')
                self.log(f'  • Отклонение от среднего: {deviation_percent:.2f}%')
            
            if price < threshold and price > 0:
                self.log(f'Цена {price} ниже порога {threshold:.2f}. Покупаю!')
                try:
                    # --- PATCH: CLICK FIX START ---
                    # Кликаем по родительскому div подарка
                    clicked = self.click_gift_element(best_gift['elem'])
                    if not clicked:
                        self.log("Не удалось кликнуть по подарку. Пробую обновить элементы и повторить.")
                        self._sleep_with_stop(2)
                        continue
                    # --- PATCH: CLICK FIX END ---
                    self._sleep_with_stop(1)
                    
                    # Проверяем, что окно покупки открылось
                    try:
                        # Ждем появления кнопки покупки
                        buy_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, PAY_BUTTON_FOR_TARGET_GIFT)))
                        self.log("Окно покупки открылось успешно")
                    except TimeoutException:
                        self.log("Окно покупки не открылось, возможно нужно выбрать вариант подарка")
                        # Пробуем найти и кликнуть по варианту подарка
                        try:
                            variant_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'div.G1mBmzxs.f5ArEO1S.starGiftItem button')
                            if variant_buttons:
                                variant_buttons[0].click()
                                self._sleep_with_stop(1)
                                buy_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, PAY_BUTTON_FOR_TARGET_GIFT)))
                                self.log("Вариант подарка выбран, окно покупки открылось")
                            else:
                                raise Exception("Не найдены варианты подарков")
                        except Exception as variant_error:
                            self.log(f"Не удалось выбрать вариант подарка: {variant_error}")
                            raise Exception("Окно покупки не открылось")
                    
                    buy_btn.click()

                    try:
                        # Ждем появления кнопки подтверждения оплаты
                        confirm_buy_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.confirm-dialog-button.primary')))
                        self.log("Кнопка подтверждения оплаты нажата")
                    except TimeoutException:
                        self.log("Не удалось найти кнопку подтверждения оплаты")
                        raise Exception("Окно покупки не открылось")
                    confirm_buy_btn.click()
                    send_telegram_notification(f'Подарок куплен за {price} ⭐', chat_id=self.chat_id)
                    self.log(f'Подарок успешно куплен за {price} ⭐!')
                    self._sleep_with_stop(2)

                    # --- PATCH: STOP AFTER BUY START ---
                    self.log("Покупка совершена, бот останавливается по требованию пользователя.")
                    return
                    # --- PATCH: STOP AFTER BUY END ---

                    # Старый код (теперь unreachable):
                    # Закрываем окно покупки
                    # try:
                    #     exit_btn = self.driver.find_element(By.CSS_SELECTOR, 'div.WA0INleU:nth-child(2)')
                    #     exit_btn.click()
                    # except Exception:
                    #     self.log("Не удалось найти кнопку закрытия, пробуем альтернативные способы...")
                    #     try:
                    #         from selenium.webdriver.common.keys import Keys
                    #         self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    #     except:
                    #         pass
                    # self.log("Покупка завершена. Начинаю новый цикл...")
                    # self._sleep_with_stop(3)
                except Exception as e:
                    self.log(f'Ошибка при покупке: {e}')
            else:
                self.log(f'Цена {price} невыгодна (порог: {threshold:.2f}), возвращаюсь в меню типов подарков...')
                # Закрываем меню вариантов и возвращаемся к типам подарков
                self.close_variant_menu()
                self._sleep_with_stop(2)

    def close_variant_menu(self):
        self.log("Закрываем меню вариантов подарка...")
        try:
            # Ищем кнопку "Назад" по нескольким селекторам
            back_button_selectors = [
                'button[aria-label="Back"]',
                'button.Button.r_Y5uG1T.smaller.translucent.round',
                'button[class*="Button"][class*="r_Y5uG1T"]',
                RETURN_TO_TYPE_GIFT_BUTTON  # Оригинальный селектор как fallback
            ]
            
            back_btn = None
            for selector in back_button_selectors:
                try:
                    back_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    self.log(f"Найдена кнопка 'Назад' с селектором: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if back_btn:
                # Прокручиваем к кнопке и кликаем
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", back_btn)
                self._sleep_with_stop(0.1)
                
                try:
                    back_btn.click()
                except Exception as click_error:
                    self.log(f"Обычный клик не сработал: {click_error}")
                    # Пробуем через JavaScript
                    try:
                        self.driver.execute_script("arguments[0].click();", back_btn)
                    except Exception as js_error:
                        self.log(f"JavaScript клик тоже не сработал: {js_error}")
                        raise Exception("Не удалось кликнуть по кнопке 'Назад'")
                
                self._sleep_with_stop(0.2)
                self.log("Меню вариантов закрыто, возвращаемся к типам подарков.")
            else:
                raise Exception("Не найдена кнопка 'Назад' ни одним из селекторов")
                
        except Exception as e:
            self.log(f"Ошибка при закрытии меню: {e}")
            self.log("Попробуйте закрыть меню вручную и нажмите Enter...")
            input()

    def sort_by_price(self):
        """Пробует кликнуть по фильтру 'По цене' в меню вариантов подарка"""
        try:
            # Пробуем найти кнопку/элемент сортировки по цене по тексту
            # Обычно это button или div с текстом 'По цене', 'Price', 'Дешевле', 'Cheapest'
            possible_texts = ["По цене", "Price", "Дешевле", "Cheapest"]
            for text in possible_texts:
                # XPATH ищет элемент-кнопку или div с нужным текстом
                xpath = f"//button[contains(., '{text}')] | //div[contains(., '{text}')]"
                elements = self.driver.find_elements(By.XPATH, xpath)
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        self.driver.execute_script("arguments[0].scrollIntoView();", el)
                        el.click()
                        self.log(f"Сортировка по цене активирована ('{text}')")
                        time.sleep(0.5)
                        return
            self.log("Не удалось найти кнопку сортировки по цене. Продолжаем без сортировки.")
        except Exception as e:
            self.log(f"Ошибка при попытке сортировки по цене: {e}")
            # Не критично, продолжаем работу

    def sort_by_price_advanced(self):
        """Кликает по кнопке смены фильтра (Date), затем по пункту Sort by Price"""
        try:
            # Метод 1: По точным селекторам из HTML
            if self._try_sort_by_exact_selectors():
                return
                
            # Метод 2: Альтернативный поиск по тексту и иконкам
            if self._try_sort_by_text_search():
                return
                
            # Метод 3: Поиск по иконке сортировки
            if self._try_sort_by_icon():
                return
                
            self.log("Не удалось найти элементы сортировки по цене")
            
        except Exception as e:
            self.log(f"Ошибка при попытке сортировки по цене: {e}")
            # Не критично, продолжаем работу
    
    def _try_sort_by_exact_selectors(self):
        """Попытка сортировки по точным селекторам из HTML"""
        try:
            # 1. Ищем контейнер с фильтрами по классу IDlp6U6g
            filter_container = self.driver.find_element(By.CSS_SELECTOR, 'div.IDlp6U6g')
            
            # 2. Ищем первую кнопку "Date" в контейнере
            date_buttons = filter_container.find_elements(By.XPATH, ".//div[contains(@class, 'qiYcBOYc') and contains(text(), 'Date')]")
            if not date_buttons:
                return False
            
            date_btn = date_buttons[0]  # Берем первую кнопку Date
            self.driver.execute_script("arguments[0].scrollIntoView();", date_btn)
            date_btn.click()
            self.log("Клик по кнопке фильтров выполнен")
            time.sleep(0.5)
            
            # 3. Ждем появления меню и ищем "Sort by Price"
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.bubble.menu-container'))
            )
            
            price_menu_item = self.driver.find_element(
                By.XPATH, 
                "//div[@role='menuitem' and .//div[contains(text(), 'Sort by Price')]]"
            )
            
            if price_menu_item.is_displayed() and price_menu_item.is_enabled():
                self.driver.execute_script("arguments[0].scrollIntoView();", price_menu_item)
                price_menu_item.click()
                self.log("✅ Сортировка по цене активирована (Sort by Price)")
                time.sleep(0.5)
                return True
                
        except Exception as e:
            self.log(f"Метод точных селекторов не сработал: {e}")
        return False
    
    def _try_sort_by_text_search(self):
        """Альтернативный поиск по тексту"""
        try:
            # Ищем любую кнопку с текстом "Date" и иконкой dropdown
            date_elements = self.driver.find_elements(
                By.XPATH, 
                "//*[contains(text(), 'Date') and .//i[contains(@class, 'dropdown') or contains(@class, 'arrow')]]"
            )
            
            for element in date_elements:
                if element.is_displayed() and element.is_enabled():
                    self.driver.execute_script("arguments[0].scrollIntoView();", element)
                    element.click()
                    self.log("Клик по элементу Date (альтернативный поиск)")
                    time.sleep(0.5)
                    
                    # Ищем меню с опциями сортировки
                    sort_options = self.driver.find_elements(
                        By.XPATH, 
                        "//*[contains(text(), 'Sort by Price') or contains(text(), 'Price')]"
                    )
                    
                    for option in sort_options:
                        if option.is_displayed() and option.is_enabled():
                            self.driver.execute_script("arguments[0].scrollIntoView();", option)
                            option.click()
                            self.log("✅ Сортировка по цене активирована")
                            time.sleep(0.5)
                            return True
                    break
                    
        except Exception as e:
            self.log(f"Метод поиска по тексту не сработал: {e}")
        return False
    
    def _try_sort_by_icon(self):
        """Поиск по иконке сортировки по цене"""
        try:
            # Ищем иконку сортировки по цене
            price_icons = self.driver.find_elements(
                By.XPATH, 
                "//i[contains(@class, 'sort-by-price') or contains(@class, 'icon-sort-by-price')]"
            )
            
            for icon in price_icons:
                parent = icon.find_element(By.XPATH, "./..")
                if parent.is_displayed() and parent.is_enabled():
                    self.driver.execute_script("arguments[0].scrollIntoView();", parent)
                    parent.click()
                    self.log("✅ Сортировка по цене активирована ")
                    time.sleep(0.5)
                    return True
                    
        except Exception as e:
            self.log(f"Метод поиска по иконке не сработал: {e}")
        return False

    def close_modal_windows(self):
        """Закрывает возможные открытые модальные окна"""
        try:
            # Пробуем закрыть через Escape
            from selenium.webdriver.common.keys import Keys
            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            self._sleep_with_stop(0.5)
            
            # Ищем и закрываем кнопки закрытия
            close_buttons = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'close') or contains(@aria-label, 'close') or contains(@title, 'close')]")
            for btn in close_buttons[:3]:  # Пробуем первые 3 кнопки
                try:
                    if btn.is_displayed() and btn.is_enabled():
                        btn.click()
                        self._sleep_with_stop(0.3)
                except:
                    continue
                    
        except Exception as e:
            self.log(f"Ошибка при закрытии модальных окон: {e}")

    def _sleep_with_stop(self, seconds):
        # Спим с проверкой флага остановки
        if not self.stop_event:
            time.sleep(seconds)
            return
        interval = 0.05
        slept = 0
        while slept < seconds:
            if self.stop_event.is_set():
                break
            time.sleep(min(interval, seconds - slept))
            slept += interval