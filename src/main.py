from selenium import webdriver
from src.gift_logic import GiftBuyer
import time
import sys
from src.gui_interface import GiftBotGUI
import subprocess
import os
from pyfiglet import Figlet
from src.notifier import send_telegram_notification
from src.config import load_config, save_config

POLLING_BOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'get_chat_id_bot.py'))

polling_bot_process = None

def print_banner():
    f = Figlet(font='slant')
    print(f.renderText('Auto Buy'))

def start_polling_bot():
    global polling_bot_process
    print_banner()
    if polling_bot_process is not None and polling_bot_process.poll() is None:
        print('Polling-бот уже запущен.')
        return
    try:
        polling_bot_process = subprocess.Popen([sys.executable, POLLING_BOT_PATH])
        print(f'Polling-бот для chat_id запущен (PID: {polling_bot_process.pid})')
    except Exception as e:
        print(f'Не удалось запустить polling-бота: {e}')

def main():
    start_polling_bot()
    try:
        print("🎨 Запуск нативного GUI интерфейса...")
        app = GiftBotGUI()
        app.run()
        return
    except ImportError as e:
        if "tkinter" in str(e):
            print("❌ tkinter не установлен")
            print("Для установки tkinter на macOS выполните:")
            print("brew install python-tk")
            print("\nПереключаемся на текстовый режим...")
        else:
            print(f"❌ Ошибка импорта GUI: {e}")
        run_text_mode()
    except Exception as e:
        print(f"❌ Ошибка запуска GUI: {e}")
        print("Переключаемся на текстовый режим...")
        run_text_mode()

def run_text_mode():
    """Текстовый режим как fallback"""
    print("🎁 Telegram Gift Bot (Текстовый режим)")
    print("=" * 40)
    print("💡 Для лучшего опыта установите tkinter:")
    print("  macOS: brew install python-tk")
    print()
    
    try:
        threshold_input = input("Введите порог в процентах ниже среднего для покупки подарка (например, 50 или 0.5): ")
        price_threshold_percent = float(threshold_input)
        
        use_absolute = input("Использовать абсолютное отклонение? (y/n, по умолчанию n): ").lower().startswith('y')
        absolute_threshold = 0
        if use_absolute:
            absolute_threshold = float(input("Введите абсолютное отклонение в звездах (например, 100): "))
        
        min_price_threshold = int(input("Введите минимальную цену для фильтрации (например, 10000): "))
        gift_elem_number = int(input("Введите номер интересующего подарка (индекс, по умолчанию 13): ") or "13")
        driver = webdriver.Firefox()
        driver.get('https://web.telegram.org')
        print("Пожалуйста, вручную авторизуйтесь и дойдите до меню подарков, затем нажмите Enter...")
        input()
        print("Проверяем, что сессия жива...")
        print(driver.title)
        buyer = GiftBuyer(driver, price_threshold_percent, gift_elem_number, min_price_threshold, use_absolute=use_absolute, absolute_threshold=absolute_threshold)
        try:
            buyer.buy_gift_if_profitable()
        except KeyboardInterrupt:
            print("\nПрограмма завершена пользователем.")
        except Exception as e:
            print(f"\nПроизошла ошибка: {e}")
        finally:
            print("Закрываем браузер...")
            driver.quit()
    except ValueError:
        print("❌ Ошибка: введите корректные числовые значения")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    try:
        main()
        if polling_bot_process is not None:
            try:
                polling_bot_process.terminate()
                polling_bot_process.wait(timeout=3)
                print('Polling-бот для chat_id завершён.')
            except Exception:
                pass
    except KeyboardInterrupt:
        print('Бот остановлен пользователем.')