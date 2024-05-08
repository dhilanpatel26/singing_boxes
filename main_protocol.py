import cc1101
import time
import sys, os
import random
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from datetime import timedelta
from uuid import getnode
from enum import Enum
from math import ceil
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio, play

""" Constants used in transceiver functions. """
RAND_LOWER = 0.05  # must be > 0 or else TX error thrown
RAND_UPPER = 0.5
WAIT_FOR_ATTENDANCE_SEC = 2  # new device on startup
ATTENDANCE_RESPONSE_SEC = 1.5  # send duration for follower responses
SEND_LIST_DELAY = 0.1  # between sending list messages on leader side
WAIT_FOR_CHECK_IN_RESPONSE = 1.5  # leader waiting for response from device
CHECK_IN_RESPONSE = 1.0  # follower send duration
CHECK_IN_DELAY = 0.5  # leader delay between different check in messages
FOLLOWER_LISTEN_THRESHOLD = 4  # how long follower waits until entering leader takeover stage
SINGLE_SEND_DURATION = 0.5  # baseline send duration
MAX_MISSED_CHECK_INS = 2  # acommodates packet loss or noisy channel

looping = True

""" Create images for leader and follower to display. """
fig, ax = plt.subplots()
role_text = None
track_text = None
fig.set_size_inches(5,3)
plt.xlim(800)
plt.ylim(480)
plt.xticks([])
plt.yticks([])
height = 480
width = 800
BLANK_IMG = np.zeros((height, width, 3), dtype=np.uint8)
BLANK_IMG[:, :, :] = (0xFF, 0xFF, 0xFF)
ax.imshow(BLANK_IMG)
fig.canvas.draw()

LEADER_IMG = np.zeros((height, width, 3), dtype=np.uint8)
LEADER_IMG[:, :, :] = (0xFF, 0, 0)

FOLLOW_IMG = np.zeros((height, width, 3), dtype=np.uint8)
FOLLOW_IMG[:, :, :] = (0, 0, 0xFF)

# audio information
AUDIO_PATH = "tracks/"  # folder of song folders
REDUCE_VOLUME = 5  # reduce volume of track
SONG_START_OFFSET = 2  # baseline delay for song start in seconds


class ActionCodes(Enum):
    """ Defines bit masks and shifts based on message details. """

    ATTENDANCE = 0b1000
    RESPONSE = 0b0001
    SONG = 0b0010
    FIRST_LIST = 0b0011
    N_LIST = 0b0100
    CHECK_IN = 0b0101
    DELETE = 0b0110
    NEW_LEADER = 0b1111
    SONG_JOIN = 0b1100


class MessageBits(Enum):
    """ Details how message bits are arranged. """
    # messages are formatted with action as least significant bits
    # option bits are most significant
    # 9223372036854775807 is max 48 bit integer
    # 65535 is max 16 bit integer

    ACTION_LEN = 4
    ACTION_SHIFT = 0
    ACTION_MASK = 0xF << ACTION_SHIFT
    FOLLOW_ADDR_LEN = 48
    FOLLOW_ADDR_SHIFT = ACTION_SHIFT + ACTION_LEN
    FOLLOW_ADDR_MASK = 0xFFFFFFFFFFFF << FOLLOW_ADDR_SHIFT
    LEADER_ADDR_LEN = 48
    LEADER_ADDR_SHIFT = FOLLOW_ADDR_SHIFT + FOLLOW_ADDR_LEN
    LEADER_ADDR_MASK = 0xFFFFFFFFFFFF << LEADER_ADDR_SHIFT
    OPTION_LEN = 16
    OPTION_SHIFT = LEADER_ADDR_SHIFT + LEADER_ADDR_LEN
    OPTION_MASK = 0xFFFF << OPTION_SHIFT


class Message:
    """ Object carrying action, payload, option with bit masking. """

    def __init__(self, msg: int):
        """
        Non-default constructor for Message object.
        :param msg: int payload to be transmitted.
        """

        self.action = self.bit_masking(
            msg, MessageBits.ACTION_MASK, MessageBits.ACTION_SHIFT
        )
        self.leader_addr = self.bit_masking(
            msg, MessageBits.LEADER_ADDR_MASK, MessageBits.LEADER_ADDR_SHIFT
        )
        self.follow_addr = self.bit_masking(
            msg, MessageBits.FOLLOW_ADDR_MASK, MessageBits.FOLLOW_ADDR_SHIFT
        )
        self.options = self.bit_masking(
            msg, MessageBits.OPTION_MASK, MessageBits.OPTION_SHIFT
        )

        # negatives are transmitted as two's complement
        if self.options == (1 << MessageBits.OPTION_LEN.value) - 1:
            self.options = -1

    def bit_masking(self, msg, mask, shift):
        """
        Shifts bits to perform bit masking.
        :param msg: desired payload
        :param mask: desired mask
        :param shift: desired shift value
        :return: masked payload
        """

        return (msg & mask.value) >> shift.value

    def __str__(self) -> str:
        """
        String representation of Message object, used for console printing.
        :return: Concatenated string representation.
        """
        out = [
            f"message w/ Action: {self.action}",
            f"Leader Address: {hex(self.leader_addr)}",
            f"Follower Address: {hex(self.follow_addr)}",
            f"Options: {self.options}",
        ]
        return "\n\t".join(out)


class Device:
    """ Lightweight device object for storing in a DeviceList. """

    def __init__(self, address):
        """
        Non-default constructor for Device object.
        :param address: identifier for instance.
        """

        self.address = address  # MAC address stored as int
        self.track = None  # track placeholder
        self.leader = False  # initialized as follower
        self.received = None
        self.missed = 0  # used by current leader

    def get_leader(self):
        """
        :return: Device's current leader.
        """

        return self.leader

    def get_address(self):
        """
        :return: Device's MAC address.
        """

        return self.address

    def get_track(self):
        """
        :return: Device's current track index.
        """

        return self.track

    def set_track(self, track):
        """
        :param track: index assigned to Device.
        """

        self.track = track


class DeviceList:
    """ Container for lightweight Device objects, held by ThisDevice. """

    def __init__(self, num_tracks):
        """
        Non-default constructor for DeviceList object.
        :param num_tracks: size of DeviceList, number of tracks in current song.
        """

        # track == -1 denotes a reserve
        self.devices = []
        self.track_options = list(range(num_tracks))

    def __str__(self):
        """
        String representation of Devices in DeviceList.
        :return: Concatenated string representation.
        """

        output = ["DeviceList:"]
        for device in self.devices:
            track = device.track if device.track is not None else "Reserve"
            output.append(f"Device: {hex(device.address)}, Track: {track}")
        return "\n\t".join(output)

    def __iter__(self):
        """
        Iterator for Devices in DeviceList.
        :return: iterator object.
        """

        return iter(self.devices)

    def __len__(self):
        """
        Length of Devices in DeviceList.
        :return: number of Devices in DeviceList as an int.
        """

        return len(self.devices)

    def update_num_tracks(self, num_tracks):
        """
        Resize DeviceList, used to upscale or downscale tracks.
        :param num_tracks: number of tracks in new song.
        """

        self.track_options = list(range(num_tracks))

    def add_device(self, address, track):
        """
        Creates Device object with address and track, stores in DeviceList.
        :param address: identifier for device, assigned to new Device object.
        :param track: track for device, assigned to new Device object.
        """

        device = Device(address)
        device.set_track(track)
        self.devices.append(device)

    def find_device(self, address):
        """
        Finds Device object with target address in DeviceList.
        :param address: identifier for target device.
        :return: Device object if found, None otherwise.
        """

        for device in self.devices:
            if device.get_address() == address:
                return device
        return None

    def remove_device(self, address):
        """
        Removes Device object with target address in DeviceList.
        :param address: identifier for target device
        :return: True if found and removed, False otherwise.
        """

        device = self.find_device(address)
        if device:
            self.devices.remove(device)
            return True
        return False

    def unused_tracks(self):
        """
        Gets list of tracks not currently assigned to a device.
        :return: list of unused track indices.
        """

        unused_tracks = self.track_options.copy()
        for d in self.devices:
            if d.get_track() != -1 and d.get_track() in unused_tracks:
                unused_tracks.remove(d.get_track())
        return unused_tracks


    def get_reserves(self):
        """
        Gets list of reserve devices (not currently assigned a track).
        :return: list of reserve devices.
        """

        reserves = []
        for d in self.devices:
            if d.get_track() == -1:
                reserves.append(d)

        return reserves

    def update_track(self, address, track):
        """
        Reassigns track to target device.
        :param address: identifier for target device.
        :param track: new track to be assigned to target.
        """

        for i in range(len(self.devices)):
            if self.devices[i].get_address() == address:
                self.devices[i].set_track(track)

    def get_highest_addr(self):
        """
        Gets highest MAC address, used for leader takeover and tiebreaker.
        :return: max MAC address value.
        """

        max_addr = 0
        for d in self.devices:
            if d.get_address() > max_addr:
                max_addr = d.get_address()

        return max_addr


class ThisDevice(Device):
    """ Object for main protocol to use, subclass of Device. """

    def __init__(self, address):
        """
        Non-default constructor for ThisDevice.
        :param address: identifier for ThisDevice, consistent with how it is viewed.
        """

        super().__init__(address)
        self.device_list = DeviceList(8)
        #self.deleted_devices = DeviceList(8)
        self.leader_address = 0
        self.leader_started_playing = None
        self.song_folder_idx = None

    def send(self, transceiver, msg: int, duration: float):
        """
        Sends message through RF antenna, 433 MHz channel.
        :param transceiver: cc1101 antenna.
        :param msg: int message to send.
        :param duration: duration of repeated sending.
        """

        start_time = time.time()
        while time.time() - start_time <= duration:
            if not looping:
                return
            print(f"Transmitting {Message(msg)}")
            transceiver.transmit(
                msg.to_bytes(length=ceil(msg.bit_length() / 8), byteorder="big")
            )
            plt.pause(random.uniform(RAND_LOWER, RAND_UPPER))

    def receive(self, transceiver, timeout):
        """
        Receives message through RF antenna, 433 MHz channel.
        :param transceiver: cc1101 antenna.
        :param timeout: how long to wait before quitting.
        :return: True if message received, False otherwise.
        """

        start_time = time.time()
        while time.time() - start_time < timeout:
            if not looping:
                return False
            msg = transceiver._wait_for_packet(timedelta(seconds=timeout))
            if (
                msg != None and msg.checksum_valid
            ):
                msg = msg.payload.hex()[2:]
                msg = int(msg, 16)
                self.received = Message(msg)
                print("Received:", end=" ")
                print(self.received)
                return True
        return False

    def setup(self, transceiver):
        """
        Boot-up sequance for all devices.
        :param transceiver: cc1101 antenna.
        """

        print("--------Listening for leader--------")
        transceiver.set_base_frequency_hertz(433.92e6)
        transceiver.set_symbol_rate_baud(4800)
        transceiver.set_output_power(
            (0, 0xC0)
        )  # 0xC0 is max power according to cc1101 datasheet
        #print(transceiver)
        if self.receive(transceiver, WAIT_FOR_ATTENDANCE_SEC):  # listen for message
            self.follower_receive_respond_attendance(
                transceiver
            )  # will enter for any message
            self.leader = False
        else:
            print("Not received - now leader, sending attendance msg")

            # leader will take track 0
            self.track = 0
            self.leader_addr = self.address
            self.device_list.add_device(self.get_address(), track=0)

            self.leader_send_attendance(transceiver)
            self.leader = True

    def follower_receive_respond_attendance(self, transceiver):
        """

        :param transceiver:
        :return:
        """
        while (
            self.received.action != ActionCodes.ATTENDANCE.value
        ):  # make sure received message is attendance message
            print("heard messages, waiting for attendance message")
            self.receive(transceiver, 5)
            if not looping:
                return

        # gets to here only if attendance message is heard
        print("Received attendance message from leader, responding")
        self.leader_address = self.received.leader_addr

        if self.device_list.find_device(self.leader_address) == None:
            # add leader to first spot in device list with top track by default
            self.device_list.add_device(self.leader_address, track=0)

        # response to attendance
        response = create_message(
            ActionCodes.RESPONSE, self.address, self.leader_address
        )
        self.send(transceiver, response, ATTENDANCE_RESPONSE_SEC)
        # self.make_follower() # comment this out to not diplay plots

    # leader functions
    def leader_send_attendance(self, transceiver, playback=None,
                               leader_started_playing=None, song_folder_idx=None):
        msg = create_message(ActionCodes.ATTENDANCE, 0, self.address)
        self.send(transceiver, msg, SINGLE_SEND_DURATION)

        # listen for responses and add unique IDs to device list
        start_time = time.time()
        new_devices = False
        open_tracks = self.device_list.unused_tracks()
        while time.time() < start_time + ATTENDANCE_RESPONSE_SEC:
            if not looping:
                return
            if self.receive(transceiver, ATTENDANCE_RESPONSE_SEC):
                received_addr = self.received.follow_addr
                # look for device in list
                if ((self.received.action == ActionCodes.RESPONSE.value)
                        and (self.device_list.find_device(received_addr) == None)):
                    # puts device in reserves if no more open tracks
                    track = open_tracks.pop(0) if len(open_tracks) > 0 else -1
                    # add address to follower list
                    self.device_list.add_device(address=received_addr, track=track)
                    new_devices = True

        if new_devices:
            self.leader_send_list(transceiver)
            if playback != None and playback.is_playing():
                # leader_send_song_join, may also need to implement follower_receive_song_join
                self.leader_send_song_join(transceiver, leader_started_playing, song_folder_idx)

    def leader_send_song_join(self, transceiver, leader_started_playing, song_folder_idx):
        # timestamp that follower should start
        #follower_start_time = time.time() + SONG_JOIN_DELAY
        #follower_start_time_int = round(follower_start_time * 1000) # get milliseconds
        #follower_start_timestamp = follower_start_time - leader_started_playing
        #follower_start_timestamp = round(follower_start_timestamp * 1000) # get milliseconds
        start_time_int = round(leader_started_playing * 1000) # get milliseconds
        msg = create_message(ActionCodes.SONG_JOIN, start_time_int, self.address, song_folder_idx)
        self.send(transceiver, msg, SINGLE_SEND_DURATION)
        # plt.pause(SONG_JOIN_DELAY) not necessary?

    def follower_receive_song_join(self):

        leader_start = self.received.follow_addr / 1000

        # get song from message
        song_folders = sorted(os.listdir(AUDIO_PATH))
        song_folder_idx = self.received.options

        # is a reserve but will still have updated information
        if self.track == None or self.track == -1:
            return None, leader_start, song_folder_idx

        song_path = os.path.join(AUDIO_PATH, song_folders[song_folder_idx])

        track_choices = sorted(os.listdir(song_path))

        if self.track > len(track_choices) - 1:
            return None, leader_start, song_folder_idx

        track_name = track_choices[self.track]
        track_path = os.path.join(song_path, track_name)

        follower_start_time = time.time()

        follower_start_timestamp = follower_start_time - leader_start
        follower_start_timestamp = round(follower_start_timestamp * 1000) # get milliseconds

        sound = AudioSegment.from_file(track_path, format="mp3")
        sound = sound.set_sample_width(2)
        sound = sound - REDUCE_VOLUME
        delay = (time.time() - follower_start_time) * 1000
        sound = sound[follower_start_timestamp + delay:]

        print(f"Playing {track_name}")
        playback = _play_with_simpleaudio(sound)
        self.device_list.update_num_tracks(len(track_choices))

        return playback, leader_start, song_folder_idx

    def leader_send_list(self, transceiver):
        # iterate through devices who's responses have been heard
        for i in range(len(self.device_list.devices)):
            device = self.device_list.devices[i]
            # create list message and send
            msg = create_message(
                ActionCodes.N_LIST,
                device.get_address(),
                self.address,
                device.get_track(),
            )
            self.send(transceiver, msg, SINGLE_SEND_DURATION)
            plt.pause(SEND_LIST_DELAY)

    def leader_send_song_start(self, transceiver):

        # get start time
        start_time = time.time() + SONG_START_OFFSET
        start_time_int = round(start_time * 1000) # get milliseconds

        # get song randomly and respective track
        song_folders = sorted(os.listdir(AUDIO_PATH))
        song_folder_idx = random.choice(range(len(song_folders)))
        song_path = os.path.join(AUDIO_PATH, song_folders[song_folder_idx])
        track_choices = sorted(os.listdir(song_path))

        if self.track == None or self.track == -1 or self.track > len(track_choices) - 1:
            return None, start_time, song_folder_idx

        track_name = track_choices[self.track]
        track_path = os.path.join(song_path, track_name)
        
        # use follower_address part of message for sending the time in milliseconds to start
        sound = AudioSegment.from_file(track_path, format="mp3")
        sound = sound.set_sample_width(2)
        sound = sound - REDUCE_VOLUME
        
        msg = create_message(ActionCodes.SONG, start_time_int, self.address, song_folder_idx)
        self.send(transceiver, msg, SINGLE_SEND_DURATION)
        
        while time.time() < start_time: # wait until play time has come
            _ = 2+2
        
        print(f"Playing {track_name}")
        playback = _play_with_simpleaudio(sound)

        self.device_list.update_num_tracks(len(track_choices))
        
        return playback, start_time, song_folder_idx

    # All devices must keep an updated list
    def leader_send_delete(self, transceiver, address):
        msg = create_message(ActionCodes.DELETE, address, self.address)
        self.send(transceiver, msg, SINGLE_SEND_DURATION)

    def leader_check_in(self, transceiver):
        for device in self.device_list: # iterate through devices in list
            address = device.get_address()
            if address != self.address: # make sure leader isn't checking in with itself
                msg = create_message(ActionCodes.CHECK_IN, address, self.address)
                self.send(transceiver, msg, SINGLE_SEND_DURATION)

                responded = False
                start_time = time.time()
                while time.time() < start_time + WAIT_FOR_CHECK_IN_RESPONSE:
                    if self.receive(transceiver, WAIT_FOR_CHECK_IN_RESPONSE):
                        if self.received.follow_addr == address:
                            responded = True
                            break

                if not responded:
                    #print("Device didn't respond :( deleting\n")
                    # d = self.device_list.find_device(address)
                    # self.deleted_devices.add_device(address, d.get_track()) # TODO add to deleted array so we can get its track back if it comes alive again?
                    device.missed += 1
                    if device.missed >= MAX_MISSED_CHECK_INS: # give chance for staying in after missed check-in 
                        self.device_list.remove_device(
                            address
                        )  # delete from leader's copy
                        self.leader_send_delete(transceiver, address)

                        unused_tracks = self.device_list.unused_tracks()  # the unused track after deletion
                        if device.track != -1: # deleted a device that was playing
                            for d in self.device_list:
                                if d.track == -1:  # detect first reserve
                                    d.track = unused_tracks[0]
                                    break

                plt.pause(CHECK_IN_DELAY)
                
    def leader_heard_attendance(self, playback):
        other_addr = self.received.leader_addr
        if self.address < other_addr:
            print("becoming follower, other leader heard")
            # become follower
            self.leader = False
            self.leader_addr = other_addr
            if playback != None:
                playback.stop()
            self.change_display_role()
        # else stay leader

    # follower functions
    def follower_receive_first_list(self):  # not necessary?
        pass

    def follower_receive_list(self):
        track = self.received.options
        address = self.received.follow_addr
        # make sure device isn't already in list
        device = self.device_list.find_device(self.received.follow_addr)
        if device == None:
            # add device to list with track
            self.device_list.add_device(address, track)

            if self.received.follow_addr == self.address:
                # set this device's track
                self.track = self.received.options
                self.change_display_role()

        else:
            # check if track has changed for respective device
            if device.get_track() != track:
                self.device_list.update_track(device.get_address(), track)
        

    def follower_receive_song_start(self):

        # get start time from message
        start_time = self.received.follow_addr / 1000

        # get song from message
        song_folders = sorted(os.listdir(AUDIO_PATH))
        song_folder_idx = self.received.options

        if self.track == None or self.track == -1:
            return None, start_time, song_folder_idx

        song_path = os.path.join(AUDIO_PATH, song_folders[song_folder_idx])
        track_choices = sorted(os.listdir(song_path))

        if self.track > len(track_choices) - 1:
            return None, start_time, song_folder_idx

        track_name = track_choices[self.track]
        track_path = os.path.join(song_path, track_name)

        # use follower_address part of message for sending the time in milliseconds to start
        sound = AudioSegment.from_file(track_path, format="mp3")
        sound = sound.set_sample_width(2)
        sound = sound - REDUCE_VOLUME
        self.device_list.update_num_tracks(len(track_choices))
        
        if time.time() > start_time:
            follower_start_time = time.time()

            follower_start_timestamp = follower_start_time - start_time
            follower_start_timestamp = round(follower_start_timestamp * 1000) # get milliseconds

            sound = AudioSegment.from_file(track_path, format="mp3")
            sound = sound.set_sample_width(2)
            sound = sound - REDUCE_VOLUME
            delay = (time.time() - follower_start_time) * 1000
            sound = sound[follower_start_timestamp + delay:]
            
        else:
            while time.time() < start_time:
                _ = 2+2

        print(f"Playing {track_name}")
        playback = _play_with_simpleaudio(sound)

        return playback, start_time, song_folder_idx

    def follower_respond_check_in(self, transceiver):
        # maybe modify ThisDevice for an easier way to access the leader address?
        #plt.pause(0.2)
        response = create_message(
            ActionCodes.RESPONSE,
            self.address,
            self.device_list.devices[0].get_address(),
        )
        print("Responding to check in!!!!!!!!")
        self.send(transceiver, response, CHECK_IN_RESPONSE)

    def follower_receive_delete(self, addressToDelete, playback=None):
        if self.address == addressToDelete:
            print(
                "I have been deleted :((( will respond to next attendance to get back in"
            )
            if playback != None:
                playback.stop()
            self.track = None
        self.device_list.remove_device(addressToDelete)

        # all devices already have updated song information
        unused_tracks = self.device_list.unused_tracks() # the unused track after deletion
        for device in self.device_list.devices:
            if device.track == -1: # detect first reserve, then break
                if device.get_address() == self.address: # this is the reserve to promote
                    self.track = unused_tracks[0]
                    device.track = unused_tracks[0]
                    return self.promote_this_reserve(self.leader_started_playing, self.song_folder_idx)
                device.track = unused_tracks[0] # other followers update their device list too
                break

    def promote_this_reserve(self, leader_start, song_folder_idx):

        song_folders = sorted(os.listdir(AUDIO_PATH))
        song_path = os.path.join(AUDIO_PATH, song_folders[song_folder_idx])
        track_choices = sorted(os.listdir(song_path))
        track_name = track_choices[self.track]
        track_path = os.path.join(song_path, track_name)
        self.change_display_role()

        follower_start_time = time.time()
        follower_start_timestamp = follower_start_time - leader_start
        follower_start_timestamp = round(follower_start_timestamp * 1000)  # get milliseconds

        sound = AudioSegment.from_file(track_path, format="mp3")
        sound = sound.set_sample_width(2)
        sound = sound - REDUCE_VOLUME
        delay = (time.time() - follower_start_time) * 1000
        sound = sound[follower_start_timestamp + delay:]

        print(f"Playing {track_name}")
        playback = _play_with_simpleaudio(sound)
        return playback

    def handle_promotion(self, transceiver):
        # remove leader from device list
        self.device_list.remove_device(self.leader_address)
        # get new leader from list based on track position
        self.leader_address = self.device_list.get_highest_addr()
        # if new leader is this device's address, self.leader = True
        if self.leader_address == self.address:
            self.leader = True
            self.change_display_role()
        # all devices already have updated song information
        unused_tracks = self.device_list.unused_tracks() # the unused track after deletion
        for device in self.device_list.devices:
            if device.track == -1: # detect first reserve, then break
                if device.get_address() == self.address: # this is the reserve to promote
                    self.track = unused_tracks[0]
                    device.track = unused_tracks[0]
                    return self.promote_this_reserve(self.leader_started_playing, self.song_folder_idx)
                device.track = unused_tracks[0] # other followers update their device list too
                break
        return self.leader

    def set_display(self):
        plt.ion()
        global role_text 
        if self.leader:
            ax.imshow(LEADER_IMG)
            role_text = fig.text(0.52, 0.5, 'LEADER', horizontalalignment='center', fontsize=30)
        else:
            ax.imshow(FOLLOW_IMG)
            role_text = fig.text(0.52, 0.5, 'FOLLOWER', horizontalalignment='center', fontsize=30)
        global track_text
        if not(self.track == None):
            if (self.track == -1):
                track_text = fig.text(0.52, 0.4, f'Reserve', horizontalalignment='center', fontsize=24)
            else:
                track_text = fig.text(0.52, 0.4, f'Track: #{self.track+1}', horizontalalignment='center', fontsize=24)
        fig.canvas.draw()
        plt.show()
    
    def change_display_role(self):
        plt.ion()
        global role_text 
        if not(role_text == None):
            role_text = role_text.remove()
            
        if self.leader:
            ax.imshow(LEADER_IMG)
            role_text = fig.text(0.52, 0.5, 'LEADER', horizontalalignment='center', fontsize=30)
        else:
            ax.imshow(FOLLOW_IMG) 
            role_text = fig.text(0.52, 0.5, 'FOLLOWER', horizontalalignment='center', fontsize=30)
            
        global track_text 
        if not(track_text == None):
            track_text = track_text.remove()
            
        if not(self.track == None):
            if (self.track == -1):
                track_text = fig.text(0.52, 0.4, f'Reserve', horizontalalignment='center', fontsize=24)
            else:
                track_text = fig.text(0.52, 0.4, f'Track: #{self.track+1}', horizontalalignment='center', fontsize=24)
        
        fig.canvas.draw()
        plt.show()
            
            


def create_message(
    action: ActionCodes, follower_addr: int, leader_addr: int, options=None
):
    msg = 0
    msg |= action.value << MessageBits.ACTION_SHIFT.value
    msg |= follower_addr << MessageBits.FOLLOW_ADDR_SHIFT.value
    msg |= leader_addr << MessageBits.LEADER_ADDR_SHIFT.value
    if not options == None:
        if options == -1:
            msg |= ((1 << MessageBits.OPTION_LEN.value) - 1) << MessageBits.OPTION_SHIFT.value
        else:
            msg |= options << MessageBits.OPTION_SHIFT.value
    return msg


def remove_length_byte(msg: int):
    mask = (1 << (msg.bit_length() - 8)) - 1
    msg &= mask
    return msg

# Define a callback function for the "Stop" button
def stop_loop(event):
    global looping
    global role_text
    global track_text
    plt.ion()
    looping = False
    ax.imshow(BLANK_IMG)
    if role_text != None:
        role_text = role_text.remove()
    if track_text != None:
        track_text = track_text.remove()
    fig.canvas.draw()
    plt.show()

# Define a callback function for the "Start" button
def start_loop(event):
    global looping
    looping = True
    main()  # Call the main loop function

def main():
    with cc1101.CC1101() as transceiver:
        # create device object
        device = ThisDevice(getnode())
        device.setup(transceiver)
        
        playback = None # instance of PlayObject
        leader_started_playing = None # time that leader started playing their track
        song_folder_idx = None # randomly chosen song folder

        if device.get_leader():
            print("--------Leader---------")
        else:
            print("--------Follower, listening...")
            
        device.set_display()

        # global looping
        while True:
            print(device.device_list)

            # break out of loop when stop button is pressed
            if not looping:
                if playback != None:
                    playback.stop()
                break

            if device.get_leader():  # Leader loop
                # check to see if song is playing
                if playback == None:
                    playback, leader_started_playing, song_folder_idx = device.leader_send_song_start(transceiver)
                elif not playback.is_playing():
                    # send song start message if not playing
                    playback, leader_started_playing, song_folder_idx = device.leader_send_song_start(transceiver)
                    
                if not looping:
                    if playback != None:
                        playback.stop()
                    break

                # send check in messages and wait for responses
                device.leader_check_in(transceiver)
                # send delete message if response not heard from device after threshold (handled in leader_check_in)
                
                if not looping:
                    if playback != None:
                        playback.stop()
                    break

                # send attendance message
                device.leader_send_attendance(transceiver, playback, leader_started_playing, song_folder_idx)
                # listen for new followers
                # send revised list if new followers are heard (handled in leader_send_attendance)
                
                if not looping:
                    if playback != None:
                        playback.stop()
                    break

            if not device.get_leader():  # follower loop
                # listen for message
                # handle depending on action code
                if not looping:
                    if playback != None:
                        playback.stop()
                    break

                if device.receive(transceiver, FOLLOWER_LISTEN_THRESHOLD):
                    action = device.received.action

                    if device.received.leader_addr != device.leader_address:
                        # device.leader_address = max(device.received.leader_addr, device.leader_address)
                        continue

                    # messages for all followers
                    if action == ActionCodes.DELETE.value:
                        reserve_promotion = device.follower_receive_delete(device.received.follow_addr, playback)
                        if reserve_promotion is not None:
                            playback = reserve_promotion
                        
                    elif action == ActionCodes.N_LIST.value:
                        print("Updating list on follower side***")
                        device.follower_receive_list()
                        
                    elif (
                        action == ActionCodes.ATTENDANCE.value
                    ) and device.track == None:  # meaning follower was wrongly deleted
                        device.follower_receive_respond_attendance(transceiver)
                        
                    elif action == ActionCodes.SONG.value:
                        # maybe we also need to check if the song is getting changed?
                        # if (playback == None) or (not playback.is_playing()):
                        playback, leader_started_playing, song_folder_idx = device.follower_receive_song_start()
                        device.leader_started_playing = leader_started_playing
                        device.song_folder_idx = song_folder_idx

                    elif action == ActionCodes.SONG_JOIN.value:
                        if ((playback != None) and (playback.is_playing())) or device.track == None:
                            continue
                        playback, leader_started_playing, song_folder_idx = device.follower_receive_song_join()
                        device.leader_started_playing = leader_started_playing
                        device.song_folder_idx = song_folder_idx

                    if action == ActionCodes.CHECK_IN.value and device.address == device.received.follow_addr:
                        plt.pause(CHECK_IN_DELAY)
                        device.follower_respond_check_in(transceiver)
                        
                else:  # no message heard
                    print("Is there anybody out there?")
                    if not looping:
                        if playback != None:
                            playback.stop()
                        break

                    if len(device.device_list) == 0:
                        break

                    # Leader dropped out
                    if device.handle_promotion(transceiver):
                        print("--------Taking over as new leader--------")
                    else:
                        print("Staying as follower under a new leader")


if __name__ == "__main__":

    # Create the buttons and connect their callbacks
    ax_stop = plt.axes([0.17, 0.15, 0.3, 0.2])
    ax_start = plt.axes([0.55, 0.15, 0.3, 0.2])
    btn_stop = Button(ax_stop, 'Stop')
    btn_start = Button(ax_start, 'Start')
    btn_stop.on_clicked(stop_loop)
    btn_start.on_clicked(start_loop)
    plt.show()

    main()
