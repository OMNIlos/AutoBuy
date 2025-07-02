#!/bin/bash

if [ "$(id -u)" -ne 0 ]; then
  echo "Скрипт должен быть запущен с правами суперпользователя (sudo)."
  exit 1
fi

cd Script_Telegram

sudo apt update

dpkg -l | grep libgl1-mesa-glx > /dev/null
if [ $? -ne 0 ]; then
  echo "Установка libgl1 (libgl1-mesa-glx)..."
  sudo apt install -y libgl1
fi

dpkg -l | grep python3-venv > /dev/null
if [ $? -ne 0 ]; then
  echo "Установка python3-venv..."
  sudo apt install -y python3-venv
fi

dpkg -l | grep python3-tk > /dev/null
if [ $? -ne 0 ]; then
  echo "Установка python3-tk..."
  sudo apt install -y python3-tk
fi

echo "Создание виртуального окружения..."
python3 -m venv venv

if [ ! -d "venv" ]; then
  echo "Не удалось создать виртуальное окружение."
  exit 1
fi

echo "Активируем виртуальное окружение..."
source venv/bin/activate

echo "Установка зависимостей..."
pip install -r requirements.txt

echo "Запуск скрипта Bot_Test.py..."
xvfb-run python3 Bot_Py/Bot_Test.py

echo "Деактивация виртуального окружения..."
deactivate