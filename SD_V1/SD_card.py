from machine import Pin, SPI
import os
import sdcard
import time

# 1. SPI Configuration (GPIO 2=SCLK, 3=MOSI, 4=MISO)
# SD cards are sensitive to speed during init; we'll start at 1MHz
spi = SPI(0, baudrate=1000000, polarity=0, phase=0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))

# 2. Chip Selects
# CRITICAL: We must keep the LCD CS LOW so it stays off the bus
lcd_cs = Pin(5, Pin.OUT, value=0) 
sd_cs = Pin(6, Pin.OUT, value=1) # SD is Active Low (1 = Idle)

print("Starting SD Card Test...")

try:
    # 3. Initialize SD Card
    # This requires the sdcard.py driver in your /lib folder
    sd = sdcard.SDCard(spi, sd_cs)
    vfs = os.VfsFat(sd)
    os.mount(vfs, "/sd")
    print("Mount Success!")

    # 4. Write Test
    print("Writing to file...")
    with open("/sd/test.txt", "w") as f:
        f.write("Pico 2W Log\n")
        f.write("SD Card Interface: Working\n")

    # 5. Read Test
    print("Reading from file...")
    with open("/sd/test.txt", "r") as f:
        data = f.read()
        print("File Content:\n", data)

    # 6. Clean up
    os.umount("/sd")
    print("Test Complete. Card unmounted safely.")

except Exception as e:
    print("SD Card Error:", e)
    print("\nTroubleshooting Checklist:")
    print("1. Is the card FAT32 formatted?")
    print("2. Is MISO (GPIO 4) connected to BoosterPack pin 14?")