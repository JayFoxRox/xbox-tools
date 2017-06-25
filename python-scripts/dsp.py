def dsp_read_u8(address):
  return read_u8(0xFE800000 + address)
def dsp_read_u16(address):
  return read_u16(0xFE800000 + address)
def dsp_read_u32(address):
  return read_u32(0xFE800000 + address)

def dsp_write_u8(address, value):
  write_u8(0xFE800000 + address, value)
def dsp_write_u16(address, value):
  write_u16(0xFE800000 + address, value)
def dsp_write_u32(address, value):
  write_u32(0xFE800000 + address, value)

def dsp_status(dump_buffers = False):
  def dump_mem(name, index):
    desc_addr = dsp_read_u32(0x2040 + index)
    print(name + " addr: 0x" + format(desc_addr, '08X')) # only the upper bits are used [aligned by 0x4000 bytes?!]
    desc_length = dsp_read_u32(0x20D4 + index)
    print(name + " length: " + str(desc_length)) # 16 bits only
    wav = export_wav("dsp-" + name + ".wav")
    desc_addr |= 0x80000000
    for i in range(0, desc_length):
      addr = read_u32(desc_addr + i * 8 + 0)
      flags = read_u16(desc_addr + i * 8 + 4)
      length = read_u16(desc_addr + i * 8 + 6)
      print(" Address: 0x" + format(addr, '08X') + "; Flags: 0x" + format(flags, '04X') + "; Length: " + str(length))
      assert(length == 0) # Shocker if this works!
      addr |= 0x80000000
      data = read(addr, length)
      wav.writeframes(data)
    wav.close()

  if False:
    dump_mem("EPF", 12)
    dump_mem("EPS", 8)
    dump_mem("GPF", 4)
    dump_mem("GPS", 0)


  NV_PAPU_VPVADDR   = 0x202C
  vpvaddr = dsp_read_u32(NV_PAPU_VPVADDR)
  NV_PAPU_VPSGEADDR = 0x2030
  vpsgeaddr = dsp_read_u32(NV_PAPU_VPSGEADDR)
  NV_PAPU_VPSSLADDR = 0x2034
  vpssladdr = dsp_read_u32(NV_PAPU_VPSSLADDR)
  NV_PAPU_VPHTADDR  = 0x2038
  vphtaddr = dsp_read_u32(NV_PAPU_VPHTADDR)
  NV_PAPU_VPHCADDR  = 0x203C
  vphcaddr = dsp_read_u32(NV_PAPU_VPHCADDR)
  NV_PAPU_GPSADDR   = 0x2040
  gpsaddr = dsp_read_u32(NV_PAPU_GPSADDR)
  NV_PAPU_GPFADDR   = 0x2044
  gpfaddr = dsp_read_u32(NV_PAPU_GPFADDR)
  NV_PAPU_EPSADDR   = 0x2048
  epsaddr = dsp_read_u32(NV_PAPU_EPSADDR)
  NV_PAPU_EPFADDR   = 0x204C
  epfaddr = dsp_read_u32(NV_PAPU_EPFADDR)

  print("NV_PAPU_VPVADDR: 0x" + format(vpvaddr, '08X'))
  print("NV_PAPU_VPSGEADDR: 0x" + format(vpsgeaddr, '08X'))
  print("NV_PAPU_VPSSLADDR: 0x" + format(vpssladdr, '08X'))
  print("NV_PAPU_VPHTADDR: 0x" + format(vphtaddr, '08X'))
  print("NV_PAPU_VPHCADDR: 0x" + format(vphcaddr, '08X'))
  print("NV_PAPU_GPSADDR: 0x" + format(gpsaddr, '08X'))
  print("NV_PAPU_GPFADDR: 0x" + format(gpfaddr, '08X'))
  print("NV_PAPU_EPSADDR: 0x" + format(epsaddr, '08X'))
  print("NV_PAPU_EPFADDR: 0x" + format(epfaddr, '08X'))
  print("")

  for i in range(0, 10):
    print("*NV_PAPU_VPVADDR[" + str(i) + "]: 0x" + format(read_u32(0x80000000 | vpvaddr+i*4), '08X'))
  print("")

  for i in range(0, 10):
    print("*NV_PAPU_VPSGEADDR[" + str(i) + "]: 0x" + format(read_u32(0x80000000 | vpsgeaddr+i*4), '08X'))
  print("")

  for i in range(0, 10):
    print("*NV_PAPU_VPSSLADDR[" + str(i) + "]: 0x" + format(read_u32(0x80000000 | vpssladdr+i*4), '08X'))
  print("")

  for i in range(0, 10):
    print("*NV_PAPU_VPHTADDR[" + str(i) + "]: 0x" + format(read_u32(0x80000000 | vphtaddr+i*4), '08X'))
  print("")

  for i in range(0, 10):
    print("*NV_PAPU_VPHCADDR[" + str(i) + "]: 0x" + format(read_u32(0x80000000 | vphcaddr+i*4), '08X'))
  print("")

  for i in range(0, 10):
    print("*NV_PAPU_GPSADDR[" + str(i) + "]: 0x" + format(read_u32(0x80000000 | gpsaddr+i*4), '08X'))
  print("")

  for i in range(0, 10):
    print("*NV_PAPU_GPFADDR[" + str(i) + "]: 0x" + format(read_u32(0x80000000 | gpfaddr+i*4), '08X'))
  print("")

  for i in range(0, 10):
    print("*NV_PAPU_EPSADDR[" + str(i) + "]: 0x" + format(read_u32(0x80000000 | epsaddr+i*4), '08X'))
  print("")

  for i in range(0, 10):
    print("*NV_PAPU_EPFADDR[" + str(i) + "]: 0x" + format(read_u32(0x80000000 | epfaddr+i*4), '08X'))
  print("")

  # Looks like EPF points to the AC97 buffer!
  epfaddr |= 0x80000000
  print("EP F..? address points to an entry which points to 0x" + format(read_u32(epfaddr), '08X'))

  vpsgeaddr |= 0x80000000
  def vp_sge(sge_handle):
    return read_u32(vpsgeaddr + sge_handle * 8)

  # Check out FIFOs

  NV_PAPU_GPOF0 = 0x3024 # 4 x 0x10 pitch
  NV_PAPU_GPIF0 = 0x3064 # 2 x 0x10 pitch

  NV_PAPU_EPOF0 = 0x4024 # 4 x 0x10 pitch
  NV_PAPU_EPIF0 = 0x4064 # 2 x 0x10 pitch

  def dump_fifo(name, addr):
    base = dsp_read_u32(addr + 0) & 0x00FFFF00
    end = dsp_read_u32(addr + 4) & 0x00FFFF00
    cur = dsp_read_u32(addr + 8) & 0x00FFFFFC
    print(name + " BASE=0x" + format(base, '08X') + " END=0x" + format(end, '08X') + " CUR=0x" + format(cur, '08X'))


  for i in range(0,4):
    dump_fifo("GPOF" + str(i), NV_PAPU_GPOF0 + i * 0x10)
  print("")
  for i in range(0,2):
    dump_fifo("GPIF" + str(i), NV_PAPU_GPIF0 + i * 0x10)
  print("")
  print("")
  for i in range(0,4):
    dump_fifo("EPOF" + str(i), NV_PAPU_EPOF0 + i * 0x10)
  print("")
  for i in range(0,2):
    dump_fifo("EPIF" + str(i), NV_PAPU_EPIF0 + i * 0x10)
  print("")


  # Dump voices
  NV_PAVS_SIZE = 0x80

  vpvaddr |= 0x80000000
  def dump_voice(voice_handle):
    def mask(value, field):
      # FIXME: Also support doing this with just a mask
      return (value >> field[1]) & ((1 << (field[0] - field[1] + 1)) - 1)
    
    voice_addr = vpvaddr + voice_handle * NV_PAVS_SIZE

    print("")
    print("Voice: 0x" + format(voice_handle, '04X'))

    NV_PAVS_VOICE_CFG_VBIN = 0x00

    NV_PAVS_VOICE_CFG_FMT = 0x04
    voice_fmt = read_u32(voice_addr + NV_PAVS_VOICE_CFG_FMT)
    # lots of unk stuff
    NV_PAVS_VOICE_CFG_FMT_SAMPLES_PER_BLOCK = (20,16)
    print("Samples per block: " + str(mask(voice_fmt, NV_PAVS_VOICE_CFG_FMT_SAMPLES_PER_BLOCK)))
    NV_PAVS_VOICE_CFG_FMT_MULTIPASS = (21,21)
    NV_PAVS_VOICE_CFG_FMT_LINKED_VOICE = (22,22)
    NV_PAVS_VOICE_CFG_FMT_PERSIST = (23,23)
    NV_PAVS_VOICE_CFG_FMT_DATA_TYPE = (24,24)
    is_stream = (mask(voice_fmt, NV_PAVS_VOICE_CFG_FMT_DATA_TYPE) > 0)
    print("Data type: " + ("stream" if is_stream else "buffer"))

    NV_PAVS_VOICE_CFG_FMT_LOOP = (25, 25)
    print("Loop: " + str(mask(voice_fmt, NV_PAVS_VOICE_CFG_FMT_LOOP)))

    # (26,26) ???

    NV_PAVS_VOICE_CFG_FMT_STEREO = (27,27)
    is_stereo = mask(voice_fmt, NV_PAVS_VOICE_CFG_FMT_STEREO) > 0
    print("Stereo: " + str(is_stereo))

    NV_PAVS_VOICE_CFG_FMT_SAMPLE_SIZE = (29,28)
    NV_PAVS_VOICE_CFG_FMT_SAMPLE_SIZE_values = [ 'U8', 'S16', 'S24', 'S32' ]
    sample_size = mask(voice_fmt, NV_PAVS_VOICE_CFG_FMT_SAMPLE_SIZE)
    print("Sample size: " + NV_PAVS_VOICE_CFG_FMT_SAMPLE_SIZE_values[sample_size])

    NV_PAVS_VOICE_CFG_FMT_CONTAINER_SIZE = (31,30)
    NV_PAVS_VOICE_CFG_FMT_CONTAINER_SIZE_values = ['B8', 'B16', 'ADPCM', 'B32']
    container_size_values = [1, 2, 4, 4]
    container_size = mask(voice_fmt, NV_PAVS_VOICE_CFG_FMT_CONTAINER_SIZE)
    print("Container size: " + NV_PAVS_VOICE_CFG_FMT_CONTAINER_SIZE_values[container_size])
    # lots of unk stuff

    NV_PAVS_VOICE_CFG_ENV0 = 0x08
    NV_PAVS_VOICE_CFG_ENVA = 0x0C
    NV_PAVS_VOICE_CFG_ENV1 = 0x10
    NV_PAVS_VOICE_CFG_ENVF = 0x14
    NV_PAVS_VOICE_CFG_MISC = 0x18
    NV_PAVS_VOICE_CFG_HRTF_TARGET = 0x1C
    NV_PAVS_VOICE_CUR_PSL_START = 0x20 # start of buffer?
    psl_start_ba = read_u32(voice_addr + NV_PAVS_VOICE_CUR_PSL_START) & 0xFFFFFF
    print("buffer start: 0x" + format(psl_start_ba, '08X'))
    NV_PAVS_VOICE_CUR_PSH_SAMPLE = 0x24 # loop start?
    cur_psh_sample = read_u32(voice_addr + NV_PAVS_VOICE_CUR_PSH_SAMPLE)
    print("loop start (samples?): " + format(cur_psh_sample & 0xFFFFFF, '08X'))
    NV_PAVS_VOICE_CUR_VOLA = 0x28
    NV_PAVS_VOICE_CUR_VOLB = 0x2C
    NV_PAVS_VOICE_CUR_VOLC = 0x30
    NV_PAVS_VOICE_CUR_ECNT = 0x34
    NV_PAVS_VOICE_CUR_PRD = 0x38
    NV_PAVS_VOICE_CUR_FCA = 0x3C
    NV_PAVS_VOICE_CUR_FCB = 0x40
    NV_PAVS_VOICE_CUR_FSA = 0x44
    NV_PAVS_VOICE_CUR_FSB = 0x48
    NV_PAVS_VOICE_CUR_FSC = 0x4C
    NV_PAVS_VOICE_PAR_LFO = 0x50
    NV_PAVS_VOICE_PAR_STATE = 0x54
    NV_PAVS_VOICE_PAR_STATE_PAUSED = (1 << 18)
    NV_PAVS_VOICE_PAR_STATE_ACTIVE_VOICE = (1 << 21)
    par_state = read_u32(voice_addr + NV_PAVS_VOICE_PAR_STATE)
    print("State[Paused]: " + str(par_state & NV_PAVS_VOICE_PAR_STATE_PAUSED > 0))
    print("State[Active]: " + str(par_state & NV_PAVS_VOICE_PAR_STATE_ACTIVE_VOICE > 0))

    NV_PAVS_VOICE_PAR_OFFSET = 0x58 # current playback offset
    par_offset = read_u32(voice_addr + NV_PAVS_VOICE_PAR_OFFSET) # Warning: Upper 8 bits will be 0xFF (?) on hw!
    print("current offset (samples?): 0x" + format(par_offset & 0xFFFFFF, '08X'))
    NV_PAVS_VOICE_PAR_NEXT = 0x5C # end of buffer?
    ebo = read_u32(voice_addr + NV_PAVS_VOICE_PAR_NEXT) & 0xFFFFFF
    print("end of buffer (samples): 0x" + format(ebo, '08X'))

    NV_PAVS_VOICE_TAR_VOLA = 0x60
    NV_PAVS_VOICE_TAR_VOLB = 0x64
    NV_PAVS_VOICE_TAR_VOLC = 0x68
    NV_PAVS_VOICE_TAR_LFO_ENV = 0x6C
    NV_PAVS_VOICE_TAR_LFO_MOD = 0x70
    NV_PAVS_VOICE_TAR_FCA = 0x74
    NV_PAVS_VOICE_TAR_FCB = 0x78

    NV_PAVS_VOICE_TAR_PITCH_LINK = 0x7c
    NV_PAVS_VOICE_TAR_PITCH_LINK_NEXT_VOICE_HANDLE = (15,0)
    NV_PAVS_VOICE_TAR_PITCH_LINK_PITCH = (31,16)

    tar_pitch_link = read_u32(voice_addr + NV_PAVS_VOICE_TAR_PITCH_LINK)
    pitch = mask(tar_pitch_link, NV_PAVS_VOICE_TAR_PITCH_LINK_PITCH)
    next_voice = mask(tar_pitch_link, NV_PAVS_VOICE_TAR_PITCH_LINK_NEXT_VOICE_HANDLE)

    # p=4096*log2(f/48000)
    # 2^(p/4096)*48000=f

    print("Pitch: 0x" + format(pitch, '04X'))

    # Get proper sign
    pitch = int.from_bytes(int.to_bytes(pitch, signed=False, byteorder='little', length=2), byteorder='little', signed=True)
    freq = 2 ** (pitch / 4096) * 48000

    print("Frequency: " + str(freq))

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
        data = read(paged, min(in_page, bytes))
        map_page(paged, mapped)

        bytes -= len(data)
        wav.writeframes(data)

        psl_start_ba_offset = 0
        psl_start_ba_page += 1
      wav.close()

    #Hack to test advancing in buffer:
    if False:
      write_u32(voice_addr + NV_PAVS_VOICE_PAR_OFFSET, ebo)

    print("Next voice: 0x" + format(next_voice, '04X'))
    return next_voice

  NV_PAPU_FEAV = 0x1118
  NV_PAPU_FEAV_VALUE = 0x0000FFFF
  NV_PAPU_FEAV_LST = 0x00030000
  NV_PAPU_FEAV_LST_values = ['INHERIT', '2D_TOP', '3D_TOP', 'MP_TOP']
  feav = dsp_read_u32(NV_PAPU_FEAV)
  active_voice = feav & NV_PAPU_FEAV_VALUE
  feav_lst = (feav & NV_PAPU_FEAV_LST) >> 16
  print("Active List: " + str(feav_lst) + " (" + NV_PAPU_FEAV_LST_values[feav_lst] + ")")

  NV_PAPU_TVL2D = 0x2054
  NV_PAPU_CVL2D = 0x2058
  top_voice = dsp_read_u32(NV_PAPU_TVL2D)

  print("Top voice: 0x" + format(top_voice, '04X'))

  next_voice = top_voice
  while next_voice != 0xFFFF:
    _next_voice = dump_voice(next_voice)
    if next_voice == _next_voice:
      print("Loop!\n")
      return
    next_voice = _next_voice

  #FIXME: Resume dumping..
