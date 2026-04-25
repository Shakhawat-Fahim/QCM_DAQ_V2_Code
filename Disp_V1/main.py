#Pin Assignemnet
#SCLK	GPIO 2
#MOSI	GPIO 3
#MISO	GPIO 4
#LCD CS	GPIO 5
#SD CS	GPIO 6
#Power	3.3V Regulated

from machine import Pin, SPI
import sharp_memory_display
import time

# 1. SPI Configuration
# GPIO 2 = SCLK, GPIO 3 = MOSI
# Polarity/Phase 0 is the standard for Sharp Memory LCDs
spi = SPI(0, baudrate=2000000, polarity=0, phase=0, sck=Pin(2), mosi=Pin(3))

# 2. Chip Select (GPIO 5)
lcd_cs = Pin(5, Pin.OUT, value=0)

# 3. Initialize Display
# This uses the 'SharpMemoryDisplay' class you just saved
display = sharp_memory_display.SharpMemoryDisplay(spi, lcd_cs, 128, 128)

print("Display test sequence starting...")

count = 0
while True:
    # Clear buffer (0 is White for HLSB mode)
    display.fill(0) 
    
    # 4. Draw Header
    display.text("PICO 2W SYSTEM", 10, 10, 1)
    display.hline(0, 22, 128, 1)
    
    # 5. Display Dynamic Data
    # Useful for tracking your RISC-V simulator cycles later!
    display.text("CYCLE: {}".format(count), 10, 40, 1)
    display.text("STATUS: RUNNING", 10, 60, 1)
    
    # Visual Pulse (A small blinking box to show the Pico is alive)
    if count % 2 == 0:
        display.fill_rect(110, 110, 10, 10, 1)
    
    # 6. Push to the physical screen
    display.show()
    
    # Console feedback so you know Thonny is still talking to the Pico
    print("Screen Updated - Cycle:", count)
    
    count += 1
    time.sleep(0.5)