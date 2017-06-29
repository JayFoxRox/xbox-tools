from . import interface

def read(address, size):
  return interface.read(address, size)
def write(address, data):
  interface.write(address, data)

def read_u8(address):
  data = interface.read(address, 1)
  return int.from_bytes(data, byteorder='little', signed=False)
def read_u16(address):
  data = interface.read(address, 2)
  return int.from_bytes(data, byteorder='little', signed=False)
def read_u32(address):
  data = interface.read(address, 4)
  return int.from_bytes(data, byteorder='little', signed=False)

def write_u8(address, value):
  interface.write(address, data=value.to_bytes(1, byteorder='little', signed=False))
def write_u16(address, value):
  interface.write(address, data=value.to_bytes(2, byteorder='little', signed=False))
def write_u32(address, value):
  interface.write(address, data=value.to_bytes(4, byteorder='little', signed=False))

def map_page(virtual_address, mapped):
  pde_base = 0xC0300000 # Hardcoded PDE
  pde_addr = pde_base + (virtual_address >> 22) * 4
  #print("PDE at 0x" + format(pde_addr, '08X'))
  pde = read_u32(pde_addr) # Get PDE entry
  #print("PDE mapping to 0x" + format(pde & 0xFFFFF000, '08X'))
  if (pde & 1) == 0:
    print("PDE not valid?!")
    return
  if (pde & (1 << 7)) == 0: # Only if not large pages (0 = 4kiB, 1 = 4MiB)
    pte_base = 0xC0000000 # Hardcoded PTE
    pte_addr = pte_base + (virtual_address >> 12) * 4 # FIXME: `& 0x3FF` ?
    #print("PTE at 0x" + format(pte_addr, '08X'))
    pte = read_u32(pte_addr) # Get PTE entry
    was_mapped = (pte & 1 == 1)
    #if (was_mapped) == 0:
    #  print("PDE was not valid?!")
    if mapped:
      pte |= 0x00000001
    else:
      pte &= 0xFFFFFFFE

    # Hack to identity map physical pages
    if (virtual_address & 0x80000000) != 0:
      pte = (virtual_address & 0x7FFFF000) | (pte & 0xFFF)

    #print("PTE mapping to 0x" + format(pte & 0xFFFFF000, '08X'))
    write_u32(pte_addr, pte)
  return was_mapped
