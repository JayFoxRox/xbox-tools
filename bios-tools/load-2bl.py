#!/usr/bin/env python3

import sys

import struct


from xboxpy import *
import time


class Xbox():
  def __init__(self):
    self.ke = ke
    self.call = api.call
    self.read = read

  def write(self, address, data):
    chunk_size = 512
    offset = 0
    while(offset < len(data)):
      #print("Writing at 0x%08X" % (address + offset))
      write(address + offset, data[offset:offset + chunk_size])
      offset += chunk_size


def load(path):
  return open(path, 'rb').read()


def store(path, data):
  return open(path, 'wb').write(data)


def extract_bl(rom, key):

  from cryptography.hazmat.backends import default_backend
  from cryptography.hazmat.primitives import hashes
  from cryptography.hazmat.primitives.ciphers import Cipher, algorithms

  def decrypt_rc4(data, key):
    cipher = Cipher(algorithms.ARC4(key), mode=None, backend=default_backend())
    ctx = cipher.decryptor()
    return ctx.update(data) + ctx.finalize()

  # Decrypt 2BL
  assert(len(key) == 16)
  bl = decrypt_rc4(rom[-0x6200:-0x6200 + 0x6000], key)

  return bl


def load_bl(xbox, bl, rom):

    # Verify the 2BL size
    assert(len(bl) == 0x6000)

    # Check the 2BL magic
    if (struct.unpack_from("<I", bl, 0x6000 - 0x2C)[0] != 0x7854794a):
      print("Trouble with 2BL: bad magic. Possible reasons:\n"
            " - WRONG RC4 KEY\n"
            " - Non-BFM BIOS image (BIOS must be Bootable From Media)\n"
            " - Faulty BIOS image\n"
            "Trying to continue anyway.")
      assert(False)
    
    if True:

      # Extract the EEPROM key from the running Xbox
      eeprom_key = xbox.read(xbox.ke.XboxEEPROMKey(), 16)

      # Patch the EEPROM key in the 2BL
      print("Patching EEPROM key: %s" % (bl[0x64:0x64 + 16].hex().upper()))
      bl = bytearray(bl)
      assert(len(eeprom_key) == 16)
      #FIXME: Original code also patches ROM image, but only the topmost mirror.
      #       We emulate that behaviour for all copies
      bl[0x64:0x64 + 16] = eeprom_key
      print("Patched EEPROM key:  %s" % (bl[0x64:0x64 + 16].hex().upper()))

    if True:

      # Construct a kernel parameter string
      kernel_parameters_string = ''
      kernel_parameters_string += ' /SHADOW'
      kernel_parameters_string += ' /HDBOOT'

      # Patch parameter in the 2BL
      print("Patching kernel param string")
      kernel_parameters = kernel_parameters_string.encode('ascii') + b'\x00'
      bl[4:4 + len(kernel_parameters)] = kernel_parameters

    # Emulate in-place decryption after all patches have been done
    rom = bytearray(rom)
    assert(len(bl) == 0x6000)
    rom[-0x6200:-0x6200 + 0x6000] = bl
    
    #FIXME: Allocate *anywhere* and we'll map the proper region into RAM, then copy after cli
    #FIXME: Also do memory repeats in low level code after cli
    assert(len(rom) <= 0x100000)
    rom_address = xbox.ke.MmAllocateContiguousMemoryEx(0x100000, 0x0000000, 0x3000000, 0, xbox.ke.PAGE_READWRITE)
    assert(rom_address != 0)
    physical_rom_address = xbox.ke.MmGetPhysicalAddress(rom_address)
    print("Physical ROM address is 0x%08X (Virtual: 0x%08X)" % (physical_rom_address, rom_address))

    # Allocate memory for the 2BL; must be at 0x00400000
    #FIXME: Allocate *anywhere* and we'll map the proper region into RAM, then copy after cli
    print("Allocate 2BL mem")
    bl_address = xbox.ke.MmAllocateContiguousMemoryEx(0x6000, 0x400000, 0x400000 + 0x6000 - 1, 0, xbox.ke.PAGE_READWRITE)
    assert(bl_address == 0x80400000)
    
    # Parse the 2BL header to find the BFM entry point
    print("Calculating 2BL entry point")
    bl_mcpx_entry = struct.unpack_from("<I", bl, 0)[0]
    #FIXME: Nothing prevents bl_mcpx_entry to be outside of 2BL I guess? Guard it.
    bl_bfm_entry = struct.unpack_from("<I", bl, (bl_mcpx_entry % 0x6000) - 4)[0]
    ram_mcpx_entry = 0x80000000 + bl_mcpx_entry
    ram_bfm_entry = 0x80000000 + bl_bfm_entry
    print("MCPX Entry point is 0x%08X" % ram_mcpx_entry)
    print("BFM Entry point is 0x%08X" % ram_bfm_entry)

    # Upload 2BL
    print("Uploading 2BL")
    xbox.write(bl_address, bl)

    # Upload ROM image, filled with repeats to fill 1 MB
    print("Uploading ROM")
    assert(0x100000 % len(rom) == 0)
    xbox.write(rom_address, rom * (0x100000 // len(rom)))

    # Upload our 2BL loader
    print("Uploading loader")
    loader_code = load("load-2bl")
    loader_address = xbox.ke.MmAllocateContiguousMemory(len(loader_code))
    assert(loader_address != 0)
    xbox.write(loader_address, loader_code)

    # Blank video
    xbox.ke.AvSendTVEncoderOption(0, 9, 1, xbox.ke.NULL);

    # We register our 2BL loader as the last shutdown notification
    priority = -0x80000000
    shutdown_notification = struct.pack("<IiIIII", loader_address, priority, 0, 0, ram_bfm_entry, physical_rom_address)
    shutdown_notification_address = xbox.ke.MmAllocateContiguousMemory(len(shutdown_notification))
    xbox.write(shutdown_notification_address, shutdown_notification)
    xbox.ke.HalRegisterShutdownNotification(shutdown_notification_address, ke.TRUE)

    # Use quick-reboot to trigger a system reset and our shutdown notification
    xbox.ke.HalReturnToFirmware(xbox.ke.HalQuickRebootRoutine)


if __name__ == '__main__':

  # Load 2BL and ROM
  bl = load(sys.argv[1])
  rom = load(sys.argv[2])

  # Load RC4 key if provided, and then verify 2BL image
  if len(sys.argv) >= 4:
    key = load(sys.argv[3])
    bl_check = extract_bl(rom, key)
    assert(bl == bl_check)
    print("Verified that 2BL belongs to ROM")
  else:
    print("No key provided\n"
          "Unable to verify that this 2BL belongs to ROM")

  # Connect to Xbox
  xbox = Xbox()

  # Load and run the 2BL
  load_bl(xbox, bl, rom)
