# `pico_peripherals` — API Reference

Driver module for the Raspberry Pi Pico 2 W providing a unified interface to a
**Sharp Memory LCD** (128×128) and a **FAT-formatted SD card** sharing a single
SPI bus.

**Version:** 3.2
**MicroPython target:** Pico 2 W (RP2350) — also works on Pico 1 / RP2040
**Dependencies:** `framebuf` (built in), `sdcard` (must exist in `/lib/`)

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Hardware Wiring](#hardware-wiring)
3. [Module Constants](#module-constants)
4. [`SharpMemoryDisplay` Class](#class-sharpmemorydisplay)
   - [Constructor](#constructor)
   - [Display state methods](#display-state-methods)
   - [Text methods](#text-methods)
   - [Drawing methods](#drawing-methods)
   - [Utility methods](#utility-methods)
5. [`SDCardStorage` Class](#class-sdcardstorage)
   - [Constructor](#constructor-1)
   - [Mount control](#mount-control)
   - [File I/O](#file-io)
   - [Filesystem operations](#filesystem-operations)
   - [Context manager](#context-manager)
6. [Bus Sharing & Arbitration](#bus-sharing--arbitration)
7. [Error Handling](#error-handling)
8. [Common Recipes](#common-recipes)

---

## Quick Start

```python
from machine import Pin, SPI
import pico_peripherals as pp

# Shared SPI bus
spi = SPI(0, baudrate=1_000_000, polarity=0, phase=0,
          sck=Pin(2), mosi=Pin(3), miso=Pin(4))

# Chip-select pins in their idle states
lcd_cs = Pin(5, Pin.OUT, value=0)   # LCD idle = LOW
sd_cs  = Pin(6, Pin.OUT, value=1)   # SD  idle = HIGH

# Instantiate — pass each device the OTHER's CS pin for auto-arbitration
lcd = pp.SharpMemoryDisplay(spi, lcd_cs, sd_cs_pin=sd_cs)
sd  = pp.SDCardStorage(spi, sd_cs, lcd_cs_pin=lcd_cs)

# Display
lcd.clear()
lcd.print_line("Hello, world!", row=0)
lcd.show()

# Storage
sd.mount()
sd.write("hello.txt", "Hi from Pico\n")
print(sd.read("hello.txt"))
sd.unmount()
```

---

## Hardware Wiring

| Function       | Pico GPIO | Notes                           |
| -------------- | --------- | ------------------------------- |
| SCLK           | 2         | SPI0 clock                      |
| MOSI           | 3         | SPI0 master-out                 |
| MISO           | 4         | SPI0 master-in (SD only)        |
| LCD CS         | 5         | Active **HIGH** for Sharp LCD   |
| SD CS          | 6         | Active **LOW** for SD card      |
| Power          | 3.3 V     | Both peripherals                |
| Ground         | GND       | Shared                          |

You can use different GPIO pins as long as they map to a valid SPI peripheral —
just adjust the `SPI()` constructor and `Pin()` numbers in your code.

---

## Module Constants

| Name              | Value | Purpose                                    |
| ----------------- | ----- | ------------------------------------------ |
| `WHITE`           | `0`   | Pixel "off" (background)                   |
| `BLACK`           | `1`   | Pixel "on" (foreground)                    |
| `CHAR_W`          | `8`   | Built-in font character width in pixels    |
| `CHAR_H`          | `8`   | Built-in font character height in pixels   |
| `__version__`     | `"3.2"` | Module version, printed on import         |

Access via the module:
```python
import pico_peripherals as pp
pp.BLACK   # 1
pp.WHITE   # 0
```

---

## class `SharpMemoryDisplay`

A subclass of `framebuf.FrameBuffer` providing a high-level API for
128×128 monochrome Sharp Memory LCDs (LS013B4DN04 and compatible).

### Constructor

```python
SharpMemoryDisplay(spi, cs, width=128, height=128, sd_cs_pin=None)
```

| Parameter   | Type       | Default | Description                                                 |
| ----------- | ---------- | ------- | ----------------------------------------------------------- |
| `spi`       | `SPI`      | —       | Configured `machine.SPI` instance                           |
| `cs`        | `Pin`      | —       | LCD chip-select pin (output, active HIGH)                   |
| `width`     | `int`      | `128`   | Pixel width                                                 |
| `height`    | `int`      | `128`   | Pixel height                                                |
| `sd_cs_pin` | `Pin\|None`| `None`  | Optional SD-card CS pin — held HIGH (idle) during LCD writes |

### Display state methods

#### `show()`
Pushes the in-memory frame buffer to the physical display. Call this after any
drawing or text operations to make them visible.

```python
lcd.show()
```

---

#### `clear(color=0)`
Fills the entire display with one color **and pushes immediately** to the
screen.

| Parameter | Type | Default | Description                  |
| --------- | ---- | ------- | ---------------------------- |
| `color`   | int  | `0`     | `0` = white, `1` = black     |

```python
lcd.clear()           # blank the screen (white)
lcd.clear(pp.BLACK)   # fill with black
```

---

#### `clear_buffer(color=0)`
Same as `clear()` but **does not push** to the display. Use when you want to
batch multiple drawing operations and only push once at the end.

```python
lcd.clear_buffer()
lcd.print_line("Title", row=0)
lcd.draw_hline(0, 10, 128)
lcd.show()            # one push for the whole frame
```

### Text methods

All text methods use the built-in 8×8 monospace font and accept these common
parameters:

| Parameter   | Type | Default | Description                                          |
| ----------- | ---- | ------- | ---------------------------------------------------- |
| `color`     | int  | `1`     | Foreground (1 = BLACK, 0 = WHITE)                    |
| `bg`        | int  | `0`     | Background color (only used when `scale > 1`)        |
| `scale`     | int  | `1`     | Integer pixel multiplier (1 = 8×8, 2 = 16×16, …)     |
| `auto_show` | bool | `False` | If `True`, automatically push to screen after drawing |

---

#### `print_line(text, row, col=0, color=1, bg=0, scale=1, auto_show=False)`
Print a string at a logical row/column position. Positions are based on the
character grid: each row is `8 * scale` pixels tall, each column `8 * scale`
pixels wide.

```python
lcd.print_line("Header",   row=0)         # top of screen
lcd.print_line("Body",     row=2, col=2)  # 2 chars in, 2 rows down
lcd.print_line("BIG",      row=3, scale=2)
```

A 128×128 display fits **16 rows × 16 columns** at scale 1.

---

#### `print_at(text, x, y, color=1, bg=0, scale=1, auto_show=False)`
Print a string at exact pixel coordinates `(x, y)` (top-left of the text).

```python
lcd.print_at("X=10,Y=30", x=10, y=30)
```

---

#### `print_multiline(lines, start_row=0, col=0, color=1, scale=1, auto_show=False)`
Print a list of strings on consecutive rows.

| Parameter   | Type      | Default | Description                          |
| ----------- | --------- | ------- | ------------------------------------ |
| `lines`     | `list[str]` | —     | Strings to print, one per row        |
| `start_row` | int       | `0`     | First row of output                  |
| `col`       | int       | `0`     | Starting column for all rows         |

```python
lcd.print_multiline([
    "Status: OK",
    "Temp:   42 C",
    "Volts:  3.3",
], start_row=2, auto_show=True)
```

### Drawing methods

All drawing methods accept `color` (default `1` = black) and `auto_show`
(default `False`).

| Method                                       | Draws                                  |
| -------------------------------------------- | -------------------------------------- |
| `draw_pixel(x, y, color=1)`                  | Single pixel                           |
| `draw_line(x1, y1, x2, y2, color=1)`         | Arbitrary line                         |
| `draw_hline(x, y, width, color=1)`           | Horizontal line                        |
| `draw_vline(x, y, height, color=1)`          | Vertical line                          |
| `draw_rect(x, y, w, h, color=1)`             | Hollow rectangle (1-pixel outline)     |
| `draw_filled_rect(x, y, w, h, color=1)`      | Solid rectangle                        |

```python
lcd.draw_hline(0, 10, 128)               # full-width separator
lcd.draw_rect(5, 30, 50, 30)             # hollow box
lcd.draw_filled_rect(70, 30, 50, 30)     # solid box
lcd.draw_line(0, 0, 127, 127)            # diagonal
lcd.draw_pixel(64, 64)                   # center dot
lcd.show()
```

### Utility methods

#### `max_text_rows(scale=1) -> int`
Returns the number of full text rows that fit on screen at the given scale.
For a 128 px tall display: 16 at scale 1, 8 at scale 2, 5 at scale 3.

#### `max_text_cols(scale=1) -> int`
Returns the number of full character columns at the given scale.

#### `screen_size() -> tuple[int, int]`
Returns `(width, height)` in pixels.

### Inherited from `framebuf.FrameBuffer`

`SharpMemoryDisplay` is a subclass of `framebuf.FrameBuffer`, so all standard
framebuffer methods are also available (lower-level, no `auto_show` parameter):

`fill(c)`, `pixel(x, y[, c])`, `hline(x, y, w, c)`, `vline(x, y, h, c)`,
`line(x1, y1, x2, y2, c)`, `rect(x, y, w, h, c)`, `fill_rect(x, y, w, h, c)`,
`text(s, x, y[, c])`, `scroll(dx, dy)`, `blit(fbuf, x, y[, key])`.

Use the high-level `draw_*` / `print_*` methods for new code; the inherited
methods are useful for advanced cases like `blit()` and `scroll()`.

---

## class `SDCardStorage`

High-level wrapper around the standard `sdcard.py` MicroPython driver. Provides
simple file I/O, directory operations, and a context manager for automatic
mount/unmount.

### Constructor

```python
SDCardStorage(spi, cs, mount_point="/sd", lcd_cs_pin=None)
```

| Parameter     | Type        | Default | Description                                            |
| ------------- | ----------- | ------- | ------------------------------------------------------ |
| `spi`         | `SPI`       | —       | Configured `machine.SPI` instance                      |
| `cs`          | `Pin`       | —       | SD chip-select pin (output, active LOW)                |
| `mount_point` | `str`       | `"/sd"` | Filesystem mount path                                  |
| `lcd_cs_pin`  | `Pin\|None` | `None`  | Optional LCD CS pin — held LOW (idle) during SD writes |

The card is **not** mounted at construction time. Call `mount()` first.

### Mount control

#### `mount(retries=3) -> bool`
Initialize and mount the SD card. The mount sequence:

1. Forces LCD CS to idle (LOW) so the LCD ignores the bus
2. Reinitializes SPI to 400 kHz (SD spec init speed)
3. Sends 256 dummy clock pulses to flush any stuck card state
4. Calls `sdcard.SDCard()` which performs the CMD0 / CMD8 / CMD41 handshake
5. Mounts the resulting block device as a FAT filesystem

| Parameter | Type | Default | Description                                |
| --------- | ---- | ------- | ------------------------------------------ |
| `retries` | int  | `3`     | Number of mount attempts before raising    |

**Returns:** `True` on success.
**Raises:** `OSError` if all retries fail.

```python
sd.mount()
```

---

#### `unmount()`
Safely unmount the SD card. Idempotent — calling on an already-unmounted card
is a no-op.

```python
sd.unmount()
```

---

#### `is_mounted` (property)
Returns `True` if the card is currently mounted.

```python
if sd.is_mounted:
    sd.unmount()
```

### File I/O

All file operations require the card to be mounted; otherwise they raise
`RuntimeError`. Filenames may be relative to the mount point (`"data.txt"`)
or absolute (`"/sd/logs/data.txt"`).

#### `write(filename, data)`
Write `data` to `filename`, **overwriting** any existing file. Accepts `str`
(opens in `"w"` mode) or `bytes`/`bytearray` (opens in `"wb"`).

```python
sd.write("notes.txt", "Hello\n")
sd.write("blob.bin", b"\x00\x01\x02")
```

---

#### `append(filename, data)`
Append `data` to the end of `filename`, creating the file if it doesn't exist.
Accepts `str` or `bytes`.

```python
sd.append("log.txt", "Event at {}\n".format(time.ticks_ms()))
```

---

#### `read(filename, binary=False) -> str | bytes`
Read the entire contents of `filename`.

| Parameter  | Type | Default | Description                                      |
| ---------- | ---- | ------- | ------------------------------------------------ |
| `filename` | str  | —       | File name relative to mount point or absolute    |
| `binary`   | bool | `False` | If `True`, returns `bytes`; otherwise returns `str` |

```python
text = sd.read("notes.txt")
data = sd.read("blob.bin", binary=True)
```

---

#### `read_lines(filename) -> list[str]`
Read a text file and return a list of lines, stripped of trailing newlines.

```python
for line in sd.read_lines("config.txt"):
    print(line)
```

---

#### `write_lines(filename, lines, newline="\n")`
Write an iterable of strings to `filename`, one per line.

```python
sd.write_lines("settings.txt", [
    "brightness=80",
    "mode=normal",
    "rate=10",
])
```

### Filesystem operations

#### `list(path="") -> list[str]`
List the contents of a directory. An empty `path` lists the root of the card.

```python
sd.list()           # root
sd.list("logs")     # contents of /sd/logs
```

---

#### `exists(filename) -> bool`
Check whether a file or directory exists.

```python
if not sd.exists("config.txt"):
    sd.write("config.txt", "default\n")
```

---

#### `remove(filename)`
Delete a file. Raises `OSError` if the file doesn't exist.

```python
sd.remove("old_log.txt")
```

---

#### `mkdir(dirname)` / `rmdir(dirname)`
Create or remove a directory. `rmdir` requires the directory to be empty.

```python
sd.mkdir("logs")
sd.rmdir("logs")
```

---

#### `size(filename) -> int`
Return file size in bytes.

```python
print(sd.size("data.csv"), "bytes")
```

---

#### `stats() -> dict`
Return filesystem statistics:

| Key            | Type | Description                          |
| -------------- | ---- | ------------------------------------ |
| `total_bytes`  | int  | Total card capacity                  |
| `free_bytes`   | int  | Available free space                 |
| `used_bytes`   | int  | Currently used space                 |
| `block_size`   | int  | Filesystem block size in bytes       |

```python
s = sd.stats()
print("Free: {} KB".format(s["free_bytes"] // 1024))
```

### Context manager

`SDCardStorage` supports the `with` statement for automatic mount/unmount:

```python
with pp.SDCardStorage(spi, sd_cs, lcd_cs_pin=lcd_cs) as sd:
    sd.write("temp.txt", "data\n")
    print(sd.read("temp.txt"))
# unmounted automatically here, even if an exception was raised inside the block
```

---

## Bus Sharing & Arbitration

Both peripherals share **SPI0**. Only one device may be active at a time —
the LCD activates on CS HIGH, the SD card on CS LOW. To prevent contention:

- Pass `sd_cs_pin=sd_cs` when constructing the `SharpMemoryDisplay`
- Pass `lcd_cs_pin=lcd_cs` when constructing the `SDCardStorage`

With both wired, every method on either class first deselects the *other*
device before starting its transaction. You don't need to manage CS pins
manually in user code.

If you only have one device on the bus, you can omit these arguments:

```python
lcd = pp.SharpMemoryDisplay(spi, lcd_cs)            # LCD only
sd  = pp.SDCardStorage(spi, sd_cs)                  # SD only
```

---

## Error Handling

Common exceptions you may encounter:

| Exception                                 | Cause                                          | Recovery                                  |
| ----------------------------------------- | ---------------------------------------------- | ----------------------------------------- |
| `OSError("timeout waiting for v2 card")`  | Card stuck in bad state                        | Remove and reinsert the card; hard-reset Pico |
| `OSError("no SD card")`                   | No card inserted, or card not responding       | Check insertion, wiring, and power        |
| `RuntimeError("SD card is not mounted")`  | File operation called before `mount()`         | Call `sd.mount()` first                   |
| `OSError(ENOENT)`                         | File or path doesn't exist                     | Use `sd.exists()` to check first          |
| `ImportError("no module named 'sdcard'")` | `sdcard.py` missing from `/lib/`               | Copy `sdcard.py` to the Pico's `/lib/`    |

Always wrap SD operations in `try / except` and use `try / finally` to
guarantee `unmount()` runs even on error:

```python
try:
    sd.mount()
    # ... your code ...
finally:
    sd.unmount()
```

---

## Common Recipes

### Read a file from SD and display it on the LCD

```python
sd.mount()
lines = sd.read_lines("readme.txt")
lcd.clear_buffer()
for i, line in enumerate(lines[:16]):
    lcd.print_line(line[:16], row=i)
lcd.show()
sd.unmount()
```

### Append a CSV row at high speed

For continuous logging, mount **once** at startup, append throughout, and
unmount at shutdown. Each append is then ~10 ms instead of ~300 ms.

```python
sd.mount()
sd.write("run.csv", "ms,value\n")
try:
    while True:
        sd.append("run.csv", "{},{}\n".format(
            time.ticks_ms(), read_sensor()))
        time.sleep(1)
finally:
    sd.unmount()
```

### Stop a logger via switch interrupt

```python
sw = Pin(28, Pin.IN, Pin.PULL_UP)
stop = [False]
sw.irq(trigger=Pin.IRQ_FALLING, handler=lambda p: stop.__setitem__(0, True))

sd.mount()
try:
    while not stop[0]:
        sd.append("log.txt", "tick\n")
        time.sleep_ms(500)
finally:
    sw.irq(handler=None)
    sd.unmount()
```

### Inverted text (white on black)

```python
lcd.draw_filled_rect(0, 0, 128, 14, pp.BLACK)
lcd.print_at("TITLE", x=4, y=3, color=pp.WHITE)
lcd.show()
```

### Centered text

```python
text = "HELLO"
text_w = len(text) * 8       # 8 px per char at scale 1
x_center = (128 - text_w) // 2
lcd.print_at(text, x=x_center, y=60)
lcd.show()
```

### Bar chart from a list of values

```python
values = [20, 45, 30, 60, 15, 50]
lcd.clear_buffer()
for i, v in enumerate(values):
    x = 5 + i * 20
    h = int(v * 100 / 100)        # scale to 0-100 px
    lcd.draw_filled_rect(x, 120 - h, 16, h)
lcd.show()
```

---

## Version History

| Version | Notes                                                                                        |
| ------- | -------------------------------------------------------------------------------------------- |
| 3.2     | SD `mount()` reinitializes SPI to 400 kHz and adds retries; bus arbitration in both classes  |
| 3.1     | Added settle delay after LCD `show()`                                                        |
| 3.0     | Unified module: `SharpMemoryDisplay` + `SDCardStorage`                                       |
