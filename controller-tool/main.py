#!/bin/env python3

import sys
import math
import usb1
import json

BUFFER_SIZE = 200

json_data=open(sys.argv[1]).read()

structure = json.loads(json_data)
#print(structure)

with usb1.USBContext() as context:

    for product in structure['products']:
      vid = int(product['vid'], 16)
      pid = int(product['pid'], 16)
      INTERFACE = 0
      ENDPOINT = product['in-endpoint']

      handle = context.openByVendorIDAndProductID(vid, pid, skip_on_error=True)
      if handle is None:
          # Device not present, or user is not allowed to access device.
        print("oops?!")
        continue

      print("Found '" + product['name'] + "'")

      break

    with handle.claimInterface(INTERFACE):
        # Do stuff with endpoints on claimed interface.
      print("claimed!");

      def MaskLength(mask):
        if (mask == 0):
          return 0
        return int(math.log(mask, 2)) + 1
      def ffs(x):
        return MaskLength((x ^ (x - 1)) >> 1)
      def setU(data, offset, mask, value):
        #FIXME: Make this work on bits and not bytes
        mask_length = (MaskLength(mask) + 7) // 8
        for i in range(0, mask_length):
          data[offset + i] = (value >> (i * 8)) & 0xFF
        return
      def getU(data, offset, mask):
        mask_length = (MaskLength(mask) + 7) // 8
        value = 0
        for i in range(0, mask_length):
          value |= data[offset + i] << (i * 8)
        return (value & mask) >> ffs(mask)
      def getS(data, offset, mask):
        value = getU(data, offset, mask)
        mask_length = (MaskLength(mask) - ffs(mask))
        sign = -(value & (1 << (mask_length - 1)))
        value = sign + (value & ~(1 << (mask_length - 1)))
        return value

      while True:
          try:
            in_data = handle.interruptRead(ENDPOINT, BUFFER_SIZE, timeout=100)
          except usb1.USBErrorTimeout:
            continue

          for k, e in structure['in'].items():
            offset = e['offset']
            mask = int(e['mask'], 16)
            try:
              signed = e['signed']
            except:
              signed = False

            if signed:
              value = getS(in_data, offset, mask)
            else:
              value = getU(in_data, offset, mask)
            print(k + " offset: " + str(offset) + "; value: " + str(value))
            


          # Process data...
          print(in_data)
          #out_data = bytearray([0,14,0x00,0x00,0x00,0x00, 0x00,0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
          out_data = bytearray([0,6,0x00,0x00,0x00,0x00])
          setU(out_data, 2, 0xFFFF, getU(in_data, 10, 0xFF) * 0x101)
          setU(out_data, 4, 0xFFFF, getU(in_data, 11, 0xFF) * 0x101)
          data = handle.interruptWrite(0x02, out_data)
