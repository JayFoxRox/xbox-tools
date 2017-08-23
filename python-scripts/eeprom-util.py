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

# Tool for decrypting, encrypting, and displaying data contained in the xbox EEPROM
#
# For more information about the xbox EEPROM, see:
# http://xboxdevwiki.net/EEPROM

from hashlib import sha1
import hmac
import optparse

class Eeprom:
  def __init__(self, eepFileLoc):
    eepFile = open(eepFileLoc, 'rb')

    # boot variables
    self.hash = bytes(eepFile.read(20))           # EEPROM hash
    self.confounder = bytes(eepFile.read(8))      # encrypted confounder
    self.hddKey = bytes(eepFile.read(16))         # encrypted HDD key
    self.gameReg = bytes(eepFile.read(4))         # encrypted game region code

    # identity variables
    self.identChk = bytes(eepFile.read(4))        # identity checksum
    self.serial = bytes(eepFile.read(12))         # serial number
    self.mac = bytes(eepFile.read(6))             # MAC address
    self.unknown0 = bytes(eepFile.read(2))        # TBD
    self.onlineKey = bytes(eepFile.read(16))      # online key
    self.videoStd = bytes(eepFile.read(4))        # NTSC / PAL
    self.unknown1 = bytes(eepFile.read(4))        # TBD

    # settings variables
    self.settChk = bytes(eepFile.read(4))         # settings checksum
    self.timeZoneBias = bytes(eepFile.read(4))    # time zone bias
    self.timeZoneStdName = bytes(eepFile.read(4)) # standard timezone
    self.timeZoneDltName = bytes(eepFile.read(4)) # daylight savings timezone
    self.unknown2 = bytes(eepFile.read(8))        # TBD
    self.timeZoneStdDate = bytes(eepFile.read(4)) # standard date / time
    self.timeZoneDltDate = bytes(eepFile.read(4)) # daylight savings date / time
    self.unknown3 = bytes(eepFile.read(8))        # TBD
    self.timeZoneStdBias = bytes(eepFile.read(4)) # standard bias
    self.timeZoneDltBias = bytes(eepFile.read(4)) # daylight savings bias
    self.languageId = bytes(eepFile.read(4))      # language identifier
    self.videoFlags = bytes(eepFile.read(4))      # video settings
    self.audioFlags = bytes(eepFile.read(4))      # audio settings
    self.gameParCont = bytes(eepFile.read(4))     # game parental contol settings
    self.parContPass = bytes(eepFile.read(4))     # parental control password
    self.dvdParCont = bytes(eepFile.read(4))      # DVD parental control settings
    self.ip = bytes(eepFile.read(4))              # IP address
    self.dns = bytes(eepFile.read(4))             # DNS server
    self.gateway = bytes(eepFile.read(4))         # default gateway
    self.subnet = bytes(eepFile.read(4))          # subnet
    self.unknown4 = bytes(eepFile.read(4))        # TBD
    self.dvdReg = bytes(eepFile.read(4))          # DVD region code
    self.unknown5 = bytes(eepFile.read(64))       # TBD

# Because of the confounder we have to split the RC4 decryption / encryption proccess
# into two functions (eepKeyPrepCrypt / eepKeyCrypt). We also need a way to share state
# between the the two functions (EepKeyObj). In a nutshell we fill and EepKeyObj method
# object with the initial state by calling eepKeyPrepCrypt. Then we call eepKeyCrypt
# on the confounder data. eepKeyCrypt will push state data back into the EepKeyObj method 
# object (i / j) which is necessary when we call eepKeyCrypt on the next chunk of data
# from the Eeprom method object (eeprom.hddKey + eeprom.gameReg). This is also why we
# don't use any standard RC4 crypto libaries here.

class EepKeyObj:
  state = bytearray(range(256))
  i = 0
  j = 0

def eepKeyPrepCrypt(eepKey, eepKeyObj):
  j = 0

  for i in range(256):
    j = (j + eepKeyObj.state[i] + eepKey[i % len(eepKey)]) % 256
    eepKeyObj.state[i], eepKeyObj.state[j] = eepKeyObj.state[j], eepKeyObj.state[i]

def eepKeyCrypt(eepCryptData, eepKeyObj):
  eepData = bytearray()
  i = eepKeyObj.i
  j = eepKeyObj.j
  xorInd = 0

  for byte in eepCryptData:
    i = (i + 1) % 256
    j = (j + eepKeyObj.state[i]) % 256
    eepKeyObj.state[i], eepKeyObj.state[j] = eepKeyObj.state[j], eepKeyObj.state[i]
    eepData.append(byte ^ eepKeyObj.state[(eepKeyObj.state[i] + eepKeyObj.state[j]) % 256])

  eepKeyObj.i = i
  eepKeyObj.j = j
  return eepData

parser = optparse.OptionParser()
parser.add_option('-f', action='store', dest='eepFileLoc')
parser.add_option('-k', action='store', dest='keyFileLoc')
(options, args) = parser.parse_args()

if options.eepFileLoc:
  eeprom = Eeprom(options.eepFileLoc)
  print ('\033[1mEncrypted EEPROM Data\033[0m')
  print ('EEPROM Hash:\t\t\t{}'.format(''.join(format(x, '02x') for x in eeprom.hash)))
  print ('Encrypted Confounder:\t\t{}'.format(''.join(format(x, '02x') for x in eeprom.confounder)))
  print ('Encrypted HDD Key:\t\t{}'.format(''.join(format(x, '02x') for x in eeprom.hddKey)))
  print ('Encrypted Game Region Code:\t{}'.format(''.join(format(x, '02x') for x in eeprom.gameReg)))

  print ('\n\033[1mIdentity EEPROM Data\033[0m')
  print ('Identity Checksum:\t\t{}'.format(''.join(format(x, '02x') for x in eeprom.identChk)))
  print ('Serial Number:\t\t\t{}'.format(eeprom.serial.decode('ascii')))
  print ('MAC Address:\t\t\t{}'.format(''.join(format(x, '02x') for x in eeprom.mac)))
  print ('Online Key:\t\t\t{}'.format(''.join(format(x, '02x') for x in eeprom.onlineKey)))

  # print NTSC / PAL instead of their respective codes
  if ''.join(format(x, '02x') for x in eeprom.videoStd) == '00014000':
    print ('Video Standard:\t\t\tNTSC')  
  elif ''.join(format(x, '02x') for x in eeprom.videoStd) == '00038000':
    print ('Video Standard:\t\t\tPAL')
  else:
    print ('Video Standard:\t\t\t{}'.format(''.join(format(x, '02x') for x in eeprom.videoStd)))

if options.eepFileLoc and options.keyFileLoc:
  # load eeprom key
  eepKeyFile = open(options.keyFileLoc, 'rb')
  eepKey = eepKeyFile.read()
  
  # generate hmac-sha1 hash of eeprom key
  eepKeyHash = hmac.new(eepKey, eeprom.hash, sha1).digest()

  # initialize EepKeyObj method object
  eepKeyObj = EepKeyObj()
  eepKeyPrepCrypt(eepKeyHash, eepKeyObj)
  
  # decrypt confounder 
  decConf = eepKeyCrypt(eeprom.confounder, eepKeyObj)
  
  # assemble encrypted HDD key and game region code into a single bytearray
  eepData = bytearray()
  for byte in eeprom.hddKey:
    eepData.append(byte)
  for byte in eeprom.gameReg:
    eepData.append(byte)

  # decrypt HDD key and game region code
  decData = eepKeyCrypt(eepData, eepKeyObj)

  # assemble decrypted EEPROM data into a single bytearray
  hashData = bytearray()
  for byte in decConf:
    hashData.append(byte)
  for byte in decData:
    hashData.append(byte)

  # hash decrypted EEPROM data
  eepHash = hmac.new(eepKey, hashData, sha1).digest()

  # make sure hashes match
  if eepHash == eeprom.hash:
    print ('\n\033[1mThe decrypted and encrypted EEPROM hashes match!\033[0m')
    
    # pull HDD key from assembled bytearray
    decHddKey = bytearray()
    for cnt in range(16):
      decHddKey.append(decData[cnt])

    # pull game region from assembled bytearray
    decGameReg = bytearray()
    for cnt in range(4):
      decGameReg.append(decData[cnt + 16])
      
    print ('Decrypted Confounder:\t\t{}'.format(''.join(format(x, '02x') for x in decConf)))
    print ('Decrypted HDD Key:\t\t{}'.format(''.join(format(x, '02x') for x in decHddKey)))
    print ('Decrypted Game Region Code:\t{}'.format(''.join(format(x, '02x') for x in decGameReg)))

  # hashes don't match
  else:
    print ('\n\033[1mThe decrypted and encrypted EEPROM hashes do not match!')
    print ('Either your EEPROM file or EEPROM key is corrupted / invalid!\033[0m')
    print ('Encrypted EEPROM Hash:\t\t{}'.format(''.join(format(x, '02x') for x in eeprom.hash)))
    print ('Decrypted EEPROM Hash:\t\t{}'.format(''.join(format(x, '02x') for x in eepHash)))
