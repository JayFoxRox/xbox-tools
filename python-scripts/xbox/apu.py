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


def vp(dump_buffers = False):
  vpsgeaddr = read_u32(NV_PAPU_VPSGEADDR)
  vpsgeaddr |= 0x80000000
  def vp_sge(sge_handle):
    return memory.read_u32(vpsgeaddr + sge_handle * 8)

  # Dump voices

  vpvaddr = read_u32(NV_PAPU_VPVADDR)
  vpvaddr |= 0x80000000
  def dump_voice(voice_handle):
    def mask(value, field):
      # FIXME: Also support doing this with just a mask
      return (value >> field[1]) & ((1 << (field[0] - field[1] + 1)) - 1)
    
    voice_addr = vpvaddr + voice_handle * NV_PAVS_SIZE

    print("")
    print("Voice: 0x" + format(voice_handle, '04X'))


    vbin = memory.read_u32(voice_addr + NV_PAVS_VOICE_CFG_VBIN)
    voice_fmt = memory.read_u32(voice_addr + NV_PAVS_VOICE_CFG_FMT)
    # lots of unk stuff

    print("Samples per block: " + str(mask(voice_fmt, NV_PAVS_VOICE_CFG_FMT_SAMPLES_PER_BLOCK)))
    is_stream = (mask(voice_fmt, NV_PAVS_VOICE_CFG_FMT_DATA_TYPE) > 0)
    print("Data type: " + ("stream" if is_stream else "buffer"))


    print("Loop: " + str(mask(voice_fmt, NV_PAVS_VOICE_CFG_FMT_LOOP)))

    # (26,26) ???


    is_stereo = mask(voice_fmt, NV_PAVS_VOICE_CFG_FMT_STEREO) > 0
    print("Stereo: " + str(is_stereo))

    NV_PAVS_VOICE_CFG_FMT_SAMPLE_SIZE_values = [ 'U8', 'S16', 'S24', 'S32' ]
    sample_size = mask(voice_fmt, NV_PAVS_VOICE_CFG_FMT_SAMPLE_SIZE)
    print("Sample size: " + NV_PAVS_VOICE_CFG_FMT_SAMPLE_SIZE_values[sample_size])


    NV_PAVS_VOICE_CFG_FMT_CONTAINER_SIZE_values = ['B8', 'B16', 'ADPCM', 'B32']
    container_size_values = [1, 2, 4, 4]
    container_size = mask(voice_fmt, NV_PAVS_VOICE_CFG_FMT_CONTAINER_SIZE)
    print("Container size: " + NV_PAVS_VOICE_CFG_FMT_CONTAINER_SIZE_values[container_size])
    # lots of unk stuff

    psl_start_ba = memory.read_u32(voice_addr + NV_PAVS_VOICE_CUR_PSL_START) & 0xFFFFFF
    print("buffer start: 0x" + format(psl_start_ba, '08X'))

    cur_psh_sample = memory.read_u32(voice_addr + NV_PAVS_VOICE_CUR_PSH_SAMPLE)
    print("loop start (samples?): " + format(cur_psh_sample & 0xFFFFFF, '08X'))

    par_state = memory.read_u32(voice_addr + NV_PAVS_VOICE_PAR_STATE)
    print("State[Paused]: " + str(par_state & NV_PAVS_VOICE_PAR_STATE_PAUSED > 0))
    print("State[Active]: " + str(par_state & NV_PAVS_VOICE_PAR_STATE_ACTIVE_VOICE > 0))

    par_offset = memory.read_u32(voice_addr + NV_PAVS_VOICE_PAR_OFFSET) # Warning: Upper 8 bits will be 0xFF (?) on hw!
    print("current offset (samples?): 0x" + format(par_offset & 0xFFFFFF, '08X'))

    ebo = memory.read_u32(voice_addr + NV_PAVS_VOICE_PAR_NEXT) & 0xFFFFFF
    print("end of buffer (samples): 0x" + format(ebo, '08X'))

    cur_vola = memory.read_u32(voice_addr + NV_PAVS_VOICE_CUR_VOLA)
    cur_volb = memory.read_u32(voice_addr + NV_PAVS_VOICE_CUR_VOLB)
    cur_volc = memory.read_u32(voice_addr + NV_PAVS_VOICE_CUR_VOLC)

    tar_vola = memory.read_u32(voice_addr + NV_PAVS_VOICE_TAR_VOLA)
    tar_volb = memory.read_u32(voice_addr + NV_PAVS_VOICE_TAR_VOLB)
    tar_volc = memory.read_u32(voice_addr + NV_PAVS_VOICE_TAR_VOLC)

    bins_data = []
    bins_data.append(vbin & 0x1F) # 0
    bins_data.append((vbin >> 5) & 0x1F) # 1
    bins_data.append((vbin >> 10) & 0x1F) # 2
    # (15,15) ?
    bins_data.append((vbin >> 16) & 0x1F) # 3
    bins_data.append((vbin >> 21) & 0x1F) # 4
    bins_data.append((vbin >> 26) & 0x1F) # 5
    # (31,31) ?
    bins_data.append(voice_fmt & 0x1F) # 6
    bins_data.append((voice_fmt >> 5) & 0x1F) # 7

    def decode_volumes(a, b, c):
      data = []
      data.append((a >> 4) & 0xFFF) # 0
      data.append((a >> 20) & 0xFFF) # 1
      data.append((b >> 4) & 0xFFF) # 2
      data.append((b >> 20) & 0xFFF) # 3
      data.append((c >> 4) & 0xFFF) # 4
      data.append((c >> 20) & 0xFFF) # 5
      data.append(((c & 0xF) << 8) | ((b & 0xF) << 4) | (a & 0xF)) # 6
      data.append(((c >> 8) & 0xF00) | ((b >> 12) & 0xF0) | ((a >> 16) & 0xF)) # 7
      return data
    cur_vols_data = decode_volumes(cur_vola, cur_volb, cur_volc)
    tar_vols_data = decode_volumes(tar_vola, tar_volb, tar_volc)

    #assert(False) #FIXME: Untested!

    bins = ""
    cur_vols = ""
    tar_vols = ""
    for i in range(0, 8):
      bins += "  " + ("0x" + format(bins_data[i], 'X')).ljust(5)
      cur_vols += "  0x" + format(cur_vols_data[i], '03X')
      tar_vols += "  0x" + format(tar_vols_data[i], '03X')
    print("VBIN   " + bins)
    print("CUR_VOL" + cur_vols)
    print("TAR_VOL" + tar_vols)

    tar_pitch_link = memory.read_u32(voice_addr + NV_PAVS_VOICE_TAR_PITCH_LINK)
    pitch = mask(tar_pitch_link, NV_PAVS_VOICE_TAR_PITCH_LINK_PITCH)
    next_voice = mask(tar_pitch_link, NV_PAVS_VOICE_TAR_PITCH_LINK_NEXT_VOICE_HANDLE)

    # p=4096*log2(f/48000)
    # 2^(p/4096)*48000=f

    # Get proper sign
    signed_pitch = int.from_bytes(int.to_bytes(pitch, signed=False, byteorder='little', length=2), byteorder='little', signed=True)
    freq = 2 ** (signed_pitch / 4096) * 48000

    print("Pitch: 0x" + format(pitch, '04X') + " (" + str(freq) + "Hz)")

    psl_start_ba_page = psl_start_ba >> 12
    psl_start_ba_offset = psl_start_ba & 0xFFF

    if dump_buffers and not is_stream: #FIXME: Should only be done while the CPU is paused / no hw is accessing said buffer
      channels = 2 if is_stereo else 1
      in_sample_size = container_size_values[container_size]
      fmt = 0x0011 if container_size == 2 else 0x0001
      wav = export_wav("buf" + format(psl_start_ba, '08X') + ".wav", channels, in_sample_size, freq, fmt)

      samples = ebo + 1
      if fmt == 0x0011: # Check for ADPCM
        #FIXME: Is this correct?
        #FIXME: Rounding issues?
        block_size =  0x24 * channels
        bytes = samples // 64 * block_size
      else:
        block_size = in_sample_size * channels
        bytes = samples * block_size

      while bytes > 0:
        page_base = vp_sge(psl_start_ba_page)
        paged = page_base + psl_start_ba_offset
        in_page = 0x1000 - (psl_start_ba_offset & 0xFFF)

        print("Dumping page " + format(paged, '08X') + " (" + str(bytes) + " bytes left)")
        paged |= 0x80000000
        mapped = map_page(paged, True)  
        data = memory.read(paged, min(in_page, bytes))
        map_page(paged, mapped)

        bytes -= len(data)
        wav.writeframes(data)

        psl_start_ba_offset = 0
        psl_start_ba_page += 1
      wav.close()

    #Hack to test advancing in buffer:
    if False:
      memory.write_u32(voice_addr + NV_PAVS_VOICE_PAR_OFFSET, ebo)

    print("Next voice: 0x" + format(next_voice, '04X'))
    return next_voice

  # This dumps information about the active voice, usually not of interest
  if False:
    NV_PAPU_FEAV_LST_values = ['INHERIT', '2D_TOP', '3D_TOP', 'MP_TOP']
    feav = read_u32(NV_PAPU_FEAV)
    active_voice = feav & NV_PAPU_FEAV_VALUE
    feav_lst = (feav & NV_PAPU_FEAV_LST) >> 16
    print("Active List: " + str(feav_lst) + " (" + NV_PAPU_FEAV_LST_values[feav_lst] + ")")

  def dump_voices(name, addr):
    top_voice = read_u32(addr)
    print(name + " Top voice: 0x" + format(top_voice, '04X'))
    next_voice = top_voice
    while next_voice != 0xFFFF:
      _next_voice = dump_voice(next_voice)
      if next_voice == _next_voice:
        assert(False)
        return
      next_voice = _next_voice

  dump_voices("2D", NV_PAPU_TVL2D)
  print("")
  dump_voices("3D", NV_PAPU_TVL3D)
  print("")
  dump_voices("MP", NV_PAPU_TVLMP)
