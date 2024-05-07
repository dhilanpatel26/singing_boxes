import cc1101
import time
import sys, os
import random
import numpy as np
# import matplotlib.pyplot as plt
# from matplotlib.widgets import Button
from datetime import timedelta
from uuid import getnode
from enum import Enum
from math import ceil


# define bit masks and shifts based on message details
class ActionCodes(Enum):
    ATTENDANCE = 0b1000
    RESPONSE = 0b0001
    SONG = 0b0010
    FIRST_LIST = 0b0011  # first list message (not necessary if we have followers add leader to list by default when attendance msg is heard)
    N_LIST = 0b0100  # following list messages
    CHECK_IN = 0b0101
    DELETE = 0b0110
    NEW_LEADER = 0b1111  # sent by a new leader to change leaders
    SONG_JOIN = 0b1100


class MessageBits(Enum):
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
    def __init__(self, msg: int):
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

        # negatives are trasmitted as two's complement
        if self.options == (1 << MessageBits.OPTION_LEN.value) - 1:
            self.options = -1

    def bit_masking(self, msg, mask, shift):
        return (msg & mask.value) >> shift.value

    def __str__(self) -> str:
        out = [
            f"message w/ Action: {self.action}",
            f"Leader Address: {hex(self.leader_addr)}",
            f"Follower Address: {hex(self.follow_addr)}",
            f"Options: {self.options}",
        ]
        return "\n\t".join(out)


def main():
    # with cc1101.CC1101() as transceiver:
    obj = cc1101.CC1101()
    transceiver = obj.__enter__()
    transceiver.set_base_frequency_hertz(433.92e6)
    transceiver.set_symbol_rate_baud(4800)
    transceiver.set_output_power(
        (0, 0xC0)
    )

    counter = 0
    while True:

        msg = transceiver._wait_for_packet(timedelta(seconds=1))
        if (
            msg != None and msg.checksum_valid
        ):
            msg = msg.payload.hex()[2:]
            msg = int(msg, 16)
            received = Message(msg)
            print("Received:", end=" ")
            print(received)

        if counter % 10 == 0:
            obj.__exit__(None, None, None)
            transceiver = obj.__enter__()
            transceiver.set_base_frequency_hertz(433.92e6)
            transceiver.set_symbol_rate_baud(4800)
            transceiver.set_output_power(
                (0, 0xC0)
            )


if __name__ == '__main__':
    main()
