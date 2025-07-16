@echo off
REM --- Автоматический запуск Telegram Gift Bot (Windows) ---

IF NOT EXIST venv (
    echo Создаю виртуальное окружение...
    python -m venv venv
)

call venv\Scripts\activate.bat

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m selenium_gift_bot.main 