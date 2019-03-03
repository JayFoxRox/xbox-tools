#!/usr/bin/env python3

# Dumps kernel keys which are used to derive most other keys.
# Also outputs to keys.bin (non human readable to avoid leaks).

from xboxpy import *

try:
  from cryptography.hazmat.backends import default_backend
  from cryptography.hazmat.primitives import hashes, hmac

  # Emulation of XcHMAC
  def HMAC(key, input1 = None, input2 = None):
    h = hmac.HMAC(key, hashes.SHA1(), backend=default_backend())
    if input1 is not None:
      h.update(input1)
    if input2 is not None:
      h.update(input2)
    return h.finalize()
except:
  #FIXME: Check if Xbox can do calls
  #       (Optional, to not exclude some xboxpy backends)

  print("Warning: Unable to find pyca/cryptography! Key correctness will not be verified.")
  pass


def get_XboxEEPROMKey():
  return memory.read(ke.XboxEEPROMKey(), 16)

def get_XboxCERTKey():

  # XboxCERTKey is just infront of XboxHDKey
  cert_key = memory.read(ke.XboxHDKey() - 16, 16)

  # As we guessed the key, we'll try to verify it with known derived keys
  if 'HMAC' in globals():
    cert_address = memory.read_u32(0x10000 + 0x118)
    cert_lan_key = memory.read(cert_address + 0xB0, 16)
    derived_lan_key = HMAC(cert_key, cert_lan_key)[0:16]
    expected_lan_key = memory.read(ke.XboxLANKey(), 16)
    assert(derived_lan_key == expected_lan_key)

  return cert_key

print()
print("These keys are protected by law.")
print("Do not redistribute them.")
print()

XboxEEPROMKey = get_XboxEEPROMKey()
print("EEPROM key: %s" % XboxEEPROMKey.hex().upper())

XboxCERTKey = get_XboxCERTKey()
print("CERT key: %s" % XboxCERTKey.hex().upper())

print()

with open('keys.bin', 'wb') as f:
  f.write(XboxEEPROMKey)
  f.write(XboxCERTKey)

  print("Wrote keys to keys.bin")
