"""
================================================================================
main.py  —  Full demo of Sharp Memory LCD + SD Card APIs on Raspberry Pi Pico 2W
================================================================================

This script walks through EVERY public method of the two classes in
`pico_peripherals.py`, one feature at a time, with on-screen labels and
console logging so you can see exactly what's happening.

REQUIREMENTS ON THE PICO FILESYSTEM
-----------------------------------
    /main.py                 (this file)
    /pico_peripherals.py     (unified driver — LCD + SD wrapper)
    /lib/sdcard.py           (stock MicroPython SD card driver)

PIN WIRING (BoosterPack / TI LCD)
---------------------------------
    SCLK    -> GPIO 2
    MOSI    -> GPIO 3
    MISO    -> GPIO 4        (required for SD card)
    LCD CS  -> GPIO 5        (Sharp LCD is active HIGH)
    SD  CS  -> GPIO 6        (SD card  is active LOW)
    Power   -> 3.3V regulated

HOW TO READ THIS FILE
---------------------
The file is organised into numbered demo sections (A through I). Each section
is a self-contained block showing ONE concept. You can delete or comment out
any section you don't need.

    A.  Hardware setup           — SPI bus + CS pins
    B.  Display basics           — clear, show, print_line
    C.  Text features            — scaling, exact positioning, multi-line
    D.  Drawing primitives       — pixels, lines, rectangles
    E.  Full dashboard           — real-world layout combining everything
    F.  SD card — basic I/O      — mount, write, read, list, unmount
    G.  SD card — advanced       — append, line-based I/O, stats, cleanup
    H.  Read SD -> show on LCD   — display a file's contents verbatim
    I.  Live loop                — combined LCD + SD data-logger
================================================================================
"""

from machine import Pin, SPI
import pico_peripherals as pp
import time


# ==============================================================================
# SECTION A — HARDWARE SETUP
# ==============================================================================
# The LCD and the SD card live on the SAME SPI0 bus. Each has its own Chip
# Select (CS) pin. Only one CS may be in its ACTIVE state at any moment —
# our driver takes care of that automatically when you pass the "other"
# CS into each constructor.
# ==============================================================================

print("Driver version:", getattr(pp, "__version__", "UNKNOWN-OLD-FILE"))

# Shared SPI bus — start at 1 MHz (SD cards need low speed during init)
spi = SPI(0, baudrate=1_000_000, polarity=0, phase=0,
          sck=Pin(2), mosi=Pin(3), miso=Pin(4))

# Chip-select pins in their IDLE state
lcd_cs = Pin(5, Pin.OUT, value=0)   # LCD: idle LOW,  active HIGH
sd_cs  = Pin(6, Pin.OUT, value=1)   # SD : idle HIGH, active LOW

# Instantiate both peripherals. Telling each class about the other's CS pin
# lets them "take turns" on the bus automatically.
lcd = pp.SharpMemoryDisplay(spi, lcd_cs, sd_cs_pin=sd_cs)
sd  = pp.SDCardStorage(spi, sd_cs, lcd_cs_pin=lcd_cs)


# ------------------------------------------------------------------------------
# Tiny helper used throughout the demo: label each section on-screen
# ------------------------------------------------------------------------------
def banner(title):
    """Clear the screen and show a section title, then a short pause."""
    lcd.clear_buffer()
    lcd.print_line(title, row=0, scale=1)
    lcd.draw_hline(0, 10, 128)
    lcd.show()
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)
    time.sleep(0.7)


# ==============================================================================
# SECTION B — DISPLAY BASICS
# ==============================================================================
# The three calls you will use 90% of the time:
#   lcd.clear()          — wipe and push in one step
#   lcd.clear_buffer()   — wipe the in-memory buffer only (no screen update)
#   lcd.show()           — push the buffer to the physical screen
#
# Drawing calls only modify the buffer; nothing appears on screen until you
# call show() (or pass auto_show=True to a drawing call).
# ==============================================================================

banner("B. DISPLAY BASICS")

# Demo B1 — fill the screen black then white
lcd.clear(pp.BLACK)            # full black + immediate push
time.sleep(0.5)
lcd.clear(pp.WHITE)            # full white + immediate push
time.sleep(0.3)

# Demo B2 — draw multiple things, THEN push once
lcd.clear_buffer()             # buffer only, no push
lcd.print_line("Hello Pico!",       row=2)
lcd.print_line("Batched update",    row=3)
lcd.print_line("one show() call",   row=4)
lcd.show()                     # single push to screen
time.sleep(1.2)


# ==============================================================================
# SECTION C — TEXT FEATURES
# ==============================================================================
# Three ways to draw text:
#   print_line(text, row, col)    — grid-based (row*8 px, col*8 px)
#   print_at(text, x, y)          — exact pixel position
#   print_multiline([...], ...)   — list of strings, auto-incrementing rows
#
# Every text call accepts:
#   color=1 (BLACK) or color=0 (WHITE)
#   bg=0 / bg=1                   (only used when scale > 1)
#   scale=1/2/3/...               (integer pixel multiplier)
#   auto_show=True                (push immediately; saves a show() call)
# ==============================================================================

banner("C. TEXT FEATURES")

# Demo C1 — grid-based layout
lcd.clear_buffer()
lcd.print_line("ROW 0",  row=0)
lcd.print_line("ROW 2",  row=2)
lcd.print_line("ROW 4",  row=4)
lcd.print_line("ROW 15", row=15)           # last row that fits on 128 px
lcd.show()
time.sleep(1.2)

# Demo C2 — exact pixel positioning
lcd.clear_buffer()
lcd.print_at("x=0,y=0",   x=0,  y=0)
lcd.print_at("x=30,y=40", x=30, y=40)
lcd.print_at("x=50,y=90", x=50, y=90)
lcd.show()
time.sleep(1.2)

# Demo C3 — scaled text (scale=2 means each pixel becomes a 2x2 block)
lcd.clear_buffer()
lcd.print_line("1x text", row=0, scale=1)
lcd.print_line("2x",      row=1, scale=2)   # row 1 at scale 2 = y=16
lcd.print_line("3x",      row=2, scale=3)   # row 2 at scale 3 = y=48
lcd.show()
time.sleep(1.5)

# Demo C4 — multi-line helper + auto_show
lcd.clear_buffer()
lcd.print_multiline([
    "Line 1: status",
    "Line 2: normal",
    "Line 3: temp OK",
    "Line 4: 42.0 C",
    "Line 5: logged",
], start_row=1, auto_show=True)             # push at the end, all at once
time.sleep(1.5)

# Demo C5 — inverse text (white text on black background)
lcd.clear_buffer()
lcd.draw_filled_rect(0, 0, 128, 12, pp.BLACK)           # black bar on top
lcd.print_at("INVERSE TITLE", x=2, y=2, color=pp.WHITE) # white text on it
lcd.print_line("Body text below", row=2)
lcd.show()
time.sleep(1.5)


# ==============================================================================
# SECTION D — DRAWING PRIMITIVES
# ==============================================================================
# Every drawing method has the same shape:
#   draw_xxx(..., color=1, auto_show=False)
#
# Available primitives:
#   draw_pixel(x, y)
#   draw_line(x1, y1, x2, y2)
#   draw_hline(x, y, width)
#   draw_vline(x, y, height)
#   draw_rect(x, y, w, h)            — hollow outline
#   draw_filled_rect(x, y, w, h)     — solid fill
# ==============================================================================

banner("D. DRAWING PRIMITIVES")

# Demo D1 — a bit of everything
lcd.clear_buffer()
lcd.print_line("DRAWING DEMO", row=0)
lcd.draw_hline(0, 10, 128)                  # separator under the title

# Horizontal & vertical lines forming a box
lcd.draw_hline(10, 20, 108)
lcd.draw_hline(10, 70, 108)
lcd.draw_vline(10, 20, 50)
lcd.draw_vline(117, 20, 50)

# Diagonal line across the box
lcd.draw_line(10, 20, 117, 70)

# Hollow + filled rectangles
lcd.draw_rect(20, 80, 40, 20)
lcd.draw_filled_rect(70, 80, 40, 20)

# A sprinkle of individual pixels in a line
for x in range(0, 128, 4):
    lcd.draw_pixel(x, 120)

lcd.show()
time.sleep(2)

# Demo D2 — simple bar chart built from filled rectangles
lcd.clear_buffer()
lcd.print_line("BAR CHART", row=0)
lcd.draw_hline(0, 10, 128)

values    = [20, 45, 30, 60, 15, 50]        # made-up data
bar_w     = 16
bar_gap   = 4
base_y    = 120
max_h     = 90                              # max bar height in pixels

for i, v in enumerate(values):
    x = 5 + i * (bar_w + bar_gap)
    h = int(v * max_h / 100)
    lcd.draw_filled_rect(x, base_y - h, bar_w, h, pp.BLACK)

lcd.show()
time.sleep(2)


# ==============================================================================
# SECTION E — FULL DASHBOARD LAYOUT
# ==============================================================================
# A realistic "one-screen dashboard" combining title bar, grouped text,
# a status indicator, and a border. This is the pattern you'd use for a
# real project — monitor, data-logger, game HUD, etc.
# ==============================================================================

banner("E. DASHBOARD LAYOUT")
time.sleep(0.3)

lcd.clear_buffer()

# Title bar (inverse)
lcd.draw_filled_rect(0, 0, 128, 14, pp.BLACK)
lcd.print_at("PICO 2W DASH", x=4, y=3, color=pp.WHITE)

# Key/value readouts
lcd.print_line("Voltage :  3.31V", row=2)
lcd.print_line("Current :  120mA", row=3)
lcd.print_line("Temp    :  42.5C", row=4)
lcd.print_line("Uptime  :  00:12", row=5)

# Divider
lcd.draw_hline(0, 56, 128)

# Status section
lcd.print_line("STATUS",      row=8)
lcd.print_line("  SYSTEM: OK",     row=9)
lcd.print_line("  SENSOR: OK",     row=10)
lcd.print_line("  SD    : READY",  row=11)

# Outer border + corner "LED" indicator
lcd.draw_rect(0, 0, 128, 128)
lcd.draw_filled_rect(118, 118, 8, 8, pp.BLACK)

lcd.show()
time.sleep(2.5)


# ==============================================================================
# SECTION F — SD CARD BASICS
# ==============================================================================
# Core workflow: mount -> do stuff -> unmount.
# Each call automatically deselects the LCD before touching the bus.
# Paths are relative to the mount point ("/sd") unless you pass an absolute
# path starting with "/".
# ==============================================================================

banner("F. SD CARD BASICS")

try:
    # F1 — Mount the card
    print("Mounting SD card...")
    sd.mount()
    print("Mount OK.  is_mounted =", sd.is_mounted)

    lcd.clear_buffer()
    lcd.print_line("SD: MOUNTED", row=0)

    # F2 — Write a text file (overwrites any existing file)
    print("Writing hello.txt...")
    sd.write("hello.txt", "Hello from Pico 2W!\nLine two\n")
    lcd.print_line("WROTE hello.txt", row=1)

    # F3 — Read it back
    content = sd.read("hello.txt")
    print("hello.txt contents:")
    print(content)
    lcd.print_line("READ OK", row=2)

    # F4 — List files at the root of the card
    files = sd.list()
    print("Files on card:", files)
    lcd.print_line("Files: {}".format(len(files)), row=3)

    # F5 — Check existence
    print("hello.txt exists?", sd.exists("hello.txt"))
    print("nope.txt   exists?", sd.exists("nope.txt"))

    # F6 — File size
    print("hello.txt size:", sd.size("hello.txt"), "bytes")
    lcd.print_line("Size: {}B".format(sd.size("hello.txt")), row=4)

    lcd.show()
    time.sleep(2)

except Exception as e:
    print("SD Error in Section F:", e)
    lcd.clear_buffer()
    lcd.print_line("SD ERROR", row=0)
    lcd.print_line(str(e)[:16], row=1)
    lcd.show()
    time.sleep(2)


# ==============================================================================
# SECTION G — SD CARD ADVANCED
# ==============================================================================
# Beyond the basics:
#   append()        — add to end of file without erasing
#   write_lines()   — write a list of strings, one per line
#   read_lines()    — read file back as a list of strings
#   stats()         — free / used / total bytes on the card
#   mkdir/rmdir     — directory management
#   remove()        — delete file
#
# Context-manager form (auto mount/unmount) is also demonstrated.
# ==============================================================================

banner("G. SD CARD ADVANCED")

try:
    if not sd.is_mounted:
        sd.mount()

    # G1 — Append to a log file (creates file if it doesn't exist)
    print("Appending to events.log...")
    sd.append("events.log", "boot  @ {}\n".format(time.ticks_ms()))
    sd.append("events.log", "ready @ {}\n".format(time.ticks_ms()))
    sd.append("events.log", "demo  @ {}\n".format(time.ticks_ms()))

    # G2 — Line-based I/O
    print("Writing lines to config.txt...")
    sd.write_lines("config.txt", [
        "brightness=80",
        "mode=normal",
        "sample_rate=10",
    ])

    lines = sd.read_lines("config.txt")
    print("config.txt has {} lines:".format(len(lines)))
    for i, ln in enumerate(lines):
        print("  {}: {}".format(i, ln))

    # G3 — Show the log on screen
    log_lines = sd.read_lines("events.log")
    lcd.clear_buffer()
    lcd.print_line("events.log:", row=0)
    lcd.draw_hline(0, 10, 128)
    for i, ln in enumerate(log_lines[:8]):       # show up to 8 entries
        lcd.print_line(ln[:16], row=2 + i)       # truncate to 16 chars
    lcd.show()
    time.sleep(2.5)

    # G4 — Filesystem stats
    stats = sd.stats()
    total_kb = stats["total_bytes"] // 1024
    free_kb  = stats["free_bytes"]  // 1024
    used_kb  = stats["used_bytes"]  // 1024
    print("Card: {} KB total, {} KB used, {} KB free".format(
        total_kb, used_kb, free_kb))

    lcd.clear_buffer()
    lcd.print_line("SD STATS",                  row=0)
    lcd.draw_hline(0, 10, 128)
    lcd.print_line("Total: {}K".format(total_kb), row=2)
    lcd.print_line("Used : {}K".format(used_kb),  row=3)
    lcd.print_line("Free : {}K".format(free_kb),  row=4)
    lcd.show()
    time.sleep(2)

    # G5 — Directory operations
    if not sd.exists("logs"):
        sd.mkdir("logs")
        print("Created /sd/logs/")
    sd.write("logs/today.txt", "Sample log entry\n")
    print("Contents of /sd/logs:", sd.list("logs"))

    # G6 — Cleanup: remove the demo files so the card doesn't fill up
    #      Comment these lines out if you want to keep the files to inspect.
    print("Cleaning up demo files...")
    for f in ["hello.txt", "events.log", "config.txt"]:
        if sd.exists(f):
            sd.remove(f)
    if sd.exists("logs/today.txt"):
        sd.remove("logs/today.txt")
    if "logs" in sd.list():
        sd.rmdir("logs")

    sd.unmount()
    print("Unmounted.")

except Exception as e:
    print("SD Error in Section G:", e)

# G7 — Context-manager form (the Pythonic way)
#      This block auto-mounts on entry and auto-unmounts on exit,
#      even if an exception is raised inside.
try:
    with pp.SDCardStorage(spi, sd_cs, lcd_cs_pin=lcd_cs) as sd2:
        sd2.write("ctx_demo.txt", "Written inside a 'with' block.\n")
        print("ctx_demo.txt:", sd2.read("ctx_demo.txt"))
        sd2.remove("ctx_demo.txt")
    print("Context manager exited cleanly (auto-unmounted).")
except Exception as e:
    print("Context-manager demo error:", e)


# ==============================================================================
# SECTION H — READ A FILE FROM SD AND DISPLAY ITS CONTENTS ON THE LCD
# ==============================================================================
# This is the simplest, most common pairing of the two peripherals:
#
#     1. Mount the SD card
#     2. Read a text file
#     3. Show the file's contents on the LCD, line by line
#     4. Unmount
#
# Design notes:
#   - The LCD fits 16 text rows of 16 characters each (at scale=1). Lines
#     longer than 16 chars are truncated with "..". Files with more than
#     14 lines (we reserve 2 rows for the filename header) are shown
#     across multiple "pages" — auto-advancing every 2 seconds.
#   - File.read() returns the whole file as one string; splitting on "\n"
#     gives us a list of lines regardless of platform.
#   - If the file doesn't exist, we show a friendly error on screen.
# ==============================================================================

banner("H. READ SD -> SHOW ON LCD")

# --- Tunables --------------------------------------------------------------
FILENAME         = "readme.txt"   # the file we will display
CHARS_PER_ROW    = 16             # 128 px / 8 px per char = 16
HEADER_ROWS      = 2              # rows reserved for the filename header
ROWS_PER_PAGE    = 14             # 16 total - 2 header = 14 body rows
PAGE_DELAY_SEC   = 2              # how long to show each page
# ---------------------------------------------------------------------------


def show_file_on_lcd(sd_obj, filename):
    """
    Read `filename` from the SD card and render it verbatim on the LCD.

    - Wraps long lines via simple truncation (not word-wrap) — this keeps
      the on-screen output a faithful mirror of the file's line structure.
    - Paginates when the file has more lines than fit on one screen.
    - Catches file-not-found and shows an on-screen error instead of crashing.
    """

    # --- Error handling: make sure the file exists before trying to read it.
    if not sd_obj.exists(filename):
        lcd.clear_buffer()
        lcd.print_line("FILE NOT FOUND", row=0)
        lcd.print_line(filename[:16],    row=2)
        lcd.show()
        print("File '{}' not found on SD".format(filename))
        return

    # --- Read the entire file. For huge files you'd stream line-by-line
    #     instead, but our LCD only holds ~14 lines per page so this is fine.
    raw = sd_obj.read(filename)
    lines = raw.split("\n")

    # Strip a trailing empty string caused by a final newline in the file
    if lines and lines[-1] == "":
        lines.pop()

    print("Read {} ({} lines, {} chars)".format(
        filename, len(lines), len(raw)))

    # --- Paginate: chunk the lines into screens of ROWS_PER_PAGE each.
    total_lines = len(lines)
    total_pages = max(1, (total_lines + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE)

    for page in range(total_pages):
        lcd.clear_buffer()

        # Header: filename on row 0, separator on row 1
        header = filename
        if total_pages > 1:
            header = "{} {}/{}".format(filename, page + 1, total_pages)
        lcd.print_line(header[:CHARS_PER_ROW], row=0)
        lcd.draw_hline(0, 10, 128)

        # Body: up to ROWS_PER_PAGE lines from the file
        start = page * ROWS_PER_PAGE
        end   = min(start + ROWS_PER_PAGE, total_lines)
        for i, line in enumerate(lines[start:end]):
            # Truncate lines that are too wide for the screen.
            # Replace last 2 chars with ".." as a "this line was cut" marker.
            if len(line) > CHARS_PER_ROW:
                shown = line[:CHARS_PER_ROW - 2] + ".."
            else:
                shown = line
            lcd.print_line(shown, row=HEADER_ROWS + i)

        lcd.show()
        time.sleep(PAGE_DELAY_SEC)


# --- Run the demo --------------------------------------------------------
try:
    sd.mount()

    # Create a sample file so the demo always has something to display.
    # In a real project, you would skip this — the file would already exist
    # on the card (e.g. copied there from your computer's card reader).
    if not sd.exists(FILENAME):
        print("Creating sample", FILENAME)
        sd.write_lines(FILENAME, [
            "Pico 2W demo",
            "----------------",
            "This file lives",
            "on the SD card.",
            "",
            "Every line you",
            "see here was",
            "read from FAT32",
            "storage and then",
            "pushed to the",
            "Sharp Memory LCD",
            "one row at a time.",
            "",
            "End of sample.",
            "",
            "(bonus page)",
            "Long lines get",
            "truncated with ..",
            "like this example of a really long line",
        ])

    # Show the file on the LCD
    show_file_on_lcd(sd, FILENAME)

    sd.unmount()

except Exception as e:
    print("Section H error:", e)
    lcd.clear_buffer()
    lcd.print_line("SD READ ERROR",  row=0)
    lcd.print_line(str(e)[:16],      row=2)
    lcd.show()
    time.sleep(2)


# ==============================================================================
# SECTION I — LIVE LOOP: COMBINED DATA LOGGER
# ==============================================================================
# Realistic continuous-operation example:
#   - Update the LCD every 500 ms with live data
#   - Every 10th cycle, append one row to a CSV file on the SD card
#   - Keep running forever (Ctrl-C to stop in Thonny)
# ==============================================================================

banner("H. LIVE LOGGER")
print("Press Ctrl-C to stop.\n")

LOG_EVERY_N_CYCLES = 10

# Open a fresh CSV and write a header row
try:
    sd.mount()
    sd.write("run.csv", "cycle,ms,note\n")
    sd.unmount()
except Exception as e:
    print("Could not prepare run.csv:", e)

count = 0
while True:
    # --- Update the LCD ---
    lcd.clear_buffer()

    # Title bar
    lcd.draw_filled_rect(0, 0, 128, 14, pp.BLACK)
    lcd.print_at("LIVE LOGGER", x=4, y=3, color=pp.WHITE)

    # Live data
    lcd.print_line("CYCLE : {:05d}".format(count),            row=2)
    lcd.print_line("MS    : {}".format(time.ticks_ms()),      row=3)
    lcd.print_line("LOGGED: {}".format(count // LOG_EVERY_N_CYCLES), row=4)

    # Outer border + heartbeat square
    lcd.draw_rect(0, 0, 128, 128)
    if count % 2 == 0:
        lcd.draw_filled_rect(116, 116, 8, 8, pp.BLACK)

    lcd.show()

    # --- Every N cycles, log a row to the CSV on SD ---
    if count % LOG_EVERY_N_CYCLES == 0 and count > 0:
        try:
            sd.mount()
            sd.append("run.csv",
                      "{},{},cycle_mark\n".format(count, time.ticks_ms()))
            sd.unmount()
            print("Logged cycle", count)
        except Exception as e:
            print("Log failed:", e)

    count += 1
    time.sleep(0.5)
