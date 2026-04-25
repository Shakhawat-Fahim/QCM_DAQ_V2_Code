# main.py — Sharp Memory LCD API demo for Pico 2W
# Drop sharp_memory_display.py alongside this file on the Pico.

from machine import Pin, SPI
import sharp_memory_display as smd
import time

# ── Hardware setup ─────────────────────────────────────────────────────────────
spi = SPI(0, baudrate=2_000_000, polarity=0, phase=0,
          sck=Pin(2), mosi=Pin(3))
cs  = Pin(5, Pin.OUT, value=0)
lcd = smd.SharpMemoryDisplay(spi, cs, 128, 128)

# ── Colour constants (module-level, NOT class attributes) ─────────────────────
BLACK = smd.BLACK   # 1
WHITE = smd.WHITE   # 0

# ==============================================================================
# DEMO 1 — Wipe the screen
# ==============================================================================
lcd.clear()          # fills white + pushes to screen
time.sleep(0.5)

# ==============================================================================
# DEMO 2 — Simple text at a logical row/col grid
# ==============================================================================
lcd.clear_buffer()
lcd.print_line("PICO 2W SYSTEM", row=0)
lcd.print_line("----------------", row=1)
lcd.print_line("STATUS: RUNNING", row=3)
lcd.print_line("HEAP:  64 KB",    row=4)
lcd.show()
time.sleep(1)

# ==============================================================================
# DEMO 3 — Exact pixel positioning
# ==============================================================================
lcd.clear_buffer()
lcd.print_at("X=10,Y=30", x=10, y=30)
lcd.print_at("X=40,Y=60", x=40, y=60)
lcd.show()
time.sleep(1)

# ==============================================================================
# DEMO 4 — Double-size (scaled) text
# ==============================================================================
lcd.clear_buffer()
lcd.print_line("BIG TEXT", row=0, scale=2)
lcd.show()
time.sleep(1)

# ==============================================================================
# DEMO 5 — Multi-line helper
# ==============================================================================
lcd.clear_buffer()
lcd.print_multiline([
    "Line one",
    "Line two",
    "Line three",
    "Line four",
], start_row=0, auto_show=True)
time.sleep(1)

# ==============================================================================
# DEMO 6 — Drawing primitives
# ==============================================================================
lcd.clear_buffer()
lcd.draw_hline(0, 20, 128)
lcd.draw_rect(5, 30, 50, 30)
lcd.draw_filled_rect(70, 30, 50, 30)
lcd.draw_line(0, 0, 127, 127)
lcd.draw_pixel(64, 64)
lcd.show()
time.sleep(1)

# ==============================================================================
# DEMO 7 — Live update loop (cycle counter + heartbeat box)
# ==============================================================================
print("Live loop — Ctrl-C to stop")
print("Screen fits {} rows x {} cols".format(
    lcd.max_text_rows(), lcd.max_text_cols()))

count = 0
while True:
    lcd.clear_buffer()

    # Header + separator
    lcd.print_line("PICO 2W SYSTEM", row=0)
    lcd.draw_hline(0, 10, 128)

    # Dynamic data
    lcd.print_line("CYCLE: {:05d}".format(count), row=2)
    lcd.print_line("STATUS: OK",               row=3)

    # Heartbeat — blink a small filled square bottom-right
    if count % 2 == 0:
        lcd.draw_filled_rect(110, 110, 10, 10, BLACK)
    else:
        lcd.draw_filled_rect(110, 110, 10, 10, WHITE)

    lcd.show()
    print("Cycle:", count)

    count += 1
    time.sleep(0.5)
