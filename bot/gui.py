import tkinter as tk
from tkinter import ttk
from bot.enums import FilterType
import threading
from tkinter import simpledialog

class ControlPanel(tk.Tk):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.title("Контрольная панель бота")
        self.geometry("450x600")
        self.configure(bg='#f2f2f2')
        self.bot.update_callbacks.append(self.update_ui)
        self.setup_ui()

    def setup_ui(self):
        header_label = ttk.Label(self, text="Контрольная панель бота", font=('Arial', 16, 'bold'), anchor="center")
        header_label.pack(pady=20)

        self.status = tk.StringVar(value=self.bot.status)
        self.stats = tk.StringVar()

        status_label = ttk.Label(self, textvariable=self.status, font=('Arial', 14), foreground='green')
        status_label.pack(pady=10)

        stats_label = ttk.Label(self, textvariable=self.stats, font=('Arial', 10), foreground='gray')
        stats_label.pack(pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20)

        self.start_button = ttk.Button(btn_frame, text="▶ Старт", command=self.start_bot, width=15)
        self.start_button.grid(row=0, column=0, padx=10)

        self.stop_button = ttk.Button(btn_frame, text="⏹ Стоп", command=self.stop_bot, width=15)
        self.stop_button.grid(row=0, column=1, padx=10)

        self.price_button = ttk.Button(btn_frame, text="💰 Цена: 🟢 on", command=self.toggle_price, width=20)
        self.price_button.grid(row=1, column=0, padx=10, pady=5)

        self.novelty_button = ttk.Button(btn_frame, text="🆕 Новизна: 🟢 on", command=self.toggle_novelty, width=20)
        self.novelty_button.grid(row=1, column=1, padx=10, pady=5)

        self.set_price_button = ttk.Button(btn_frame, text=f"🛠 Установить цену", command=self.set_price, width=20)
        self.set_price_button.grid(row=2, column=0, padx=10, pady=5)

        self.max_gifts_button = ttk.Button(btn_frame, text=f"🎁 Макс. подарков: {self.bot.config['max_gifts_per_scan']}", command=self.set_max_gifts, width=20)
        self.max_gifts_button.grid(row=2, column=1, padx=10, pady=5)

        self.refresh_button = ttk.Button(btn_frame, text="🔄 Обновить", command=self.refresh_ui, width=20)
        self.refresh_button.grid(row=3, column=0, padx=10, pady=5)

        self.reset_filters_button = ttk.Button(btn_frame, text="🔧 Сбросить фильтры", command=self.reset_filters, width=20)
        self.reset_filters_button.grid(row=3, column=1, padx=10, pady=5)

        self.update_stats()
        self.update_ui() 
        
    def start_bot(self):
        self.bot.start_monitoring()
        self.bot.status = "🟢 Бот активен"
        self.status.set(self.bot.status)
        self.bot.send_control_buttons()
        self.update_stats()
        self.update_ui()

    def stop_bot(self):
        self.bot.stop_monitoring()
        self.bot.status = "🟠 Ожидание"
        self.status.set(self.bot.status)
        self.bot.send_control_buttons()
        self.update_stats()
        self.update_ui()

    def toggle_price(self):
        self.bot.filters[FilterType.PRICE]['enabled'] = not self.bot.filters[FilterType.PRICE]['enabled']
        self.update_ui()

    def toggle_novelty(self):
        self.bot.filters[FilterType.NOVELTY]['enabled'] = not self.bot.filters[FilterType.NOVELTY]['enabled']
        self.update_ui()

    def set_price(self):
        current_min = self.bot.filters[FilterType.PRICE].get('min', 0)
        current_max = self.bot.filters[FilterType.PRICE].get('max', 999999)

        min_price = simpledialog.askinteger(
            "Установить минимальную цену",
            f"Введите минимальную цену (текущая: {current_min} ⭐):",
            initialvalue=current_min
        )
        if min_price is None:
            return

        max_price = simpledialog.askinteger(
            "Установить максимальную цену",
            f"Введите максимальную цену (текущая: {current_max} ⭐):",
            initialvalue=current_max
        )
        if max_price is None:
            return

        if min_price > max_price:
            self.bot.send_telegram_message("❌ Минимальная цена не может быть больше максимальной.")
            return

        self.bot.filters[FilterType.PRICE]['min'] = min_price
        self.bot.filters[FilterType.PRICE]['max'] = max_price
        self.bot.send_telegram_message(f"Цена установлена: от {min_price} ⭐ до {max_price} ⭐")
        self.update_ui()

    def set_max_gifts(self):
        max_gifts = simpledialog.askinteger("Установить макс. подарков", "Введите максимальное количество подарков:")
        if max_gifts is not None:
            self.bot.config['max_gifts_per_scan'] = max_gifts
            self.bot.send_telegram_message(f"Максимальное количество подарков установлено: {max_gifts}")
            self.update_ui()

    def refresh_ui(self):
        self.bot.send_control_buttons()

    def reset_filters(self):
        for key in self.bot.filters:
            self.bot.filters[key]["enabled"] = False
            if "min" in self.bot.filters[key]:
                self.bot.filters[key]["min"] = 0
            if "max" in self.bot.filters[key]:
                self.bot.filters[key]["max"] = 999999
        self.bot.send_telegram_message("Все фильтры сброшены 🔧")
        self.update_ui()

    def update_ui(self):
        price_filter = self.bot.filters[FilterType.PRICE]
        price_enabled = '🟢 on' if price_filter['enabled'] else '🔴 off'
        price_min = price_filter.get('min', 0)
        price_max = price_filter.get('max', 10000)

        self.price_button.config(
            text=f"💰 Цена: {price_enabled}\nот {price_min} ⭐ до {price_max} ⭐"
        )

        self.novelty_button.config(text=f"🆕 Новизна: {'🟢 on' if self.bot.filters[FilterType.NOVELTY]['enabled'] else '🔴 off'}")

        self.start_button.config(state="normal" if self.bot.status == "🟠 Ожидание" else "disabled")
        self.stop_button.config(state="normal" if self.bot.status == "🟢 Бот активен" else "disabled")

        self.max_gifts_button.config(text=f"🎁 Макс. подарков: {self.bot.config['max_gifts_per_scan']}")

    def update_stats(self):
        self.stats.set(f"Обработано подарков: {self.bot.stats['gifts_bought']} | Ошибок: {self.bot.stats['errors']}")
        self.after(1000, self.update_stats)