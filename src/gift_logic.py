import time
import re
import os
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.config_constants import (
    TARGET_TYPE_GIFT, TARGET_GIFT, TARGET_PRICE, SECOND_PRICE, THIRD_PRICE,
    RETURN_TO_TYPE_GIFT_BUTTON, PAY_BUTTON_FOR_TARGET_GIFT, EXIT_FROM_PAYING_GIFT_BUTTON
)
from src.config import load_gift_selector
from selenium.webdriver.common.keys import Keys
from src.notifier import send_telegram_notification
from selenium.common.exceptions import TimeoutException


class GiftBuyer:
    def __init__(self, driver, price_threshold_percent=50.0, gift_elem_number=13, min_price_threshold=1000, log_callback=None, stop_event=None, gift_selector=None, use_absolute=False, absolute_threshold=0.0, chat_id=None):
        self.driver = driver
        self.wait = WebDriverWait(driver, 8)
        self.type_gift_selector = gift_selector or load_gift_selector() or TARGET_TYPE_GIFT
        self.price_threshold_percent = price_threshold_percent 
        self.min_price_threshold = min_price_threshold  
        self.log_callback = log_callback  
        self.stop_event = stop_event 
        self.gift_selector = gift_selector
        self.gift_elem_number = gift_elem_number
        self.use_absolute = use_absolute  
        self.absolute_threshold = absolute_threshold  
        self.chat_id = chat_id  
        
    def log(self, message):
        """Отправка сообщения в лог"""
        print(message)
        if self.log_callback:
            self.log_callback(message)

    def open_type_gift(self):
        self.log("Загружаем выбранный тип подарка...")
        try:
            type_gift_elems = self.driver.find_elements(By.CSS_SELECTOR, 'div.G1mBmzxs.f5ArEO1S.starGiftItem')
            if not type_gift_elems:
                self.log("❌ Не найдено ни одного типа подарка!")
                return
            
            # Преобразуем номер подарка (1-based) в индекс списка (0-based)
            gift_index = self.gift_elem_number - 1
            
            # Проверяем границы
            if gift_index >= len(type_gift_elems):
                self.log(f"❌ Номер подарка {self.gift_elem_number} выходит за границы списка (всего {len(type_gift_elems)} подарков)")
                gift_index = len(type_gift_elems) - 1
                self.log(f"Используем последний доступный подарок (номер {gift_index + 1})")
            elif gift_index < 0:
                self.log(f"❌ Номер подарка должен быть больше 0")
                gift_index = 0
                self.log(f"Используем первый подарок (номер 1)")
            
            type_gift_btn = type_gift_elems[gift_index]
            
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", type_gift_btn)
            time.sleep(0.1)
            
            WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.G1mBmzxs.f5ArEO1S.starGiftItem'))
            )
            
            try:
                type_gift_btn.click()
            except Exception as click_error:
                self.log(f"Обычный клик не сработал")
                
                try:
                    self.driver.execute_script("arguments[0].click();", type_gift_btn)
                except Exception as js_error:
                    self.log(f"JavaScript клик тоже не сработал")
                    try:
                        button_inside = type_gift_btn.find_element(By.TAG_NAME, 'button')
                        button_inside.click()
                    except Exception as button_error:
                        self.log(f"Клик по кнопке внутри элемента не сработал")
            
            time.sleep(0.1)
            self.log(f"Тип подарка выбран (индекс {self.gift_elem_number}).")
            
            time.sleep(0.2)
            
            self.sort_by_price_advanced()
            
        except Exception as e:
            self.log(f"Ошибка при выборе типа подарка")
            time.sleep(2)

    def get_gift_elements(self):
        """Возвращает список всех элементов подарков на странице"""
        try:
            gift_elems = self.driver.find_elements(By.CSS_SELECTOR, 'div.G1mBmzxs.f5ArEO1S.starGiftItem')
            
            valid_elems = []
            for elem in gift_elems:
                try:
                    if not self._is_element_stale(elem):
                        valid_elems.append(elem)
                except:
                    continue
            return valid_elems
        except Exception as e:
            self.log(f"Ошибка при получении элементов подарков")
            return []

    def extract_price_from_gift(self, gift_elem):
        """Пытается извлечь цену из элемента подарка"""
        import re
        try:
            
            if not self._is_element_stale(gift_elem):
                # Метод 1: Поиск цены в кнопке
                price = self._extract_price_from_button(gift_elem)
                if price > 0:
                    return price
                
                # Метод 2: Поиск цены в иконках звездочек
                price = self._extract_price_from_stars(gift_elem)
                if price > 0:
                    return price
                
                # Метод 3: Поиск цены в тексте элемента
                price = self._extract_price_from_text(gift_elem)
                if price > 0:
                    return price
                
                # Метод 4: Поиск цены в дочерних элементах
                price = self._extract_price_from_children(gift_elem)
                if price > 0:
                    return price
            else:
                self.log("Элемент подарка стал устаревшим, пропускаем")
            
            return 0
        except Exception as e:
            self.log(f"Ошибка извлечения цены")
            return 0
    
    def _is_element_stale(self, element):
        """Проверяет, является ли элемент устаревшим"""
        try:
           
            element.get_attribute('class')
            return False
        except:
            return True
    
    def _extract_price_from_button(self, gift_elem):
        """Извлекает цену из кнопки подарка"""
        try:
            
            if self._is_element_stale(gift_elem):
                return 0
                
            buttons = gift_elem.find_elements(By.TAG_NAME, 'button')
            for button in buttons:
                try:
                    
                    if self._is_element_stale(button):
                        continue
                        
                    text = button.text.strip()
                                        
                    clean_text = re.sub(r'[✦⭐\s\n]+', '', text)
                    
                    comma_numbers = re.findall(r'(\d{1,3}(?:,\d{3})*)', clean_text)
                    if comma_numbers:
                       
                        last_comma_num = comma_numbers[-1]
                        
                        price = int(last_comma_num.replace(',', ''))
                        if price >= 100: 
                            return price
                                        
                    numbers = re.findall(r'\d+', clean_text)
                    if numbers:
                        
                        max_price = max(int(num) for num in numbers)
                        if max_price >= 100: 
                            return max_price
                except Exception as button_error:                   
                    continue
        except Exception as e:
            self.log(f"Ошибка извлечения цены из кнопки")
        return 0
    
    def _extract_price_from_stars(self, gift_elem):
        try:
            if self._is_element_stale(gift_elem):
                return 0
                
            star_elements = gift_elem.find_elements(By.XPATH, ".//i[contains(@class, 'star') or contains(@class, 'icon-star')]")
            for star in star_elements:
                try:
                   
                    if self._is_element_stale(star):
                        continue
                        
                    parent = star.find_element(By.XPATH, "./..")
                    
                    if self._is_element_stale(parent):
                        continue
                        
                    text = parent.text.strip()
                
                    clean_text = re.sub(r'[✦⭐\s\n]+', '', text)
                    
                    comma_numbers = re.findall(r'(\d{1,3}(?:,\d{3})*)', clean_text)
                    if comma_numbers:
                        last_comma_num = comma_numbers[-1]
                        price = int(last_comma_num.replace(',', ''))
                        if price >= 100:  
                            return price
                    
                    numbers = re.findall(r'\d+', clean_text)
                    if numbers:
                       
                        max_price = max(int(num) for num in numbers)
                        if max_price >= 100:  
                            return max_price
                except Exception as star_error:
                    continue
        except Exception as e:
            self.log(f"Ошибка извлечения цены из звездочек: {e}")
        return 0
    
    def _extract_price_from_text(self, gift_elem):
        """Извлекает цену из текста элемента подарка"""
        try:
            
            if self._is_element_stale(gift_elem):
                return 0
                
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
                    price = max(valid_prices)
                    return price
        except Exception as e:
            self.log(f"Ошибка извлечения цены из текста: {e}")
        return 0
    
    def _extract_price_from_children(self, gift_elem):
        """Извлекает цену из дочерних элементов"""
        try:
           
            if self._is_element_stale(gift_elem):
                return 0
                
            children = gift_elem.find_elements(By.XPATH, ".//*[text()]")
            for child in children:
                try:
                    
                    if self._is_element_stale(child):
                        continue
                        
                    text = child.text.strip()
                    if text and len(text) < 50:  
                        
                        clean_text = re.sub(r'[✦⭐\s\n]+', '', text)
                        
                        comma_numbers = re.findall(r'(\d{1,3}(?:,\d{3})*)', clean_text)
                        if comma_numbers:
                            last_comma_num = comma_numbers[-1]
                            price = int(last_comma_num.replace(',', ''))
                            if price >= 100:  
                                return price
                        
                        numbers = re.findall(r'\d+', clean_text)
                        if numbers:
                            max_price = max(int(num) for num in numbers)
                            if max_price >= 100:  
                                return max_price
                except Exception as child_error:
                    continue
        except Exception as e:
            pass
        return 0

    def click_gift_element(self, gift_elem):
        try:
            
            try:
                gift_elem.click()
                print("D")
                return True
            except Exception as e:
                self.log(f"Обычный клик не сработал: {e}")
            
        except Exception as e:
            self.log(f"Ошибка в click_gift_element: {e}")
            return False
        

    def buy_gift_if_profitable(self):
        while not (self.stop_event and self.stop_event.is_set()):
            self.log("\n=== НОВЫЙ ЦИКЛ ПОИСКА ПОДАРКА ===")
            
            if self.stop_event and self.stop_event.is_set():
                self.log("🛑 Получена команда остановки в начале цикла")
                break
                
            self.open_type_gift()
            self.log("Ожидаем появления вариантов подарков...")
            try:
                
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
                
                if self.stop_event and self.stop_event.is_set():
                    self.log("🛑 Получена команда остановки во время анализа подарков")
                    return
                
                
                if self._is_element_stale(elem):
                    stale_count += 1
                    continue
                
                price = self.extract_price_from_gift(elem)
                    
                if price >= self.min_price_threshold:
                    gifts.append({'elem': elem, 'price': price, 'index': i+1})
            
           
            if stale_count > total_count * 0.5: 
                self.log(f"⚠️ Обнаружено много устаревших элементов ({stale_count}/{total_count}), перезапускаем поиск...")
                self._sleep_with_stop(2)
                continue

            if not gifts:
                self.log('❌ Нет подарков с подходящей ценой. Жду и пробую снова...')
                self._sleep_with_stop(2)
                continue

            
            gifts.sort(key=lambda x: x['price'])
            
            self.log(f"Анализируем интересующие подарки...")
            for i, gift in enumerate(gifts[:3]):  
                self.log(f"Подарок №{i+1}. стоимость: {gift['price']}⭐")
            
            best_gift = gifts[0]
            price = best_gift['price']
            
            
            first_three_prices = [gift['price'] for gift in gifts[:3]]
            average_price = sum(first_three_prices) / len(first_three_prices)
            
            
            if self.use_absolute:
                
                threshold = average_price - self.absolute_threshold
                self.log(f'\n🎯 Анализ лучшего подарка:')
                self.log(f'  • Подарок №1: {price}⭐')
                self.log(f'  • Средняя цена (3 подарка): {average_price:.2f}⭐')
                self.log(f'  • Абсолютный порог: {average_price:.2f} - {self.absolute_threshold} = {threshold:.2f}⭐')
                self.log(f'  • Отклонение от среднего: {average_price - price:.2f}⭐')
            else:
                
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
                    
                    clicked = self.click_gift_element(best_gift['elem'])
                    if not clicked:
                        self.log("Не удалось кликнуть по подарку. Пробую обновить элементы и повторить.")
                        self._sleep_with_stop(2)
                        continue
                    
                    self._sleep_with_stop(1)
                    
                    try:
                        
                        buy_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, PAY_BUTTON_FOR_TARGET_GIFT)))
                        self.log("Окно покупки открылось успешно")
                    except TimeoutException:
                        self.log("Окно покупки не открылось, возможно нужно выбрать вариант подарка")
                        
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
                            pass
                            raise Exception("Окно покупки не открылось")
                    
                    buy_btn.click()

                    try:
                        
                        confirm_buy_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.confirm-dialog-button.primary')))
                        self.log("Кнопка подтверждения оплаты нажата")
                    except TimeoutException:
                        self.log("Не удалось найти кнопку подтверждения оплаты")
                        raise Exception("Окно покупки не открылось")
                    confirm_buy_btn.click()
                    send_telegram_notification(f'Подарок куплен за {price} ⭐', chat_id=self.chat_id)
                    self.log(f'Подарок успешно куплен за {price} ⭐!')
                    self._sleep_with_stop(2)

                    self.log("Покупка совершена, бот останавливается по требованию пользователя.")
                    return
                    
                except Exception as e:
                    self.log(f'Ошибка при покупке: {e}')
            else:
                self.log(f'Цена невыгодна (порог: {threshold:.2f}), возвращаюсь в меню типов подарков...')
                self.close_variant_menu()
                self._sleep_with_stop(2)

    def close_variant_menu(self):
        self.log("Закрываем меню вариантов подарка...")
        try:
            
            back_button_selectors = [
                'button[aria-label="Back"]',
                'button.Button.r_Y5uG1T.smaller.translucent.round',
                'button[class*="Button"][class*="r_Y5uG1T"]',
                RETURN_TO_TYPE_GIFT_BUTTON  
            ]
            
            back_btn = None
            for selector in back_button_selectors:
                try:
                    back_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    self.log(f"Найдена кнопка 'Назад'")
                    break
                except TimeoutException:
                    continue
            
            if back_btn:
                
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", back_btn)
                self._sleep_with_stop(0.1)
                
                try:
                    back_btn.click()
                except Exception as click_error:
                    self.log(f"Обычный клик не сработал: {click_error}")
                    
                    try:
                        self.driver.execute_script("arguments[0].click();", back_btn)
                    except Exception as js_error:
                        self.log(f"JavaScript клик тоже не сработал: {js_error}")
                        raise Exception("Не удалось кликнуть по кнопке 'Назад'")
                
                self._sleep_with_stop(0.2)
                self.log("Меню вариантов закрыто, возвращаемся к типам подарков.")
            else:
                pass
                
        except Exception as e:
            self.log("Попробуйте закрыть меню вручную и нажмите Enter...")
            input()

    def sort_by_price(self):
        """Пробует кликнуть по фильтру 'По цене' в меню вариантов подарка"""
        try:
            possible_texts = ["По цене", "Price", "Дешевле", "Cheapest"]
            for text in possible_texts:
                xpath = f"//button[contains(., '{text}')] | //div[contains(., '{text}')]"
                elements = self.driver.find_elements(By.XPATH, xpath)
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        self.driver.execute_script("arguments[0].scrollIntoView();", el)
                        el.click()
                        self.log(f"Сортировка по цене активирована ('{text}')")
                        time.sleep(0.5)
                        return
        except Exception as e:
            pass

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
                
        except Exception as e:
            pass
    
    def _try_sort_by_exact_selectors(self):
        """Попытка сортировки по точным селекторам из HTML"""
        try:
            # 1. Ищем контейнер с фильтрами по классу IDlp6U6g
            filter_container = self.driver.find_element(By.CSS_SELECTOR, 'div.IDlp6U6g')
            
            # 2. Ищем первую кнопку "Date" в контейнере
            date_buttons = filter_container.find_elements(By.XPATH, ".//div[contains(@class, 'qiYcBOYc') and contains(text(), 'Date')]")
            if not date_buttons:
                return False
            
            date_btn = date_buttons[0] 
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
            pass
        return False
    
    def _try_sort_by_text_search(self):
        """Альтернативный поиск по тексту"""
        try:
            date_elements = self.driver.find_elements(
                By.XPATH, 
                "//*[contains(text(), 'Date') and .//i[contains(@class, 'dropdown') or contains(@class, 'arrow')]]"
            )
            
            for element in date_elements:
                if element.is_displayed() and element.is_enabled():
                    self.driver.execute_script("arguments[0].scrollIntoView();", element)
                    element.click()
                    self.log("Клик по элементу Date ")
                    time.sleep(0.5)
                    
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
            pass
        return False

    def close_modal_windows(self):
        """Закрывает возможные открытые модальные окна"""
        try:
            
            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            self._sleep_with_stop(0.5)
            
            close_buttons = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'close') or contains(@aria-label, 'close') or contains(@title, 'close')]")
            for btn in close_buttons[:3]: 
                try:
                    if btn.is_displayed() and btn.is_enabled():
                        btn.click()
                        self._sleep_with_stop(0.3)
                except:
                    continue
                    
        except Exception as e:
            pass

    def _sleep_with_stop(self, seconds):
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