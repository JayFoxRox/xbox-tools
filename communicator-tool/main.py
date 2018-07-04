#!/bin/env python3

import sys
import math
import usb1
import struct
import pyaudio

sample_rate = 0

sample_rates = [
  # Sample rate in kHz, usb frame size, timing data?
  [ 8000, 16,  0], # 0
  [11025, 22, 40], # 1
  [16000, 32,  0], # 2
  [22050, 44, 20], # 3
  [24000, 48,  0]  # 4
]

pya = pyaudio.PyAudio()
stream = pya.open(format=pya.get_format_from_width(width=2), channels=1, rate=sample_rates[sample_rate][0], output=True)

with usb1.USBContext() as context:

  vid = 0x045e
  pid = 0x0283
  interface = 1

  handle = context.openByVendorIDAndProductID(vid, pid, skip_on_error=True)
  if handle is None:
      # Device not present, or user is not allowed to access device.
    print("oops?!")

  set_sample_rate = 0

  handle.controlWrite(usb1.REQUEST_TYPE_VENDOR | usb1.RECIPIENT_INTERFACE, usb1.REQUEST_SET_FEATURE, 0x0100 | sample_rate, set_sample_rate, bytes([]))

  with handle.claimInterface(interface):

    def in_callback(transfer):
      if transfer.getStatus() != usb1.TRANSFER_COMPLETED:
          return
      #data = transfer.getBuffer()[:transfer.getActualLength()]

      for data in transfer.iterISO():
        #print(data[0])
        print(data[1])
        

        # Process data...
        stream.write(bytes(data[1]))

      # Resubmit transfer once data is processed.
      transfer.submit()

    def out_callback(transfer):
      if transfer.getStatus() != usb1.TRANSFER_COMPLETED:
          return
      print("out")
      transfer.submit()

    BUFFER_SIZE = 0x30 #FIXME

    # Build a list of transfer objects and submit them to prime the pump.
    transfer_list = []
    for _ in range(1):
      transfer = handle.getTransfer(1)
      transfer.setIsochronous(usb1.ENDPOINT_IN | 5, BUFFER_SIZE, callback=in_callback)
      transfer.submit()
      transfer_list.append(transfer)

      # Prepare output data
      data = bytes([])
      for i in range(BUFFER_SIZE // 2):
        data += bytes([i, i])

      transfer = handle.getTransfer(1)
      transfer.setIsochronous(usb1.ENDPOINT_OUT | 4, data, callback=out_callback)
      transfer.submit()
      transfer_list.append(transfer)

    # Loop as long as there is at least one submitted transfer.
    while any(x.isSubmitted() for x in transfer_list):
        try:
            context.handleEvents()
        except usb1.USBErrorInterrupted:
            pass
