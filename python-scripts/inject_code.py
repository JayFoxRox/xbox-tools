#!/usr/bin/env python3

# Injects code and runs it

from xboxpy import *

import sys

f = open(sys.argv[1], 'rb')
code = f.read()

pointer = ke.MmAllocateContiguousMemory(len(code))
memory.write(pointer, code)
api.call(pointer, bytes([]))
ke.MmFreeContiguousMemory(pointer)
