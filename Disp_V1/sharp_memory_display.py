from machine import Pin, SPI
import framebuf

class SharpMemoryDisplay(framebuf.FrameBuffer):
    def __init__(self, spi, cs, width=128, height=128):
        self.spi = spi
        self.cs = cs
        self.width = width
        self.height = height
        self.buffer = bytearray((width * height) // 8)
        # HLSB is usually better for Sharp bit-mapping
        super().__init__(self.buffer, width, height, framebuf.MONO_HLSB)
        self.vcom = 0x00

    def _reverse_bits(self, x):
        # Flips 01000000 to 00000010 (Required for DN04 addresses)
        x = ((x & 0x55) << 1) | ((x & 0xAA) >> 1)
        x = ((x & 0x33) << 2) | ((x & 0xCC) >> 2)
        x = ((x & 0x0F) << 4) | ((x & 0xF0) >> 4)
        return x

    def show(self):
        self.vcom ^= 0x40  
        self.cs.value(1)   
        
        # Command (0x80 is the bit-reversed version of 0x01)
        # DN04 prefers the Write command bit-reversed
        cmd = self._reverse_bits(0x01 | self.vcom)
        self.spi.write(bytearray([cmd]))
        
        for line in range(self.height):
            # Bit-reverse the line address so the LCD understands it
            line_addr = self._reverse_bits(line + 1)
            start = line * (self.width // 8)
            end = start + (self.width // 8)
            
            self.spi.write(bytearray([line_addr]))
            self.spi.write(self.buffer[start:end])
            self.spi.write(bytearray([0x00])) # Trailer
            
        self.spi.write(bytearray([0x00])) 
        self.cs.value(0)