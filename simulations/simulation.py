import random
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

def generate_transmissions(num_devices, message_length, sim_duration, min_interval, max_interval):
    transmissions = [[] for _ in range(num_devices)] # list of lists of start and end times
    num_heard = [0 for _ in range(num_devices)] # count for number of non-overlapping messages
    for device in range(num_devices):
        start_time = 0.0
        while start_time < sim_duration:
            end_time = start_time + message_length
            if end_time >= sim_duration:
                break
            transmissions[device].append((start_time, end_time))
            remaining_time = sim_duration - end_time
            if remaining_time <= min_interval:
                start_time = sim_duration
            else:
                next_interval = random.uniform(min_interval, max_interval)
                start_time = end_time + next_interval
    return transmissions, num_heard

def check_overlap(transmissions):
    for i in range(len(transmissions)):
        device_transmissions = transmissions[i]
        for start_time, end_time in device_transmissions:
            overlap = False
            for j in range(len(transmissions)):
                if i != j:
                    for other_start, other_end in transmissions[j]:
                        if other_start < end_time and other_end > start_time:
                            overlap = True
                            break
            if not overlap:
                return True
    return False

def num_unobstructed(transmissions, num_heard):
    for i in range(len(transmissions)):
        device_transmissions = transmissions[i]
        for start_time, end_time in device_transmissions:
            overlap = False
            # make sure transmission doesn't overlap with any other transmissions
            for j in range(len(transmissions)):
                if i != j:
                    for other_start, other_end in transmissions[j]:
                        if other_start < end_time and other_end > start_time:
                            overlap = True
                            break
            if not overlap:
                num_heard[i] += 1
    return num_heard

# issue with this function is that it counts a success if a single transmission is heard from one device
def simulate(num_devices, message_length, sim_duration, min_interval, max_interval, num_simulations):
    success_count = 0
    for _ in range(num_simulations):
        transmissions, num_heard = generate_transmissions(num_devices, message_length, sim_duration, min_interval, max_interval)
        if check_overlap(transmissions):
            success_count += 1
    return success_count / num_simulations

def simulate_num_heard(num_devices, message_length_bits, baud, sim_duration, min_interval, max_interval, num_simulations):
    message_length = message_length_bits / baud
    avg_num_heard = [0 for _ in range(num_devices)]
    for _ in range(num_simulations):
        transmissions, num_heard = generate_transmissions(num_devices, message_length, sim_duration, min_interval, max_interval)
        num_heard = num_unobstructed(transmissions, num_heard)
        for i in range(len(num_heard)):
            avg_num_heard[i] += num_heard[i]

    for i in range(len(avg_num_heard)):
        avg_num_heard[i] /= num_simulations
    return avg_num_heard


# parameters
num_devices = [6,7,8]
message_length_bits = 116
baud_rate = [4800, 6400, 8000]
sim_duration = [.5, .75, 1, 1.5, 2] # seconds
min_interval = [0, 0.05, 0.1]
max_interval = [0.5, 0.75, 1]
num_simulations = 1000

# probability_of_success = simulate(num_devices, message_length_sec, sim_duration, min_interval, max_interval, num_simulations)
# print(f"Probability of at least one message from each device not overlapping: {probability_of_success:.4f}")

data = []
for n in num_devices:
    for baud in baud_rate:
        for duration in sim_duration:
            for min in min_interval:
                for max in max_interval:
                    num_heard = simulate_num_heard(n, message_length_bits, baud, duration, min, max, num_simulations)
                    data.append([n, message_length_bits, baud, duration, min, max, round(np.mean(num_heard), 4)])

cols = ['num devices', 'message length (bits)', 'baud rate (bits/sec)',  'sim duration (sec)', 'min delay (sec)', 'max delay (sec)', 'average messages heard']
df = pd.DataFrame(data, columns=cols)
df_corr = df.drop(columns='message length (bits)')

f = plt.figure(figsize=(9, 7))
plt.matshow(df_corr.corr(), fignum=f.number, cmap='coolwarm', vmin=-1, vmax=1)
plt.xticks(range(df_corr.select_dtypes(['number']).shape[1]), df_corr.select_dtypes(['number']).columns, fontsize=8, rotation=45, wrap=True)
plt.yticks(range(df_corr.select_dtypes(['number']).shape[1]), df_corr.select_dtypes(['number']).columns, fontsize=8, wrap=True)
cb = plt.colorbar()
cb.ax.tick_params(labelsize=8)
plt.title('Correlation Matrix', fontsize=16)
plt.show()

