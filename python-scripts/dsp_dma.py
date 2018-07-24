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
BUFFER_SCRATCH_CIRCULAR = 0xE #FIXME: Test

FORMAT_8_BIT = 0x0
FORMAT_16_BIT = 0x1
FORMAT_24_BIT_MSB = 0x2
FORMAT_32_BIT = 0x3
FORMAT_24_BIT_LSB = 0x6 #FIXME: Check endianess

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


def dsp_write_dma_command_block(address, next_block, is_eol, transfer_direction, buffer, sample_format, sample_count, dsp_address, buffer_offset, buffer_base, buffer_limit):

  w0 = next_block & 0x3FFF
  if is_eol:
    w0 |= 1 << 14

  w1 = 0
  if transfer_direction:
    w1 |= 1 << 1
  w1 |= buffer << 5
  w1 |= sample_format << 10

  #FIXME: Turn into a parameter
  # This is how many samples the read (?) cursor advances
  step = 1
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
  if False:
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










dsp_stop()

  

dsp_write_dma_command_block(0x100, 0x0, True, DSP_TO_BUFFER, BUFFER_SCRATCH_CIRCULAR, FORMAT_24_BIT_MSB, 2, DSP_MEMORY_X + 0x200, 0x100, 0x0, 0xFFF)

dsp_write_code("""
; Clear all interrupts
movep #$FFF, x:$FFFFC5

; Set next DMA command block address (0x100 has been prepared by CPU)
movep #$100, x:$FFFFD4
; Set DMA to unfrozen
movep #$4, x:$FFFFD6
; Set DMA to running 
movep #$1, x:$FFFFD6


start
  ; Move x:$0 to y:$0 to verify the DSP is still running
  move x:$0, a0
  move a0, y:$0
  jmp start
""")

# Write a pattern to X memory at 0x200 (DMA source)
dsp_write(NV_PAPU_GPXMEM, 0x200, bytes(range(40)))
#dsp_write(NV_PAPU_GPXMEM, 0x200, [0xAA] * 10)

# Write a pattern to scratch memory (DMA destination)
dsp_write_scratch(0x100, [0xFF] * 40)

dsp_start()

# Monitor Y:0 which should be same as X:0
t = 0
while True:

  # Monitory scratch space for changes
  s = ""
  for x in dsp_read_scratch(0x100, 10):
    s += "%02X" % x
  print(s)

  apu.write_u32(NV_PAPU_GPXMEM + 0, t)
  print("Step %i (if this is not incrementing, the DSP is dead)" % apu.read_u32(NV_PAPU_GPYMEM + 0))
  time.sleep(0.1)
  t += 1
