#!/bin/env python3

import sys
import math
import usb1
import json
import time
import struct
from collections import OrderedDict

BUFFER_SIZE = 200

json_data=open(sys.argv[1]).read()

structure = json.loads(json_data)
#print(structure)

def parse_fields(fields, data):
  values = OrderedDict()
  offset = 0
  for f in fields:
    value = struct.unpack_from('<' + f[1], data, offset)
    if len(value) == 1: value = value[0]
    values[f[0]] = value
    offset += struct.calcsize(f[1])
  if offset != len(data):
    print("Unparsed: %s" % data[offset:])
    #assert(False)
  return values

def usb_get_device_descriptor(handle):
  
  # Get device descriptor, the raw way
  data = usb_control(handle, usb1.ENDPOINT_IN, 6, 0x0100, 0x0000, 64)
  print(data)

  # Get configuration descriptor
  fields = []
  fields += [('bLength', 'B')]
  fields += [('bDescriptorType', 'B')]
  fields += [('bcdUSB', 'H')]
  fields += [('bDeviceClass', 'B')]
  fields += [('bDeviceSubClass', 'B')]
  fields += [('bDeviceProtocol', 'B')]
  fields += [('bMaxPacketSize0', 'B')]
  fields += [('idVendor', 'H')]
  fields += [('idProduct', 'H')]
  fields += [('bcdDevice', 'H')]
  fields += [('iManufacturer', 'B')]
  fields += [('iProduct', 'B')]
  fields += [('iSerialNumber', 'B')]
  fields += [('bNumConfigurations', 'B')]
  print(json.dumps(parse_fields(fields, data[1]),indent=2))



def usb_get_configuration_descriptor(handle, configuration):
  #FIXME: For each configuration

  # Get Configuration Descriptor, the raw way
  data = usb_control(handle, usb1.ENDPOINT_IN, 6, 0x0200 | configuration, 0x0000, 80)
  print(data)

  offset = 0

  fields = []
  fields += [('bLength', 'B')]
  fields += [('bDescriptorType', 'B')]
  fields += [('wTotalLength', 'H')]
  fields += [('bNumInterfaces', 'B')]
  fields += [('bConfigurationValue', 'B')]
  fields += [('iConfiguration', 'B')]
  fields += [('bmAttributes', 'B')]
  fields += [('bMaxPower', 'B')]
  configuration_values = parse_fields(fields, data[1][offset:])
  print(json.dumps(configuration_values, indent=2))

  offset += configuration_values['bLength']

  # Get interface descriptor
  for i in range(configuration_values['bNumInterfaces']):
    fields = []
    fields += [('bLength', 'B')]
    fields += [('bDescriptorType', 'B')]
    fields += [('bInterfaceNumber', 'B')]
    fields += [('bAlternateSetting', 'B')]
    fields += [('bNumEndpoints', 'B')]
    fields += [('bInterfaceClass', 'B')]
    fields += [('bInterfaceSubClass', 'B')]
    fields += [('bInterfaceProtocol', 'B')]
    fields += [('iInterface', 'B')]
    interface_values = parse_fields(fields, data[1][offset:])
    print(json.dumps(interface_values, indent=2))

    offset += interface_values['bLength']

    # Get endpoint descriptors
    for j in range(interface_values['bNumEndpoints']):
      fields = []
      fields += [('bLength', 'B')]
      fields += [('bDescriptorType', 'B')]
      fields += [('bEndpointAddress', 'B')]
      fields += [('bmAttributes', 'B')]
      fields += [('wMaxPacketSize', 'H')]
      fields += [('bInterval', 'B')]
      endpoint_values = parse_fields(fields, data[1][offset:])
      print(json.dumps(endpoint_values, indent=2))

      offset += endpoint_values['bLength']

  assert(offset == len(data[1]))

#FIXME: Get string descriptors

def usb_set_configuration(handle, configuration):

  # libusb_set_configuration docs:
  #   You should always use this function rather than formulating your own
  #   SET_CONFIGURATION control request. This is because the underlying
  #   operating system needs to know when such changes happen.
  handle.setConfiguration(configuration)


def usb_control(handle, request_type, request, value, index, buffer_or_len, timeout=0):
  transfer = handle.getTransfer()
  transfer.setControl(request_type, request, value, index, buffer_or_len, timeout=timeout)
  return _do_usb_transfer(transfer, request_type & usb1.ENDPOINT_DIR_MASK)

def usb_interrupt(handle, endpoint, buffer_or_len, timeout=0):
  transfer = handle.getTransfer()
  transfer.setInterrupt(endpoint, buffer_or_len, timeout=timeout)
  return _do_usb_transfer(transfer, endpoint & usb1.ENDPOINT_DIR_MASK)

def _do_usb_transfer(transfer, direction):

  # Submit the transfer
  transfer.submit()

  # Wait until it has finished
  while transfer.isSubmitted():
    context.handleEvents()

  # Return transfer status and data
  status = transfer.getStatus()

  # Probably NAK or STALL
  if status != usb1.TRANSFER_COMPLETED:
    return (status, None)

  # Don't return the data for outputs
  if direction == usb1.ENDPOINT_OUT:
    return (status, transfer.getActualLength())
  else:
    data = bytes(transfer.getBuffer())
    return (status, data[0:transfer.getActualLength()])

def xid_get_descriptor_data(handle, interface_number, size):
  data = usb_control(handle, (0xC1 & ~usb1.ENDPOINT_DIR_MASK) | usb1.ENDPOINT_IN, 6, 0x4200, interface_number, size, timeout=100)
  # ?
  return data

def xid_get_descriptor(handle, interface_number, size):
  data = xid_get_descriptor_data(handle, interface_number, size)

  # Only handle ACK replies
  if data[0] != 0:
    return data

  fields = []
  fields += [('bLength', 'B')]
  fields += [('bDescriptorType', 'B')]
  fields += [('bcdXid', 'H')]
  fields += [('bType', 'B')]
  fields += [('bSubType', 'B')]
  fields += [('bMaxInputReportSize', 'B')]
  fields += [('bMaxOutputReportSize', 'B')]
  fields += [('wAlternateProductIds', 'H' * 4)]
  print(json.dumps(parse_fields(fields, data[1]),indent=2))

  return data

def xid_get_capabilities(handle, report_type, interface_number, size):
  data = usb_control(handle, (0xC1 & ~usb1.ENDPOINT_DIR_MASK) | usb1.ENDPOINT_IN, 1, report_type, interface_number, size, timeout=100)
  # stall
  return data

def xid_set_report(handle, report_type, interface_number, data):
  data = usb_control(handle, (0xA1 & ~usb1.ENDPOINT_DIR_MASK) | usb1.ENDPOINT_OUT, 9, report_type, interface_number, data, timeout=100)
  # stall
  return data

def xid_get_report(handle, report_type, interface_number, size):
  data = usb_control(handle, (0xA1 & ~usb1.ENDPOINT_DIR_MASK) | usb1.ENDPOINT_IN, 1, report_type, interface_number, size, timeout=100)
  # stall
  # ack
  # nak
  return data


with usb1.USBContext() as context:

    for product in structure['products']:
      vid = int(product['vid'], 16)
      pid = int(product['pid'], 16)
      ENDPOINT = product['in-endpoint']

      handle = context.openByVendorIDAndProductID(vid, pid, skip_on_error=True)
      if handle is None:
        # Device not present, or user is not allowed to access device.
        print("Unable to open device %04X:%04X" % (vid, pid))
        continue

      print("Found '" + product['name'] + "'")

      break

    if handle is None:
      print("Unable to open any suitable device")
      sys.exit(1)

    # Unset the current configuration.
    # -1 is libusb specific to workaround bugs in devices. So this is the
    # cleanest way to do this probably.
    handle.setConfiguration(-1)


    interface_number = 0

    #with handle.claimInterface(interface_number):
    if True:

      USB_STATUS = {
        usb1.TRANSFER_COMPLETED: 'ACK',
        usb1.TRANSFER_TIMED_OUT: 'NAK',
        usb1.TRANSFER_STALL: 'STALL'
      }

      print("usb_get_device_descriptor:")
      usb_get_device_descriptor(handle)

      print("usb_get_configuration_descriptor:")
      usb_get_configuration_descriptor(handle, 0)

      print("usb_set_configuration:")
      usb_set_configuration(handle, 1)

      print("xid_get_descriptor:")
      xid_descriptor = xid_get_descriptor(handle, interface_number, 50)
      print(xid_descriptor)

      print("xid_get_capabilities for 0x0100:")
      xid_capabilities_0x0100 = xid_get_capabilities(handle, 0x0100, interface_number, 50)
      print(xid_capabilities_0x0100)

      print("xid_get_capabilities for 0x0200:")
      xid_capabilities_0x0200 = xid_get_capabilities(handle, 0x0200, interface_number, 50)
      print(xid_capabilities_0x0200)

      print("xid_get_report for 0x0100:")
      xid_report_0x0100 = xid_get_report(handle, 0x0100, interface_number, 20)
      print(xid_report_0x0100)

      print("xid_get_report on non-existing report:")
      xid_report_0x0300 = xid_get_report(handle, 0x0300, interface_number, 20)
      print((USB_STATUS[xid_report_0x0300[0]], xid_report_0x0300[1]))

      print("xid_set_report:")
      data = bytearray([0x00,0x06,0x00,0x00,0x00,0x00])
      #data = bytearray([0x00,0x06,0xFF,0xFF,0xFF,0xFF])
      xid_report_0x0200 = xid_set_report(handle, 0x0200, interface_number, data)
      print(str(xid_report_0x0200))

      #sys.exit(0)

      while True:
        size = 30

        t = usb_interrupt(handle, usb1.ENDPOINT_IN | ENDPOINT, size, timeout=100)
        print("G %s" % str((USB_STATUS[t[0]], t[1])))
        data = bytearray([0x00,0x06,0x00,0x00,0x00,0x00])
        #t = usb_interrupt(handle, usb1.ENDPOINT_OUT | 2, data, timeout=100)
        #print((USB_STATUS[t[0]], t[1]))

        t = xid_get_report(handle, 0x0100, interface_number, 20)
        print("correct length: %s" % str((USB_STATUS[t[0]], t[1])))

        t = xid_get_report(handle, 0x0100, interface_number, 16)
        print("too short: %s" % str((USB_STATUS[t[0]], t[1])))

        t = xid_get_report(handle, 0x0100, interface_number, 32)
        print("too long: %s" % str((USB_STATUS[t[0]], t[1])))



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

            size = 6

            reqtype = 0xC1 # vendor interface request
            req = 1
            value = 0x100
            index = 0
            in_data = handle.controlRead(reqtype, req, value, index, size, timeout=100)

            size = 20

            reqtype = 0xA1 # class interface request
            req = 1
            value = 0x100
            index = 0
            in_data = handle.controlRead(reqtype, req, value, index, size, timeout=100)


            in_data = handle.interruptRead(ENDPOINT, size, timeout=100)
          except usb1.USBErrorTimeout:
            print("Timeout!")
            continue
          print("Got %s" % str(in_data))

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
