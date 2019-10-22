#!/usr/bin/env python3

# Dumps EEPROM image to eeprom.bin

from xboxpy import *


# Allocate a temporary ULONG
tmp_ptr = ke.MmAllocateContiguousMemory(4)

# Read EEPROM
eeprom = bytes([])
for i in range(0, 256, 2):

  # Read 16-bit from EEPROM into a ULONG
  ret = ke.HalReadSMBusValue(0xA9, i, ke.TRUE, tmp_ptr) # 0xA9 = EEPROM Read
  assert(ret == 0)
  tmp = memory.read_u32(tmp_ptr)

  # Split the 16-bit word into 2 bytes
  assert(tmp & ~0xFFFF == 0)
  eeprom += bytes([tmp & 0xFF, (tmp >> 8) & 0xFF])

# Free our temporary buffer
ke.MmFreeContiguousMemory(tmp_ptr)

# Output EEPROM image to file
with open("eeprom.bin", "wb") as f:
  f.write(eeprom)

  print("Wrote EEPROM to eeprom.bin")
