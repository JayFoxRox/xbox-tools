import os
import sys

from . import api

# Helper to find the target

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
  used_interface = os.environ['XBOX_IF'].strip().lower()
except:
  used_interface = None

if used_interface == None or used_interface == 'xbdm':
  print("Using XBDM interface")
  from . import if_xbdm
elif used_interface == 'gdb':
  print("Using gdb interface")
  from . import if_gdb
elif used_interface == 'nxdk-rdt':
  print("Using nxdk-rdt interface")
  from . import if_nxdk_rdt
else:
  print("Unknown interface '" + used_interface + "'")
  sys.exit(1)
