#!/usr/bin/env python3

# Run this from a clean Xbox environment (= not while a game is running)
# NXDK-RDT is a good environment

from xbox import *

def dsp_homebrew():
  #FIXME: Pass dsp object which provides all the device details and registers instead

  # Disable DSP
  apu.write_u32(NV_PAPU_EPRST, NV_PAPU_EPRST_EPRST) # If this is zero, the EP will not allow reads/writes to memory?!
  time.sleep(0.1) # FIXME: Not sure if DSP reset is synchronous, so we wait for now

  # Allocate some scratch space (at least 2 pages!)
  page_count = 2
  page_head = MmAllocateContiguousMemory(4096)
  apu.write_u32(NV_PAPU_EPSADDR, MmGetPhysicalAddress(page_head))
  page_base = MmAllocateContiguousMemory(4096 * page_count)
  for i in range(0, page_count):
    write_u32(page_head + i * 8 + 0, MmGetPhysicalAddress(page_base + 0x1000 * i))
    write_u32(page_head + i * 8 + 4, 0) # Control
  apu.write_u32(NV_PAPU_EPSMAXSGE, page_count - 1)

  # It was assembled using `a56 loop.inc && toomf < a56.out`.
  # The resulting code was then copied here.
  # `a56` (inc. `toomf`) can be found at: http://www.zdomain.com/a56.html
  try:
    raise #FIXME: Test this codepath
    code = dsp.assemble("""
    ; Simple test program
    start
      move x:$000000, a
      move a, y:$000000
      jmp start
    """)
  except:
    code = "56F000 000000 5E7000 000000 0AF080 000000"

  # Write code to PMEM
  code_words = code.split()
  for i in range(0, len(code_words)):
    data = int(code_words[i], 16)
    apu.write_u32(NV_PAPU_EPPMEM + i*4, data)
    # According to XQEMU, 0x800 * 4 bytes will be loaded from scratch to PMEM at startup.
    # So just to be sure, let's also write this to the scratch..
    write_u32(page_base + i*4, data)

  # Set XMEM
  apu.write_u32(NV_PAPU_EPXMEM + 0*4, 0x001337)

  # Set YMEM
  apu.write_u32(NV_PAPU_EPYMEM + 0*4, 0x000000)

  # Test readback
  print("Read back X:0x" + format(apu.read_u32(NV_PAPU_EPXMEM + 0*4), '06X'))
  print("Read back Y:0x" + format(apu.read_u32(NV_PAPU_EPYMEM + 0*4), '06X'))

  print("Read back P:0x" + format(apu.read_u32(NV_PAPU_EPPMEM + 0*4), '06X'))
  print("Read back P:0x" + format(apu.read_u32(NV_PAPU_EPPMEM + 1*4), '06X'))

  # Set frame duration (?!)
  apu.write_u32(NV_PAPU_SECTL, 3 << 3)

  # Enable DSP
  # NV_PAPU_EPRST_EPRST < crashes!
  # NV_PAPU_EPRST_EPDSPRST < works!
  apu.write_u32(NV_PAPU_EPRST, NV_PAPU_EPRST_EPRST | NV_PAPU_EPRST_EPDSPRST)
  time.sleep(0.1)

  # Write X again. Bootcode in the DSP seems to overwrites XMEM + YMEM
  apu.write_u32(NV_PAPU_EPXMEM + 0*4, 0x001337)

  # Read destination data from YMEM
  print("Read back X:0x" + format(apu.read_u32(NV_PAPU_EPXMEM + 0*4), '06X'))
  print("Read back Y:0x" + format(apu.read_u32(NV_PAPU_EPYMEM + 0*4), '06X'))

dsp_homebrew()
