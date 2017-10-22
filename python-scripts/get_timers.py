#!/usr/bin/env python3

# Prints information about some of the Xbox timers

from xbox import *

import time

NV_PRAMDAC = 0x680000
NV_PRAMDAC_NVPLL_COEFF = 0x500
NV_PRAMDAC_NVPLL_COEFF_MDIV = 0x000000FF
NV_PRAMDAC_NVPLL_COEFF_NDIV = 0x0000FF00
NV_PRAMDAC_NVPLL_COEFF_PDIV = 0x00070000

# Some early debug units use 13500000 Hz instead
# Retail should have 16666666 Hz
NV2A_CRYSTAL_FREQ = 16666666 # Hz

NV_PTIMER = 0x9000
NV_PTIMER_TIME_0 = 0x400
NV_PTIMER_TIME_1 = 0x410
NV_PTIMER_NUMERATOR = 0x00000200
NV_PTIMER_DENOMINATOR = 0x00000210

if __name__ == "__main__":

  while(True):

    KeTickCount = memory.read_u32(ke.KeTickCount())
    KeTickCountInSeconds = KeTickCount / 1000

    GPUTimer0 = nv2a.read_u32(NV_PTIMER + NV_PTIMER_TIME_0)
    GPUTimer1 = nv2a.read_u32(NV_PTIMER + NV_PTIMER_TIME_1)
    GPUTimer0dec = (GPUTimer0 >> 5) & 0x7FFFFFF
    GPUTimer1dec = (GPUTimer1 & 0x1FFFFFFF) << 27
    GPUTimer = GPUTimer1dec | GPUTimer0dec
    
    GPUNumerator = nv2a.read_u32(NV_PTIMER + NV_PTIMER_NUMERATOR)
    GPUDenominator = nv2a.read_u32(NV_PTIMER + NV_PTIMER_DENOMINATOR)

    nvpll_coeff = nv2a.read_u32(NV_PRAMDAC + NV_PRAMDAC_NVPLL_COEFF)
    mdiv = nvpll_coeff & NV_PRAMDAC_NVPLL_COEFF_MDIV
    ndiv = (nvpll_coeff & NV_PRAMDAC_NVPLL_COEFF_NDIV) >> 8
    pdiv = (nvpll_coeff & NV_PRAMDAC_NVPLL_COEFF_PDIV) >> 16
    GPUClockrate = (NV2A_CRYSTAL_FREQ * ndiv) / (1 << pdiv) / mdiv
    GPUTimerClockrate = GPUClockrate / (GPUNumerator / GPUDenominator)
    GPUTimerInSeconds = GPUTimer / GPUTimerClockrate

    print("GPU Clockrate: (NV2A_CRYSTAL_FREQ * ndiv) / (1 << pdiv) / mdiv")
    print("GPU Clockrate: (" + str(NV2A_CRYSTAL_FREQ)+" * " + str(ndiv) + ") / (1 << " + str(pdiv) + ") / " + str(mdiv) + " = " + str(GPUClockrate) + " Hz")
    print("GPU Timer clockrate: " + str(GPUClockrate) + " / (" + str(GPUNumerator) + " / " + str(GPUDenominator) + ") = " + str(GPUTimerClockrate) + " Hz")
    print("GPU Timer: " + str(GPUTimer) + " [" + str(round(GPUTimerInSeconds)) + " s]")
    print("KeTickCount: " + str(KeTickCount) + " [" + str(round(KeTickCountInSeconds)) + " s]")
    print()
    
    time.sleep(0.02)
