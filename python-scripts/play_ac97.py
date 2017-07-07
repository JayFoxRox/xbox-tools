#!/usr/bin/env python3

# A standalone AC97 audio player, based on XAudio from OpenXDK
# The interrupt related code has been removed as it's currently not supported.

from xbox import *

import sys
import time
import wave

pcmDescriptors = 0
spdifDescriptors = 0
nextDescriptor = 0

def XAudioPlay():
  #aci.write_u32(0x118, 0x1D000000) # PCM out - run, allow interrupts
  #aci.write_u32(0x178, 0x1D000000) # SPDIF out - run, allow interrupts
  aci.write_u32(0x118, 0x01000000) # PCM out - run
  aci.write_u32(0x178, 0x01000000) # SPDIF out - run

def XAudioPause():
  #aci.write_u32(0x118, 0x1C000000) # PCM out - PAUSE, allow interrupts
  #aci.write_u32(0x178, 0x1C000000) # SPDIF out - PAUSE, allow interrupts
  aci.write_u32(0x118, 0x00000000) # PCM out - PAUSE
  aci.write_u32(0x178, 0x00000000) # SPDIF out - PAUSE

# This is the function you should call when you want to give the
# audio chip some more data.  If you have registered a callback, it
# should call this method.  If you are providing the samples manually,
# you need to make sure you call this function often enough so the

# chip doesn't run out of data
def XAudioProvideSamples(address, length, final = False):
  global pcmDescriptors
  global spdifDescriptors
  global nextDescriptor

  bufferControl = 0

  if final:
    bufferControl |= 0x4000 # b14=1=last in stream
  if False:
    bufferControl |= 0x8000 # b15=1=issue IRQ on completion

  write_u32(pcmDescriptors + nextDescriptor * 8 + 0, ke.MmGetPhysicalAddress(address))
  write_u16(pcmDescriptors + nextDescriptor * 8 + 4, length)
  write_u16(pcmDescriptors + nextDescriptor * 8 + 6, bufferControl)
  aci.write_u8(0x115, nextDescriptor) # set last active PCM descriptor

  write_u32(spdifDescriptors + nextDescriptor * 8 + 0, ke.MmGetPhysicalAddress(address))
  write_u16(spdifDescriptors + nextDescriptor * 8 + 4, length)
  write_u16(spdifDescriptors + nextDescriptor * 8 + 6, bufferControl)
  aci.write_u8(0x175, nextDescriptor) # set last active SPDIF descriptor

  # increment to the next buffer descriptor (rolling around to 0 once you get to 31)
  nextDescriptor = (nextDescriptor + 1) % 32

def XAudioInit():
  global pcmDescriptors
  global spdifDescriptors

  # perform a cold reset
  tmp = aci.read_u32(0x12C)
  aci.write_u32(0x12C, tmp & 0xFFFFFFFD)
  time.sleep(0.1)
  aci.write_u32(0x12C, tmp | 2)
  
  # wait until the chip is finished resetting...
  while not aci.read_u32(0x130) & 0x100:
    pass

  # clear all interrupts
  aci.write_u8(0x116, 0xFF)
  aci.write_u8(0x176, 0xFF)

  # According to OpenXDK code, alignment for these should be 8, BUT..
  # ..I don't want it across 2 pages (for safety)
  pcmDescriptors = ke.MmAllocateContiguousMemory(32 * 8)
  spdifDescriptors = ke.MmAllocateContiguousMemory(32 * 8)

  # Clear the descriptors
  write(pcmDescriptors, [0] * 32 * 8)
  write(spdifDescriptors, [0] * 32 * 8)
  print("PCM desc is v 0x" + format(pcmDescriptors, '08X'))
  print("PCM desc is p 0x" + format(ke.MmGetPhysicalAddress(pcmDescriptors), '08X'))

  # Tell the audio chip where it should look for the descriptors
  aci.write_u32(0x100, 0) # no PCM input
  aci.write_u32(0x110, ke.MmGetPhysicalAddress(pcmDescriptors)) # PCM
  aci.write_u32(0x170, ke.MmGetPhysicalAddress(spdifDescriptors)) # SPDIF

  # default to being silent...
  XAudioPause()
  
  # Register our ISR
  #AUDIO_IRQ = 6
  #irql_address = malloc(1)
  #vector = HalGetInterruptVector(AUDIO_IRQ, irql_address)
  #KeInitializeDpc(&DPCObject,&DPC,NULL)
  #KeInitializeInterrupt(&InterruptObject, &ISR, NULL, vector, read_u8(irql_address), LevelSensitive, FALSE)
  #KeConnectInterrupt(&InterruptObject)

def main():
  wav = wave.open(sys.argv[1], 'rb')

  # This code currently only supports signed 16-bit stereo PCM at 48000 Hz
  assert(wav.getnchannels() == 2)
  assert(wav.getsampwidth() == 2)
  assert(wav.getframerate() == 48000)

  # Initialize audio
  XAudioInit()
  print("Audio initialized!")

  # Don't use more than 32 buffers.. or you will overwrite the beginning
  while True:
    data = wav.readframes(0xFFFF // 2)
    if len(data) == 0:
      break
    address = ke.MmAllocateContiguousMemory(len(data))
    print("Allocated " + str(len(data)) + " bytes")
    write(address, data)
    XAudioProvideSamples(address, len(data) // 2)
    print("Next buffer")

  print("Starting audio playback!")
  XAudioPlay()

if __name__ == '__main__':
    main()
