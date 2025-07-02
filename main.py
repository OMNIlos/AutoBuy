import json
from bot.telegram_interface import TelegramGiftBot
from bot.gui import ControlPanel

if __name__ == "__main__":
    with open('config/config.json', 'r') as f:
        config = json.load(f)

    bot = TelegramGiftBot(config)
    bot.start()

    panel = ControlPanel(bot)
    panel.mainloop()