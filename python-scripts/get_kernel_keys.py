#!/usr/bin/env python3

# Retrieves all kernel keys from memory
#
# For more information about these, see:
# http://xboxdevwiki.net/Kernel

import optparse
from xbox import *

parser = optparse.OptionParser()
parser.add_option('-d', action='store_true', dest='dump',
                  help='dump keys to eeprom_key.bin and hdd_key.bin')
parser.add_option('-a', action='store_true', dest='all',
                  help='view all keys found in kernel memory space')
(options, args) = parser.parse_args()

eepKey = bytes(read(ke.XboxEEPROMKey(), 16, False))
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
