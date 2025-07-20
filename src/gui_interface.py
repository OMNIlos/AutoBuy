import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
from selenium import webdriver
from src.gift_logic import GiftBuyer
import queue
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from src.auth import TelegramWebNavigator
from src.config import load_config, save_config
from src.notifier import send_telegram_notification
import requests
import numpy as np
from PIL import ImageDraw
from PIL import Image, ImageTk
import os

class GiftBotGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Gift buyer bot")
        self.root.geometry("800x700")
        
        self.bg_main = '#1a0826'  
        self.bg_panel = '#2d1040' 
        self.bg_frame = '#3a1760' 
        self.fg_text = '#e0d6ff'  
        self.fg_accent = '#a259ff' 
        self.fg_status = '#c084fc' 
        self.root.configure(bg=self.bg_main)
        
        self.price_threshold = tk.StringVar(value="50")
        self.min_price_filter = tk.IntVar(value=100)
        self.gift_elem_number_filter = tk.IntVar(value=13) 
        self.use_absolute_threshold = tk.BooleanVar(value=False)
        self.absolute_threshold = tk.StringVar(value="100")
        self.is_running = False
        self.user_confirmed = False
        self.stop_thread = threading.Event()
        self.driver = None
        self.stage = 'idle' 
        
        self.log_queue = queue.Queue()
        
        self.chat_id_var = tk.StringVar()
        self.chat_id_status_var = tk.StringVar()
        self.load_chat_id_from_config()
        
        self.setup_styles()
        
        self.setup_ui()
        
        self.update_logs()
        self.update_buttons_state()
        
    def setup_styles(self):
        """Настройка стилей для красивого интерфейса"""
        style = ttk.Style()
        style.theme_use('alt')
        
        style.configure('Title.TLabel', font=('Arial', 18, 'bold'), foreground=self.fg_accent, background=self.bg_main)
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'), foreground=self.fg_accent, background=self.bg_panel)
        style.configure('Status.TLabel', font=('Arial', 10), foreground=self.fg_status, background=self.bg_frame)
        style.configure('Error.TLabel', font=('Arial', 10), foreground='#ff4b8e', background=self.bg_frame)
        style.configure('TLabel', background=self.bg_panel, foreground=self.fg_text)
        style.configure('TFrame', background=self.bg_panel)
        style.configure('TButton', font=('Arial', 10, 'bold'), background=self.fg_accent, foreground=self.bg_main)
        style.configure('Start.TButton', font=('Arial', 10, 'bold'), background=self.fg_accent, foreground=self.bg_main)
        style.configure('Stop.TButton', font=('Arial', 10, 'bold'), background='#ff4b8e', foreground=self.bg_main)
        style.configure('Continue.TButton', font=('Arial', 10, 'bold'), background='#7c3aed', foreground=self.bg_main)
        style.map('TButton', background=[('active', self.fg_status)])
        
    def setup_ui(self):
        """Создание пользовательского интерфейса"""
        logo_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'gift_logo.png')
        logo_img = None
        if os.path.exists(logo_path):
            try:
                pil_img = Image.open(logo_path).resize((90, 90)).convert('RGBA')
                
                size = pil_img.size
                mask = Image.new('L', size, 0)
                draw = Image.new('L', size, 0)
                ImageDraw.Draw(mask).ellipse((0, 0) + size, fill=255)
                pil_img.putalpha(mask)
                logo_img = ImageTk.PhotoImage(pil_img)
                logo_label = tk.Label(self.root, image=logo_img, bg=self.bg_main, bd=0, highlightthickness=0)
                logo_label.pack(pady=(18, 2))
                self.logo_img = logo_img
            except Exception:
                tk.Label(self.root, text="🎁", font=("Arial", 44), bg=self.bg_main, fg=self.fg_accent).pack(pady=(18, 2))
        else:
            tk.Label(self.root, text="🎁", font=("Arial", 44), bg=self.bg_main, fg=self.fg_accent).pack(pady=(18, 2))
            tk.Label(self.root, text="Поместите файл gift_logo.png в папку templates/ для фирменного логотипа", font=("Arial", 8), bg=self.bg_main, fg=self.fg_status).pack()
       
        title_label = ttk.Label(
            self.root, 
            text="AutoBuy bot", 
            style='Title.TLabel'
        )
        title_label.pack(pady=(2, 18))
        
        main_frame = ttk.Frame(self.root, style='TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
       
        left_frame = tk.LabelFrame(main_frame, text="⚙️ Настройки", padx=15, pady=10, bg=self.bg_panel, fg=self.fg_accent, font=("Arial", 12, "bold"), relief=tk.GROOVE, bd=2)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        chatid_frame = tk.LabelFrame(left_frame, text="💬 Telegram Chat ID", padx=10, pady=8, bg=self.bg_frame, fg=self.fg_accent, font=("Arial", 11, "bold"), relief=tk.GROOVE, bd=2)
        chatid_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(chatid_frame, text="Chat ID пользователя для уведомлений:", bg=self.bg_frame, fg=self.fg_text, font=("Arial", 10)).pack(anchor=tk.W)
        chatid_entry = tk.Entry(chatid_frame, textvariable=self.chat_id_var, width=30, bg=self.bg_panel, fg=self.fg_accent, insertbackground=self.fg_accent, relief=tk.FLAT)
        chatid_entry.pack(fill=tk.X, padx=(0, 0), pady=(2, 6))
        btns_frame = tk.Frame(chatid_frame, bg=self.bg_frame)
        btns_frame.pack(fill=tk.X, pady=(0, 6))
        save_btn = tk.Button(btns_frame, text="💾 Сохранить", command=self.save_chat_id_to_config, width=16, bg=self.fg_accent, fg=self.bg_main, font=("Arial", 10, "bold"), relief=tk.RAISED, bd=1, activebackground=self.fg_status)
        save_btn.pack(side=tk.LEFT, padx=(0, 5))
        get_btn = tk.Button(btns_frame, text="Получить мой Chat ID", command=lambda: threading.Thread(target=self.get_chat_id_from_telegram, daemon=True).start(), width=20, bg=self.fg_accent, fg=self.bg_main, font=("Arial", 10, "bold"), relief=tk.RAISED, bd=1, activebackground=self.fg_status)
        get_btn.pack(side=tk.LEFT)
        status_label = tk.Label(chatid_frame, textvariable=self.chat_id_status_var, font=("Arial", 9), fg=self.fg_status, bg=self.bg_frame)
        status_label.pack(anchor=tk.W, pady=(2, 0))
       
        button_frame = tk.Frame(left_frame, bg=self.bg_panel)
        button_frame.pack(fill=tk.X, pady=20)
        self.start_button = tk.Button(
            button_frame,
            text="▶ Начать работу",
            command=self.start_bot,
            bg=self.fg_accent, fg=self.bg_main, font=("Arial", 10, "bold"), width=20, relief=tk.RAISED, bd=1, activebackground=self.fg_status
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        self.stop_button = tk.Button(
            button_frame,
            text="⏹ Остановить",
            command=self.stop_bot,
            bg="#ff4b8e", fg=self.bg_main, font=("Arial", 10, "bold"), width=20, relief=tk.RAISED, bd=1, activebackground=self.fg_status, state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        self.restart_browser_button = tk.Button(
            button_frame,
            text="🔄 Перезапустить браузер",
            command=self.restart_browser,
            bg="#7c3aed", fg=self.bg_main, font=("Arial", 10, "bold"), width=22, relief=tk.RAISED, bd=1, activebackground=self.fg_status, state=tk.DISABLED
        )
        self.restart_browser_button.pack(side=tk.LEFT, padx=(0, 10))
        self.continue_button = tk.Button(
            button_frame,
            text="✅ Продолжить",
            command=self.confirm_ready,
            bg="#7c3aed", fg=self.bg_main, font=("Arial", 10, "bold"), width=20, relief=tk.RAISED, bd=1, activebackground=self.fg_status, state=tk.DISABLED
        )
        self.continue_button.pack(side=tk.LEFT)
       
        filter_frame = tk.LabelFrame(left_frame, text="💸 Фильтрация и порог", padx=10, pady=8, bg=self.bg_frame, fg=self.fg_accent, font=("Arial", 11, "bold"), relief=tk.GROOVE, bd=2)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
       
        percent_row = tk.Frame(filter_frame, bg=self.bg_frame)
        percent_row.pack(fill=tk.X, pady=(2, 0))
        tk.Label(percent_row, text="Порог в процентах ниже среднего:", bg=self.bg_frame, fg=self.fg_text, font=("Arial", 10)).pack(side=tk.LEFT)
        percent_entry = tk.Entry(percent_row, textvariable=self.price_threshold, width=8, bg=self.bg_panel, fg=self.fg_accent, insertbackground=self.fg_accent, relief=tk.FLAT)
        percent_entry.pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(percent_row, text="%", bg=self.bg_frame, fg=self.fg_accent, font=("Arial", 10)).pack(side=tk.LEFT, padx=(2, 0))
       
        min_row = tk.Frame(filter_frame, bg=self.bg_frame)
        min_row.pack(fill=tk.X, pady=(8, 0))
        tk.Label(min_row, text="Мин. цена для фильтрации:", bg=self.bg_frame, fg=self.fg_text, font=("Arial", 10)).pack(side=tk.LEFT)
        min_price_entry = tk.Entry(min_row, textvariable=self.min_price_filter, width=10, bg=self.bg_panel, fg=self.fg_accent, insertbackground=self.fg_accent, relief=tk.FLAT)
        min_price_entry.pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(min_row, text="⭐", bg=self.bg_frame, fg=self.fg_accent, font=("Arial", 10)).pack(side=tk.LEFT, padx=(2, 0))
       
        index_row = tk.Frame(filter_frame, bg=self.bg_frame)
        index_row.pack(fill=tk.X, pady=(8, 0))
        tk.Label(index_row, text="Индекс интересующего подарка:", bg=self.bg_frame, fg=self.fg_text, font=("Arial", 10)).pack(side=tk.LEFT)
        gift_elem_entry = tk.Entry(index_row, textvariable=self.gift_elem_number_filter, width=8, bg=self.bg_panel, fg=self.fg_accent, insertbackground=self.fg_accent, relief=tk.FLAT)
        gift_elem_entry.pack(side=tk.LEFT, padx=(8, 0))
      
        abs_row = tk.Frame(filter_frame, bg=self.bg_frame)
        abs_row.pack(fill=tk.X, pady=(10, 0))
        absolute_check = tk.Checkbutton(
            abs_row,
            text="Использовать абсолютное отклонение",
            variable=self.use_absolute_threshold,
            command=self.toggle_threshold_type,
            bg=self.bg_frame, fg=self.fg_text, font=("Arial", 10), selectcolor=self.bg_panel, activebackground=self.bg_frame
        )
        absolute_check.pack(side=tk.LEFT)
       
        abs_val_row = tk.Frame(filter_frame, bg=self.bg_frame)
        abs_val_row.pack(fill=tk.X, pady=(4, 0), padx=(24, 0))
        tk.Label(abs_val_row, text="Абсолютное отклонение от среднего (в звездах):", bg=self.bg_frame, fg=self.fg_text, font=("Arial", 8)).pack(side=tk.LEFT)
        self.absolute_entry = tk.Entry(
            abs_val_row,
            textvariable=self.absolute_threshold,
            font=("Arial", 10),
            width=10,
            state=tk.DISABLED,
            bg=self.bg_panel, fg=self.fg_accent, insertbackground=self.fg_accent, relief=tk.FLAT
        )
        self.absolute_entry.pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(abs_val_row, text="⭐", font=("Arial", 12), bg=self.bg_frame, fg=self.fg_accent).pack(side=tk.LEFT, padx=(2, 0))
       
        status_frame = tk.LabelFrame(left_frame, text="📊 Статус", padx=10, pady=8, bg=self.bg_frame, fg=self.fg_accent, font=("Arial", 11, "bold"), relief=tk.GROOVE, bd=2)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        self.status_label = tk.Label(
            status_frame, 
            text="🟠 Ожидание", 
            font=("Arial", 10),
            fg=self.fg_status,
            bg=self.bg_frame
        )
        self.status_label.pack()
       
        info_frame = tk.LabelFrame(left_frame, text="ℹ️ Информация", padx=10, pady=8, bg=self.bg_frame, fg=self.fg_accent, font=("Arial", 11, "bold"), relief=tk.GROOVE, bd=2)
        info_frame.pack(fill=tk.BOTH, pady=(0, 10), expand=True)
        info_text = """
• Бот автоматически ищет выгодные подарки
• Для получения уведомлений укажите свой Telegram chat_id:
  1. Откройте чат с вашим Telegram-ботом (ссылка на бота указана в настройках или документации)
  2. Нажмите Start/Запустить
  3. Отправьте команду /get_chat_id
  4. Бот пришлёт вам ваш chat_id — скопируйте его и вставьте в поле выше
• После этого вы будете получать уведомления именно на свой Telegram
• Кнопка "Получить мой Chat ID" работает только если бот запущен с polling-обработчиком (см. README)
• Нажмите "Начать работу" для запуска браузера
• Авторизуйтесь в Telegram Web и дойдите до меню подарков
• Нажмите "Продолжить" для запуска автоматизации
• Процентный порог: от 0% до 100% (можно дробные, например 0.5%)
• Абсолютный порог: отклонение в звездах от среднего (например, 100⭐)
• Номер подарка: индекс в списке подарков (0, 1, 2, ...)
• Логи с цветными иконками для лучшего понимания
• Если при запуске бота открывается QR код без логотипа Telegram, вам необходимо остановить бота и запустить его заново
        """
        info_text_widget = tk.Text(info_frame, wrap=tk.WORD, height=12, bg=self.bg_frame, fg=self.fg_text, font=("Arial", 9), relief=tk.FLAT, bd=0)
        info_text_widget.insert(tk.END, info_text)
        info_text_widget.config(state=tk.DISABLED)
        info_text_widget.pack(fill=tk.BOTH, expand=True)
       
        info_scroll = tk.Scrollbar(info_frame, command=info_text_widget.yview)
        info_text_widget.config(yscrollcommand=info_scroll.set)
        info_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
       
        right_frame = ttk.LabelFrame(main_frame, text="📝 Логи работы", padding=15, style='TFrame')
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
       
        self.log_area = scrolledtext.ScrolledText(
            right_frame,
            wrap=tk.WORD,
            width=60,
            height=12,
            font=('Consolas', 9),
            bg=self.bg_frame,
            fg=self.fg_text,
            insertbackground=self.fg_text
        )
        self.log_area.pack(fill=tk.BOTH, expand=True)
        
       
        ttk.Button(
            right_frame,
            text="🗑 Очистить логи",
            command=self.clear_logs,
            width=15
        ).pack(pady=(10, 0))
        
        self.update_logs()
        
    def log_message(self, message, level="INFO"):
        """Добавление сообщения в лог с уровнем важности"""
        timestamp = time.strftime("%H:%M:%S")
        
        level_icons = {
            "INFO": "ℹ️",
            "SUCCESS": "✅", 
            "WARNING": "⚠️",
            "ERROR": "❌",
            "DEBUG": "🔍",
            "START": "🚀",
            "STOP": "⏹️",
            "BROWSER": "🌐",
            "GIFT": "🎁",
            "MONEY": "💰"
        }
        
        icon = level_icons.get(level, "ℹ️")
        log_entry = f"[{timestamp}] {icon} {message}\n"
        self.log_queue.put(log_entry)
        
    def update_logs(self):
        """Обновление области логов"""
        try:
            while True:
                log_entry = self.log_queue.get_nowait()
                self.log_area.insert(tk.END, log_entry)
                self.log_area.see(tk.END)
        except queue.Empty:
            pass
        
        self.root.after(100, self.update_logs)
        
    def clear_logs(self):
        """Очистка области логов"""
        self.log_area.delete(1.0, tk.END)
        
    def reset_ui(self):
        """Сброс интерфейса к исходному состоянию"""
        self.is_running = False
        self.stage = 'idle'
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        self.continue_button.config(state=tk.DISABLED)
        self.status_label.config(text="🟠 Ожидание")
        self.update_buttons_state()
        self.log_message("Интерфейс сброшен к исходному состоянию", "INFO")
        
    def confirm_ready(self):
        """Подтверждение готовности пользователя"""
        if self.stage == 'automation' and self.is_running:
            self.user_confirmed = True
            self.continue_button.config(state=tk.DISABLED)
            self.log_message("Пользователь подтвердил готовность!", "SUCCESS")
        else:
            self.log_message("Кнопка 'Продолжить' недоступна в текущем состоянии", "WARNING")
        
    def wait_for_user_confirmation(self):
        """Ожидание подтверждения от пользователя"""
        self.user_confirmed = False
        self.continue_button.config(state=tk.NORMAL)
        self.log_message("Ожидание подтверждения от пользователя...", "INFO")
        
        while not self.user_confirmed and not self.stop_thread.is_set():
            time.sleep(0.1) 
            
        if self.stop_thread.is_set():
            raise Exception("Бот остановлен пользователем")
        
        self.user_confirmed = False
        
    def start_bot(self):
        """Запуск бота в отдельном потоке"""
        if self.is_running:
            return
            
        try:
            self.log_message("Запуск Telegram Gift Bot...", "START")
            self.status_label.config(text="🟡 Инициализация...")
            
            self.stop_thread.clear()
            self.user_confirmed = False
            
            threshold = float(self.price_threshold.get())
            min_price = self.min_price_filter.get()
            gift_elem_number = self.gift_elem_number_filter.get()
            use_absolute = self.use_absolute_threshold.get()
            absolute_threshold = float(self.absolute_threshold.get()) if use_absolute else 0

            gift_selector = 'div.G1mBmzxs.f5ArEO1S.starGiftItem'
            chat_id = self.chat_id_var.get().strip() or None
            
            self.log_message("Настройки загружены:", "INFO")
            if use_absolute:
                self.log_message(f"   • Абсолютный порог: {absolute_threshold}⭐ ниже среднего", "MONEY")
            else:
                self.log_message(f"   • Процентный порог: {threshold}% ниже среднего", "MONEY")
            self.log_message(f"   • Мин. цена: {min_price}⭐", "MONEY")
            self.log_message(f"   • Номер подарка: {gift_elem_number}", "GIFT")
            self.log_message(f"   • Селектор подарка: {gift_selector}", "DEBUG")
            if chat_id:
                self.log_message(f"   • Chat ID: {chat_id}", "INFO")
            
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
            self.driver = webdriver.Firefox()
            self.driver.maximize_window()
            self.driver.get('https://web.telegram.org')
            
            self.bot_thread = threading.Thread(target=self.run_bot, args=(threshold, gift_elem_number, min_price, gift_selector, use_absolute, absolute_threshold, chat_id))
            self.bot_thread.daemon = True
            self.bot_thread.start()
            
            self.is_running = True
            self.stage = 'automation'
            self.update_buttons_state()
            self.status_label.config(text="🟢 Бот активен")
            
            self.log_message("Браузер для автоматизации запущен!", "BROWSER")
            self.log_message("Откройте Telegram Web, авторизуйтесь и дойдите до меню с типами подарков, затем нажмите 'Продолжить'", "INFO")
        except Exception as e:
            self.log_message(f"Ошибка запуска: {e}", "ERROR")
            messagebox.showerror("Ошибка", f"Не удалось запустить бота:\n{e}")
            self.status_label.config(text="🟠 Ожидание")
            self.stage = 'idle'
            self.update_buttons_state()
            
    def run_bot(self, threshold, gift_elem_number, min_price, gift_selector, use_absolute, absolute_threshold, chat_id):
        """Основная логика работы бота"""
        try:
            driver = self.driver
            self.log_message("Ожидание авторизации пользователя...", "INFO")
            self.log_message("Пожалуйста, авторизуйтесь и вручную дойдите до меню с типами подарков", "INFO")
            self.wait_for_user_confirmation()
            self.log_message("Меню подарков открыто! Запуск автоматизации...", "GIFT")
            buyer = GiftBuyer(driver, threshold, gift_elem_number, min_price, self.log_message, stop_event=self.stop_thread, gift_selector=gift_selector, use_absolute=use_absolute, absolute_threshold=absolute_threshold, chat_id=chat_id)
            buyer.buy_gift_if_profitable()
        except Exception as e:
            self.log_message(f"Ошибка работы бота: {e}", "ERROR")
            self.log_message("Проверьте подключение к интернету и попробуйте снова", "WARNING")
        finally:
            if not self.is_running:
                if self.driver:
                    try:
                        self.log_message("Закрытие браузера...", "BROWSER")
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                self.root.after(0, self.reset_ui)
            
    def stop_bot(self):
        """Остановка бота"""
        if not self.is_running:
            self.log_message("Бот уже остановлен", "WARNING")
            return "Success"
            
        self.log_message("Остановка бота...", "STOP")
        
        self.stop_thread.set()
        
        if hasattr(self, 'bot_thread') and self.bot_thread.is_alive():
            self.log_message("Ожидание завершения потока бота...", "INFO")
            self.bot_thread.join(timeout=5)  # Ждем максимум 5 секунд
            if self.bot_thread.is_alive():
                self.log_message("Поток бота не завершился за 5 секунд", "WARNING")
        
        self.is_running = False
        self.stage = 'idle'
        
        if self.driver:
            try:
                self.log_message("Закрытие браузера...", "BROWSER")
                self.driver.quit()
            except Exception as e:
                self.log_message(f"Ошибка при закрытии браузера: {e}", "ERROR")
            finally:
                self.driver = None
        
        self.update_buttons_state()
        self.status_label.config(text="🟠 Ожидание")
        self.log_message("Бот успешно остановлен", "SUCCESS")
        
    def on_closing(self):
        """Обработка закрытия окна"""
        if self.is_running:
            if messagebox.askokcancel("Выход", "Бот работает. Остановить и выйти?"):
                self.stop_bot()
                self.root.destroy()
        else:
            self.root.destroy()
            
    def run(self):
        """Запуск GUI"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def toggle_threshold_type(self):
        """Переключение между процентным и абсолютным порогом"""
        if self.use_absolute_threshold.get():
            self.absolute_entry.config(state=tk.NORMAL)
        else:
            self.absolute_entry.config(state=tk.DISABLED)
    
    def update_buttons_state(self):
        if self.stage == 'idle':
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.continue_button.config(state=tk.DISABLED)
        elif self.stage == 'automation':
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.continue_button.config(state=tk.NORMAL)
        
        self.restart_browser_button.config(state=tk.NORMAL if self.driver else tk.DISABLED)



    def restart_browser(self):
        if not self.driver:
            self.log_message("Перезапуск браузера невозможен: браузер не запущен", "WARNING")
            return
        if self.is_running and self.stage == 'automation':
            self.log_message("Остановка автоматизации для перезапуска браузера...", "INFO")
            self.stop_thread.set()
            if hasattr(self, 'bot_thread') and self.bot_thread.is_alive():
                self.bot_thread.join(timeout=10)
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = webdriver.Firefox()
            self.driver.maximize_window()
            self.driver.get('https://web.telegram.org')
            self.log_message("Новый браузер запущен. Авторизуйтесь и дойдите до нужного места, затем нажмите 'Продолжить'", "BROWSER")
            self.stop_thread = threading.Event()
            threshold = float(self.price_threshold.get())
            min_price = self.min_price_filter.get()
            gift_elem_number = self.gift_elem_number_filter.get()
            use_absolute = self.use_absolute_threshold.get()
            absolute_threshold = float(self.absolute_threshold.get()) if use_absolute else 0
            gift_selector = 'div.G1mBmzxs.f5ArEO1S.starGiftItem'
            chat_id = self.chat_id_var.get().strip() or None
            self.bot_thread = threading.Thread(target=self.run_bot, args=(threshold, gift_elem_number, min_price, gift_selector, use_absolute, absolute_threshold, chat_id))
            self.bot_thread.daemon = True
            self.bot_thread.start()
            self.is_running = True
            self.stage = 'automation'
            self.update_buttons_state()
            self.log_message("Автоматизация перезапущена. Дождитесь загрузки Telegram Web и нажмите 'Продолжить'", "INFO")
            return
        try:
            self.log_message("Перезапуск браузера...", "BROWSER")
            self.driver.quit()
            self.driver = webdriver.Firefox()
            self.driver.maximize_window()
            self.driver.get('https://web.telegram.org')
            self.log_message("Новый браузер запущен. Авторизуйтесь и дойдите до нужного места", "BROWSER")
            self.update_buttons_state()
        except Exception as e:
            self.log_message(f"Ошибка при перезапуске браузера: {e}", "ERROR")

    def load_chat_id_from_config(self):
        try:
            config = load_config()
            chat_id = config.get('telegram_chat_id', '')
            if chat_id:
                self.chat_id_var.set(str(chat_id))
                self.chat_id_status_var.set('✅ Chat ID получен')
            else:
                self.chat_id_var.set('')
                self.chat_id_status_var.set('❌ Chat ID не задан')
        except Exception as e:
            self.chat_id_var.set('')
            self.chat_id_status_var.set(f'Ошибка загрузки: {e}')

    def save_chat_id_to_config(self):
        try:
            config = load_config()
            config['telegram_chat_id'] = self.chat_id_var.get().strip()
            save_config(config)
            self.chat_id_status_var.set('✅ Chat ID сохранён')
        except Exception as e:
            self.chat_id_status_var.set(f'Ошибка сохранения: {e}')

    def get_chat_id_from_telegram(self):
        try:
            token = load_config().get('telegram_bot_token')
            if not token:
                self.chat_id_status_var.set('❌ Не задан токен бота!')
                return
            
            send_telegram_notification('Пожалуйста, отправьте /get_chat_id этому боту в Telegram, чтобы получить ваш Chat ID.')
            self.chat_id_status_var.set('⏳ Ожидание ответа от пользователя...')
            
            url = f'https://api.telegram.org/bot{token}/getUpdates'
            for _ in range(10):
                resp = requests.get(url, timeout=5)
                if resp.ok:
                    data = resp.json()
                    if 'result' in data:
                        for update in reversed(data['result']):
                            msg = update.get('message')
                            if msg and 'text' in msg and msg['text'] == '/get_chat_id':
                                chat_id = msg['chat']['id']
                                self.chat_id_var.set(str(chat_id))
                                self.save_chat_id_to_config()
                                self.chat_id_status_var.set('✅ Chat ID получен автоматически')
                                return
                time.sleep(2)
            self.chat_id_status_var.set('❌ Не удалось получить Chat ID. Проверьте, что вы написали /get_chat_id боту.')
        except Exception as e:
            self.chat_id_status_var.set(f'Ошибка: {e}')

if __name__ == "__main__":
    app = GiftBotGUI()
    app.run() 