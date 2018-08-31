#!/usr/bin/env python3

# Dumps the DSP memory

from xboxpy import *
import struct

f = open('dsp.bin', 'wb')

data = []

print("GP P")
for i in range(4096):
  data += [apu.read_u32(NV_PAPU_GPPMEM + i*4)]
print("GP X")
for i in range(4096):
  data += [apu.read_u32(NV_PAPU_GPXMEM + i*4)]
print("GP Y")
for i in range(2048):
  data += [apu.read_u32(NV_PAPU_GPYMEM + i*4)]
print("GP MIXBUF")
for i in range(1024):
  data += [apu.read_u32(NV_PAPU_GPMIXBUF + i*4)]

print("EP P")
for i in range(4096):
  data += [apu.read_u32(NV_PAPU_EPPMEM + i*4)]
print("EP X")
for i in range(3072):
  data += [apu.read_u32(NV_PAPU_EPXMEM + i*4)]
print("EP Y")
for i in range(256):
  data += [apu.read_u32(NV_PAPU_EPYMEM + i*4)]


encoded = bytes(sum([list(struct.pack("<I", x)) for x in data], list()))
f.write(encoded)

f.close()
