import sys
import os
import imp

try:
  imp.find_module('gdb')
  os.environ['XBOX-IF'] = 'gdb'
except ImportError:
  pass

# Add ourselves to the module path first
if not "" in sys.path:
  sys.path += [""]

# Now load the API
from xbox import *
