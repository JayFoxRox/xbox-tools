#!/usr/bin/env python3

# Retrieves all kernel keys from memory
#
# For more information about these, see:
# http://xboxdevwiki.net/Kernel


from xbox import *

eepromKey = int.from_bytes(read(ke.XboxEEPROMKey(), 16, False), byteorder='big', signed=False)
hddKey = int.from_bytes(read(ke.XboxHDKey(), 16, False), byteorder='big', signed=False)
sigKey = int.from_bytes(read(ke.XboxSignatureKey(), 16, False), byteorder='big', signed=False)
lanKey = int.from_bytes(read(ke.XboxLANKey(), 16, False), byteorder='big', signed=False)

print ('EEPROM Key:\t{:x}'.format(eepromKey))
print ('HDD Key:\t{:x}'.format(hddKey))
print ('Signature Key:\t{:x}'.format(sigKey))
print ('LAN Key:\t{:x}'.format(lanKey))
