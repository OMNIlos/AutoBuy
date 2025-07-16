#!/bin/bash
# --- Автоматический запуск Telegram Gift Bot ---

set -e

# 1. Создать виртуальное окружение, если его нет
if [ ! -d "venv" ]; then
  echo "Создаю виртуальное окружение..."
  python3 -m venv venv
fi

# 2. Активировать виртуальное окружение
source venv/bin/activate

# 3. Обновить pip
pip install --upgrade pip

# 4. Установить зависимости
pip install -r requirements.txt

# 5. Запустить бота
python3 -m src.main 