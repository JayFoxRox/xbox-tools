#!/bin/env python3

import sys
import math
import usb1
import struct

BUFFER_SIZE = 200

with usb1.USBContext() as context:

  vid = 0x045e
  pid = 0x0284
  INTERFACE = 1

  handle = context.openByVendorIDAndProductID(vid, pid, skip_on_error=True)
  if handle is None:
      # Device not present, or user is not allowed to access device.
    print("oops?!")

  rom_info = 1
  info = handle.controlRead(usb1.REQUEST_TYPE_VENDOR | usb1.RECIPIENT_INTERFACE, rom_info, 0, INTERFACE, 6)

  (version, code_length) = struct.unpack("<HI", info)
  print("version %X.%X" % (version >> 8, version & 0xFF))
  print(str(code_length - 6) + " bytes")

  with open('default.xbe', 'wb') as f:

    rom_download = 2
    remaining = code_length
    cursor = 0
    while(remaining > 0):
      chunkSize = min(remaining, 1024)
      data = handle.controlRead(usb1.REQUEST_TYPE_VENDOR | usb1.RECIPIENT_INTERFACE, rom_download, cursor >> 10, INTERFACE, chunkSize)
      assert(chunkSize == len(data))
      # The first block contains a copy of the (version, code_length)
      if cursor == 0:
        assert(data[0:6] == info)
        data = data[6:]
      f.write(data)
      remaining -= chunkSize
      cursor += chunkSize



