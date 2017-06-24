import socket
import struct

#HOST = "127.0.0.1"
#PORT = 8731 # FIXME: Actually 731, but linux doesn't like that [needs more permissions]
HOST = "192.168.177.2"
PORT = 731

xbdm = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
xbdm.connect((HOST, PORT))

def xbdm_read_line():
	data = b''
	while True:
		#print("Waiting")
		byte = xbdm.recv(1)
		#print("Got " + str(byte))
		if byte == b'\r':
			byte = xbdm.recv(1)
			assert(byte == b'\n')
			break
		data += byte
	return data

def xbdm_parse_response():
	res = xbdm_read_line()
	status = res[0:4]
	if status == b'200-':
		return res
	if status == b'201-':
		print(status)
		return
	if status == b'202-':
		lines = []
		while True:
			line = xbdm_read_line()
			if line == b'.':
				return lines
			lines += [line]
	print("Unknown status: " + str(status))
	print("from response: " + str(res))
	assert(False)


def xbdm_command(cmd):
	#FIXME: If type is already in bytes we just send it binary!
	#print("Running '" + cmd + "'")
	xbdm.send(bytes(cmd + "\r\n", encoding='ascii'))
	#print("Sent")
	lines = xbdm_parse_response()
	#print("Done")
	return lines

def GetModules():
	lines = xbdm_command("modules")
	for line in lines:
		print(line)
		chunks = line.split()
		for chunk in chunks:
			if (chunk[0:6] == b'name=\"'):
				print("  name = '" + str(chunk[6:-1]) + "'")
			elif (chunk[0:5] == b'base='):
				print("  base = '" + str(chunk[5]) + "'")
			else:
				print('  unparsed: ' + str(chunk))
				pass
				#assert(False)
	return []
#202- multiline response follows
#name="xboxkrnl.exe" base=0x80010000 size=0x001380e0 check=0x0013eb88 timestamp=0x3cfcc86a
#name="xbdm.dll" base=0xb0011000 size=0x000620c0 check=0x0007007d timestamp=0x407c6068
#name="vx.dxt" base=0xb00b3000 size=0x00018d80 check=0x00024302 timestamp=0x407c620b
#name="wavebank.exe" base=0x00010c40 size=0x0004fa40 check=0x00000000 timestamp=0x4c14abd2 tls xbe
#.


def GetMem(addr, length):
	cmd = "getmem addr=0x" + format(addr, 'X') + " length=0x" + format(length, 'X')
	lines = xbdm_command(cmd)
	data = bytearray()
	for line in lines:
		line = str(line, encoding='ascii').strip()
		for i in range(0, len(line) // 2):
			byte = line[i*2+0:i*2+2]
			if '?' in byte:
				print("Oops?!")
				byte = '00'
			data.append(int(byte,16))
	assert(len(data) == length)
	return bytes(data)

def SetMem(addr, data):
	value = bytes(data)
	cmd="setmem addr=0x" + format(addr, 'X') + " data="
	for i in range(0, len(data)):
		cmd += format(value[i], '02X')
	xbdm_command(cmd)

def read(address, size):
	return GetMem(address, size)
def write(address, data):
	return SetMem(address, size)

# Get login message
xbdm_parse_response()

# Hack some functions so we have better read/write access
# See xbdm-hack.md for more information

hacked = False
if True:
	modules = GetModules()
	# FIXME: Get location of xbdm.dll
	DmResumeThread_addr = resolve_export(35, image_base=0x0B0011000) #FIXME: Use location of xbdm.dll
	#DmResumeThread_addr = resolve_export(35) #FIXME: Use location of xbdm.dll
	hack = "8B5424048B1A8B4A048B4208E2028A03E203668B03E2028B03E2028803E203668903E2028903894208B80000DB02C20400"
	xbdm_command("setmem addr=0x" + format(DmResumeThread_addr, 'X') + " data=" + hack)
	
	#hack_bank = DmResumeThread_addr + (len(hack) // 2) # Put communication base behind the hack code [pretty shitty..]
	hack_bank = 0xd0032FC0#  0xD004E000 - 12 # Top of stack

	hacked = True
	print("Hack installed, bank at 0x" + format(hack_bank, '08X'))
	#base=0xb0011000

def xbdm_hack(address, operation, data=0):
	SetMem(hack_bank, struct.pack("<III", address, operation, data))
	xbdm_command("resume thread=0x" + format(hack_bank, 'X'))
	return GetMem(hack_bank + 8, 4)

def xbdm_read_8(address):
	return xbdm_hack(address, 1)
def xbdm_read_16(address):
	return xbdm_hack(address, 2)
def xbdm_read_32(address):
	return xbdm_hack(address, 3)

def xbdm_write_8(address, data):
	xbdm_hack(address, 4, int.from_bytes(data, byteorder='little', signed=False))
def xbdm_write_16(address, data):
	xbdm_hack(address, 5, int.from_bytes(data, byteorder='little', signed=False))
def xbdm_write_32(address, data):
	xbdm_hack(address, 6, int.from_bytes(data, byteorder='little', signed=False))

def read(address, size):
	if hacked:
		if size == 1:
			return xbdm_read_8(address)[0:1]
		if size == 2:
			return xbdm_read_16(address)[0:2]
		if size == 4:
			return xbdm_read_32(address)[0:4]
	return GetMem(address, size)
def write(address, data):
	if hacked:
		size = len(data)
		if size == 1:
			return xbdm_write_8(address, data)
		if size == 2:
			return xbdm_write_16(address, data)
		if size == 4:
			return xbdm_write_32(address, data)
	return SetMem(address, size)

print(read_u32(0x80010000))
