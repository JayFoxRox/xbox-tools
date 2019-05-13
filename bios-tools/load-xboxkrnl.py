#!/usr/bin/env python3

import sys

import struct


from xboxpy import *


class Xbox():
  def __init__(self):
    self.ke = ke
    self.call = api.call
    self.read = read

  def write(self, address, data):
    chunk_size = 512
    offset = 0
    while(offset < len(data)):
      print("Writing at 0x%08X" % (address + offset))
      write(address + offset, data[offset:offset + chunk_size])
      offset += chunk_size


def load(path):
  return open(path, 'rb').read()


def store(path, data):
  return open(path, 'wb').write(data)


def upload(xbox, data, low = 0, high = 0xFFFFFFFF):
  address = xbox.ke.MmAllocateContiguousMemoryEx(len(data), low, high, 0, ke.PAGE_READWRITE)
  assert(address != 0)
  xbox.write(address, data)
  return address


def load_xboxkrnl(xbox, xboxkrnl, xboxkrnl_parameters, xboxkrnl_keys):

  # Upload loader code to Xbox and get its physical address
  # This is done first, because it must be at 0x400000 until we make it PIC
  print("Uploading loader (physical)")
  loader_code = load("load-xboxkrnl")
  loader_address = upload(xbox, loader_code, 0x400000, 0x400000 + len(loader_code) - 1)
  physical_loader_adddress = xbox.ke.MmGetPhysicalAddress(loader_address)
  
  print("0x%08X" % loader_address)
  print("0x%08X" % physical_loader_adddress)

  assert(loader_address == 0x80000000 + physical_loader_adddress)

  # Read the xboxkrnl data header
  data_header = struct.unpack_from("<IIII", xboxkrnl, 40)
  data_uninitialized_size = data_header[0]
  data_initialized_size = data_header[1]
  data_raw_address = data_header[2]
  data_virtual_address = data_header[3]

  # Locate some space where we can put the data section
  future_data_address = xbox.ke.MmAllocateContiguousMemoryEx(data_initialized_size, 0x0000000, 0x3000000, 0, ke.PAGE_READWRITE)
  physical_future_data_address = xbox.ke.MmGetPhysicalAddress(future_data_address)
  assert(future_data_address == 0x80000000 + physical_future_data_address)
  print("Mapping data page to 0x%08X" % (future_data_address))

  # Create a copy of the initialized data section in the new page
  assert(data_virtual_address >= 0x80010000)
  data_image_address = data_virtual_address - 0x80010000
  print("Re-uploading %d bytes from image offset 0x%X" % (data_initialized_size, data_image_address))
  data_page = xboxkrnl[data_image_address:data_image_address + data_initialized_size]
  xbox.write(future_data_address, data_page)

  # Patch the kernel data header to point at new page for re-initialization
  data_header = list(data_header)
  data_header[2] = future_data_address 
  xboxkrnl = bytearray(xboxkrnl)
  struct.pack_into("<IIII", xboxkrnl, 40, *data_header)    

  # Upload kernel image to Xbox
  print("Uploading kernel")
  xboxkrnl_address = upload(xbox, xboxkrnl, 0x400000)
  physical_xboxkrnl_address = xbox.ke.MmGetPhysicalAddress(xboxkrnl_address)
  
  # Upload arguments to Xbox
  print("Uploading kernel arguments")
  xboxkrnl_parameters_address = upload(xbox, xboxkrnl_parameters, 0x400000)
  physical_xboxkrnl_parameters_address = xbox.ke.MmGetPhysicalAddress(xboxkrnl_parameters_address)
  xboxkrnl_keys_address = upload(xbox, xboxkrnl_keys, 0x400000)
  physical_xboxkrnl_keys_address = xbox.ke.MmGetPhysicalAddress(xboxkrnl_keys_address)
  
  # We register our kernel loader as the last shutdown notification
  priority = -0x80000000
  shutdown_notification = struct.pack("<IiIIIII", loader_address, priority, 0, 0, physical_xboxkrnl_address, physical_xboxkrnl_parameters_address, physical_xboxkrnl_keys_address)
  shutdown_notification_address = xbox.ke.MmAllocateContiguousMemory(len(shutdown_notification))
  xbox.write(shutdown_notification_address, shutdown_notification)
  xbox.ke.HalRegisterShutdownNotification(shutdown_notification_address, ke.TRUE)

  # Use quick-reboot to trigger a system reset and our shutdown notification
  xbox.ke.HalReturnToFirmware(xbox.ke.HalQuickRebootRoutine)


if __name__ == '__main__':

  # Load kernel image
  xboxkrnl = load(sys.argv[1])

  # Load all kernel arguments
  xboxkrnl_parameters = load(sys.argv[2])
  xboxkrnl_keys = load(sys.argv[3])

  # Connect to Xbox
  xbox = Xbox()

  # Verify the EEPROM key
  xboxkrnl_eeprom_key = xboxkrnl_keys[0:16]
  xbox_eeprom_key = xbox.read(xbox.ke.XboxEEPROMKey(), 16)
  print("Xbox EEPROM key:   %s" % xbox_eeprom_key.hex().upper())
  print("Kernel EEPROM key: %s" % xboxkrnl_eeprom_key.hex().upper())
  #assert(xboxkrnl_eeprom_key == xbox_eeprom_key)
  
  if True:

    # Patch EEPROM key
    #FIXME: Is this a good idea?
    xboxkrnl_keys = bytearray(xboxkrnl_keys)
    xboxkrnl_keys[0:16] = xbox_eeprom_key

  # Start loading and running the kernel
  load_xboxkrnl(xbox, xboxkrnl, xboxkrnl_parameters, xboxkrnl_keys)
