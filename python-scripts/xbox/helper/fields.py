#FIXME: Move to some common space
def GetMask(mask):
  if type(mask) is tuple:
    return ((1 << (mask[0] - mask[1] + 1)) - 1) << mask[1]
  return mask

def ffs(x):
    """Returns the index, counting from 0, of the
    least significant set bit in `x`.
    """
    return (x&-x).bit_length()-1

def GetMasked(storage, mask):
  return (storage & mask) >> ffs(mask)

def SetMasked(storage, mask, value):
  value = value << ffs(mask)
  return (storage & ~mask) | (value & mask)

