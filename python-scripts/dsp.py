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

def dsp_status(dump_buffers = True):
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

	NV_PAPU_VPSGEADDR = 0x2030
	vpsgeaddr = dsp_read_u32(NV_PAPU_VPSGEADDR)
	print("Voices SGE stored at 0x" + format(vpsgeaddr, '08X'))
	vpsgeaddr |= 0x80000000
	def vp_sge(sge_handle):
		return read_u32(vpsgeaddr + sge_handle * 8)

	# Dump voices
	NV_PAPU_VPVADDR = 0x202C
	NV_PAVS_SIZE = 0x80

	vpvaddr = dsp_read_u32(NV_PAPU_VPVADDR)
	print("Voices stored at 0x" + format(vpvaddr, '08X'))
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
		print("Data type: " + ("stream" if mask(voice_fmt, NV_PAVS_VOICE_CFG_FMT_DATA_TYPE) else "buffer"))
		NV_PAVS_VOICE_CFG_FMT_LOOP = (25, 25)
		print("Loop: " + str(mask(voice_fmt, NV_PAVS_VOICE_CFG_FMT_LOOP)))
		# ???
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
		print("loop start (samples?): " + format(read_u32(voice_addr + NV_PAVS_VOICE_CUR_PSH_SAMPLE), '08X'))
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
		print("current offset (samples?): 0x" + format(read_u32(voice_addr + NV_PAVS_VOICE_PAR_OFFSET), '08X'))
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

		if dump_buffers: #FIXME: Should only be done while the CPU is paused / no hw is accessing said buffer
			channels = 2 if is_stereo else 1
			in_sample_size = container_size_values[container_size]
			fmt = 0x0069 if container_size == 2 else 0x0001
			wav = export_wav("buf" + format(psl_start_ba, '08X') + ".wav", channels, in_sample_size, freq, fmt)
			samples = ebo + 1
			while samples > 0:
				page_base = vp_sge(psl_start_ba_page)
				paged = page_base + psl_start_ba_offset
				in_page = 0x1000 - (psl_start_ba_offset & 0xFFF)

				block_size = in_sample_size * channels

				print("Dumping page " + format(paged, '08X') + " (" + str(samples) + " samples left)")
				paged |= 0x80000000
				mapped = map_page(paged, True)	
				data = read(paged, min(in_page, samples * block_size))
				map_page(paged, mapped)

				samples -= len(data) // block_size
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

