#!/usr/bin/env python3

from xbox import *

#FIXME: Move to fields, however, globals() has another context there >.<
def Field(offset_name, mask_name=None):
  offset_value = globals().get(offset_name)
  if offset_value == None:
    raise NameError(offset_name)
  if mask_name == None:
    mask_value = 0xFFFFFFFF
  else:
    mask_name = offset_name + '_' + mask_name
    mask_value = globals().get(mask_name)
    if mask_value == None:
      raise NameError(mask_name)
    mask_value = GetMask(mask_value)
  return(offset_value, mask_value)

def ReadVoiceField(voice, field_name, mask_name=None, comment=None, show=True):
  real_field_name = 'NV_PAVS_VOICE_' + field_name
  field = Field(real_field_name, mask_name)
  value = apu.ReadVoice(voice, *field)
  if show:
    mask_length = (field[1] >> ffs(field[1])).bit_length()
    if mask_length == 1:  #FIXME: If mask is 1 bit only, display bool
      value_str = str(value > 0)
    else:
      #FIXME: Format by mask length
      value_str = "0x" + format(value, 'X')
    #FIXME: Use decimal if asked to do so
    #FIXME: append comment if there is one
    print(field_name + (("." + mask_name) if mask_name != None else "") + ": " + value_str)
  return value


def ProcessStream(voice):
  ssla_count = ReadVoiceField(voice, 'CUR_PSL_START', 'SSLA_COUNT')
  ssla_base = ReadVoiceField(voice, 'CUR_PSL_START', 'SSLA_BASE')
  cso = ReadVoiceField(voice,'PAR_OFFSET', 'CSO')
  sslb_count = ReadVoiceField(voice, 'PAR_NEXT', 'SSLB_COUNT')
  sslb_base = ReadVoiceField(voice, 'PAR_NEXT', 'SSLB_BASE')

  #FIXME: More research.. this might be wrong
  #FIXME: Read internal memory to figure out where the SSL data is stored?
  #FIXME: Read VPSSLADDR as it stores sample data for SSL?

  pass

last_list = None
def ListVoices(voice, name):
  global last_list
  if name != last_list:
    print('Starting ' + name + ' list')
    last_list = name

  is_stream = ReadVoiceField(voice, 'CFG_FMT', 'DATA_TYPE', show=False) > 0

  # Enable this / modify this if you only want to show one type: buffers or streams
  if False:
    if not is_stream:
      next_voice = ReadVoiceField(voice, 'TAR_PITCH_LINK', 'NEXT_VOICE_HANDLE', show=False)
      return next_voice

  print("")
  print("Voice: 0x" + format(voice, '04X'))

  vbin = ReadVoiceField(voice, 'CFG_VBIN', show=False)
  # lots of unk stuff

  #FIXME: Don't print
  voice_fmt = ReadVoiceField(voice, 'CFG_FMT', show=False)

  samples_per_block = ReadVoiceField(voice, 'CFG_FMT', 'SAMPLES_PER_BLOCK')

  print("Data type: " + ("stream" if is_stream else "buffer"))


  loop = ReadVoiceField(voice, 'CFG_FMT', 'LOOP') > 0

  # (26,26) ???

  is_stereo = ReadVoiceField(voice, 'CFG_FMT', 'STEREO') > 0

  NV_PAVS_VOICE_CFG_FMT_SAMPLE_SIZE_values = [ 'U8', 'S16', 'S24', 'S32' ]
  sample_size = ReadVoiceField(voice, 'CFG_FMT', 'SAMPLE_SIZE', show=False)
  print("Sample size: " + NV_PAVS_VOICE_CFG_FMT_SAMPLE_SIZE_values[sample_size])

  NV_PAVS_VOICE_CFG_FMT_CONTAINER_SIZE_values = ['B8', 'B16', 'ADPCM', 'B32']
  container_size = ReadVoiceField(voice, 'CFG_FMT', 'CONTAINER_SIZE', show=False)
  print("Container size: " + NV_PAVS_VOICE_CFG_FMT_CONTAINER_SIZE_values[container_size])
  # lots of unk stuff

  paused = ReadVoiceField(voice, 'PAR_STATE', 'PAUSED')
  active = ReadVoiceField(voice, 'PAR_STATE', 'ACTIVE_VOICE')

  cur_vola = ReadVoiceField(voice, 'CUR_VOLA', show=False)
  cur_volb = ReadVoiceField(voice, 'CUR_VOLB', show=False)
  cur_volc = ReadVoiceField(voice, 'CUR_VOLC', show=False)

  tar_vola = ReadVoiceField(voice, 'TAR_VOLA', show=False)
  tar_volb = ReadVoiceField(voice, 'TAR_VOLB', show=False)
  tar_volc = ReadVoiceField(voice, 'TAR_VOLC', show=False)

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

  pitch = ReadVoiceField(voice, 'TAR_PITCH_LINK', 'PITCH')
  # Make sure our pitch is signed
  pitch = int.from_bytes(int.to_bytes(pitch, signed=False, byteorder='little', length=2), signed=True, byteorder='little')
  freq = apu.PitchToFrequency(pitch)
  print("Frequency: " + str(freq) + " Hz")

  # Envelopes

  def DumpEnvelope(prefix1, prefix2, reg):
    ReadVoiceField(voice, prefix1, reg + '_DELAYTIME')
    ReadVoiceField(voice, prefix1, reg + '_ATTACKRATE')
    ReadVoiceField(voice, prefix2, reg + '_HOLDTIME')
    ReadVoiceField(voice, prefix2, reg + '_DECAYRATE')
    ReadVoiceField(voice, prefix2, reg + '_SUSTAINLEVEL')

  # Envelope for volume
  print("Volume Envelope:")
  DumpEnvelope('CFG_ENV0', 'CFG_ENVA', 'EA')
  ReadVoiceField(voice, 'TAR_LFO_ENV', 'EA_RELEASERATE')
  ReadVoiceField(voice, 'PAR_STATE','EACUR')  
  ReadVoiceField(voice, 'CUR_ECNT','EACOUNT')

  # Envelope for pitch
  print("Pitch / Cutoff Envelope:")
  DumpEnvelope('CFG_ENV1', 'CFG_ENVF', 'EF')
  ReadVoiceField(voice, 'CFG_MISC', 'EF_RELEASERATE')
  ReadVoiceField(voice, 'PAR_STATE','EFCUR')
  ReadVoiceField(voice, 'CUR_ECNT','EFCOUNT')
  ReadVoiceField(voice, 'CFG_ENV0', 'EF_PITCHSCALE')
  ReadVoiceField(voice, 'CFG_ENV1', 'EF_FCSCALE')

  if is_stream:

    ProcessStream(voice)

  else:

    psl_start_ba = ReadVoiceField(voice, 'CUR_PSL_START','BA')
    cur_psh_sample = ReadVoiceField(voice, 'CUR_PSH_SAMPLE','LBO')
    par_offset = ReadVoiceField(voice, 'PAR_OFFSET','CBO') # Warning: Upper 8 bits will be 0xFF (?) on hw!
    ebo = ReadVoiceField(voice, 'PAR_NEXT','EBO')

    # FIXME: Move to apu.py with callbacks?
    def DumpVoiceBuffer(path):
      #FIXME: Respect samples per block
      #FIXME: Rewrite, this is overall pretty horrible
      channels = 2 if is_stereo else 1
      container_size_values = [1, 2, 4, 4]
      in_sample_size = container_size_values[container_size]
      fmt = 0x0011 if container_size == 2 else 0x0001
      wav = aci.export_wav(path, channels, in_sample_size, freq, fmt)

      samples = ebo + 1
      if fmt == 0x0011: # Check for ADPCM
        block_size = 36 * channels
        bytes = samples // 65 * block_size
      else:
        block_size = in_sample_size * channels
        bytes = samples * block_size

      data = apu.ReadSGE(psl_start_ba, bytes)
      wav.writeframes(data)

      wav.close()

    #FIXME: Make this an option
    if True:
      print("Dumping buffer")
      DumpVoiceBuffer("vp-buffer-" + format(psl_start_ba, '08X') + ".wav")

  next_voice = ReadVoiceField(voice, 'TAR_PITCH_LINK', 'NEXT_VOICE_HANDLE')
  return next_voice

apu.IterateVoiceLists(ListVoices)
