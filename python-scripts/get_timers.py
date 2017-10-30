#!/usr/bin/env python3

# Prints information about some of the Xbox timers

from xbox import *

import time
import struct

NV_PRAMDAC = 0x680000
NV_PRAMDAC_NVPLL_COEFF = 0x500
NV_PRAMDAC_NVPLL_COEFF_MDIV = 0x000000FF
NV_PRAMDAC_NVPLL_COEFF_NDIV = 0x0000FF00
NV_PRAMDAC_NVPLL_COEFF_PDIV = 0x00070000

# Some early debug units use 13500000 Hz instead
# Retail should have 16666666 Hz
NV2A_CRYSTAL_FREQ = 16666666 # Hz

NV_PTIMER = 0x9000
NV_PTIMER_NUMERATOR = 0x200
NV_PTIMER_DENOMINATOR = 0x210
NV_PTIMER_TIME_0 = 0x400
NV_PTIMER_TIME_1 = 0x410

class Timer:

  def __init__(self, name):
    self.name = name
    self.base_ticks = 0
    self.last_ticks = None
    self.last_update = None

  def Adjust(self):
    self.base_ticks = self.GetTicks(False)

  def GetTicks(self, adjusted=True):
    return self.ticks - (self.base_ticks if adjusted else 0)

  def GetFrequency(self):
    return self.frequency

  def GetActualFrequency(self):
    return self.actual_frequency

  def UpdateFrequency(self):
    self.frequency = self.RetrieveFrequency()

  def UpdateTicks(self):
    update_time = time.time()
    self.ticks = self.RetrieveTicks()
    if self.last_ticks is not None and self.last_update_time is not None:
      self.actual_frequency = (self.ticks - self.last_ticks) / (update_time - self.last_update_time)
    self.last_ticks = self.ticks
    self.last_update_time = update_time

  def Print(self, flush=False):
    ticks = self.GetTicks()
    frequency = self.GetFrequency()
    actual_frequency = self.GetActualFrequency()
    #FIXME: Also show non-adjusted ticks somewhere?
    print("%-14s %12d [f: %12.1f Hz] = %5.1f s [f: %12.1f Hz]" % (self.name + ":", ticks, frequency, ticks / frequency, actual_frequency), flush=flush)


class KeTickCountTimer(Timer):

  def __init__(self):
    super(KeTickCountTimer, self).__init__("KeTickCount")

  def RetrieveFrequency(self):
    return 1000.0

  def RetrieveTicks(self):
    return memory.read_u32(ke.KeTickCount())

class RDTSCTimer(Timer):

  def __init__(self):
    super(RDTSCTimer, self).__init__("RDTSC")
    code = bytes([
      0x0F, 0x31,             # rdtsc
      0x8B, 0x4C, 0x24, 0x04, # mov    ecx,DWORD PTR [esp+0x4]
      0x89, 0x01,             # mov    DWORD PTR [ecx],eax
      0x89, 0x51, 0x04,       # mov    DWORD PTR [ecx+0x4],edx
      0xC2, 0x04, 0x00        # ret    0x4
    ])
    pointer = ke.MmAllocateContiguousMemory(len(code) + 8)
    memory.write(pointer, code)
    self.code = pointer
    self.data = pointer + len(code)

  def RetrieveFrequency(self):
    return 2200000000.0 / 3.0 # 733.3 MHz

  def RetrieveTicks(self):
    api.call(self.code, struct.pack("<I", self.data))
    return (memory.read_u32(self.data + 4) << 32) | memory.read_u32(self.data + 0)


class GPUTimer(Timer):

  def __init__(self):
    super(GPUTimer, self).__init__("GPU Timer")

  def RetrieveFrequency(self):
    self.GPUNumerator = nv2a.read_u32(NV_PTIMER + 0x200)
    self.GPUDenominator = nv2a.read_u32(NV_PTIMER + 0x210)

    self.nvpll_coeff = nv2a.read_u32(NV_PRAMDAC + NV_PRAMDAC_NVPLL_COEFF)
    self.mdiv = self.nvpll_coeff & NV_PRAMDAC_NVPLL_COEFF_MDIV
    self.ndiv = (self.nvpll_coeff & NV_PRAMDAC_NVPLL_COEFF_NDIV) >> 8
    self.pdiv = (self.nvpll_coeff & NV_PRAMDAC_NVPLL_COEFF_PDIV) >> 16
    self.GPUClockrate = (NV2A_CRYSTAL_FREQ * self.ndiv) / (1 << self.pdiv) / self.mdiv

    return self.GPUClockrate / (self.GPUNumerator / self.GPUDenominator)

  def RetrieveTicks(self):
    GPUTimer0 = nv2a.read_u32(NV_PTIMER + NV_PTIMER_TIME_0)
    GPUTimer1 = nv2a.read_u32(NV_PTIMER + NV_PTIMER_TIME_1)
    GPUTimer0dec = (GPUTimer0 >> 5) & 0x7FFFFFF
    GPUTimer1dec = (GPUTimer1 & 0x1FFFFFFF) << 27
    return GPUTimer1dec | GPUTimer0dec
    
  def Print(self):
    super().Print()
    print("  Core clockrate:  (    XTAL *   n) / (1 <<   p) /   m", flush=False)
    print("                   (%-8d * %3d) / (1 << %3d) / %3d = %.1f Hz" % (NV2A_CRYSTAL_FREQ, self.ndiv, self.pdiv, self.mdiv, self.GPUClockrate), flush=False)
    print("  Timer clockrate: %.1f / (%d / %d)" % (self.GPUClockrate, self.GPUNumerator, self.GPUDenominator), flush=False)


if __name__ == "__main__":

  timers = []

  timers.append(RDTSCTimer())
  timers.append(KeTickCountTimer())
  timers.append(GPUTimer())

  for timer in timers:
    timer.UpdateFrequency()
    timer.UpdateTicks()
    timer.Adjust() #FIXME: Make this optional

  while(True):

    for timer in timers:
      timer.UpdateTicks()
      timer.Print()

    print(flush=True)
    time.sleep(0.02)
