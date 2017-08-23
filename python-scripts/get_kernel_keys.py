#!/usr/bin/env python3

# Copyright (c) 2017 Alexander McWhirter

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Tool for retrieving and displaying kernel keys from xbox memory
#
# For more information about the xbox kernel, see:
# http://xboxdevwiki.net/Kernel

import optparse
from xbox import *

parser = optparse.OptionParser()
parser.add_option('-d', action='store_true', dest='dump',
                  help='dump keys to eeprom_key.bin and hdd_key.bin')
parser.add_option('-a', action='store_true', dest='all',
                  help='view all keys found in kernel memory space')
(options, args) = parser.parse_args()

eepKey = bytes(read(ke.XboxEEPROMKey(), 20, False))
hddKey = bytes(read(ke.XboxHDKey(), 16, False))
sigKey = bytes(read(ke.XboxSignatureKey(), 16, False))
lanKey = bytes(read(ke.XboxLANKey(), 16, False))

if int.from_bytes(eepKey, 'big', signed=False) == 0:
  print ("\nWARNING: Your EEPROM Key has been erased! Is your xbox running a retail BIOS?")
  print ('For more information please go to http://xboxdevwiki.net/Kernel/XboxEEPROMKey\n')
  eepKeyErased = True
else:
  print ('')
  eepKeyErased = False

if options.dump:
  if eepKeyErased:
    print ('EEPROM Key:\t{}'.format(''.join(format(n, '02x') for n in eepKey)))
    print ('Your EEPROM key has been erased, not dumping...\n')
  else:
    print ('EEPROM Key:\t{}'.format(''.join(format(n, '02x') for n in eepKey)))
    eepKeyFile = open('eeprom_key.bin', 'wb')
    print ('Dumping EEPROM key to eeprom_key.bin...\n')
    eepKeyFile.write(eepKey)

  print ('HDD Key:\t{}'.format(''.join(format(n, '02x') for n in hddKey)))
  hddKeyFile = open('hdd_key.bin', 'wb')
  print ('Dumping HDD key to hdd_key.bin...\n')
  hddKeyFile.write(hddKey)

else:
  print ('EEPROM Key:\t{}'.format(''.join(format(n, '02x') for n in eepKey)))
  print ('HDD Key:\t{}'.format(''.join(format(n, '02x') for n in hddKey)))

if options.all:
  print ('Signature Key:\t{}'.format(''.join(format(n, '02x') for n in sigKey)))
  print ('LAN Key:\t{}'.format(''.join(format(n, '02x') for n in lanKey)))
