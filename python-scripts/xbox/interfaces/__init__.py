import os
import sys

def get_xbox_address(default_port, default_host = "localhost"):
  try:
    XBOX = os.environ['XBOX']
  except:
    XBOX = ""

  pt = XBOX.partition(":")
  HOST = pt[0].strip()
  if len(HOST) == 0:
    HOST = default_host
    print("Using default host '" + HOST + "'")
  PORT = 0
  if (pt[2] != ""):
    try:
      PORT = int(pt[2])
      if PORT < 0:
        print("Negative port number not allowed: '" + pt[2] + "'")
        PORT = 0
      elif PORT > 0xFFFF:
        print("Port number to high: '" + pt[2] + "'")
        PORT = 0
    except:
      print("Unable to parse port: '" + pt[2] + "'")
  if PORT == 0:
    PORT = default_port
    print("Using default port " + str(PORT))
  return (HOST, PORT)

try:
  interface = os.environ['XBOX-IF'].strip().lower()
except:
  interface = None

if interface == None or interface == 'xbdm':
  print("Using XBDM interface")
  from .memory_xbdm import *
elif interface == 'gdb':
  print("Using gdb interface")
  from .memory_gdb import *
elif interface == 'nxdk-rdt':
  print("Using NXDK-RDT interface")
  from .memory_nxdk_rdt import *
else:
  print("Unknown interface '" + interface + "'")
  sys.exit(1)
