#!/usr/bin/env python3

# Run this from a clean Xbox environment (= not while a game is running)
# NXDK-RDT is a good environment

from xboxpy.xboxpy import *

import sys
import time

def dsp_homebrew():
  #FIXME: Pass dsp object which provides all the device details and registers instead

  # Disable DSP
  apu.write_u32(NV_PAPU_GPRST, NV_PAPU_GPRST_GPRST) # If this is zero, the GP will not allow reads/writes to memory?!
  time.sleep(0.1) # FIXME: Not sure if DSP reset is synchronous, so we wait for now

  # Allocate some scratch space (at least 2 pages!)
  #FIXME: Free memory after running
  page_count = 2
  page_head = ke.MmAllocateContiguousMemory(4096)
  apu.write_u32(NV_PAPU_GPSADDR, ke.MmGetPhysicalAddress(page_head))
  page_base = ke.MmAllocateContiguousMemory(4096 * page_count)
  for i in range(0, page_count):
    write_u32(page_head + i * 8 + 0, ke.MmGetPhysicalAddress(page_base + 0x1000 * i))
    write_u32(page_head + i * 8 + 4, 0) # Control
  apu.write_u32(NV_PAPU_GPSMAXSGE, page_count - 1)

  # It was assembled using `a56 loop.inc && toomf < a56.out`.
  # The resulting code was then copied here.
  # `a56` (inc. `toomf`) can be found at: http://www.zdomain.com/a56.html
  if False:
    print("Starting assembler")
    #raise #FIXME: Test this codepath
    data = dsp.assemble("""
    ; Simple test program
    start
      move x:$000000, a
      move a, y:$000000
      jmp start
    """)
    print("Using assembler result!")
  else:
    code = "56F000 000000 5E7000 000000 0AF080 000000"
    code_words = code.split()
    data = bytearray()
    for i in range(0, len(code_words)):
      data += int.to_bytes(int(code_words[i], 16), length=3, byteorder='little', signed=False)

  if False:
    code = open("tiny-gp.inc").read()
    print(code)
    data = dsp.assemble(code)

  print(data)

  # Convert the 24 bit words to 32 bit words
  data = dsp.from24(data)

  while True:

    # Write code to PMEM (normally you can just use write() but we don't support that for apu MMIO yet.. boo!)
    for i in range(0, len(data) // 4):
      word = int.from_bytes(data[i*4:i*4+4], byteorder='little', signed=False) & 0xFFFFFF
      apu.write_u32(NV_PAPU_GPPMEM + i*4, word)
      # According to XQEMU, 0x800 * 4 bytes will be loaded from scratch to PMEM at startup.
      # So just to be sure, let's also write this to the scratch..
      write_u32(page_base + i*4, word)

    # Set XMEM
    apu.write_u32(NV_PAPU_GPXMEM + 0*4, 0x001337)

    # Set YMEM
    apu.write_u32(NV_PAPU_GPYMEM + 0*4, 0x000000)

    # Test readback
    print("Read back X[0]:0x" + format(apu.read_u32(NV_PAPU_GPXMEM + 0*4), '06X'))
    print("Read back Y[0]:0x" + format(apu.read_u32(NV_PAPU_GPYMEM + 0*4), '06X'))

    print("Read back P[0]:0x" + format(apu.read_u32(NV_PAPU_GPPMEM + 0*4), '06X'))
    print("Read back P[1]:0x" + format(apu.read_u32(NV_PAPU_GPPMEM + 1*4), '06X'))

    # Set frame duration (?!)
    apu.write_u32(NV_PAPU_SECTL, 3 << 3)

    # Enable DSP
    # NV_PAPU_GPRST_GPRST < crashes!
    # NV_PAPU_GPRST_GPDSPRST < works!
    apu.write_u32(NV_PAPU_GPRST, NV_PAPU_GPRST_GPRST | NV_PAPU_GPRST_GPDSPRST)
    time.sleep(0.1)

    # Write X again. Bootcode in the DSP seems to overwrites XMEM + YMEM
    apu.write_u32(NV_PAPU_GPXMEM + 0*4, 0x001338)

    time.sleep(0.5)

    #if (apu.read_u32(NV_PAPU_GPXMEM + 0*4) == 0x1338):
    #  continue

    # Read destination data from YMEM
    #while True:
    print("Read back X[0]:0x" + format(apu.read_u32(NV_PAPU_GPXMEM + 0*4), '06X'))
    print("Read back Y[0]:0x" + format(apu.read_u32(NV_PAPU_GPYMEM + 0*4), '06X'))
    time.sleep(0.5)


dsp_homebrew()
