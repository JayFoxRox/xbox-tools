import sys
if not "" in sys.path:
	sys.path += [""]
import better_wave
import time
import pyaudio

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
	def dump_buffers(addr,name):
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
	dump_buffers(0x110, "pcm.wav")
	dump_buffers(0x170, "spdif.wav")

def ac97_trace():
	descriptor = ac97_read_u32(0x110)
	print("??? desc is p 0x" + format(descriptor, '08X'))
	descriptor |= 0x80000000
	wav = export_wav("pcm_trace.wav")
	for i in range(0, 32):
		addr = read_u32(descriptor + i * 8 + 0)
		length = read_u16(descriptor + i * 8 + 4)
		control = read_u16(descriptor + i * 8 + 6)
		if (addr != 0) or (length != 0) or (control != 0):
			print(str(i) + ": 0x" + format(addr, '08X') + " (" + str(length) + " samples); control: 0x" + format(control, '04X'))
			addr |= 0x80000000
			current_milli_time = lambda: time.time() * 1000.0
			chunks = 16
			buffer_size = length * 2
			chunk_size = buffer_size // chunks
			catchup = 0

			# Wait for start of playback
			
			sample_rate = 48000.0
			time_for_buffer = (length / 2) / sample_rate * 1000.0
			time_per_chunk = time_for_buffer / chunks

			pya = pyaudio.PyAudio()
			stream = pya.open(format=pya.get_format_from_width(width=2), channels=2, rate=int(sample_rate), output=True)

			#FIXME: This was an experiment on how long it would take to dump the entire buffer
			#				We can probably dump the entire buffer and then just grab the data we need
			#				[as we can follow the write cursor by diff'ing the buffers]
			if False:
				start = current_milli_time()
				data = read(addr, buffer_size)
				took = current_milli_time() - start
				print("Took " + str(took) + " / " + str(time_for_buffer) + " ms")

			# This is a poc where I try to find out when buffers are written
			print("Waiting for playback")
			last = None
			while True:
				new = read_u32(addr + chunk_size - 4)
				if last != None and last != new:
					print("Playback started!")
					time.sleep(time_for_buffer * 0.5 / 1000.0) # Give it another half buffer headstart
					# Playback reached us! Wait until the write cursor reaches the other half of the buffer
					break
				last = new
			
			underruns = 0
			for i in range(0, 500):
				offset = 0
				streamed_data = bytearray()
				for j in range(0, chunks):
					start = current_milli_time()
					data = read(addr + offset, chunk_size)
					offset += chunk_size
					streamed_data += data
					stream.write(bytes(data))
					took = current_milli_time() - start
					remain = time_per_chunk - took
					remain -= catchup
					if remain > 0:
						time.sleep(remain / 1000.0)
						took = current_milli_time() - start
						remain = time_per_chunk - took
					else:
						underruns += 1
					catchup -= remain
						#print("too slow!")
				wav.writeframes(streamed_data)
			print("Had " + str(underruns) + " underruns")

			stream.stop_stream()
			stream.close()


