import threading
import requests
import time
import logging

class ProxyRotator:
    def __init__(self, proxies):
        self.proxies = proxies or [None]
        self.index = 0
        self.lock = threading.Lock()

    def get_proxy(self):
        with self.lock:
            while not self.proxies[self.index]['is_active']:
                self.index = (self.index + 1) % len(self.proxies)
            proxy = self.proxies[self.index]
            self.index = (self.index + 1) % len(self.proxies)
        return proxy

    def mark_bad_proxy(self, proxy):
        with self.lock:
            for p in self.proxies:
                if p == proxy:
                    p['is_active'] = False
            if not any(p['is_active'] for p in self.proxies):
                self.proxies[0]['is_active'] = True

    def handle_monitoring_error(self, error, send_telegram_message):
        logging.error(f"Ошибка мониторинга: {error}")
        send_telegram_message(f"❌ Ошибка мониторинга: {str(error)}")
        retry_interval = 5
        retries = 3
        for _ in range(retries):
            try:
                break
            except requests.exceptions.RequestException as e:
                logging.error(f"Повторная ошибка при запросе: {e}")
                time.sleep(retry_interval)