from .. import interface
import gdb

inf = gdb.selected_inferior()

def read(address, size):
  return bytes(inf.read_memory(address, size))

def write(address, data):
  value = bytes(data)
  inf.write_memory (address, value)

def call(address, stack, registers=None):
  assert(False)
  # Some magic with `call` using:
  # gdb.execute (command [, from_tty [, to_string]])
  # Maybe?
  out_registers = {}
  out_registers['eax'] = 0
  return out_registers

interface.read = read
interface.write = write
