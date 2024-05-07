import matplotlib.pyplot as plt
import numpy as np

width = 100
height = 100

img = np.zeros((height, width, 3), dtype=np.uint8)
img[:, :, :] = (0, 0, 0xFF)
print(img)

plt.axis('off')

plt.imshow(img)
plt.show()
