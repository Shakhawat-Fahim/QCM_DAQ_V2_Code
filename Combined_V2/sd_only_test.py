"""
sd_only_test.py — SD card isolation diagnostic for Pico 2W

Run this BY ITSELF (not alongside any LCD code) to verify the SD card works.
This holds LCD CS firmly in its idle state the whole time so the LCD can
never interfere with the SPI bus.

If this script fails with the same timeout error, the problem is definitely
hardware (wiring, power, card, or sdcard.py not installed), NOT software.
If this script succeeds, the issue is specific to sharing the bus with
the LCD and we can debug from there.
"""

from machine import Pin, SPI
import os
import time

# Force LCD CS into idle state (LOW = idle for Sharp LCD) and LEAVE IT ALONE
lcd_cs = Pin(5, Pin.OUT, value=0)

# SD CS in idle state (HIGH = idle for SD card)
sd_cs = Pin(6, Pin.OUT, value=1)

print("LCD CS held LOW (idle). Starting SD test...\n")

# Try progressively slower baud rates if the first one fails
for baud in (1_000_000, 400_000, 100_000):
    print("--- Trying baudrate =", baud, "Hz ---")
    try:
        spi = SPI(0, baudrate=baud, polarity=0, phase=0,
                  sck=Pin(2), mosi=Pin(3), miso=Pin(4))

        # Give the card time to settle
        time.sleep(0.1)

        import sdcard
        sd = sdcard.SDCard(spi, sd_cs)

        vfs = os.VfsFat(sd)
        os.mount(vfs, "/sd")
        print(">>> MOUNT SUCCESS at", baud, "Hz")

        print("Files on card:", os.listdir("/sd"))

        # Write/read round-trip
        with open("/sd/diag.txt", "w") as f:
            f.write("diagnostic OK at {} Hz\n".format(baud))
        with open("/sd/diag.txt", "r") as f:
            print("Read back:", f.read().strip())

        os.umount("/sd")
        print(">>> SD CARD IS WORKING.  Use baudrate =", baud)
        break

    except Exception as e:
        print("FAILED at", baud, "Hz:", e)
        # Try to unmount in case it partially mounted
        try:
            os.umount("/sd")
        except:
            pass
        time.sleep(0.5)
else:
    print("\n>>> ALL SPEEDS FAILED.")
    print("Hardware checks:")
    print("  1. Is MISO physically connected to GPIO 4?")
    print("  2. Is the card inserted all the way?")
    print("  3. Is sdcard.py in /lib/ on the Pico?")
    print("  4. Is the card formatted FAT32 (not exFAT)?")
    print("  5. Is the card 32GB or smaller?")
    print("  6. Is VCC 3.3V (NOT 5V)?")
