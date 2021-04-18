#!/usr/bin/env python3

from unicorn import *
from unicorn.x86_const import *

import ctypes
import struct
import sys


def load(path):
  return open(path, 'rb').read()


def store(path, data):
  open(path, 'wb').write(data)


def dump_state(uc):
  cs = uc.reg_read(UC_X86_REG_CS)
  print("CS: 0x%04X" % cs)
  eip = uc.reg_read(UC_X86_REG_EIP)
  print("EIP: 0x%08X" % eip)
  eax = uc.reg_read(UC_X86_REG_EAX)
  print("EAX: 0x%08X" % eax)
  ebx = uc.reg_read(UC_X86_REG_EBX)
  print("EBX: 0x%08X" % ebx)
  esi = uc.reg_read(UC_X86_REG_ESI)
  print("ESI: 0x%08X" % esi)
  esp = uc.reg_read(UC_X86_REG_ESP)
  print("ESP: 0x%08X" % esp)
  cr0 = uc.reg_read(UC_X86_REG_CR0)
  print("CR0: 0x%08X" % cr0)


def hook_code(uc, address, size, user_data):
  print("Tracing instruction at 0x%X, instruction size = 0x%X" %(address, size))

  dump_state(uc)

  # Read instruction bytes from memory
  code = uc.mem_read(address, size)
  print("Code: %s" % (code.hex().upper()))

hooks_mcpx = []
def hook_block_mcpx(uc, address, size, user_data):
  print("Running MCPX")

  #FIXME: Differentiate between running MCPX ROM and MCPX RAM.
  #       Debugs or MIST attack run in MCPX RAM (for lack of a better term).

  dumped_mcpx = uc.mem_read(0xFFFFFE00, 0x200)
  store("mcpx.bin", dumped_mcpx)
  for h in hooks_mcpx:
    uc.hook_del(h)

hooks_fbl = []
def hook_block_fbl(uc, address, size, user_data):
  print("Running FBL from 0x%08X" % address)

  dumped_fbl = uc.mem_read(0xFFFFD400, 0x2880)
  store("fbl.bin", dumped_fbl)
  for h in hooks_fbl:
    uc.hook_del(h)

hooks_2bl = []
def hook_block_2bl(uc, address, size, user_data):
  print("Running 2BL from 0x%08X" % address)

  # Check if this is the relocated or original address
  address &= 0x7FFFFFFF
  if address >= 0x00400000:
    dumped_2bl = uc.mem_read(0x00400000, 0x6000)
  else:
    dumped_2bl = uc.mem_read(0x00090000, 0x6000)

  store("2bl.bin", dumped_2bl)
  for h in hooks_2bl:
    uc.hook_del(h)


def hook_block_wrap(uc, address, size, user_data):
  print("Tracing basic block at 0x%X, block size = 0x%X" %(address, size))
  if address == 0:
    dumped_wrap = uc.mem_read(0, 0x1000)
    store("wrap.bin", dumped_wrap)


hooks_kernel = []
def hook_block_kernel(uc, address, size, user_data):
  print("Tracing basic block at 0x%X, block size = 0x%X" %(address, size))
  xboxkrnl_base = 0x80010000

  # Check if this address qualifies for being in xboxkrnl
  #FIXME: Do this before reading the xboxkrnl_base memory (perf reasons)
  if address >= xboxkrnl_base:

    # Check if we have a kernel loaded already
    if uc.mem_read(xboxkrnl_base, 2) == b'MZ':

      # Get the kernel image size
      def read_u32(address):
        return struct.unpack("<I", uc.mem_read(address, 4))[0]
      pe_header_offset = read_u32(xboxkrnl_base + 0x3C)
      optional_header_offset = pe_header_offset + 4 + 20
      xboxkrnl_size = read_u32(xboxkrnl_base + optional_header_offset + 56)
      print("Size is %d bytes" % xboxkrnl_size)

      # Check if the size is valid, and if the address belongs to kernel
      if (xboxkrnl_size > 0) and (address < xboxkrnl_base + xboxkrnl_size):

        # Read entry point, and assert that we have hit it
        xboxkrnl_entry = read_u32(xboxkrnl_base + optional_header_offset + 16)
        assert(address == (xboxkrnl_base + xboxkrnl_entry))

        # Dump kernel
        dumped_xboxkrnl = uc.mem_read(xboxkrnl_base, xboxkrnl_size)
        store("xboxkrnl.exe", dumped_xboxkrnl)

        # Stop running
        uc.emu_stop()

class xbox():
  ram_size = 128 * 1024 * 1024

class usb():
  scratch1 = 0
  scratch2 = 0

class pci_config():
  address = 0

class smbus():
  slave = 0
  command = 0
  status = 0x10

class smc():
  version_string = b'P01' # x[0] != 'P': Debug Xbox
  version_string_index = 0

class mcpx():
  revision = 0x000000C2 # >= C3: MCPX 1.1
  has_rom = True

# callback for IN instruction
def hook_in(uc, port, size, user_data):

    eip = uc.reg_read(UC_X86_REG_EIP)
    print("--- reading from port 0x%X, size: %u, address: 0x%X" %(port, size, eip))

    if port == 0x80CE:
      assert(size == 1)
      #FIXME: Unknown port. Probably an emu error reading PCI IO base
      return 0x00        
    elif port == 0xc000:
      assert(size in [1, 2])
      # Used for SMBus status, so fake the "cycle complete" flag
      return smbus.status
    elif port == 0xc006:
      assert(size in [1, 2])
      return smbus.data
    elif port == 0xc009:
      assert(size == 1)
      #FIXME: What is this?
      #FIXME: Is this correct?
      return smbus.command >> 8
    elif port == 0xcfc:
      print("PCI Config space read 0x%08X" % pci_config.address)
      #FIXME: Emulate PCI config space read

      if pci_config.address == 0x8000103C:
        assert(size == 4)
        return usb.scratch1
      elif pci_config.address == 0x8000183C:
        assert(size == 4)
        return usb.scratch2
      elif pci_config.address == 0x80000808:
        assert(size in [1, 4])
        return mcpx.revision
      elif pci_config.address == 0x80000880:
        assert(size == 4)
        v = 0
        if not mcpx.has_rom: v |= 0x00001000
        return v
      


      return 0x00100000
    else:
      assert(False)


# callback for OUT instruction
def hook_out(uc, port, size, value, user_data):

    eip = uc.reg_read(UC_X86_REG_EIP)
    print("--- writing to port 0x%X, size: %u, value: 0x%X, address: 0x%X" %(port, size, value, eip))

    # confirm that value is indeed the value of AL/AX/EAX
    v = 0

    if port in [0x8026, 0x8049, 0x80D9]:
      assert(size == 1)
      #FIXME: Unknown MCPX IO ports
      pass
    elif port == 0xc000:
      assert(size in [1, 2])
      #FIXME: What does `out(c000, in(c000))`?
      pass
    elif port == 0xc002:
      assert(size == 1)

      assert(value in [0x0A, 0x0B, 0xD])

      # Always false in Xbox-Linux docs
      is_unk = bool(value & 2)

      is_word = bool(value & 1)

      if smbus.slave == 0x20:
        assert(is_word == False)
        print("SMC write access: 0x%02X" % smbus.command)
        #FIXME: Print value?
      elif smbus.slave == 0x21:
        assert(is_word == False)
        print("SMC read access: 0x%02X" % smbus.command)
        if smbus.command == 0x01:
          # Read SMC version string
          smbus.data = smc.version_string[smc.version_string_index % 3]
          smc.version_string_index += 1
        elif smbus.command in [0x1c, 0x1d, 0x1e, 0x1f]:
          # Watchdog disable
          smbus.data = 0x55
        else:
          assert(False)
      elif smbus.slave == 0x8A:
        print("Conexant video encoder write access")
      elif smbus.slave == 0xA9:
        print("EEPROM read access")
        assert(len(eeprom) == 256)

        smbus.data = eeprom[smbus.command]

        if is_word == True:
          #FIXME: how to deal with this?
          pass

        pass
      elif smbus.slave == 0xD4:
        print("Focus video encoder write access")
      elif smbus.slave == 0xE1:
        #FIXME: what device is this?
        print("Unknown SMBus read access")
        pass
      else:
        print("SMBus access to 0x%02X" % smbus.slave)
        assert(False)

      # Mark cycle complete
      smbus.status = 0x10

    elif port == 0xc004:
      smbus.slave = value
    elif port == 0xc006:
      smbus.data = value
    elif port == 0xc008:
      smbus.command = value
    elif port == 0xc200:
      # Something to do with SMBus setup
      pass
    elif port == 0xcf8:
      assert(size == 4)
      # Ignore unknown bits
      #FIXME: Improve this
      pci_config.address = value & 0xF7FFFFFF
    elif port == 0xcfc:
      print("PCI Config space write 0x%08X: 0x%08X" % (pci_config.address, value))

      if pci_config.address == 0x80000880:
        #FIXME: Do this in a separate function
        # Disable MCPX ROM
        assert(size in [1, 4])
        if value & 0x2:
          uc.mem_write(0x100000000 - 512, flash_rom[-512:])
      elif pci_config.address == 0x8000103C:
        assert(size == 4)
        usb.scratch1 = value
      elif pci_config.address == 0x8000183C:
        assert(size == 4)
        usb.scratch2 = value

    else:
      assert(False)

def hook_unmapped(uc, _type, address, size, value, user_data):
  print("Unmapped: 0x%08X" % address)
  assert(False)
  return True




def extract_bios():
  try:

    # Initialize emulator
    uc = Uc(UC_ARCH_X86, UC_MODE_32)

    # Map Xbox RAM
    #FIXME: Use memory balooning to save on RAM use for raspberrypi etc.
    #FIXME: Use 64MB, but also fixup the registers
    ram = ctypes.create_string_buffer(xbox.ram_size)
    uc.mem_map_ptr(0x00000000, xbox.ram_size, UC_PROT_ALL, ram)

    #FIXME: Remove this dirty hack, it's only necessary because paging
    #       seems to be ignored.
    uc.mem_map_ptr(0x80000000, xbox.ram_size, UC_PROT_ALL, ram)

    # Map a dummy GPU which is used for RAM configuration (exact size unknown)
    #FIXME: This could all point at the same memory page
    #FIXME: Zero initialize so we know what we'll read?
    #FIXME: Replace with MMIO handler
    gpu_size = 16 * 1024 * 1024
    gpu = ctypes.create_string_buffer(gpu_size)
    uc.mem_map_ptr(0xFD000000, gpu_size, UC_PROT_ALL, gpu)

    #FIXME: This one is only available during boot, and will be relocated 
    uc.mem_map_ptr(0x0F000000, gpu_size, UC_PROT_ALL, gpu)

    # This is a hack because unicorn doesn't wrap around
    uc.mem_map(0x100000000, 4096)
    uc.mem_write(0x100000000, b'\xE9\xFB\xFF\xFF\xFF')

    # Map Xbox flash
    uc.mem_map(0xFF000000, 16 * 1024 * 1024)

    # Write flash to RAM
    print("Writing Flash ROM")
    assert(len(flash_rom) % 4096 == 0)
    addr = 0xFF000000
    while(addr < 0x100000000):
      uc.mem_write(addr, flash_rom)
      addr += len(flash_rom)

    # On MCPX X3, overlay secret ROM
    if mcpx.has_rom:
      print("Enabling MCPX ROM")
      assert(len(mcpx_rom) == 512)
      uc.mem_write(0x100000000 - 512, mcpx_rom)

    # Initialize stack
    #FIXME: What's the x86 stack address?
    uc.reg_write(UC_X86_REG_ESP, 0x200000)

    # Trace basic blocks in MCPX region
    global hooks_mcpx
    hooks_mcpx += [uc.hook_add(UC_HOOK_BLOCK, hook_block_mcpx, begin=0xFFFFFE00, end=0x100000000 - 1)]

    # Trace basic blocks in FBL region
    global hooks_fbl
    hooks_fbl += [uc.hook_add(UC_HOOK_BLOCK, hook_block_fbl, begin=0xFFFFD400, end=0xFFFFFC80 - 1)]

    # Trace basic blocks in 2BL region
    #FIXME: Evox ROMs only seem to use 0x3000 bytes.
    #       We should mark memory so we know how large it is.
    global hooks_2bl
    hooks_2bl += [uc.hook_add(UC_HOOK_BLOCK, hook_block_2bl, begin=0x80090000, end=0x80096000 - 1)]
    hooks_2bl += [uc.hook_add(UC_HOOK_BLOCK, hook_block_2bl, begin=0x00090000, end=0x00096000 - 1)]
    hooks_2bl += [uc.hook_add(UC_HOOK_BLOCK, hook_block_2bl, begin=0x80400000, end=0x80406000 - 1)]
    hooks_2bl += [uc.hook_add(UC_HOOK_BLOCK, hook_block_2bl, begin=0x00400000, end=0x00406000 - 1)]

    # Trace basic blocks in kernel region 
    global hooks_kernel
    hooks_kernel += [uc.hook_add(UC_HOOK_BLOCK, hook_block_kernel, begin=0x80010000, end=0x80000000 + xbox.ram_size - 1)]

    # Trace basic blocks for wrap-around
    uc.hook_add(UC_HOOK_BLOCK, hook_block_wrap, begin=0x0, end=0x1000)

    #FIXME: Find a way to dump x-codes?
    #       Possibly by looking at basic blocks in x-code interpreter
    #       We could monitor the x-code IP and keep track of the bounds

    # Trace all instructions (very slow!)
    if False:
      uc.hook_add(UC_HOOK_CODE, hook_code)

    # Hook IO ports
    uc.hook_add(UC_HOOK_INSN, hook_in, None, 1, 0, UC_X86_INS_IN)
    uc.hook_add(UC_HOOK_INSN, hook_out, None, 1, 0, UC_X86_INS_OUT)

    # Handle errors
    uc.hook_add(UC_HOOK_MEM_READ_UNMAPPED, hook_unmapped)
    uc.hook_add(UC_HOOK_MEM_WRITE_UNMAPPED, hook_unmapped)
    uc.hook_add(UC_HOOK_MEM_FETCH_UNMAPPED, hook_unmapped)

    # Decides wether we want to do HLE
    if True:

      # Setup LDT and IDT from MCPX
      gdtr_base = 0xFFFFFFD8
      gdtr_limit = 0x18
      gdtr = (0, gdtr_base, gdtr_limit, 0)
      uc.reg_write(UC_X86_REG_GDTR, gdtr)
      uc.reg_write(UC_X86_REG_IDTR, gdtr)

      # Set protected mode
      cr0 = uc.reg_read(UC_X86_REG_CR0)
      uc.reg_write(UC_X86_REG_CR0, cr0 | 1)
      uc.reg_write(UC_X86_REG_CS, 0x8)

      # Decides wether we skip X-Codes
      if False:

        # Setup segment registers (will be skipped)
        uc.reg_write(UC_X86_REG_EAX, 0x10)
        uc.reg_write(UC_X86_REG_DS, 0x10)
        uc.reg_write(UC_X86_REG_ES, 0x10)
        uc.reg_write(UC_X86_REG_SS, 0x10)

        # X-Codes would run here
        pass

        # Emulate return value from X-Codes
        uc.reg_write(UC_X86_REG_EBX, 0x806)

        # Skip X-Codes and go to MTRR setup in MCPX 1.0 and 1.1
        entry = 0xFFFFFEBC

      else:
        
        # Skip to segment register setup and X-Codes
        entry = 0xFFFFFE00

    else:

      # Go to real x86 entry-point
      entry = 0xFFFFFFF0

      #FIXME: support 16 bit + low level for x-codes
      assert(False)

    # Run emulation
    print("Starting emulation at 0x%08X" % entry)
    uc.emu_start(entry, -1) #, ADDRESS + len(code))
    print("Emulation done")    

    # Retrieve header for the initialized data section
    data_header = struct.unpack_from("<IIII", uc.mem_read(0x80010000 + 40, 16))
    data_uninitialized_size = data_header[0]
    data_initialized_size = data_header[1]
    data_raw_address = data_header[2]
    data_virtual_address = data_header[3]

    # Print the header for debug purposes
    print("Data header:")
    print(" - uninitialized size: %d bytes" % (data_uninitialized_size))
    print(" - initialized size: %d bytes" % (data_initialized_size))
    print(" - raw address: 0x%08X" % (data_raw_address))
    print(" - virtual address: 0x%08X" % (data_virtual_address))

    # Read data and verify it's actual data being used on first-boot
    kernel_data_raw = uc.mem_read(data_raw_address, data_initialized_size)
    kernel_data_virtual = uc.mem_read(data_virtual_address, data_initialized_size)
    assert(kernel_data_raw == kernel_data_virtual)

    # Read 2 kernel arguments from stack
    esp = uc.reg_read(UC_X86_REG_ESP)
    print("Stack at 0x%08X" % (esp))
    a1, a2 = struct.unpack("<II", uc.mem_read(esp + 4, 8))

    # Retrieve kernel parameters
    # This should only be 64 bytes, but for custom bioses we support 256.
    # We print 64, because that appears to be the most common length.
    kernel_parameters = uc.mem_read(a1, 256)
    print("Kernel parameters: %s" % kernel_parameters[0:64])
    store("kernel_parameters.bin", kernel_parameters)

    # Read crypto keys. By default, there are 3 (2 of which are used).
    # In custom bioses there can be more keys; we just read 256 byte (16 keys).
    # We print 4, because that appears to be a common number of stored keys.
    kernel_keys = uc.mem_read(a2, 256)
    for i in range(4):
      print("Key[%d]: %s" % (i, kernel_keys[i * 16:(i + 1) *16].hex().upper()))
    store("kernel_keys.bin", kernel_keys)

  except UcError as e:
    print("Error: %s" % e)
    dump_state(uc)

  return (None, None, None, None, None, kernel_parameters)


if __name__ == '__main__':

  # Read arguments
  mcpx_rom_path = sys.argv[1]
  if mcpx_rom_path.strip() != "":
    mcpx_rom = load(mcpx_rom_path)
  else:
    mcpx_rom = None
  flash_rom = load(sys.argv[2])
  if len(sys.argv) >= 4:
    print("Loading eeprom")
    eeprom = load(sys.argv[3])
  else:
    eepom = None

  # Assume that there's no MCPX if no path was provided (for debug bios)
  if mcpx_rom == None:
    mcpx_rom = flash_rom[-512:]

  # Work around some unicorn oddity
  def my_except_hook(exctype, value, traceback):
    if exctype == KeyboardInterrupt:
      print("Handler code goes here")
    else:
      sys.__excepthook__(exctype, value, traceback)
    sys.exit(1)
  sys.excepthook = my_except_hook

  # Extract kernel
  dumped_mcpx, dumped_fbl, dumped_2bl, dumped_xboxkrnl, dumped_xboxkrnl_keys, dumped_xboxkrnl_parameters = extract_bios()

