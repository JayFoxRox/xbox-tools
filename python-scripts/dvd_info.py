#!/usr/bin/env python3

# This dumps out the DVDs SS.bin, DMI.bin and PFI.bin
#
# For more information about these files, see:
# http://xboxdevwiki.net/Xbox_Game_Disc


from xbox import *


#FIXME: Move these libc style functions to some helper module?

def malloc(size):
  #FIXME: Use keNtAllocateVirtualMemory(&addr, 0, &size, ke.MEM_RESERVE | ke.MEM_COMMIT, ke.PAGE_READWRITE)
  #       (Where addr is a pointer to 32 bit of 0)
  return ke.MmAllocateContiguousMemory(size)

def free(ptr):
  #FIXME: Once malloc is fixed, use ke.NtFreeVirtualMemory(ptr, 0, ke.MEM_RELEASE)
  ke.MmFreeContiguousMemory(ptr)

def strdup(string):
  addr = malloc(len(string) + 1)
  write(addr, bytes(string + '\x00', encoding='ascii'))
  return addr


def get_dvd_device_object():
  #static PDEVICE_OBJECT device = NULL;
  #if (device == NULL):
  #ANSI_STRING cdrom

  ANSI_STRING_len = 8
  cdrom_addr = malloc(ANSI_STRING_len)

  string = strdup("\\Device\\Cdrom0")
  ke.RtlInitAnsiString(cdrom_addr, string)

  # Get a reference to the dvd object so that we can query it for info.
  device_ptr_addr = malloc(4) # Pointer to device
  status = ke.ObReferenceObjectByName(cdrom_addr, 0, ke.IoDeviceObjectType(), ke.NULL, device_ptr_addr)
  device_ptr = read_u32(device_ptr_addr)
  free(device_ptr_addr)

  free(string)
  free(cdrom_addr)

  print("Status: 0x" + format(status, '08X'))
  print("Device: 0x" + format(device_ptr, '08X'))

  if (status != 0):
    return ke.NULL

  assert(device_ptr != ke.NULL)
  return device_ptr

def main():
  device_ptr = get_dvd_device_object()
  assert(device_ptr != ke.NULL)

  #SCSI_PASS_THROUGH_DIRECT pass_through;
  #RtlZeroMemory(&pass_through, sizeof(SCSI_PASS_THROUGH_DIRECT));

  if True:
    length = 2048+4
    cdb = [0xAD, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, (length >> 8) & 0xFF, length & 0xFF, 0x00, 0xC0] # Get PFI
    #cdb = [0xAD, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x04, (length >> 8) & 0xFF, length & 0xFF, 0x00, 0xC0] # Get DMI
    #cdb = [0xAD, 0x00, 0xFF, 0x02, 0xFD, 0xFF, 0xFE, 0x00, (length >> 8) & 0xFF, length & 0xFF, 0x00, 0xC0] # Get SS
  else:
    length = 20+8 # Length of auth page + mode sense header
    cdb = [0x5A, 0x00, 0x3E, 0x00, 0x00, 0x00, 0x00, (length >> 8) & 0xFF, length & 0xFF, 0x00]

  buffer_length = length
  buffer_addr = malloc(buffer_length) #FIXME: How long does this have to be?
  write(buffer_addr, [0xFF] * buffer_length)

  # Now write the SCSI_PASS_THROUGH_DIRECT structure:
  #USHORT Length; // 0
  #UCHAR ScsiStatus; // 2
  #UCHAR PathId; // 3
  #UCHAR TargetId; // 4
  #UCHAR Lun; // 5
  #UCHAR CdbLength; // 6
  #UCHAR SenseInfoLength; // 7
  #UCHAR DataIn; // 8
  #ULONG DataTransferLength; // 12
  #ULONG TimeOutValue; // 16
  #PVOID DataBuffer; // 20
  #ULONG SenseInfoOffset; // 24
  #UCHAR Cdb[16]; // 28
  #// 44

  SCSI_PASS_THROUGH_DIRECT_len = 44
  pass_through_addr = malloc(SCSI_PASS_THROUGH_DIRECT_len)
  write(pass_through_addr, [0] * SCSI_PASS_THROUGH_DIRECT_len)
  write_u16(pass_through_addr + 0, SCSI_PASS_THROUGH_DIRECT_len) # Length
  #write_u8(pass_through_addr + 6, len(cdb)) #CdbLength # FIXME: Not necessary.. remove!
  write_u8(pass_through_addr + 8, ke.SCSI_IOCTL_DATA_IN) # DataIn
  write_u32(pass_through_addr + 12, buffer_length) # DataTransferLength
  write_u32(pass_through_addr + 20, buffer_addr) # DataBuffer
  assert(len(cdb) <= 16)
  write(pass_through_addr + 28, cdb) # Cdb

  status = ke.IoSynchronousDeviceIoControlRequest(ke.IOCTL_SCSI_PASS_THROUGH_DIRECT, device_ptr, pass_through_addr, SCSI_PASS_THROUGH_DIRECT_len, ke.NULL, 0, ke.NULL, ke.FALSE)

  print("Status: 0x" + format(status, '08X'))

  buffer_data = read(buffer_addr, buffer_length)
  print(buffer_data)

  free(buffer_addr)
  free(pass_through_addr)

if __name__ == '__main__':
  main()
