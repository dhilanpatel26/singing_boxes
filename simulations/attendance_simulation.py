#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import math

# for duration, pick random sleep times, return all start times
def pick_random_times(duration, transmit_time):
    # devices will all start sending within 1 second of each other
    start = random.randint(0, 1000) / 1000
    new_list = []
    
    while (start <= duration):
        new_list.append(round(start, 5))
        # sleep between start times
        sleep_time = random.randint(300, 1400) / 1000
        start += (transmit_time + sleep_time)
    
    return new_list

# baud is bits per second, message is # of bits
def calc_transmit_time(message_len, baud_rate):
    t = round((message_len / baud_rate), 5)
    return t

# take in sorted array of start times and calc prob of corruption
def calc_probability(sim_list, transmit_time):
    corrupted = 0
    tot = len(sim_list)
    
    for i in range(tot-1): 
        j = i + 1
        # if next send starts while previous is still sending, both messages corrupted
        while (j < tot and math.isclose(sim_list[i], sim_list[j], abs_tol=transmit_time)):
            corrupted += 2
            j += 1
            
    return corrupted / tot

# run test w given parameters, return probability of corruption
def run_test(ndevices, message_len, baud_rate, duration):
    transmit_time = calc_transmit_time(message_len, baud_rate)
    times = []
    
    # add times for each device
    for i in range(ndevices):
        times += pick_random_times(duration, transmit_time)
        
    times = sorted(times)
    prob = calc_probability(times, transmit_time)
    prob *= 100
    
    return prob

# run 20 trials and return avg probability
def run_trials(ndevices, message_len, baud_rate, duration):
    sum_prob = 0
    
    # run 20 trials
    for i in range(20):
        p = run_test(ndevices, message_len, baud_rate, duration)
        sum_prob += p
        
    avg = sum_prob / 20
    
    return avg

# Change parameters to see different chances of corruption

# 3-6 devices, message len of 16 bits, 4.8kbaud, duration of 5 seconds
print("Parameters: 16bits, 4.8kbaud, 5s")
print("   Chance of corruption...")
for i in range(3, 7):
    prob_rounded = round(run_trials(i, 16, 4800, 5), 3)
    print(f'       w/ {i} devices: {prob_rounded:.3f}%')
print()
    
# 3-6 devices, message len of 32 bits, 4.8kbaud, duration of 5 seconds
print("Parameters: 32bits, 4.8kbaud, 5s")
print("   Chance of corruption...")
for i in range(3, 7):
    prob_rounded = round(run_trials(i, 32, 4800, 5), 3)
    print(f'       w/ {i} devices: {prob_rounded:.3f}%') 
    
    
# add more tests 
