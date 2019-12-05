#!/usr/bin/env python3

# Fills the DSP memory with known pattern

from xboxpy import *

print("GP P")
for i in range(4096):
  apu.write_u32(NV_PAPU_GPPMEM + i*4, 0x313373)
print("GP X")
for i in range(4096):
  apu.write_u32(NV_PAPU_GPXMEM + i*4, 0x313373)
print("GP Y")
for i in range(2048):
  apu.write_u32(NV_PAPU_GPYMEM + i*4, 0x313373)
print("GP MIXBUF")
for i in range(1024):
  apu.write_u32(NV_PAPU_GPMIXBUF + i*4, 0x313373)

print("EP P")
for i in range(4096):
  apu.write_u32(NV_PAPU_EPPMEM + i*4, 0x313373)
print("EP X")
for i in range(3072):
  apu.write_u32(NV_PAPU_EPXMEM + i*4, 0x313373)
print("EP Y")
for i in range(256):
  apu.write_u32(NV_PAPU_EPYMEM + i*4, 0x313373)
