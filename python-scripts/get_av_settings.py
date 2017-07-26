#!/usr/bin/env python3

# Retrieves the AV cable type
#
# For more information about these, see:
# http://xboxdevwiki.net/AV_Cables#Supported_signals_.2F_AV_cables


from xbox import *


#FIXME: Move these libc style functions to some helper module?

def malloc(size):
  #FIXME: Use keNtAllocateVirtualMemory(&addr, 0, &size, ke.MEM_RESERVE | ke.MEM_COMMIT, ke.PAGE_READWRITE)
  #       (Where addr is a pointer to 32 bit of 0)
  return ke.MmAllocateContiguousMemory(size)

def free(ptr):
  #FIXME: Once malloc is fixed, use ke.NtFreeVirtualMemory(ptr, 0, ke.MEM_RELEASE)
  ke.MmFreeContiguousMemory(ptr)


def print_av_settings():
  val_addr = malloc(4)
  VIDEO_BASE = 0xFD000000
  VIDEO_ENC_GET_SETTINGS = 6
  ke.AvSendTVEncoderOption(VIDEO_BASE, VIDEO_ENC_GET_SETTINGS, 0, val_addr);
  val = read_u32(val_addr)
  free(val_addr)

  print("Value is: 0x" + format(val, '08X'))

  cable = val & 0xFF
  cables = [
    "No cable connected",
    "Standard AV Cable (Composite)",
    "RF Adapter",
    "Advanced SCART Cable",
    "High Definition AV Pack (Component)",
    "Unofficial: VGA",
    "Advanced AV Pack (S-Video)"
  ]
  print("Cable type: 0x" + format(cable, '02X') + " (" + cables[cable] + ")")

  standard = (val >> 8) & 0xFF
  standards = [
    "Unknown",
    "NTSC-M",
    "NTSC-J",
    "PAL-I",
    "PAL-M"
  ]
  print("Video standard: 0x" + format(standard, '02X') + " (" + standards[standard] + ")")

  refresh_rate = val & 0x00C00000
  if (refresh_rate == 0x00800000):
    print("50 Hz")
  elif (refresh_rate == 0x00400000):
    print("60 Hz")
  else:
    print("Unknown refresh rate: 0x" + format(refresh_rate, '08X'))

  print("Enabled HDTV modes {")
  mode = val & 0x000E0000
  if (mode & 0x00010000):
    print("  HDTV 480i")
  if (mode & 0x00020000):
    print("  HDTV 720p")
  if (mode & 0x00040000):
    print("  HDTV 1080i")
  if (mode & 0x00080000):
    print("  HDTV 480p")
  print("}")

  print("Flags {")

  if val & 0x00010000:
    print("  Widescreen")

  if val & 0x00100000:
    print("  Letterbox")

  if val & 0x02000000:
    print("  10x11 Pixels")

  if val & 0x00200000:
    print("  Interlaced")

  if val & 0x01000000:
    print("  Field rendering")

  print("}")

def main():
  print_av_settings()

if __name__ == '__main__':
  main()
