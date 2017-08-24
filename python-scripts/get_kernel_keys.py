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

# Tool for retrieving and displaying kernel keys from Xbox memory
#
# For more information about the Xbox kernel, see:
# http://xboxdevwiki.net/Kernel

from xbox import *
import argparse
import textwrap

parser = argparse.ArgumentParser()
parser.add_argument('-d', action='store_true', dest='dump',
                  help='dump security keys to a file (combine with -s)')
parser.add_argument('-s', action='store_true', dest='sec',
                  help='view security keys found in kernel memory space')
parser.add_argument('-o', action='store_true', dest='other',
                  help='view other keys found in kernel memory space')
parser.add_argument('-x', action='store_true', dest='exec',
                  help='view executable keys found in kernel memory space')
args = parser.parse_args()

eepKey = read(ke.XboxEEPROMKey(), 16, False)
hddKey = read(ke.XboxHDKey(), 16, False)
sigKey = read(ke.XboxSignatureKey(), 16, False)
lanKey = read(ke.XboxLANKey(), 16, False)
altSigKeysDump = bytearray(read(ke.XboxAlternateSignatureKeys(), 256, False))
pubKeyDataDump = read(ke.XePublicKeyData(), 284, False)

if args.exec or args.other or args.sec:
  print ("\n\033[1mWARNING: These keys are specific to your Xbox, please keep them safe!")
  print ("Making them publicly available would likely be a bad idea...\033[0m")


if args.exec:
  print ("\n\033[1mExecutable Keys\033[0m")
  print ('Signature Key:\t\t\t{}'.format(''.join(format(n, '02x') for n in sigKey)))
  print ('LAN Key:\t\t\t{}'.format(''.join(format(n, '02x') for n in lanKey)))

if args.other:
  print ("\n\033[1mOther Keys\033[0m")
  
  altSigKeys = []
  
  for x in range(16):
    altSigKeys.append('')

    for y in range(16):
      altSigKeys[x] += (format(altSigKeysDump[y * (x + 1)], '02x'))

    print ('Alternate Signature Key[{}]:\t{}'.format(x, altSigKeys[x]))

  wrapper = textwrap.TextWrapper()
  wrapper.width = 32
  pubKeyData = wrapper.wrap(''.join(format(n, '02x') for n in pubKeyDataDump))

  printPubKeyDataHeader = True
  for x in range(18):
    if printPubKeyDataHeader:
      print ('Public Key Data:\t\t{}'.format(pubKeyData[x]))
      printPubKeyDataHeader = False
    else:
      print ('\t\t\t\t{}'.format(pubKeyData[x]))

if args.sec:
  if int.from_bytes(eepKey, 'big', signed=False) == 0:
    print ("\n\033[1mWARNING: Your EEPROM Key has been erased! Is your Xbox running a retail BIOS?")
    print ('For more information please go to http://xboxdevwiki.net/Kernel/XboxEEPROMKey\033[0m')
    eepKeyErased = True
  else:
    eepKeyErased = False
  
  print ("\n\033[1mSecurity Keys\033[0m")
  print ('EEPROM Key:\t\t\t{}'.format(''.join(format(n, '02x') for n in eepKey)))
  print ('HDD Key:\t\t\t{}'.format(''.join(format(n, '02x') for n in hddKey)))

  if args.dump:
    if eepKeyErased:
      print ('Your EEPROM key has been erased, not dumping...')
    else:
      print ('Dumping EEPROM key to eeprom_key.bin...')
      eepKeyFile = open('eeprom_key.bin', 'wb')
      eepKeyFile.write(eepKey)

    print ('Dumping HDD key to hdd_key.bin...')
    hddKeyFile = open('hdd_key.bin', 'wb')  
    hddKeyFile.write(hddKey)
