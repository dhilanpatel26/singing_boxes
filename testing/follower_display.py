import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button

fig, ax = plt.subplots()
fig.set_size_inches(5,3)
plt.xlim(800)
plt.ylim(480)
plt.xticks([])
plt.yticks([])
height = 480
width = 800

FOLLOW_IMG = np.zeros((height, width, 3), dtype=np.uint8)
FOLLOW_IMG[:, :, :] = (0, 0, 0xFF)
TRACK = 3

ax_stop = plt.axes([0.4, 0.15, 0.1, 0.075])
ax_start = plt.axes([0.55, 0.15, 0.1, 0.075])

btn_stop = Button(ax_stop, 'Stop')
btn_start = Button(ax_start, 'Start')

ax.imshow(FOLLOW_IMG)
role_text = fig.text(0.52, 0.5, 'FOLLOWER', horizontalalignment='center', fontsize=30)
if (TRACK!= None):
    fig.text(0.52, 0.4, f'Track: #{TRACK}', horizontalalignment='center', fontsize=24)
        
plt.show()  
