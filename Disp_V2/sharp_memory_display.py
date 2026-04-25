"""
Sharp Memory LCD Driver for Raspberry Pi Pico 2W
================================================
Supports: LS013B4DN04 and compatible 128x128 Sharp Memory LCDs

Pin Assignment:
  SCLK   -> GPIO 2
  MOSI   -> GPIO 3
  LCD CS -> GPIO 5

Usage:
    from machine import Pin, SPI
    import sharp_memory_display as smd

    spi = SPI(0, baudrate=2_000_000, polarity=0, phase=0,
              sck=Pin(2), mosi=Pin(3))
    cs  = Pin(5, Pin.OUT, value=0)
    lcd = smd.SharpMemoryDisplay(spi, cs)

    lcd.clear()
    lcd.print_line("Hello World!", row=0)
    lcd.show()

Colour constants:
    smd.WHITE   # 0
    smd.BLACK   # 1
"""

from machine import Pin, SPI
import framebuf

# ── Public constants ──────────────────────────────────────────────────────────
# Use these AFTER importing the module, e.g. `smd.BLACK`.
# They are NOT referenced inside the class body because MicroPython's
# C-extension subclassing doesn't resolve class-body names the same way CPython
# does. Methods use raw ints (0/1) in their default arguments instead.
WHITE  = 0
BLACK  = 1
CHAR_W = 8   # built-in font character width  (pixels)
CHAR_H = 8   # built-in font character height (pixels)


class SharpMemoryDisplay(framebuf.FrameBuffer):
    """
    Driver for 128x128 Sharp Memory LCDs (LS013B4DN04 and compatible).
    All colour defaults are expressed as raw ints (0 = white, 1 = black)
    so the class is robust under MicroPython.
    """

    def __init__(self, spi, cs, width=128, height=128):
        """
        Args:
            spi    : configured machine.SPI instance
            cs     : chip-select Pin (OUT)
            width  : pixel width  (default 128)
            height : pixel height (default 128)
        """
        self.spi    = spi
        self.cs     = cs
        self.width  = width
        self.height = height
        self._vcom  = 0x00
        self._buf   = bytearray((width * height) // 8)
        super().__init__(self._buf, width, height, framebuf.MONO_HLSB)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rev8(self, x):
        """Reverse the bits of a byte (required by the Sharp SPI protocol)."""
        x = ((x & 0x55) << 1) | ((x & 0xAA) >> 1)
        x = ((x & 0x33) << 2) | ((x & 0xCC) >> 2)
        x = ((x & 0x0F) << 4) | ((x & 0xF0) >> 4)
        return x

    # ------------------------------------------------------------------
    # Core display API
    # ------------------------------------------------------------------

    def show(self):
        """Push the entire frame buffer to the physical display."""
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
            # Render text once into a scratch buffer, then scale-copy pixels.
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
