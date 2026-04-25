"""
sd_speed_benchmark.py — Measure SD write throughput at different SPI speeds

Writes a 100 KB file at various baud rates and reports MB/s.
This tells you how fast your SD card logger CAN go.

Note: actual logger performance depends on:
  - Size of each write (small appends are dominated by overhead)
  - Whether you mount/unmount per write (slow) or stay mounted (fast)
  - The card itself (cheap cards slow down on sustained writes)
"""

from machine import Pin, SPI
import pico_peripherals as pp
import time

print("Driver version:", getattr(pp, "__version__", "UNKNOWN"))
print()

# Fixed SPI setup — we change the SD's baudrate attribute between trials
spi = SPI(0, baudrate=1_000_000, polarity=0, phase=0,
          sck=Pin(2), mosi=Pin(3), miso=Pin(4))
lcd_cs = Pin(5, Pin.OUT, value=0)
sd_cs  = Pin(6, Pin.OUT, value=1)

# 100 KB payload
CHUNK     = b"A" * 1024   # 1 KB buffer reused
TOTAL_KB  = 100

def benchmark(speed):
    """Write TOTAL_KB kilobytes at the given SPI speed, measure throughput."""
    sd = pp.SDCardStorage(spi, sd_cs, lcd_cs_pin=lcd_cs, baudrate=speed)
    try:
        sd.mount()

        # Ensure the file doesn't exist so first-write cost isn't a factor
        if sd.exists("bench.bin"):
            sd.remove("bench.bin")

        start = time.ticks_ms()
        with open("/sd/bench.bin", "wb") as f:
            for _ in range(TOTAL_KB):
                f.write(CHUNK)
        elapsed_ms = time.ticks_diff(time.ticks_ms(), start)

        kb_per_s = (TOTAL_KB * 1000) / elapsed_ms
        print("  {:>9} Hz  -> {:5} ms  ->  {:6.1f} KB/s".format(
              speed, elapsed_ms, kb_per_s))

        sd.remove("bench.bin")
        sd.unmount()
    except Exception as e:
        print("  {:>9} Hz  -> FAILED: {}".format(speed, e))
        try:
            sd.unmount()
        except:
            pass


print("Writing {} KB at different SPI speeds:".format(TOTAL_KB))
print("-" * 50)

for speed in (1_000_000, 4_000_000, 8_000_000, 12_000_000, 20_000_000):
    benchmark(speed)
    time.sleep(0.5)   # let the card settle between runs

print("-" * 50)
print("If a speed FAILS, your card or wiring can't handle it.")
print("Pick the fastest one that succeeds for your logger.")
