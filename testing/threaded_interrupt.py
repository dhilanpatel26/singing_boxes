# import threading
# import time
# import numpy as np
# from matplotlib import pyplot as plt
# from matplotlib.widgets import Button

# looping = True

# def loop_main():
#     i = 1
#     plt.imshow(np.random.randn(10,10), cmap='gray')
#     global looping
#     while looping:
#         # plt.title(f'{i}')
#         # plt.draw()
#         print(i)
#         time.sleep(1)
#         i += 1
#     print("stopping")
    
    
# class Index:
#     ind = 0

#     def start(self, event):
#         global looping
#         looping = True
#         loop_thread = threading.Thread(target=loop_main)
#         loop_main()

#     def stop(self, event):
#         global looping
#         looping = False

# if __name__ == "__main__":
#     freqs = np.arange(2, 20, 3)

#     fig, ax = plt.subplots()
#     fig.subplots_adjust(bottom=0.2)
    
#     callback = Index()
#     axprev = fig.add_axes([0.7, 0.05, 0.1, 0.075])
#     axnext = fig.add_axes([0.81, 0.05, 0.1, 0.075])
#     bnext = Button(axnext, 'Start')
#     bnext.on_clicked(callback.start)
#     bprev = Button(axprev, 'Stop')
#     bprev.on_clicked(callback.stop)

#     plt.show()


import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import numpy as np
import time

# Initialize the figure and create a subplot
fig, ax = plt.subplots()

# A variable to track the state of the loop
loop_active = True

# Define a callback function for the "Stop" button
def stop_loop(event):
    global loop_active
    loop_active = False

# Define a callback function for the "Start" button
def start_loop(event):
    global loop_active
    loop_active = True
    main_loop()  # Call the main loop function

# Your main loop function
def main_loop():
    i = 0
    while True:
        # Check if the loop should continue
        if not loop_active:
            break

        # Code to update the figure goes here
        ax.clear()
        ax.imshow(np.random.randn(10,10))
        ax.set_title(f"{i}")
        i += 1
        plt.draw()
        # time.sleep(0.1) # time.sleep breaks this, might need to remove time.sleep from our program
        time_before = time.time()
        plt.pause(0.1)
        # print("delay after pause", time.time() - time_before)

# Create the buttons and connect their callbacks
fig.set_facecolor('white')
ax_stop = plt.axes([0.5, 0.05, 0.2, 0.1])
ax_start = plt.axes([0.75, 0.05, 0.2, 0.1])
btn_stop = Button(ax_stop, 'Stop')
btn_start = Button(ax_start, 'Start')
btn_stop.on_clicked(stop_loop)
btn_start.on_clicked(start_loop)

# Start the main loop initially
main_loop()

plt.show()