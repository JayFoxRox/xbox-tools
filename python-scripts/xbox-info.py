#!/usr/bin/python3 -u

from xboxpy import *

import struct

def malloc(size):
  #FIXME: Use keNtAllocateVirtualMemory(&addr, 0, &size, ke.MEM_RESERVE | ke.MEM_COMMIT, ke.PAGE_READWRITE)
  #       (Where addr is a pointer to 32 bit of 0)
  return ke.MmAllocateContiguousMemory(size)

def free(ptr):
  #FIXME: Once malloc is fixed, use ke.NtFreeVirtualMemory(ptr, 0, ke.MEM_RELEASE)
  ke.MmFreeContiguousMemory(ptr)

def read_pci_config(address):
  addr = malloc(4)
  assert(address & 0x80000000)
  BusNumber = (address >> 16) & 0xFF
  SlotNumber = (address >> 11) & 0x1F
  function = (address >> 8) & 0x7
  RegisterNumber = (address >> 0) & 0xFF
  assert(RegisterNumber & 0x3 == 0)
  ke.HalReadWritePCISpace(BusNumber, SlotNumber, (function << 8) | RegisterNumber, addr, 4, ke.FALSE)
  v = struct.unpack("<I", read(addr, 4))[0]
  free(addr)
  return v


# Get MCPX information
mcpxRevision = read_pci_config(0x80000808)
mcpxRomEnable = read_pci_config(0x80000880)
mcpx_is_x2 = mcpxRomEnable & 0x1000
print("MCPX: %s, Revision 0x%02X" % ("X2" if mcpx_is_x2 else "X3",mcpxRevision & 0xFF))


# Get video encoder version and assume motherboard revision (Stolen from PBL)
#FIXME: What was this? I'd assume IO base?
verdetect = read_pci_config(0x80000810)
value = malloc(4)
if ke.HalReadSMBusValue(0x8a, 0x00, ke.FALSE, value) == 0:
  print("Video encoder: Conexant")
  if (verdetect == 0x00008001):
    print("Motherboard: v1.0")
  else:
    print("Motherboard: v1.1 or v1.2 or v1.3")
elif ke.HalReadSMBusValue(0xd4, 0x00, ke.FALSE, value) == 0:
  print("Video encoder: Focus");
  print("Motherboard: v1.4 or v1.5")
elif ke.HalReadSMBusValue(0xe0, 0x01, ke.FALSE, value) == 0:
  print("Video encoder: Xcalibur")
  print("Motherboard: v1.6")
else:
  print("Video encoder: Unknown")
  print("Motherboard: Unknown")
free(value)


# Dump SMC details
#FIXME: These calls like to return STATUS_IO_DEVICE_ERROR; why?
smc_version_addr = malloc(3 * 4)
assert(ke.HalWriteSMBusValue(0x20, 0x01, ke.FALSE, 0) == 0)
for i in range(3):
  assert(ke.HalReadSMBusValue(0x20, 0x01, ke.FALSE, smc_version_addr + i * 4) == 0)
smc_version = read(smc_version_addr, 3 * 4)[0::4]
free(smc_version_addr)
print("SMC: Version '%.3s' (%s)" % (smc_version.decode("ascii"), smc_version.hex().upper()))


