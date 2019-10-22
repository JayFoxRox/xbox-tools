#!/usr/bin/env python3

# Dumps flash image to flash.bin

from xboxpy import *


# Assume that the flash is the maximum size (16 MiB)
max_flash_size = 16*1024*1024

# The last 512 byte of flash overlap the MCPX ROM.
# However, if MCPX ROM is hidden, Xbox 1.1 and newer will crash on access.
# So we only ever dump 8 MiB (16 MiB is unlikely anyway)
max_flash_dump_size = max_flash_size // 2

# Map flash into memory
flash_ptr = ke.MmMapIoSpace(0xFF000000, max_flash_dump_size, ke.PAGE_READONLY | ke.PAGE_NOCACHE)

flash = memory.read(flash_ptr, max_flash_dump_size)

# Unmap flash
ke.MmUnmapIoSpace(flash_ptr, max_flash_dump_size)

# Try to find out the actual flash size
while len(flash) > 1:

  # Split the flash so the highest address bit is ignored
  assert(len(flash) % 2 == 0)
  first_half = flash[0:len(flash)//2]
  second_half = flash[len(flash)//2:]

  # If the parts are different, then we must keep both
  if first_half != second_half:
    break

  # Only keep the first half
  flash = first_half

# Report flash trimming
print("Assuming flash size of %u bytes (or duplicated contents)" % len(flash))

# Warn about our limitations
if len(flash) == max_flash_dump_size:
  print()
  print("The flash might be larger, this tool dumps at most %u bytes" % max_flash_dump_size)
  print()

# Output flash image to file
with open("flash.bin", "wb") as f:
  f.write(flash)

  print("Wrote flash to flash.bin")
