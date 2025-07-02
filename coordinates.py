import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

# Загрузите изображение
image_path = "./region_capture.png"  # Укажите путь к вашему изображению
image = Image.open(image_path)
img_array = np.array(image)

# Создайте фигуру и оси
fig, ax = plt.subplots(figsize=(10, 6))

# Отобразите изображение
ax.imshow(img_array, extent=[0, img_array.shape[1], img_array.shape[0], 0])

# Настройте координатную сетку
ax.grid(True, which='both', linestyle='--', linewidth=0.5)
ax.set_xticks(np.arange(0, img_array.shape[1] + 1, 10))  # Шаг сетки по X (10 пикселей)
ax.set_yticks(np.arange(0, img_array.shape[0] + 1, 10))  # Шаг сетки по Y (10 пикселей)
ax.set_xlabel('X (пиксели)')
ax.set_ylabel('Y (пиксели)')
ax.set_title('Координатная разметка изображения')

# Включите минорные деления
ax.set_xticks(np.arange(0, img_array.shape[1] + 1, 1), minor=True)
ax.set_yticks(np.arange(0, img_array.shape[0] + 1, 1), minor=True)

plt.tight_layout()
plt.show()