from . import api
from . import get_xbox_address
import socket
from .dbg_pb2 import *

(HOST, PORT) = get_xbox_address(9269)

rdt = socket.create_connection((HOST, PORT), 5)

def _send_simple_request(req, buffer_size=256):
  """Send a simple request, expect success"""
  rdt.send(req.SerializeToString())
  res = Response()
  res.ParseFromString(rdt.recv(buffer_size))
  if res.type != Response.OK:
    raise XboxError(res.msg)
  return res

def read(address, size, physical):
  # nxdk-rdt is very buggy.. it needs all data in one network packet
  # in order to make this work, we split large reads into chunks
  N = 256
  if size > N:
    chunk = read(address, N, physical) # Do read
    return chunk + read(address + N, size - N, physical) # Process rest of data
  if physical:
    adddress |= 0x80000000
  req = Request()
  req.type = Request.MEM_READ
  req.size = size
  req.address = address
  res = _send_simple_request(req, size + 256)
  return res.data

def write(address, data, physical):
  # nxdk-rdt is very buggy.. it needs all data in one network packet
  # in order to make this work, we split large writes into chunks
  N = 256
  if len(data) > N:
    write(address, data[0:N], physical) # Do write
    return write(address + N, data[N:], physical) # Process rest of data
  if physical:
    adddress |= 0x80000000
  req = Request()
  req.type = Request.MEM_WRITE
  req.data = bytes(data)
  req.address = address
  res = _send_simple_request(req)

def call(address, stack, registers=None):
  req = Request()
  req.type = Request.CALL
  req.address = address
  req.data = stack
  #FIXME: req.registers = registers
  res = _send_simple_request(req)
  out_registers = {}
  out_registers['eax'] = res.address
  return out_registers

api.read = read
api.write = write
api.call = call
