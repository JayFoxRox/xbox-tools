from . import *
from . import memory
from .apu_regs import *
from .aci import export_wav
import math

def read_u8(address):
  return memory.read_u8(0xFE800000 + address)
def read_u16(address):
  return memory.read_u16(0xFE800000 + address)
def read_u32(address):
  return memory.read_u32(0xFE800000 + address)

def write_u8(address, value):
  memory.write_u8(0xFE800000 + address, value)
def write_u16(address, value):
  memory.write_u16(0xFE800000 + address, value)
def write_u32(address, value):
  memory.write_u32(0xFE800000 + address, value)


def mem():
  def dump_mem(name, index):
    desc_addr = read_u32(0x2040 + index)
    print(name + " addr: 0x" + format(desc_addr, '08X')) # only the upper bits are used [aligned by 0x4000 bytes?!]
    desc_length = read_u32(0x20D4 + index)
    print(name + " length: " + str(desc_length)) # 16 bits only
    wav = export_wav("dsp-" + name + ".wav")
    desc_addr |= 0x80000000
    for i in range(0, desc_length):
      addr = memory.read_u32(desc_addr + i * 8 + 0)

      print(" Address: 0x" + format(addr, '08X') + "; Flags: 0x" + format(flags, '04X') + "; Length: " + str(length))

      addr |= 0x80000000
      data = memory.read(addr, length)
      wav.writeframes(data)
    wav.close()

  if False:
    dump_mem("EPF", 12)
    dump_mem("EPS", 8)
    dump_mem("GPF", 4)
    dump_mem("GPS", 0)

  vpvaddr = read_u32(NV_PAPU_VPVADDR)
  vpsgeaddr = read_u32(NV_PAPU_VPSGEADDR)
  vpssladdr = read_u32(NV_PAPU_VPSSLADDR)
  vphtaddr = read_u32(NV_PAPU_VPHTADDR)
  vphcaddr = read_u32(NV_PAPU_VPHCADDR)
  gpsaddr = read_u32(NV_PAPU_GPSADDR)
  gpfaddr = read_u32(NV_PAPU_GPFADDR)
  epsaddr = read_u32(NV_PAPU_EPSADDR)
  epfaddr = read_u32(NV_PAPU_EPFADDR)

  def dump_mem_map(name, addr, sge_count = 0):
    print(name + ": 0x" + format(addr, '08X'))
    if sge_count == 0:
      return
    length = 0
    for i in range(0, sge_count + 1): # Last one is just to dump out data
      if i < sge_count:
        data_addr = memory.read_u32(0x80000000 | addr + i * 8 + 0)
        data_flags = memory.read_u16(0x80000000 | addr + i * 8 + 4)
        data_length = memory.read_u16(0x80000000 | addr + i * 8 + 6)
      addr_from = i * 0x1000
      # Be smart and combine multiple entries into one..
      if (i > 0 and (data_addr != last_data_addr + 0x1000 or data_flags != last_data_flags)) or i == sge_count:
        print("  0x" + format(addr_from - length, '06X') + " - 0x" + format(addr_from - 1, '06X') + " maps to RAM 0x" + format(last_data_addr - length, '08X') + " - 0x" + format(last_data_addr + 0xFFF, '08X') + " flags: 0x" + format(last_data_flags, '04X'))
        length = 0
      length += 0x1000
      assert(data_flags == 0)
      assert(data_length == 0) #FIXME: This should be enabled, but the last entries are sometimes bogus?!
      last_data_addr = data_addr
      last_data_flags = data_flags

  gpsmaxsge = read_u32(NV_PAPU_GPSMAXSGE) & 0xFFFF
  gpfmaxsge = read_u32(NV_PAPU_GPFMAXSGE) & 0xFFFF
  epsmaxsge = read_u32(NV_PAPU_EPSMAXSGE) & 0xFFFF
  epfmaxsge = read_u32(NV_PAPU_EPFMAXSGE) & 0xFFFF

  dump_mem_map("NV_PAPU_VPVADDR", vpvaddr)
  dump_mem_map("NV_PAPU_VPSGEADDR", vpsgeaddr, 0x1000 // 8)
  dump_mem_map("NV_PAPU_VPSSLADDR", vpssladdr)
  dump_mem_map("NV_PAPU_VPHTADDR", vphtaddr)
  dump_mem_map("NV_PAPU_VPHCADDR", vphcaddr)
  # This looks like an off-by-one in the MS code?!
  # (Should be MAXSGE+1 but then we get bogus data)
  #FIXME: Test on hardware
  dump_mem_map("NV_PAPU_GPSADDR", gpsaddr, gpsmaxsge)
  dump_mem_map("NV_PAPU_GPFADDR", gpfaddr, gpfmaxsge)
  dump_mem_map("NV_PAPU_EPSADDR", epsaddr, epsmaxsge)
  dump_mem_map("NV_PAPU_EPFADDR", epfaddr, epfmaxsge)


#FIXME: Take argument for max_sge
def read_mem(sge_addr, base, length):
  #FIXME: Also make work with odd data  
  data = bytearray()
  address = base
  remaining = length
  while remaining > 0:
    page = address // 0x1000
    offset = address % 0x1000
    data_addr = memory.read_u32(0x80000000 | sge_addr + page * 8 + 0)
    data += memory.read(0x80000000 | data_addr + offset, min(remaining, 0x1000 - offset))
    remaining = length - len(data)
  return data

def write_mem(sge_addr, base, data):
  #FIXME: Also make work with odd data
  assert(base & 0xFFF == 0)
  first_sge_idx = base // 0x1000
  for idx in range(first_sge_idx, first_sge_idx + len(data) // 0x1000 + 1):
    data_addr = memory.read_u32(0x80000000 | sge_addr + idx * 8 + 0)
    memory.write(0x80000000 | data_addr, data[0x1000 * idx:0x1000 * idx + 0x1000])

def fifos(dump = False):
  def dump_fifo(name, addr, sge_addr):
    base = read_u32(addr + 0) & 0x00FFFF00
    end = read_u32(addr + 4) & 0x00FFFF00
    cur = read_u32(addr + 8) & 0x00FFFFFC
    print(name + " BASE=0x" + format(base, '08X') + " END=0x" + format(end, '08X') + " CUR=0x" + format(cur, '08X'))
    if dump:
      data = read_mem(sge_addr, base, end - base)
      wav = export_wav(name + ".wav")
      wav.writeframes(data)
      wav.close()

  # Check out FIFOs

  gpfaddr = read_u32(NV_PAPU_GPFADDR)
  for i in range(0,4):
    dump_fifo("GPOF" + str(i), NV_PAPU_GPOF0 + i * 0x10, gpfaddr)
  print("")
  for i in range(0,2):
    dump_fifo("GPIF" + str(i), NV_PAPU_GPIF0 + i * 0x10, gpfaddr)
  print("")

  epfaddr = read_u32(NV_PAPU_EPFADDR)
  for i in range(0,4):
    dump_fifo("EPOF" + str(i), NV_PAPU_EPOF0 + i * 0x10, epfaddr)
  print("")
  for i in range(0,2):
    dump_fifo("EPIF" + str(i), NV_PAPU_EPIF0 + i * 0x10, epfaddr)
  print("")

#FIXME: Keep padding byte there and instead provide conversion routines
def read_dsp_mem(addr, length):
  assert(length % 4 == 0)
  data = bytearray()
  if True:
    # FIXME: This code path might not work in XQEMU!
    data = memory.read(0xFE800000 + addr, length)
  else:
    for i in range(0, length // 4):
      value = read_u32(addr + i * 4)
      data += int.to_bytes(value & 0xFFFFFF, length=4, byteorder='little')
  return bytes(data)

def write_dsp_mem(addr, data):
  assert(len(data) % 4 == 0)
  for i in range(0, len(data) // 4):
    value = int.from_bytes(data[i*4:i*4+3], byteorder='little', signed=False)
    write_u32(addr + i * 4, value)

def gp():
  gpsaddr = read_u32(NV_PAPU_GPSADDR)

  data = bytearray()
  seconds = 2
  start = time.time()
  duration = 0

  #FIXME: Hack for performance
  addr = 0x9000 # See http://xboxdevwiki.net/APU#Usage_in_DirectSound for the channel order
  data_addr = memory.read_u32(0x80000000 | gpsaddr + (addr // 0x1000) * 8 + 0)
  for i in range(0, seconds * 48000 // 0x20):
    #FIXME: Improve performance of the following:
    #data += read_mem(gpsaddr, 0x8000, 256)

    data += memory.read(0x80000000 | data_addr + (addr % 0x1000) + (0x20 * 4 * i) % 0x800, 0x20 * 4)
    while duration < i * 0x20 / 48000:
      duration = time.time() - start
  data = to_dsp(data)

  print("Took " + str(duration * 1000.0) + "ms. Expected " + str(seconds * 1000.0) + "ms")

  wav = export_wav("GP-outmaybemaybenot.wav", channels=1, sample_width=3)
  wav.writeframes(data)
  wav.close()

  # Dump out MIXBUF [should be part of VP functions imo]
  #FIXME: Support dumping multiple bins at once?
  def dump_bin(index, seconds=2):
    # MIXBUF is 0x400 = 32 bins * 0x20 words which contain 48kHz 24-bit PCM
    data = bytearray()

    start = time.time()
    duration = 0
    for i in range(0, seconds * 48000 // 0x20):
      data += read_dsp_mem(NV_PAPU_GPMIXBUF + index * 0x20 * 4, 0x20 * 4)
      while duration < i * 0x20 / 48000:
        duration = time.time() - start
    data = to_dsp(data)
    print("Took " + str(duration * 1000.0) + "ms. Expected " + str(seconds * 1000.0) + "ms")

    wav = export_wav("GP-MIXBUF" + str(index) + ".wav", channels=1, sample_width=3)
    wav.writeframes(data)
    wav.close()

  hook_code = True

  if hook_code:

    #FIXME: Turn off GP DSP
    write_u32(NV_PAPU_GPRST, NV_PAPU_GPRST_GPRST)

    code_data = from_dsp(load_dsp_code("a56.out"))
    code_backup = read_dsp_mem(NV_PAPU_GPPMEM, len(code_data))
    scratch_backup = read_mem(gpsaddr, 0, len(code_data))
    write_dsp_mem(NV_PAPU_GPPMEM, code_data)
    write_mem(gpsaddr, 0, code_data)
    print("Patched code!")

    # Re-Enable the GP DSP
    write_u32(NV_PAPU_GPRST, NV_PAPU_GPRST_GPRST | NV_PAPU_GPRST_GPDSPRST)
    
  if True:
    print("Audio sniffing")
    # memory.read MIXBUF even while GP DSP is off (Works pretty good)
    print(read_u32(NV_PAPU_GPXMEM + 0) & 0xFFFFFF)
    dump_bin(0)
    print(read_u32(NV_PAPU_GPXMEM + 0) & 0xFFFFFF)
    dump_bin(1)
    print(read_u32(NV_PAPU_GPXMEM + 0) & 0xFFFFFF)
  else:
    print("Audio injection")
    # memory.write GP output scratch space while GP DSP is off (Does not work too good yet)
    addr = 0x8000 # See http://xboxdevwiki.net/APU#Usage_in_DirectSound for the channel order
    data_addr = memory.read_u32(0x80000000 | gpsaddr + (addr // 0x1000) * 8 + 0)
    data = bytearray()
    for i in range(0, seconds * 48000 // 0x20):
      chunk = bytearray()
      for j in range(0, 0x20):
        t = (i * 0x20 + j) / 48000
        chunk += int.to_bytes(int(0x1FFFFF * math.sin(t * math.pi * 2 * 500)), signed=True, length=3, byteorder='little') + bytes([0])
      data += chunk
      while duration < i * 0x20 / 48000:
        duration = time.time() - start
      assert(len(chunk) == 0x20 * 4)
      memory.write(0x80000000 | data_addr + (addr % 0x1000) + (0x20 * 4 * i) % 0x800, chunk)
    data = to_dsp(data)
    print("Took " + str(duration * 1000.0) + "ms. Expected " + str(seconds * 1000.0) + "ms")
    wav = export_wav("GP-injected.wav", channels=1, sample_width=3)
    wav.writeframes(data)
    wav.close()

  if hook_code:
    # Check if we ran the correct code
    code_verify = read_dsp_mem(NV_PAPU_GPPMEM, len(code_data))
    if code_verify != code_data:
      print("Oops! Code was not written successfully!")

    # Resume normal DSP operation
    write_u32(NV_PAPU_GPRST, NV_PAPU_GPRST_GPRST)
    write_dsp_mem(NV_PAPU_GPPMEM, code_backup)
    write_mem(gpsaddr, 0, scratch_backup)
    print("Recovered!")
    write_u32(NV_PAPU_GPRST, NV_PAPU_GPRST_GPRST | NV_PAPU_GPRST_GPDSPRST)

  # Dump GP Memory (aside from MIXBUF)

  wav = export_wav("GP-XMEM.wav")
  data = read_dsp_mem(NV_PAPU_GPXMEM, 0x1000 * 4)
  wav.writeframes(data)
  wav.close()
  wav = export_wav("GP-YMEM.wav")
  data = read_dsp_mem(NV_PAPU_GPYMEM, 0x800 * 4)
  wav.writeframes(data)
  wav.close()
  wav = export_wav("GP-PMEM.wav")
  data = read_dsp_mem(NV_PAPU_GPPMEM, 0x1000 * 4)
  wav.writeframes(data)
  wav.close()

def InvalidateCache(offset = None):
  pass #FIXME: Auto invalidate on writes near offset with apu functions

def RetrievePointer(register):
  #FIXME: Cache these values!
  return read_u32(register)

def ReadSSL(offset, length):
  pass

def ReadSGE(offset, length):
  vpsgeaddr = RetrievePointer(NV_PAPU_VPSGEADDR)
  def vp_sge(sge_handle):
    return memory.read_u32(vpsgeaddr + sge_handle * 8, True)
  out = bytearray()
  while length > 0:
    page_base = vp_sge(offset // 0x1000)
    paged = page_base + offset % 1000
    in_page = 0x1000 - (offset % 0x1000)
    # FIXME: Somehow handle this permission stuff differently
    mapped = map_page(0x80000000 | paged, True)  
    data = memory.read(paged, min(in_page, length), True)
    map_page(0x80000000 | paged, mapped)
    out += data
    length -= len(data)
  return bytes(out)

def ReadVoice(voice_handle, field_offset, field_mask):
  vpvaddr = RetrievePointer(NV_PAPU_VPVADDR) #FIXME: Pass as string so we can look it up in a cache more easily 'NV_PAPU_VPVADDR'
  value = memory.read_u32(vpvaddr + voice_handle * NV_PAVS_SIZE + field_offset, True); # FIXME: Physical address
  return GetMasked(value, field_mask)

def WriteVoice(voice_handle):
  assert(False) # FIXME

# This dumps information about the active voice, usually not of interest
if False:
  NV_PAPU_FEAV_LST_values = ['INHERIT', '2D_TOP', '3D_TOP', 'MP_TOP']
  feav = read_u32(NV_PAPU_FEAV)
  active_voice = feav & NV_PAPU_FEAV_VALUE
  feav_lst = (feav & NV_PAPU_FEAV_LST) >> 16
  print("Active List: " + str(feav_lst) + " (" + NV_PAPU_FEAV_LST_values[feav_lst] + ")")

# p = 4096*log2(f/48000)
def PitchToFrequency(pitch):
  # Get proper sign
  signed_pitch = int.from_bytes(int.to_bytes(pitch, signed=False, byteorder='little', length=2), byteorder='little', signed=True)
  return 2 ** (signed_pitch / 4096) * 48000

# f = 2^(p/4096)*48000
def FrequencyToPitch(frequency):
  assert(False) # FIXME

#FIXME: Take a voice_handle as argument instead
def IterateVoices(addr, callback, name=None):
  top_voice = read_u32(addr)
  # print(name + " Top voice: 0x" + format(top_voice, '04X'))
  next_voice = top_voice
  while next_voice != 0xFFFF:
    _next_voice = callback(next_voice, name)
    if next_voice == _next_voice:
      assert(False)
      return
    next_voice = _next_voice

def IterateVoiceLists(callback):
  IterateVoices(NV_PAPU_TVL2D, callback, name="2D")
  IterateVoices(NV_PAPU_TVL3D, callback, name="3D")
  IterateVoices(NV_PAPU_TVLMP, callback, name="MP")
