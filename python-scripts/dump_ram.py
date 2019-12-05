#!/usr/bin/env python3

# Read all physical memory

from xboxpy import *

ram_size = 64 * 1024 * 1024

f = open('ram.bin', 'wb')

offset = 0
chunk_size = 0x1000
assert(ram_size % chunk_size == 0)
while offset < ram_size:
  mapped = ke.MmMapIoSpace(offset, chunk_size, ke.PAGE_READWRITE)
  data = memory.read(mapped, chunk_size)
  f.write(data)
  ke.MmUnmapIoSpace(mapped, chunk_size)
  offset += chunk_size

f.close()
