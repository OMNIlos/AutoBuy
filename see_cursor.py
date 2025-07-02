from pynput import mouse

def on_move(x, y):
    print(f'Координаты курсора: x={x}, y={y}')

# Создаем обработчик событий мыши
listener = mouse.Listener(on_move=on_move)

# Запускаем обработчик
listener.start()

print("Отслеживание координат мыши запущено. Для остановки нажмите Ctrl+C.")

try:
    # Бесконечный цикл, чтобы программа не завершалась сразу
    while True:
        pass
except KeyboardInterrupt:
    print("\nОтслеживание остановлено.")
    listener.stop()