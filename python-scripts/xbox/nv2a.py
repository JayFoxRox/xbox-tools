from . import memory

def read_u8(address):
  return memory.read_u8(0xFD000000 + address)
def read_u16(address):
  return memory.read_u16(0xFD000000 + address)
def read_u32(address):
  return memory.read_u32(0xFD000000 + address)

def write_u8(address, value):
  memory.write_u8(0xFD000000 + address, value)
def write_u16(address, value):
  memory.write_u16(0xFD000000 + address, value)
def write_u32(address, value):
  memory.write_u32(0xFD000000 + address, value)

def ReadCRTC(i):
  write_u8(0x6013D4, i)
  return read_u8(0x6013D5)

#FIXME: Swizzler ported from XQEMU.. does not work - WHY?!

def GenerateSwizzleMask(size):
  bit = 1
  mask_bit = 1
  x = 0
  y = 0
  z = 0
  done = False
  while not done:
    done = True
    if bit < size[0]:
      x |= mask_bit
      mask_bit <<= 1
      done = False
    if bit < size[1]:
      y |= mask_bit
      mask_bit <<= 1
      done = False
    if bit < size[2]:
      z |= mask_bit
      mask_bit <<= 1
      done = False
    bit <<= 1
  assert(x ^ y ^ z == (mask_bit - 1))
  return (x, y, z)

# This fills a pattern with a value if your value has bits abcd and your
# pattern is 11010100100 this will return: 0a0b0c00d00
def _FillPattern(pattern, value):
  result = 0
  bit = 1
  while value > 0:
    if (pattern & bit):
      result |= bit if (value & 1) else 0
      value >>= 1
    bit <<= 1
  return result

def GetSwizzledOffset(offset, mask, bits_per_pixel):
  assert(bits_per_pixel % 8 == 0)
  new_offset  = _FillPattern(mask[0], offset[0])
  new_offset |= _FillPattern(mask[1], offset[1])
  new_offset |= _FillPattern(mask[2], offset[2])
  return (bits_per_pixel // 8) * new_offset

def Swizzle():
  assert(False)

def _Unswizzle(data, bits_per_pixel, size, pitch):
  assert(bits_per_pixel % 8 == 0)
  bytes_per_pixel = bits_per_pixel // 8

  if len(size) == 2:
    size = (size[0], size[1], 1)
    pitch = (pitch, 0)
  elif len(size) == 3:
    assert(len(pitch) == 2)
  else:
    assert(False) # Unknown size

  data = bytes(data)
  unswizzled = bytearray([0] * len(data))

  print(size)
  mask = GenerateSwizzleMask(size)
  print(bin(mask[0]).rjust(34))
  print(bin(mask[1]).rjust(34))
  print(bin(mask[2]).rjust(34))

  for z in range(0, size[2]):
    for y in range(0, size[1]):
      for x in range(0, size[0]):
        src = GetSwizzledOffset((x, y, z), mask, bits_per_pixel)
        dst = z * pitch[1] + y * pitch[0] + x * bytes_per_pixel

        for i in range(0, bytes_per_pixel):
          b = data[src+i]
          unswizzled[dst+i] = b
        #unswizzled[dst:dst + bytes_per_pixel] = data[src:src + bytes_per_pixel]

      #if y == 190:
      #  return unswizzled


  return bytes(unswizzled)


# Ugly unswizzle code by xbox7887 follows
block = [ 0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 15,
         18, 19,
         16, 17,
         22, 23,
         20, 21,
         26, 27,
         24, 25,
         30, 31,
         28, 29,
         33, 34, 35,
         32,
         37, 38, 39,
         36,
         41, 42, 43,
         40,
         45, 46, 47,
         44,
         51,
         48, 49, 50,
         55,
         52, 53, 54,
         59,
         56, 57, 58,
         63,
         60, 61, 62 ]
def Unswizzle(data, bits_per_pixel, size, pitch):
  data = bytes(data)
  unswizzled = bytearray([0] * len(data))

  assert(len(size) == 2)
  assert(size[0] == 640)
  assert(size[1] == 480)

  swiz = 0
  index = 0
  offset = 0
  deswiz = 0

  for y in range(0, 480): # 30
      for x in range(0, 640): # 10
          blockX = x // 64
          blockY = y // 16

          offY = y % 16
          offX = x % 64

          if offX != 0:
              continue

          for l in range(0, 4):
                index = l * 16 + offY
                bv = block[index]
                offset = ((bv // 4) * 256) + ((bv % 4) * 16)

                for i in range(0, 4):
                    for v in range(0, 4):
                          s = (blockY * 10 + blockX) * 4096
                          s += i * 64

                          d = 0
                          d += 2560*479 # Go to end of image
                          d -= blockY * (17 * 2560) # Go up 17 lines?!
                          d += (blockY * 10 + blockX) * (16 * 2560 + 256)
                          d -= ((blockY * 10 + blockX) * 4 + l) * (4 * 2560 + 256)
                          d += (((blockY * 10 + blockX) * 4 + l) * 16 + offY) * 16
                          d -= 2560 * i

                          if True:
                            if ((blockY & 1) == 1):
                                if ((blockX & 1) == 1):
                                  d -= 256
                                else:
                                  d += 256

                          for channel in range(0, 3):
                            o = v * 4 + channel
                            b = data[s + offset + o]
                            unswizzled[d + o] = b

  flipped = bytearray([0] * len(unswizzled))
  for i in range(0, size[1]):
    flipped[i*2560:(i+1)*2560] = unswizzled[-2560*(i+1):-2560*i]

  return bytes(flipped)
