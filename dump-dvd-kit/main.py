#!/bin/env python3

import sys
import math
import usb1
import struct

with usb1.USBContext() as context:

  vid = 0x045e
  pid = 0x0284
  interface = 1

  handle = context.openByVendorIDAndProductID(vid, pid, skip_on_error=True)
  if handle is None:
      # Device not present, or user is not allowed to access device.
    print("oops?!")

  rom_info = 1
  info = handle.controlRead(usb1.REQUEST_TYPE_VENDOR | usb1.RECIPIENT_INTERFACE, rom_info, 0, interface, 6)

  (version, code_length) = struct.unpack("<HI", info)
  print("Version: %X.%X" % (version >> 8, version & 0xFF))
  print("Size: " + str(code_length) + " bytes")

  with open("dvd-dongle-rom.bin", 'wb') as f:

    rom_download = 2
    remaining = code_length
    cursor = 0

    xbe = bytes([])

    while(remaining > 0):
      chunkSize = min(remaining, 1024)
      data = handle.controlRead(usb1.REQUEST_TYPE_VENDOR | usb1.RECIPIENT_INTERFACE, rom_download, cursor >> 10, interface, chunkSize)
      assert(chunkSize == len(data))
      # The first block contains a copy of the (version, code_length)
      if cursor == 0:
        assert(data[0:6] == info)
        xbe += data[6:]
      else:
        xbe += data
      f.write(data)
      remaining -= chunkSize
      cursor += chunkSize

  # Do some sanity checks and print out DVD region

  BaseAddress = struct.unpack('I', xbe[260:264])[0]
  Certificate = struct.unpack('I', xbe[280:284])[0] - BaseAddress
  SectionHeaders = struct.unpack('I', xbe[288:292])[0] - BaseAddress
  SizeOfImage = struct.unpack('I', xbe[268:272])[0]
  assert((6 + SizeOfImage) == code_length) # SizeOfImage
  assert(struct.unpack('I', xbe[Certificate+156:Certificate+160])[0] == 0x00000100) # AllowedMediaTypes == DONGLE
  assert(struct.unpack('I', xbe[Certificate+172:Certificate+176])[0] == version) # Version
  RawData = struct.unpack('I', xbe[SectionHeaders+12:SectionHeaders+16])[0]
  SizeOfRawData = struct.unpack('I', xbe[SectionHeaders+16:SectionHeaders+20])[0]
  assert(RawData + SizeOfRawData == SizeOfImage)
  GameRegion = struct.unpack('I', xbe[Certificate+160:Certificate+164])[0]
  print("Region: " + str(GameRegion))
