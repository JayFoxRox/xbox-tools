#!/usr/bin/env python3

# Run this from a clean Xbox environment (= not while a game is running)
# NXDK-RDT is a good environment

from xboxpy import *

import json
import sys
import time

reserved_words = 0x20

def get_word(s):
  #FIXME: Assert type is string or int
  s = str(s)
  s = s.strip()
  s = s.replace('$', '0x')
  s = s.lower()
  if s[0:2] == "0x":
    return int(s[2:], 16)
  else:
    return int(s, 10)

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

  # We reserve some program words (jump targets, as magic for p-word injection)
  code += "nop\n" * reserved_words

  # Setup memory registers
  #FIXME: Do this before every writeback / address outputs directly
  code += "\n; Memory register setup\n\n"
  code += "movec #$FFFF, M7\n"
  code += "move #$100, R7\n"
  code += "move #1, N7\n"
  code += "nop\n"

  # Generate each test
  r7 = 0x100 #FIXME: X:0 seems to be used during DSP reset?!
  n7 = 1
  for t in tests:
    i = t[0]
    p = t[1]
    o = t[2]

    code += "\n; Test\n\n"

    #FIXME: Allow only 24 bit registers
    #       - Replace 'a' by ('a2', 'a1', 'a0')
    #       - Replace 'b' by ('b2', 'b1', 'b0')

    control_regs = [
      "vba", "sr", "omr", "sp", "ssh", "ssl", "la", "lc",
      "m0", "m1", "m2", "m3", "m4", "m5", "m6", "m7",
    ]

    # Add any register which would cause trouble
    forbidden_regs = [
      "ssh", # Crash in XQEMU (possibly bug in a56?)
      "vba", # Caused error in a56
      "m7", "r7", "n7" # Used for input/output addressing
    ]

    # Input
    for k, v in i.items():

      if k.find(':') != -1:
        print("Memory %s unsupported in setter" % k)
        space, colon, address = k.partition(':')
        address = get_word(address)

        for w in v:
          print("Would have set %s:$%X to 0x%06X" % (space, address, w))
          address += 1

      elif k.lower() in forbidden_regs:
        print("Register %s forbidden in setter" % k)
      else:
        if k.lower() in control_regs:
          code += "movec x:(R7)+N7, %s\n" % (k)
        else:
          code += "move x:(R7)+N7, %s\n" % (k)
        apu.write_u32(NV_PAPU_GPXMEM + r7*4, v)
        r7 += n7
        code += "nop\n" # Avoid hazards

    # Processing, while avoiding the mix any of the surrounding instructions    
    code += "nop\n"
    code += p[0] + "\n"
    code += "nop\n"

    # Setup memory registers for output
    code += "movec #$FFFF, M7\n"
    code += "move #$100, R7\n"
    code += "move #1, N7\n"
    code += "nop\n"

    # Output
    for k in o:

      if k.lower() in forbidden_regs:
        print("Register %s forbidden in getter" % k)
        code += "move a0, y:(R7)+N7\n" # Used to advance R7
      elif k.lower() in control_regs:
        code += "movec %s, y:(R7)+N7\n" % (k)
      else:
        code += "move %s, y:(R7)+N7\n" % (k)

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

  # Write code to PMEM, and also inject p-words
  print("Writing program to DSP")
  for i in range(0, len(data) // 4):
    word = int.from_bytes(data[i*4:i*4+4], byteorder='little', signed=False) & 0xFFFFFF

    # Check for the magic jmp, to inject p-words
    if word & 0xFFF000 == 0x0C0000:
      jmp_label = word & 0xFFF
      if jmp_label < reserved_words:
        word = p[1][jmp_label]

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
  r7 = 0x100
  n7 = 1
  for t in tests:
    i = t[0]
    p = t[1]
    o = t[2]

    #FIXME: Verify that inputs were not touched

    # Loop over all outputs
    results = {}
    for k in o:
      results[k] = apu.read_u32(NV_PAPU_GPYMEM + r7*4)
      r7 += n7

    # Add result for this test
    all_results += [results]

  # Remove forbidden outputs
  for k in forbidden_regs:
    if k in results:
      del results[k]

  # Return the output
  return all_results




# Process all tests
for path in sys.argv[1:]:

  print("")
  print("Processing '%s'" % path)
  print("")

  # Load test from file
  #FIXME: Error checking
  with open(path, 'rb') as f:
    source = f.read()
  test = json.loads(source)

  # Turn all prefixed strings into words
  new_input = {}
  for k, v in test['input'].items():
    if k.find(':') != -1:
      new_input[k] = [get_word(word) for word in v]
    else:
      new_input[k] = get_word(v)
  new_input
    
  # Turn line-array into string
  new_code = ""
  inject = []
  for l in test['code']:

    # Check for raw p-words to inject
    if l[0] == ":":
      v = get_word(l[1:])
      print("Unsupported program-word: 0x%06X" % v)
      #FIXME: We need some syntax for parallel words?
      new_code += "jmp <$%X\n" % len(inject)
      inject += [v]
      assert(len(inject) <= reserved_words)

    else:
      new_code += l + "\n"

  #FIXME: This is a legacy format; this weird conversion shouldn't be necessary
  # Assemble a test
  tests = [(new_input, (new_code, inject), test['output'])]

  # Run the tests
  results = dsp_homebrew(tests)

  # Print results
  print("Finished:")
  output_json = {} 
  for r in results:
    print("")
    for k, v in r.items():
      print("%s: 0x%X" % (k, v))
      output_json[k] = '0x%X' % (v)

  #FIXME: Write to log
  output_source = json.dumps(output_json, indent=2)
  with open(path + "-out.json", 'wb') as f:
    f.write(output_source.encode("utf-8"))
