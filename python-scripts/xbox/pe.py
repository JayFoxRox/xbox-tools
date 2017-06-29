from .memory import *

def resolve_export(ordinal, image_base=0x80010000):
  #FIXME: If this is a string, look up its ordinal
  TempPtr = read_u32(image_base + 0x3C);
  TempPtr = read_u32(image_base + TempPtr + 0x78);
  ExportCount = read_u32(image_base + TempPtr + 0x14);
  ExportBase = image_base + read_u32(image_base + TempPtr + 0x1C);
  #FIXME: Read all exports at once and parse them locally
  
  #for i in range(0, ExportCount):
  #  ordinal = i + 1
  #  print("@" + str(ordinal) + ": 0x" + format(image_base + read_u32(ExportBase + i * 4), '08X'))

  index = (ordinal - 1) # Ordinal
  #assert(index < ExportCount) #FIXME: Off by one?
  return image_base + read_u32(ExportBase + index * 4)
