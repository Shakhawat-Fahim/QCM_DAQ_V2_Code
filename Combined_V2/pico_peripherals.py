"""
================================================================================
pico_peripherals.py  —  Sharp Memory LCD + SD Card driver for Raspberry Pi Pico 2W
================================================================================

Two classes in one module:

    SharpMemoryDisplay   — 128x128 Sharp Memory LCD (LS013B4DN04 compatible)
    SDCardStorage        — FAT32 SD card read/write/list/append helpers

Both peripherals share the same SPI bus (SPI0) but have separate Chip Select
pins. The two classes cooperate on the bus: whenever one is active, the other's
CS is held inactive so only one device talks to the Pico at a time.

--------------------------------------------------------------------------------
HARDWARE PINOUT (BoosterPack / TI LCD)
--------------------------------------------------------------------------------
  SCLK    -> GPIO 2
  MOSI    -> GPIO 3
  MISO    -> GPIO 4        (required for SD card)
  LCD CS  -> GPIO 5        (active HIGH for Sharp LCD)
  SD  CS  -> GPIO 6        (active LOW for SD card)
  Power   -> 3.3V regulated

--------------------------------------------------------------------------------
DEPENDENCIES
--------------------------------------------------------------------------------
  - sdcard.py  in /lib (standard MicroPython SD driver)
  - framebuf   (built into MicroPython)

--------------------------------------------------------------------------------
QUICK START
--------------------------------------------------------------------------------
    from machine import Pin, SPI
    import pico_peripherals as pp

    # Shared SPI bus
    spi = SPI(0, baudrate=1_000_000, polarity=0, phase=0,
              sck=Pin(2), mosi=Pin(3), miso=Pin(4))

    # Chip-select pins
    lcd_cs = Pin(5, Pin.OUT, value=0)   # LCD idle = LOW
    sd_cs  = Pin(6, Pin.OUT, value=1)   # SD  idle = HIGH

    # Display usage
    lcd = pp.SharpMemoryDisplay(spi, lcd_cs, sd_cs_pin=sd_cs)
    lcd.clear()
    lcd.print_line("Hello!", row=0)
    lcd.show()

    # SD usage
    sd = pp.SDCardStorage(spi, sd_cs, lcd_cs_pin=lcd_cs)
    sd.mount()
    sd.write("test.txt", "Hello SD\n")
    print(sd.read("test.txt"))
    sd.unmount()

Colour constants (module level):
    pp.WHITE  # 0
    pp.BLACK  # 1
================================================================================
"""

from machine import Pin, SPI
import framebuf
import os
import time

# ── Version marker (prints on import to confirm correct file is loaded) ───────
__version__ = "3.1"
print("[pico_peripherals] v{} loaded".format(__version__))

# ── Public colour constants ───────────────────────────────────────────────────
WHITE  = 0
BLACK  = 1

# Built-in font character dimensions
CHAR_W = 8
CHAR_H = 8


# ==============================================================================
# SHARED-BUS HELPER
# ==============================================================================
# Both the LCD and the SD card live on SPI0. Only one device may talk at a time.
# Each class is told about the OTHER device's CS pin so it can deselect it
# before starting its own transaction.
# ==============================================================================


# ==============================================================================
#                           SHARP MEMORY DISPLAY
# ==============================================================================

class SharpMemoryDisplay(framebuf.FrameBuffer):
    """
    Driver for 128x128 Sharp Memory LCDs (LS013B4DN04 and compatible).

    All colour defaults are raw ints (0 = white, 1 = black) so the class is
    robust under MicroPython's C-extension subclassing.
    """

    def __init__(self, spi, cs, width=128, height=128, sd_cs_pin=None):
        """
        Args:
            spi        : configured machine.SPI instance
            cs         : LCD chip-select Pin (OUT) — Sharp LCD is active HIGH
            width      : pixel width  (default 128)
            height     : pixel height (default 128)
            sd_cs_pin  : optional SD card CS Pin — held HIGH (idle) during
                         LCD writes to prevent bus conflicts on a shared SPI
        """
        self.spi       = spi
        self.cs        = cs
        self.sd_cs_pin = sd_cs_pin
        self.width     = width
        self.height    = height
        self._vcom     = 0x00
        self._buf      = bytearray((width * height) // 8)
        super().__init__(self._buf, width, height, framebuf.MONO_HLSB)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rev8(self, x):
        """Reverse the bits of a byte (Sharp SPI protocol requirement)."""
        x = ((x & 0x55) << 1) | ((x & 0xAA) >> 1)
        x = ((x & 0x33) << 2) | ((x & 0xCC) >> 2)
        x = ((x & 0x0F) << 4) | ((x & 0xF0) >> 4)
        return x

    def _claim_bus(self):
        """Deselect SD card (idle HIGH) before LCD transaction."""
        if self.sd_cs_pin is not None:
            self.sd_cs_pin.value(1)

    # ------------------------------------------------------------------
    # Core display API
    # ------------------------------------------------------------------

    def show(self):
        """Push the entire frame buffer to the physical display."""
        self._claim_bus()
        self._vcom ^= 0x40
        self.cs.value(1)

        cmd = self._rev8(0x01 | self._vcom)
        self.spi.write(bytearray([cmd]))

        for line in range(self.height):
            addr  = self._rev8(line + 1)
            start = line * (self.width // 8)
            end   = start + (self.width // 8)
            self.spi.write(bytearray([addr]))
            self.spi.write(self._buf[start:end])
            self.spi.write(bytearray([0x00]))   # line trailer

        self.spi.write(bytearray([0x00]))        # frame trailer
        self.cs.value(0)
        # Small settle time so the bus is clean before any other device uses it
        time.sleep_us(50)

    def clear(self, color=0):
        """Fill the entire display with one color and push to screen.
           color: 0 = WHITE (default), 1 = BLACK"""
        self.fill(color)
        self.show()

    def clear_buffer(self, color=0):
        """Fill the frame buffer without pushing to screen.
           color: 0 = WHITE (default), 1 = BLACK"""
        self.fill(color)

    # ------------------------------------------------------------------
    # Text API
    # ------------------------------------------------------------------

    def print_line(self, text, row, col=0, color=1, bg=0,
                   scale=1, auto_show=False):
        """
        Print a string at a logical text row/column position.

        Args:
            text      : string to display
            row       : text row (0-based; each row = 8*scale px)
            col       : text column (0-based; each col = 8*scale px)
            color     : 1 = BLACK (default), 0 = WHITE
            bg        : background color (only used when scale > 1)
            scale     : integer scale factor (1 = normal, 2 = double, ...)
            auto_show : if True, push to screen after drawing
        """
        x = col * 8 * scale
        y = row * 8 * scale
        self.print_at(text, x, y, color=color, bg=bg, scale=scale,
                      auto_show=auto_show)

    def print_at(self, text, x, y, color=1, bg=0,
                 scale=1, auto_show=False):
        """
        Print a string at exact pixel coordinates.

        Args:
            text      : string to display
            x, y      : top-left pixel position
            color     : 1 = BLACK (default), 0 = WHITE
            bg        : background color (only used when scale > 1)
            scale     : integer scale factor
            auto_show : if True, push to screen after drawing
        """
        if scale == 1:
            self.text(text, x, y, color)
        else:
            # Render text into a scratch buffer, then scale-copy pixels.
            w_tmp = len(text) * 8
            tmp_buf = bytearray(((w_tmp * 8) // 8) + 1)
            tmp = framebuf.FrameBuffer(tmp_buf, w_tmp, 8, framebuf.MONO_HLSB)
            tmp.fill(bg)
            tmp.text(text, 0, 0, color)
            for ty in range(8):
                for tx in range(w_tmp):
                    px = tmp.pixel(tx, ty)
                    for sy in range(scale):
                        for sx in range(scale):
                            self.pixel(x + tx * scale + sx,
                                       y + ty * scale + sy,
                                       px)
        if auto_show:
            self.show()

    def print_multiline(self, lines, start_row=0, col=0,
                        color=1, scale=1, auto_show=False):
        """
        Print a list of strings on consecutive rows.
        color: 1 = BLACK (default), 0 = WHITE
        """
        for i, line in enumerate(lines):
            self.print_line(line, row=start_row + i, col=col,
                            color=color, scale=scale)
        if auto_show:
            self.show()

    # ------------------------------------------------------------------
    # Drawing API
    # ------------------------------------------------------------------

    def draw_pixel(self, x, y, color=1, auto_show=False):
        """Set a single pixel.  color: 1 = BLACK, 0 = WHITE"""
        self.pixel(x, y, color)
        if auto_show:
            self.show()

    def draw_line(self, x1, y1, x2, y2, color=1, auto_show=False):
        """Draw a line between two points."""
        self.line(x1, y1, x2, y2, color)
        if auto_show:
            self.show()

    def draw_hline(self, x, y, width, color=1, auto_show=False):
        """Draw a horizontal line."""
        self.hline(x, y, width, color)
        if auto_show:
            self.show()

    def draw_vline(self, x, y, height, color=1, auto_show=False):
        """Draw a vertical line."""
        self.vline(x, y, height, color)
        if auto_show:
            self.show()

    def draw_rect(self, x, y, w, h, color=1, auto_show=False):
        """Draw a hollow rectangle."""
        self.rect(x, y, w, h, color)
        if auto_show:
            self.show()

    def draw_filled_rect(self, x, y, w, h, color=1, auto_show=False):
        """Draw a filled rectangle."""
        self.fill_rect(x, y, w, h, color)
        if auto_show:
            self.show()

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def max_text_rows(self, scale=1):
        """Return the number of full text rows that fit on screen."""
        return self.height // (8 * scale)

    def max_text_cols(self, scale=1):
        """Return the number of full character columns that fit on screen."""
        return self.width // (8 * scale)

    def screen_size(self):
        """Return (width, height) in pixels."""
        return (self.width, self.height)


# ==============================================================================
#                               SD CARD STORAGE
# ==============================================================================

class SDCardStorage:
    """
    High-level SD card wrapper around the standard `sdcard` MicroPython driver.
    Provides simple read / write / append / list / exists / remove helpers,
    plus a context-manager interface for automatic mount/unmount.

    Usage:
        sd = SDCardStorage(spi, sd_cs, lcd_cs_pin=lcd_cs)
        sd.mount()
        sd.write("log.txt", "line 1\\n")
        sd.append("log.txt", "line 2\\n")
        print(sd.read("log.txt"))
        print(sd.list())
        sd.unmount()

        # Or as context manager — auto mount/unmount:
        with SDCardStorage(spi, sd_cs, lcd_cs_pin=lcd_cs) as sd:
            sd.write("data.csv", "1,2,3\\n")
    """

    def __init__(self, spi, cs, mount_point="/sd", lcd_cs_pin=None):
        """
        Args:
            spi         : configured machine.SPI instance (shared with LCD)
            cs          : SD card chip-select Pin (OUT) — active LOW
            mount_point : filesystem mount path (default "/sd")
            lcd_cs_pin  : optional LCD CS Pin — held LOW (idle) during SD
                          transactions to prevent bus conflicts
        """
        self.spi         = spi
        self.cs          = cs
        self.mount_point = mount_point
        self.lcd_cs_pin  = lcd_cs_pin
        self._sd         = None
        self._vfs        = None
        self._mounted    = False

        # Leave SD in idle state (CS high)
        self.cs.value(1)

    # ------------------------------------------------------------------
    # Bus arbitration
    # ------------------------------------------------------------------

    def _claim_bus(self):
        """Deselect LCD (idle LOW) before SD transaction."""
        if self.lcd_cs_pin is not None:
            self.lcd_cs_pin.value(0)

    # ------------------------------------------------------------------
    # Mount / unmount
    # ------------------------------------------------------------------

    def mount(self):
        """
        Initialize the SD card and mount it as a FAT filesystem.
        Requires sdcard.py driver in /lib.

        Bus-preparation sequence (important when sharing SPI with the LCD):
          1. Force LCD CS to idle LOW so the LCD ignores the bus
          2. Hold SD CS HIGH (idle) and toggle clock for >74 cycles so the
             card can leave whatever state it was in and enter SPI mode
          3. Pause briefly to let the card settle
          4. Call sdcard.SDCard() — this performs CMD0/CMD8/etc. handshake
        """
        if self._mounted:
            return True

        import sdcard

        # Step 1 — LCD out of the way
        if self.lcd_cs_pin is not None:
            self.lcd_cs_pin.value(0)

        # Step 2 — give the SD card time to wake up, then clock it into a
        # known state. Sending 10 bytes of 0xFF with CS HIGH generates
        # 80 clock pulses, which the SD spec requires before CMD0.
        self.cs.value(1)
        time.sleep_ms(10)
        self.spi.write(b"\xff" * 10)
        time.sleep_ms(10)

        # Step 3 — hand off to the low-level driver
        self._sd  = sdcard.SDCard(self.spi, self.cs)
        self._vfs = os.VfsFat(self._sd)
        os.mount(self._vfs, self.mount_point)
        self._mounted = True
        return True

    def unmount(self):
        """Safely unmount the SD card."""
        if not self._mounted:
            return
        try:
            os.umount(self.mount_point)
        finally:
            self._mounted = False
            self._sd  = None
            self._vfs = None

    @property
    def is_mounted(self):
        """True if the card is currently mounted."""
        return self._mounted

    # Context-manager support: `with SDCardStorage(...) as sd:`
    def __enter__(self):
        self.mount()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unmount()
        return False

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _path(self, name):
        """Prepend the mount point to `name` if it isn't already absolute."""
        if name.startswith("/"):
            return name
        return "{}/{}".format(self.mount_point, name)

    def _require_mounted(self):
        if not self._mounted:
            raise RuntimeError("SD card is not mounted. Call mount() first.")

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def write(self, filename, data):
        """
        Write `data` (str or bytes) to `filename`, overwriting any existing file.

        Args:
            filename : file name relative to mount point (e.g. "log.txt")
                       or an absolute path starting with "/"
            data     : str or bytes to write
        """
        self._require_mounted()
        self._claim_bus()
        mode = "wb" if isinstance(data, (bytes, bytearray)) else "w"
        with open(self._path(filename), mode) as f:
            f.write(data)

    def append(self, filename, data):
        """Append `data` (str or bytes) to `filename`, creating it if needed."""
        self._require_mounted()
        self._claim_bus()
        mode = "ab" if isinstance(data, (bytes, bytearray)) else "a"
        with open(self._path(filename), mode) as f:
            f.write(data)

    def read(self, filename, binary=False):
        """
        Read the entire contents of `filename`.

        Args:
            filename : file name relative to mount point or absolute path
            binary   : if True, return bytes; otherwise return str
        Returns:
            str or bytes
        """
        self._require_mounted()
        self._claim_bus()
        mode = "rb" if binary else "r"
        with open(self._path(filename), mode) as f:
            return f.read()

    def read_lines(self, filename):
        """Read a text file and return a list of lines (no trailing newlines)."""
        self._require_mounted()
        self._claim_bus()
        with open(self._path(filename), "r") as f:
            return [line.rstrip("\n") for line in f]

    def write_lines(self, filename, lines, newline="\n"):
        """Write an iterable of strings to `filename`, one per line."""
        self._require_mounted()
        self._claim_bus()
        with open(self._path(filename), "w") as f:
            for line in lines:
                f.write(line)
                f.write(newline)

    # ------------------------------------------------------------------
    # Filesystem helpers
    # ------------------------------------------------------------------

    def list(self, path=""):
        """List contents of a directory on the SD card.
           Empty string = root of the card."""
        self._require_mounted()
        self._claim_bus()
        target = self.mount_point if path == "" else self._path(path)
        return os.listdir(target)

    def exists(self, filename):
        """Return True if `filename` exists on the SD card."""
        self._require_mounted()
        self._claim_bus()
        try:
            os.stat(self._path(filename))
            return True
        except OSError:
            return False

    def remove(self, filename):
        """Delete `filename` from the SD card."""
        self._require_mounted()
        self._claim_bus()
        os.remove(self._path(filename))

    def mkdir(self, dirname):
        """Create a directory on the SD card."""
        self._require_mounted()
        self._claim_bus()
        os.mkdir(self._path(dirname))

    def rmdir(self, dirname):
        """Remove an empty directory from the SD card."""
        self._require_mounted()
        self._claim_bus()
        os.rmdir(self._path(dirname))

    def size(self, filename):
        """Return the size of `filename` in bytes."""
        self._require_mounted()
        self._claim_bus()
        return os.stat(self._path(filename))[6]

    def stats(self):
        """
        Return filesystem statistics as a dict:
            total_bytes, free_bytes, used_bytes, block_size
        """
        self._require_mounted()
        self._claim_bus()
        s = os.statvfs(self.mount_point)
        block_size  = s[0]
        total_blocks = s[2]
        free_blocks  = s[3]
        total_bytes = block_size * total_blocks
        free_bytes  = block_size * free_blocks
        return {
            "total_bytes": total_bytes,
            "free_bytes":  free_bytes,
            "used_bytes":  total_bytes - free_bytes,
            "block_size":  block_size,
        }
