import sys
if not "" in sys.path:
	sys.path += [""]
import better_wave

def ac97_read_u8(address):
	return read_u8(0xFEC00000 + address)
def ac97_read_u16(address):
	return read_u16(0xFEC00000 + address)
def ac97_read_u32(address):
	return read_u32(0xFEC00000 + address)

def ac97_write_u8(address, value):
	write_u8(0xFEC00000 + address, value)
def ac97_write_u16(address, value):
	write_u16(0xFEC00000 + address, value)
def ac97_write_u32(address, value):
	write_u32(0xFEC00000 + address, value)


def export_wav(path, channels=2, sample_width=2, sample_rate=48000, fmt=better_wave.WAVE_FORMAT_PCM):
	# Also see https://github.com/Sergeanur/XboxADPCM/blob/master/XboxADPCM/XboxADPCM.cpp for ADPCM
	wav = better_wave.open(path, 'wb')
	wav.setformat(fmt)
	wav.setnchannels(channels)
	wav.setsampwidth(sample_width)
	wav.setframerate(sample_rate)
	return wav

def ac97_status():
	print("global control=0x" + format(ac97_read_u32(0x12C), '08X'))
	print("global status=0x" + format(ac97_read_u32(0x130), '08X'))
	def dump_buffers(addr):
		descriptor = ac97_read_u32(addr)
		print("??? desc is p 0x" + format(descriptor, '08X'))
		descriptor |= 0x80000000
		# FIXME: Download all descriptors in one packet and then parse here
		wav = export_wav(format(addr, 'X') + ".wav")
		for i in range(0, 32):
			addr = read_u32(descriptor + i * 8 + 0)
			length = read_u16(descriptor + i * 8 + 4)
			control = read_u16(descriptor + i * 8 + 6)
			if (addr != 0) or (length != 0) or (control != 0):
				print(str(i) + ": 0x" + format(addr, '08X') + " (" + str(length) + " samples); control: 0x" + format(control, '04X'))
				addr |= 0x80000000
				data = read(addr, length * 2)
				wav.writeframes(data)
		wav.close()
		print("CIV=0x" + format(ac97_read_u8(addr + 0x4), '02X'))
		print("LVI=0x" + format(ac97_read_u8(addr + 0x5), '02X'))
		print("SR=0x" + format(ac97_read_u16(addr + 0x6), '04X'))
		print("pos=0x" + format(ac97_read_u16(addr + 0x8), '04X'))
		print("piv=0x" + format(ac97_read_u16(addr + 0xA), '04X'))
		print("CR=0x" + format(ac97_read_u8(addr + 0xB), '02X'))
	dump_buffers(0x110)
	dump_buffers(0x170)
