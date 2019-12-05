#!/usr/bin/env python3

# Search empty memory regions and fill them with a pattern

from xboxpy import *

pattern = b'JayFoxRox'
page_contents = (pattern * ((0x1000 // len(pattern) + 1)))[0:0x1000]
print(len(page_contents))
assert(len(page_contents) == 0x1000)

ram_size = 64 * 1024 * 1024

page_count = 0

#FIXME: Walk the pagetable instead and map memory using MmMapIoSpace!
offset = 0
while offset < ram_size:
  allocated = ke.MmAllocateContiguousMemoryEx(0x1000, offset, offset + 0x1000, 0x1000, ke.PAGE_READWRITE)
  if allocated != 0:
    memory.write(allocated, page_contents[0:len(pattern)])
    print("Filling 0x%08X" % ke.MmGetPhysicalAddress(allocated))
    ke.MmFreeContiguousMemory(allocated)
    page_count += 1
  offset += 0x1000

print("Filled %d pages" % page_count)
