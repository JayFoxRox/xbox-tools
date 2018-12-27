#!/usr/bin/env python3

# This resets the GP DSP and attempts to do DMA transfers

from xboxpy import *

import random
import sys
import time
import struct




BUFFER_TO_DSP = False
DSP_TO_BUFFER = True

BUFFER_FIFO0 = 0x0
BUFFER_FIFO1 = 0x1
BUFFER_FIFO2 = 0x2
BUFFER_FIFO3 = 0x3
BUFFER_SCRATCH_CIRCULAR = 0xE
BUFFER_SCRATCH = 0xF

FORMAT_8_BIT = 0x0
FORMAT_16_BIT = 0x1
FORMAT_24_BIT_MSB = 0x2
FORMAT_32_BIT = 0x3
FORMAT_24_BIT_LSB = 0x6

FLAGS_UNK0 = (1 << 0)
FLAGS_UNK4 = (1 << 4)
FLAGS_UNK9 = (1 << 9)

DSP_MEMORY_X = 0x0
DSP_MEMORY_Y = 0x1800
DSP_MEMORY_P = 0x2800


page_base = 0


def dsp_write(base, address, data):
  # Write code to PMEM (normally you can just use write() but we don't support that for apu MMIO yet.. boo!)
  for i in range(0, len(data) // 4):
    word = int.from_bytes(data[i*4:i*4+4], byteorder='little', signed=False) & 0xFFFFFF
    apu.write_u32(base + (address + i)*4, word)

def dsp_read_scratch(address, size):
  global page_base
  return read(page_base + address, size)  

def dsp_write_scratch(address, data):
  global page_base
  write(page_base + address, data)


def dsp_write_dma_command_block(address, next_block, is_eol, transfer_direction, buffer, sample_format, sample_count, dsp_address, buffer_offset, buffer_base, buffer_limit, control_flags, step):

  w0 = next_block & 0x3FFF
  if is_eol:
    w0 |= 1 << 14

  w1 = 0
  if transfer_direction:
    w1 |= 1 << 1
  w1 |= buffer << 5
  w1 |= sample_format << 10
  w1 |= control_flags

  #FIXME: Turn into a parameter
  # This is how many samples the read (?) cursor advances
  w1 |= step << 14

  w2 = sample_count

  w3 = dsp_address

  w4 = buffer_offset

  w5 = buffer_base

  w6 = buffer_limit

  data = struct.pack("<IIIIIII", w0, w1, w2, w3, w4, w5, w6)
  dsp_write(NV_PAPU_GPXMEM, address, data)



def dsp_stop():
  global page_base
  #FIXME: Pass dsp object which provides all the device details and registers instead

  # Reset GP and GP DSP
  apu.write_u32(NV_PAPU_GPRST, 0)
  time.sleep(0.1) # FIXME: Not sure if DSP reset is synchronous, so we wait for now

  # Enable GP first, otherwise memory writes won't be handled
  apu.write_u32(NV_PAPU_GPRST, NV_PAPU_GPRST_GPRST)

  # Allocate some scratch space (at least 2 pages!)
  #FIXME: Why did I put: "(at least 2 pages!)" ?
  page_count = 2

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

  #FIXME: Set up a FIFO
  


def dsp_write_code(code):
  apu.write_u32(NV_PAPU_GPRST, 0)
  time.sleep(0.1) # FIXME: Not sure if DSP reset is synchronous, so we wait for now

  # Enable GP first, otherwise memory writes won't be handled
  apu.write_u32(NV_PAPU_GPRST, NV_PAPU_GPRST_GPRST)

  data = dsp.assemble(code)

  # Convert 24 bit words to 32 bit words
  data = dsp.from24(data)

  # Write program to memory
  dsp_write(NV_PAPU_GPPMEM, 0, data)

  # According to XQEMU, 0x800 * 4 bytes will be loaded from scratch to PMEM at startup.
  # So just to be sure, let's also write this to the scratch..
  dsp_write_scratch(0, data)



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









# Stop the DSP
dsp_stop()

# Prepare code to kick off DMA
dsp_write_code("""

; Start transfer
move #$100, a
jsr DMA_Transfer

; Wait for EOL and reset it
jsr DMA_WaitAndResetEOL




; Start second transfer
move #$100, a
jsr DMA_Transfer

; Wait for EOL and reset it
jsr DMA_WaitAndResetEOL





; Mark success
move #$1337, a
move a, y:$0

; Wait in loop
Finished
  jmp Finished


DMA_StopAndFreeze

  ; Stop DMA and wait until idle
  movep #$000002, x:$FFFFD6
  DMA_StopAndFreeze_WaitUntilIdle
    jset #4, x:$FFFFD6, DMA_StopAndFreeze_WaitUntilIdle

  ; Freeze DMA and wait until frozen
  movep #$000003, x:$FFFFD6
  DMA_StopAndFreeze_WaitUntilFrozen
    jclr #3, x:$FFFFD6, DMA_StopAndFreeze_WaitUntilFrozen

  rts


DMA_UnfreezeAndStart

  ; Unfreeze DMA and wait until unfrozen
  movep #$000004, x:$FFFFD6
  DMA_UnfreezeAndStart_WaitUntilUnfrozen
    jset #3, x:$FFFFD6, DMA_UnfreezeAndStart_WaitUntilUnfrozen

  ; Start DMA and wait until running
  movep #$000001, x:$FFFFD6
  DMA_UnfreezeAndStart_WaitUntilRunning
    jclr #4, x:$FFFFD6, DMA_UnfreezeAndStart_WaitUntilRunning

  rts


DMA_WaitAndResetEOL

  ; Wait for EOL
  DMA_WaitAndResetEOL_WaitForEOL
    jclr #7, x:$FFFFC5, DMA_WaitAndResetEOL_WaitForEOL

  ; Reset EOL
  movep #$000080, x:$FFFFC5

  rts


; Arguments:
;
;   `a` = DMA block address
;
; Modifies:
;
;   `a`, `x0`
;
DMA_Transfer

  ; Stop and freeze DMA
  jsr DMA_StopAndFreeze

  ; Remove EOL from next DMA block
  move #$FFDFFF, x0
  and x0, a
  movep a, x:$FFFFD4

  ; Unfreeze and start DMA
  jsr DMA_UnfreezeAndStart

  rts

""")

# Write a DMA transfer to memory

#dsp dma block 0x48 (dsp -> buffer)
#    next-block 0x0 (eol)
#    control 0x0059d2: unk0:0, unk4:1 buf 0xe (scratch-circular?) unk9:0 format 0x6 (24 bit lsb) step 0x1
#    count 0x20
#    dsp-offset 0x1460 (x:$1460)
#    buffer-offset 0x0 (+ buffer-base 0xa800 = 0xa800)
#    buffer-size 0x800


dsp_write_dma_command_block(0x100, 0x107, False, # address / next / eol
                            DSP_TO_BUFFER, # direction
                            BUFFER_SCRATCH, # buffer
                            FORMAT_16_BIT, 0x2 << 4 | 0x1, # sample-format / sample-count
                            DSP_MEMORY_X + 0x600, # dsp-offset
                            0x100, # buffer-offset
                            0x0, 0x0, # buffer-base / buffer-size
                            FLAGS_UNK0, # control flags
                            0x12) # step

dsp_write_dma_command_block(0x107, 0x10E, False, # address / next / eol
                            BUFFER_TO_DSP, # direction
                            BUFFER_SCRATCH, # buffer
                            FORMAT_16_BIT, 0x5, # sample-format / sample-count
                            DSP_MEMORY_X + 0x700, # dsp-offset
                            0x200, # buffer-offset
                            0x0, 0x0, # buffer-base / buffer-size
                            FLAGS_UNK0 | FLAGS_UNK9, # control flags
                            0x20) # step

dsp_write_dma_command_block(0x10E, 0, True, # address / next / eol
                            BUFFER_TO_DSP, # direction
                            BUFFER_SCRATCH_CIRCULAR, # buffer
                            FORMAT_24_BIT_LSB, 0x1, # sample-format / sample-count
                            DSP_MEMORY_X + 0x800, # dsp-offset
                            0x0, # buffer-offset
                            0x300, 0x100, # buffer-base / buffer-size
                            0, # control flags
                            1) # step

# Write a pattern to X memory at 0x200 (DMA source)
#dsp_write(NV_PAPU_GPXMEM, 0x200, bytes(range(40)))
for i in range(40):
  apu.write_u32(NV_PAPU_GPXMEM + (0x600 + i) * 4, 0x123456)
  apu.write_u32(NV_PAPU_GPXMEM + (0x700 + i) * 4, 0xFFFFFF)
  apu.write_u32(NV_PAPU_GPXMEM + (0x800 + i) * 4, 0xFFFFFF)

# Write a pattern to scratch memory (DMA destination)
dsp_write_scratch(0x100, [0xFF] * 40)
dsp_write_scratch(0x200, [0x00,0xFE,0xFF,0x00,0xEE,0xEE,0xEE,0xEE])
dsp_write_scratch(0x300, [0x56,0x34,0x12,0xFF,0xEE,0xEE,0xEE,0xEE])

# Place marker in YMEM
apu.write_u32(NV_PAPU_GPYMEM + 0, 0x000000)
assert(apu.read_u32(NV_PAPU_GPYMEM + 0) != 0x1337)

def print_scratch(address, size, group_size, gap_size):
  s = ""
  i = 0
  for x in dsp_read_scratch(address, size):
    if i == 0 and group_size > 0:
      s += " "
    s += "%02X" % x
    i += 1
    if i >= group_size and group_size > 0:
      s += " "
      i = -gap_size
  print(s.strip())

def print_x(address, count, silent = False):
  words = []
  for i in range(count):
    words += ["%06X" % apu.read_u32(NV_PAPU_GPXMEM + (address + i) * 4)]
  if not silent:
    print("%s" % words)
  return str(words)

def print_dma_block(address):
  x = print_x(address, 7, silent = True)
  print("dma x:$%x: %s" % (address, x))
  
# Check input data
old = print_dma_block(0x100)
#print_scratch(0x100, 40, 3, 1)
print_scratch(0x200, 40, 3, 1)
print_scratch(0x300, 40, 3, 1)
print_x(0x600, 10)
#print_x(0x700, 10)
#print_x(0x800, 10)

# Start DSP
dsp_start()

# Wait for results
while apu.read_u32(NV_PAPU_GPYMEM + 0) != 0x1337:
  pass

# Signal success
print("Finished")

# Check output data
new = print_dma_block(0x100)
print_scratch(0x100, 40, 0, 0)
#print_scratch(0x200, 40, 0, 0)
#print_scratch(0x300, 40, 0, 0)
#print_x(0x600, 10)
print_x(0x700, 10)
print_x(0x800, 10)

assert(new == old)


