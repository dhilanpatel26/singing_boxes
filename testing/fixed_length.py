import cc1101
import time
import sys
from datetime import timedelta

with cc1101.CC1101() as transceiver:
    #transceiver._set_modulation_format(cc1101.ModulationFormat.MSK)
    transceiver.set_base_frequency_hertz(433.5e6)
    transceiver.set_symbol_rate_baud(float(sys.argv[2]))
    #transceiver.set_sync_mode(cc1101.SyncMode.NO_PREAMBLE_AND_SYNC_WORD)
    #transceiver.set_sync_mode(cc1101.SyncMode.TRANSMIT_16_MATCH_16_BITS)
    #transceiver.set_packet_length_mode(cc1101.PacketLengthMode.FIXED)
    #transceiver.set_packet_length_bytes(4)
    #transceiver.disable_checksum()
    transceiver.set_output_power((0, 0xC0))  # OOK modulation: (off, on)
    print(transceiver)
    
    TRANSMITTER = sys.argv[1] == "1"
    
    while TRANSMITTER:
        transceiver.transmit(b"\xff\x00\xaa\xff")
        print("transmitting!")
        time.sleep(1)


    while not TRANSMITTER:
        msg = transceiver._wait_for_packet(timedelta(seconds=2))
        if msg != None and msg.checksum_valid:
            print("Received:", end=' ')
            #print(int(msg.payload.hex(), 16))
            print(msg.payload.hex())
