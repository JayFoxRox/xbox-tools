#!/usr/bin/env python3

# This prints the path of the currently running XBE, and then restarts it

from xboxpy import *

import struct


def runningXBEPath():

  # USHORT Length
  # USHORT MaximumLength
  # CONST char *Buffer
  filename = read(ke.XeImageFileName(), 8)
  filename_len, filename_maxlen, filename_str_addr = struct.unpack("<HHL", filename)

  filename_str = read(filename_str_addr, filename_len).decode('ascii')
  print(filename_str)
  
  return filename_str


def launchXBE(path):
  launch_data_page_addr_addr = ke.LaunchDataPage()
  launch_data_page_addr = read_u32(launch_data_page_addr_addr)

  # Allocate LaunchDataPage if necessary
  if launch_data_page_addr == 0x00000000:
    launch_data_page_addr = ke.MmAllocateContiguousMemory(0x1000)
    ke.MmPersistContiguousMemory(launch_data_page_addr, 0x1000, 1)
    write_u32(launch_data_page_addr_addr, launch_data_page_addr)

  #struct {
  #  uint32_t launch_data_type;
  #  uint32_t title_id;
  #  char launch_path[520];
  #  uint32_t flags;
  #  uint8_t pad[492];
  #  uint32_t launch_data[3072];
  #}* LaunchDataPage;

  xbe_path, sep, xbe_name = path.rpartition('\\')
  xbe_launch_str = xbe_path + ";" + xbe_name
  print(xbe_launch_str)

  write(launch_data_page_addr, bytes([0] * 0x1000))
  write(launch_data_page_addr + 0, struct.pack("<L", 0xFFFFFFFF))
  write(launch_data_page_addr + 4, struct.pack("<L", 0))
  write(launch_data_page_addr + 8, (xbe_launch_str + "\0").encode('ascii'))
  write(launch_data_page_addr + 528,  struct.pack("<L", 0))

  ke.HalReturnToFirmware(ke.HalQuickRebootRoutine)

# Restart the running XBE
xbe_path = runningXBEPath()
print("Currently running '%s'. Restarting..." % xbe_path)
launchXBE(xbe_path)
