import json
import logging
import threading
import requests
import time
from queue import PriorityQueue
from bot.proxy_manager import ProxyRotator
from bot.enums import FilterType, GiftPriority
import cv2
import numpy as np
import pytesseract
import re
from bot.gift_processor import GiftProcessor

class TelegramGiftBot:
    def __init__(self, config):
        self.config = config
        self.filters = {
            FilterType.PRICE: {'enabled': True, 'min': 0, 'max': 10000},
            FilterType.NOVELTY: {'enabled': True, 'score_threshold': 0.5},
        }
        self.control_panel_sent = False
        self.priority_strategy = GiftPriority.BEST_VALUE
        self.stats = {'gifts_bought': 0, 'errors': 0, 'proxy_rotations': 0}
        self.stop_thread = threading.Event()
        self.gift_queue = PriorityQueue()
        self.proxy_rotator = ProxyRotator(config.get("proxies", []))
        self.telegram_token = config.get("telegram_bot_token")
        self.chat_id = config.get("telegram_chat_id")
        self.last_update_id = None
        self.setup_templates()
        self.update_callbacks = []
        self.telegram_lock = threading.Lock()
        self.status = "🟠 Ожидание"
        self.last_control_message_id = None
        self.last_update_time = time.time()
        self.gift_processor = GiftProcessor(config, self.filters, self.log_error, self.stop_thread)
        logging.basicConfig(level=logging.INFO)
        self.waiting_for_price = False
        self.waiting_for_min_price = False
        self.waiting_for_max_price = False
        self.waiting_for_max_gifts = False
        self.temp_min_price = None
        self.temp_max_price = None
        self.config['max_gifts_per_scan'] = 0

    def setup_templates(self):
        try:
            self.templates = {
                'gift': cv2.imread('templates/gift.png', 0)
            }
            if self.templates['gift'] is None:
                raise FileNotFoundError("Не удалось загрузить шаблон 'gift.png'")
        except Exception as e:
            logging.error(f"Ошибка при загрузке шаблонов: {e}")
            self.send_telegram_message(f"Ошибка при загрузке шаблонов: {e}")

    def start_monitoring(self):
        if not self.stop_thread.is_set():
            self.stop_thread.clear()
            threading.Thread(target=self.gift_processor.monitor_and_process, daemon=True).start()

    def stop_monitoring(self):
        self.stop_thread.set()

    def send_telegram_message(self, message):
        if not self.telegram_token or not self.chat_id:
            return
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {'chat_id': self.chat_id, 'text': message}
            with self.telegram_lock:
                response = requests.post(url, data=payload)
                if not response.ok:
                    logging.error(f"Ошибка при отправке сообщения: {response.text}")
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение в Telegram: {e}")

    def send_control_buttons(self):
        price_filter = self.filters[FilterType.PRICE]
        novelty_filter = self.filters[FilterType.NOVELTY]

        keyboard = {
            "inline_keyboard": [
                [{"text": f"📟 Статус: {self.status}", "callback_data": "status"}],
                [
                    {"text": "▶ Старт", "callback_data": "start_bot"},
                    {"text": "⏹ Стоп", "callback_data": "stop_bot"}
                ],
                [{"text": f"💰 Цена: {'🟢 on' if price_filter['enabled'] else '🔴 off'}", "callback_data": "toggle_price"}],
                [{"text": f"🆕 Новизна: {'🟢 on' if novelty_filter['enabled'] else '🔴 off'}", "callback_data": "toggle_novelty"}],
                [{"text": f"🛠 Установить цену: min {price_filter['min']} / max {price_filter['max']}", "callback_data": "set_price"}],
                [{"text": f"🎁 Макс. подарков: {self.config['max_gifts_per_scan']}", "callback_data": "set_max_gifts"}],
                [{"text": "🔄 Обновить", "callback_data": "refresh_ui"}],
                [{"text": "🔧 Сбросить фильтры", "callback_data": "reset_filters"}]
            ]
        }

        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        data = {
            "chat_id": self.chat_id,
            "text": "Панель управления ботом:",
            "reply_markup": json.dumps(keyboard)
        }
        with self.telegram_lock:
            if self.last_control_message_id:
                try:
                    delete_url = f"https://api.telegram.org/bot{self.telegram_token}/deleteMessage"
                    delete_payload = {
                        "chat_id": self.chat_id,
                        "message_id": self.last_control_message_id
                    }
                    logging.info(f"Удаление старого сообщения с ID {self.last_control_message_id}")
                    response = requests.post(delete_url, data=delete_payload)
                    if response.ok:
                        logging.info(f"Удалено старое сообщение с ID {self.last_control_message_id}")
                    else:
                        logging.error(f"Ошибка при удалении сообщения: {response.text}")
                except Exception as e:
                    logging.warning(f"Не удалось удалить старое сообщение: {e}")

            logging.info(f"Отправка нового сообщения с панелью управления")
            response = requests.post(url, data=data)
            if response.ok:
                self.last_control_message_id = response.json().get("result", {}).get("message_id")
                logging.info(f"Новое сообщение отправлено, ID: {self.last_control_message_id}")
            else:
                logging.error(f"Ошибка при отправке панели управления: {response.text}")

    def handle_updates(self):
        while not self.stop_thread.is_set():
            try:
                url = f"https://api.telegram.org/bot{self.telegram_token}/getUpdates"
                params = {'timeout': 10, 'offset': self.last_update_id}
                response = requests.get(url, params=params, timeout=15)
                updates = response.json().get("result", [])
                if updates:
                    logging.info(f"Получено {len(updates)} обновлений.")
                for update in updates:
                    self.last_update_id = update["update_id"] + 1
                    self.process_update(update)
            except Exception as e:
                logging.error(f"Ошибка при получении обновлений: {e}")
            time.sleep(1)

    def process_update(self, update):
        if 'callback_query' in update:
            data = update['callback_query'].get("data")
            if data == "start_bot":
                if self.status != "🟠 Ожидание":
                    self.send_telegram_message("Бот уже запущен! Нельзя снова нажать на 'Старт'.")
                    return
                self.status = "🟢 Бот активен"
                self.start_monitoring()
                self.send_telegram_message("Бот запущен ✅")
                self.send_control_buttons()

            elif data == "stop_bot":
                if self.status != "🟢 Бот активен":
                    self.send_telegram_message("Бот уже остановлен!")
                    return
                self.status = "🟠 Ожидание"
                self.stop_monitoring()
                self.send_telegram_message("Бот остановлен ⛔")
                self.send_control_buttons()

            elif data == "toggle_price":
                self.filters[FilterType.PRICE]['enabled'] = not self.filters[FilterType.PRICE]['enabled']

            elif data == "toggle_novelty":
                self.filters[FilterType.NOVELTY]['enabled'] = not self.filters[FilterType.NOVELTY]['enabled']

            elif data == "set_price":
                self.send_telegram_message("Введите минимальную цену для подарков:")
                self.waiting_for_min_price = True

            elif data == "set_max_gifts":
                self.send_telegram_message("Введите максимальное количество подарков:")
                self.waiting_for_max_gifts = True

            elif data == "refresh_ui":
                self.send_control_buttons()

            elif data == "reset_filters":
                for key in self.filters:
                    self.filters[key]["enabled"] = False
                    if "min" in self.filters[key]:
                        self.filters[key]["min"] = 0
                    if "max" in self.filters[key]:
                        self.filters[key]["max"] = 999999
                self.send_telegram_message("Все фильтры сброшены 🔧")
                self.send_control_buttons()

            self.notify_ui_update()
            self.send_control_buttons()

            callback_id = update["callback_query"]["id"]
            requests.post(
                f"https://api.telegram.org/bot{self.telegram_token}/answerCallbackQuery",
                data={"callback_query_id": callback_id}
            )

        if 'message' in update and 'text' in update['message']:
            message_text = update['message']['text']
            self.handle_user_input(message_text)



    def handle_user_input(self, message):
        try:
            if self.waiting_for_min_price:
                min_price = int(message.strip())
                if min_price < 0:
                    self.send_telegram_message("Минимальная цена не может быть отрицательной. Попробуйте снова.")
                else:
                    self.temp_min_price = min_price
                    self.waiting_for_min_price = False
                    self.waiting_for_max_price = True
                    self.send_telegram_message(f"Минимальная цена установлена: {min_price}. Теперь введите максимальную цену:")
            
            elif self.waiting_for_max_price:
                max_price = int(message.strip())
                if max_price < self.temp_min_price:
                    self.send_telegram_message(f"Максимальная цена не может быть меньше минимальной ({self.temp_min_price}). Попробуйте снова.")
                else:
                    self.temp_max_price = max_price
                    self.filters[FilterType.PRICE]['min'] = self.temp_min_price
                    self.filters[FilterType.PRICE]['max'] = self.temp_max_price
                    self.waiting_for_max_price = False
                    self.send_telegram_message(f"Цены обновлены: Минимальная - {self.temp_min_price}, Максимальная - {self.temp_max_price}")
                    self.update_ui()

            elif self.waiting_for_max_gifts:
                try:
                    max_gifts = int(message.strip())
                    if max_gifts <= 0:
                        self.send_telegram_message("Максимальное количество подарков должно быть больше 0. Попробуйте снова.")
                    else:
                        self.config['max_gifts_per_scan'] = max_gifts
                        self.waiting_for_max_gifts = False
                        self.send_telegram_message(f"Максимальное количество подарков обновлено: {max_gifts}")
                        self.send_control_buttons()
                except ValueError:
                    self.send_telegram_message("Ошибка: Введите корректное количество подарков.")

        except ValueError:
            self.send_telegram_message("Ошибка: Введите число для цены.")

    def notify_ui_update(self):
        for callback in self.update_callbacks:
            callback()

    def log_info(self, msg):
        logging.info(msg)
        self.send_telegram_message(f"ИНФО: {msg}")

    def log_error(self, msg):
        logging.error(msg)
        self.send_telegram_message(f"ОШИБКА: {msg}")

    def start(self):
        threading.Thread(target=self.handle_updates, daemon=True).start()
        self.send_telegram_message("Панель управления запущена")
        self.send_control_buttons()

    def stop(self):
        self.stop_monitoring()
        self.send_telegram_message("Бот остановлен.")