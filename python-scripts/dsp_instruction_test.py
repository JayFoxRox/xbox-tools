#!/usr/bin/env python3

# Run this from a clean Xbox environment (= not while a game is running)
# NXDK-RDT is a good environment

from xboxpy import *

import sys
import time

def dsp_stop():
  # Reset GP and GP DSP
  apu.write_u32(NV_PAPU_GPRST, 0)
  time.sleep(0.1) # FIXME: Not sure if DSP reset is synchronous, so we wait for now

  # Enable GP first, otherwise memory writes won't be handled
  apu.write_u32(NV_PAPU_GPRST, NV_PAPU_GPRST_GPRST)


def dsp_allocate_scratch_space(page_count):

  # Allocate some scratch space (at least 2 pages!)
  #FIXME: Why did I put: "(at least 2 pages!)" ?
  assert(page_count >= 2)

  # Apparently NV_PAPU_GPSADDR has to be aligned to 0x4000 bytes?!
  #FIXME: Free memory after running
  page_head = ke.MmAllocateContiguousMemoryEx(4096, 0x00000000, 0xFFFFFFFF, 0x4000, ke.PAGE_READWRITE)
  page_head_p = ke.MmGetPhysicalAddress(page_head)
  apu.write_u32(NV_PAPU_GPSADDR, page_head_p)
  page_base = ke.MmAllocateContiguousMemory(4096 * page_count)
  for i in range(0, page_count):
    write_u32(page_head + i * 8 + 0, ke.MmGetPhysicalAddress(page_base + 0x1000 * i))
    write_u32(page_head + i * 8 + 4, 0) # Control

  # I'm not sure if this is off-by-one (maybe `page_count - 1`)
  apu.write_u32(NV_PAPU_GPSMAXSGE, page_count)

  return page_base

def dsp_start():

  # Set frame duration (?!)
  if True:
    apu.write_u32(NV_PAPU_SECTL, 3 << 3)

  # Mark GP as ready?
  NV_PAPU_GPIDRDY = 0x3FF10
  NV_PAPU_GPIDRDY_GPSETIDLE = (1 << 0)
  apu.write_u32(NV_PAPU_GPIDRDY, NV_PAPU_GPIDRDY_GPSETIDLE)

  # Clear interrupts
  NV_PAPU_GPISTS = 0x3FF14
  apu.write_u32(NV_PAPU_GPISTS, 0xFF)

  # Now run GP DSP by removing reset bit
  apu.write_u32(NV_PAPU_GPRST, NV_PAPU_GPRST_GPRST | NV_PAPU_GPRST_GPDSPRST)
  time.sleep(0.1)

def dsp_homebrew(tests):
  #FIXME: Pass dsp object which provides all the device details and registers instead

  # Stop the running DSP
  print("Stopping DSP")
  dsp_stop()

  # Allocate new scratch space
  print("Allocating DSP scratch space")
  page_base = dsp_allocate_scratch_space(20)

  # Start with empty code
  print("Generating DSP code")
  code = ""

  # Setup memory registers
  #FIXME: Do this before every writeback / address outputs directly
  code += "\n; Memory register setup\n\n"
  code += "move #$100, R0\n"
  code += "move #1, N0\n"
  code += "movec #$FFFF, M0\n"
  code += "move #$100, R1\n"
  code += "move #1, N1\n"
  code += "movec #$FFFF, M1\n"

  # Generate each test
  r0 = 0x100 #FIXME: X:0 seems to be used during DSP reset?!
  n0 = 1
  for t in tests:
    i = t[0]
    p = t[1]
    o = t[2]

    code += "\n; Test\n\n"

    #FIXME: Allow only 24 bit registers
    #       - Replace 'a' by ('a2', 'a1', 'a0')
    #       - Replace 'b' by ('b2', 'b1', 'b0')

    # Input
    for k, v in i.items():
      #FIXME: Check for special registers like SR etc.

      if k == 'sr':
        code += "movec x:(R0)+N0, %s\n" % (k)
      else:
        code += "move x:(R0)+N0, %s\n" % (k)
      apu.write_u32(NV_PAPU_GPXMEM + r0*4, v)
      r0 += n0

    # Processing      
    code += p + "\n"

    # Output
    for k in o:

      if k == 'sr':
        code += "movec %s, y:(R1)+N1\n" % (k)
      else:
        code += "move %s, y:(R1)+N1\n" % (k)

  # Mark results as ready and stick in a loop
  code += "\n; Result marker\n\n"
  code += "move #$1337, a\n"
  code += "move a, y:$0\n"
  code += "finished_loop\n"
  code += "  jmp finished_loop"

  # Assemble code and convert the 24 bit words to 32 bit words
  print("Starting assembler")
  data = dsp.assemble(code)
  data = dsp.from24(data)

  # Write code to PMEM (normally you can just use write() but we don't support that for apu MMIO yet.. boo!)
  print("Writing program to DSP")
  for i in range(0, len(data) // 4):
    word = int.from_bytes(data[i*4:i*4+4], byteorder='little', signed=False) & 0xFFFFFF
    apu.write_u32(NV_PAPU_GPPMEM + i*4, word)
    # According to XQEMU, 0x800 * 4 bytes will be loaded from scratch to PMEM at startup.
    # So just to be sure, let's also write this to the scratch..
    write_u32(page_base + i*4, word)

  # Set Y:0, so we can see when the program modifies it later
  apu.write_u32(NV_PAPU_GPYMEM + 0*4, 0x000000)
  assert(apu.read_u32(NV_PAPU_GPYMEM + 0*4) == 0x000000)

  # Run the test
  print("Running test")
  dsp_start()

  # Wait until results are ready
  print("Waiting for test results")
  while(apu.read_u32(NV_PAPU_GPYMEM + 0*4) != 0x1337):
    time.sleep(0.5)

  # Read all results from memory
  print("Reading test results")
  all_results = []
  r1 = 0x100
  n1 = 1
  for t in tests:
    i = t[0]
    p = t[1]
    o = t[2]

    #FIXME: Verify that inputs were not touched

    # Loop over all outputs
    results = {}
    for k in o:
      results[k] = apu.read_u32(NV_PAPU_GPYMEM + r1*4)
      r1 += n1

    # Add result for this test
    all_results += [results]

  # Return the output
  return all_results


# Generate some test cases
sr = 0xC00310
inputs = (
  {'a2':0x00, 'a1': 0x001000, 'a0': 0xFFFFFF, 'b1': 0x10, 'sr': sr },
  {'a2':0x80, 'a1': 0x002000, 'a0': 0x000001, 'b1': 0x20, 'sr': sr },
  {'a2':0xFF, 'a1': 0x003000, 'a0': 0xFFFFFF, 'b1': 0x30, 'sr': sr }
)
processing = ['asr a'] * len(inputs)
outputs = [['a2','a1','a0','b1','sr']] * len(inputs)
tests = list(zip(inputs, processing, outputs))


# Run the tests
results = dsp_homebrew(tests)

# Print results
print("Finished:")
for r in results:
  print("")
  for k, v in r.items():
    print("%s: 0x%X" % (k, v))



