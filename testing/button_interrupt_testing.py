import signal
import sys
import RPi.GPIO as GPIO
from datetime import timedelta
import time
import cc1101
import threading

BUTTON_GPIO = 26
running = False
button_thread = None
main_thread = None


def signal_handler(sig, frame):
    GPIO.cleanup()
    sys.exit(0)


def button_pressed_callback(channel):
    global running, button_thread, main_thread
    if running:
        print("Button pressed! Stopping main")
        running = False
        main_thread.join()
    else:
        print("Button pressed! Running main")
        main_thread = threading.Thread(target=main)
        main_thread.start()


def send(transceiver, duration):
    # send repeatedly for duration of time given
    start_time = time.time()
    num = 0
    while time.time() - start_time <= duration:
        print(f"Transmitting: {num}")
        transceiver.transmit(bytes([num]))
        num += 1
        num %= 255
        time.sleep(0.2)


def receive(transceiver, timeout):
    # listen for message until timeout reached
    start_time = time.time()
    while time.time() - start_time < timeout:
        msg = transceiver._wait_for_packet(timedelta(seconds=2))
        if msg != None:
            # msg.payload.hex() gives string of hex digits
            # convert to int w/ base 16
            print("Received:", end=" ")
            print(int(msg.payload.hex(), 16))
            return True
    return False

        
def main():
    global running
    running = True
    # read cmd line args
    LEADER = sys.argv[1] == "1"
    if LEADER:
        print("--------Leader---------")
    else:
        print("--------Follower, listening...")

    with cc1101.CC1101() as transceiver:
        transceiver.set_base_frequency_hertz(433.92e6)
        transceiver.set_symbol_rate_baud(4800)  # default
        # ~ transceiver._set_modulation_format(cc1101.ModulationFormat.FSK2)
        num = 0
        # ~ transceiver.disable_checksum() # don't think we want to disable this
        transceiver.set_output_power((5, 0xC6))
        print(transceiver)

        while LEADER:  # leader loop
            # print(f"Transmitting: {num}")
            # transceiver.transmit(bytes([num]))
            # num += 1
            # num %= 255
            # time.sleep(1)
            send(transceiver, 1)
            response = False
            start_time = time.time()
            if receive(transceiver, 2):  # later will also check for correct address
                response = True
                time.sleep(1)

        while not LEADER:  # receiver (follower) loop
            # msg = transceiver._wait_for_packet(timedelta(seconds=2))
            # if msg != None:
            # msg.payload.hex() gives string of hex digits
            # convert to int w/ base 16
            # print(int(msg.payload.hex(), 16))
            if receive(transceiver, 5):
                time.sleep(1)
                send(transceiver, 1)  # send response after hearing a message


if __name__ == "__main__":
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(
        BUTTON_GPIO, GPIO.FALLING, callback=button_pressed_callback, bouncetime=200
    )
    signal.signal(signal.SIGINT, signal_handler)

    button_thread = threading.Thread(target=signal.pause)
    button_thread.start()

    signal.pause()


