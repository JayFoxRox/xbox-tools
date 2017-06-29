from . import interface
from . import pe
import struct

def MmAllocateContiguousMemory(NumberOfBytes):
	return call_stdcall(165, "<I", NumberOfBytes)

def MmGetPhysicalAddress(BaseAddress):
	return call_stdcall(173, "<I", BaseAddress)

def call_stdcall(function, types, *arguments):
	address = pe.resolve_export(function)
	registers = interface.call(address, struct.pack(types, *arguments))
	return registers['eax']
