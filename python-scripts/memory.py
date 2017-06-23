import gdb

inf = gdb.selected_inferior()

def read(address, size):
	return bytes(inf.read_memory(address, size))

def write(address, data):
	value = bytes(data)
	inf.write_memory (address, value)

def read_u8(address):
	data = read(address, 1)
	return int.from_bytes(data, byteorder='little', signed=False)
def read_u16(address):
	data = read(address, 2)
	return int.from_bytes(data, byteorder='little', signed=False)
def read_u32(address):
	data = read(address, 4)
	return int.from_bytes(data, byteorder='little', signed=False)

def write_u8(address, value):
	write(address, data=value.to_bytes(1, byteorder='little', signed=False))
def write_u16(address, value):
	write(address, data=value.to_bytes(2, byteorder='little', signed=False))
def write_u32(address, value):
	write(address, data=value.to_bytes(4, byteorder='little', signed=False))

def map_page(virtual_address, mapped):
	pde_base = 0xC0300000 # Hardcoded PDE
	pde_addr = pde_base + (virtual_address >> 22) * 4
	#print("PDE at 0x" + format(pde_addr, '08X'))
	pde = read_u32(pde_addr) # Get PDE entry
	if False: # FIXME: Only if not valid
		return
	if True: # FIXME: Only if not large pages
		pte_base = 0xC0000000 #FIXME: Why not pde & 0xFFFFF000
		pte_addr = pte_base + (virtual_address >> 12) * 4 # FIXME: `& 0x3FF` ?
		#print("PTE at 0x" + format(pte_addr, '08X'))
		pte = read_u32(pte_addr) # Get PTE entry
		was_mapped = (pte & 1 == 1)
		if mapped:
			pte |= 0x00000001
		else:
			pte &= 0xFFFFFFFE
	write_u32(pte_addr, pte)
	return was_mapped
