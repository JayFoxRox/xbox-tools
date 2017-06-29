import gdb

inf = gdb.selected_inferior()

def read(address, size):
	return bytes(inf.read_memory(address, size))

def write(address, data):
	value = bytes(data)
	inf.write_memory (address, value)

