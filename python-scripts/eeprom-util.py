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
import argparse

class Eeprom:
  def __init__(self, eepDump):
    # boot variables
    self.hash = eepDump[0:20]           # EEPROM hash
    self.confounder = eepDump[20:28]      # encrypted confounder
    self.hddKey = eepDump[28:44]         # encrypted HDD key
    self.gameReg = eepDump[44:48]         # encrypted game region code

    # identity variables
    self.identChk = eepDump[48:52]        # identity checksum
    self.serial = eepDump[52:64]         # serial number
    self.mac = eepDump[64:70]             # MAC address
    self.unknown0 = eepDump[70:72]        # TBD
    self.onlineKey = eepDump[72:88]      # online key
    self.videoStd = eepDump[88:92]        # NTSC / PAL
    self.unknown1 = eepDump[92:96]        # TBD

    # settings variables
    self.settChk = eepDump[96:100]         # settings checksum
    self.timeZoneBias = eepDump[100:104]   # time zone bias
    self.timeZoneStdName = eepDump[104:108] # standard timezone
    self.timeZoneDltName = eepDump[108:112] # daylight savings timezone
    self.unknown2 = eepDump[112:120]        # TBD
    self.timeZoneStdDate = eepDump[120:124] # standard date / time
    self.timeZoneDltDate = eepDump[124:128] # daylight savings date / time
    self.unknown3 = eepDump[128:136]       # TBD
    self.timeZoneStdBias = eepDump[136:140] # standard bias
    self.timeZoneDltBias = eepDump[140:144] # daylight savings bias
    self.languageId = eepDump[144:148]      # language identifier
    self.videoFlags = eepDump[148:152]      # video settings
    self.audioFlags = eepDump[152:156]      # audio settings
    self.gameParCont = eepDump[156:160]     # game parental contol settings
    self.parContPass = eepDump[160:164]     # parental control password
    self.dvdParCont = eepDump[164:168]      # DVD parental control settings
    self.ip = eepDump[168:172]              # IP address
    self.dns = eepDump[172:176]             # DNS server
    self.gateway = eepDump[176:180]         # default gateway
    self.subnet = eepDump[180:184]          # subnet
    self.unknown4 = eepDump[184:188]        # TBD
    self.dvdReg = eepDump[188:192]          # DVD region code
    self.unknown5 = eepDump[192:256]       # TBD

# Because of the confounder we have to split the RC4 decryption / encryption proccess
# into two functions (eepKeyPrepCrypt / eepKeyCrypt). We also need a way to share state
# between the the two functions (EepKeyObj). In a nutshell we fill and EepKeyObj method
# object with the initial state by calling eepKeyPrepCrypt. Then we call eepKeyCrypt
# on the confounder data. eepKeyCrypt will push state data back into the EepKeyObj method 
# object (i / j) which is necessary when we call eepKeyCrypt on the next chunk of data
# from the Eeprom method object (eeprom.hddKey + eeprom.gameReg). This is also why we
# don't use any standard RC4 crypto libaries here.

# This code was adapted from https://en.wikipedia.org/wiki/RC4

# store RC4 key permuataion data here
class EepKeyObj:
  state = bytearray(range(256))
  i = 0
  j = 0

# RC4 Key-Scheduling Algorithm (KSA)
# because of the confounder we only want to call this once
def eepKeyPrepCrypt(eepKey, eepKeyObj):
  j = 0

  for i in range(256):
    j = (j + eepKeyObj.state[i] + eepKey[i % len(eepKey)]) % 256
    eepKeyObj.state[i], eepKeyObj.state[j] = eepKeyObj.state[j], eepKeyObj.state[i]

# RC4 Pseudo-Random Generation Algorithm (PRGA)
# because of the confounder this has been slighly modified to keep
# i / j stored in EepKeyObj rather than setting them to 0 per decryption
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

parser = argparse.ArgumentParser()
parser.add_argument('-f', action='store', dest='eepFileLoc',
                  help='location of your Xbox eeprom dump')
parser.add_argument('-k', action='store', dest='keyFileLoc',
                  help='location of your Xbox eeprom key dump')
args = parser.parse_args()

if args.eepFileLoc:
  eepFile = open(args.eepFileLoc, 'rb')
  eepDump = eepFile.read(256)
  eepFile.close()
  eeprom = Eeprom(eepDump)
  print ('ENCRYPTED EEPROM DATA')
  print ('EEPROM Hash:\t\t\t{}'.format(''.join(format(x, '02x') for x in eeprom.hash)))
  print ('Encrypted Confounder:\t\t{}'.format(''.join(format(x, '02x') for x in eeprom.confounder)))
  print ('Encrypted HDD Key:\t\t{}'.format(''.join(format(x, '02x') for x in eeprom.hddKey)))
  print ('Encrypted Game Region Code:\t{}'.format(''.join(format(x, '02x') for x in eeprom.gameReg)))

  print ('\nIDENTITY EEPROM DATA')
  print ('Identity Checksum:\t\t{}'.format(''.join(format(x, '02x') for x in eeprom.identChk)))
  print ('Serial Number:\t\t\t{}'.format(eeprom.serial.decode('ascii')))
  print ('MAC Address:\t\t\t{}'.format(''.join(format(x, '02x') for x in eeprom.mac)))
  print ('Online Key:\t\t\t{}'.format(''.join(format(x, '02x') for x in eeprom.onlineKey)))

  # print NTSC / PAL instead of their respective codes
  if int.from_bytes(eeprom.videoStd, 'big', signed=False) == 81920: # 81920 == 00014000 
    print ('Video Standard:\t\t\tNTSC ({})'.format(''.join(format(x, '02x') for x in eeprom.videoStd)))  
  elif int.from_bytes(eeprom.videoStd, 'big', signed=False) == 229376: # 229376 == 00038000
    print ('Video Standard:\t\t\tPAL ({})'.format(''.join(format(x, '02x') for x in eeprom.videoStd)))
  else:
    print ('Video Standard:\t\t\t{}'.format(''.join(format(x, '02x') for x in eeprom.videoStd)))

  if args.keyFileLoc:
    # load eeprom key
    eepKeyFile = open(args.keyFileLoc, 'rb')
    eepKey = eepKeyFile.read()
    eepKeyFile.close()
  
    # generate hmac-sha1 hash of eeprom key
    eepKeyHash = hmac.new(eepKey, eeprom.hash, sha1).digest()

    # initialize EepKeyObj method object
    eepKeyObj = EepKeyObj()
    eepKeyPrepCrypt(eepKeyHash, eepKeyObj)
  
    # decrypt confounder 
    decConf = eepKeyCrypt(eepDump[20:28], eepKeyObj)

    # decrypt HDD key and game region code
    decData = eepKeyCrypt(eepDump[28:48], eepKeyObj)

    # we need to hash the confounder and data as one
    hashData = decConf + decData

    # hash decrypted EEPROM data
    eepHash = hmac.new(eepKey, hashData, sha1).digest()

    # make sure hashes match
    if eepHash == eeprom.hash:
      print ('\nDECRYPTED EEPROM DATA')

      # pull HDD key from decryted data
      decHddKey = bytearray()
      for cnt in range(16):
        decHddKey.append(decData[cnt])

      # pull game region from decrypted data
      decGameReg = bytearray()
      for cnt in range(4):
        decGameReg.append(decData[cnt + 16])

      print ('Verified EEPROM Hash:\t\t{}'.format(''.join(format(x, '02x') for x in eepHash)))      
      print ('Decrypted Confounder:\t\t{}'.format(''.join(format(x, '02x') for x in decConf)))
      print ('Decrypted HDD Key:\t\t{}'.format(''.join(format(x, '02x') for x in decHddKey)))
      print ('Decrypted Game Region Code:\t{}'.format(''.join(format(x, '02x') for x in decGameReg)))

    # hashes don't match
    else:
      print ('\nWARNING: The decrypted and encrypted EEPROM hashes do not match!')
      print ('Either your EEPROM file or EEPROM key is corrupt / invalid!\n')
      print ('Original EEPROM Hash:\t\t{}'.format(''.join(format(x, '02x') for x in eeprom.hash)))
      print ('Invalid EEPROM Hash:\t\t{}'.format(''.join(format(x, '02x') for x in eepHash)))
