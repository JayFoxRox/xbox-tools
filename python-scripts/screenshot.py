#!/usr/bin/env python3

# Takes a screenshot

from xboxpy import *

from PIL import Image

def screenshot(path):
  #FIXME: Move some of this stuff into xbox module


  pitch = nv2a.ReadCRTC(0x13)
  pitch |= (nv2a.ReadCRTC(0x19) & 0xE0) << 3
  pitch |= (nv2a.ReadCRTC(0x25) & 0x20) << 6
  pitch *= 8
  bytes_per_pixel = nv2a.ReadCRTC(0x28) & 0x7F #FIXME: 3 when it's actually 4..
  is_565 = False if bytes_per_pixel != 2 else (nv2a.read_u32(0x680600) & 0x1000) > 0
  framebuffer_addr = nv2a.read_u32(0x600800)
  print("fb: " + format(framebuffer_addr, '08X'))
  print("pitch: " + str(pitch))
  print("565: " + str(is_565))
  print("bytes_per_pixel: " + str(bytes_per_pixel))

  # Stolen from QEMU:
  if False: #  if (s->vbe_regs[VBE_DISPI_INDEX_ENABLE] & VBE_DISPI_ENABLED) {
    #      width = s->vbe_regs[VBE_DISPI_INDEX_XRES];
    #      height = s->vbe_regs[VBE_DISPI_INDEX_YRES];
    assert(False)
  else:
    VGA_CRTC_H_DISP     = 1
    VGA_CRTC_OVERFLOW   = 7
    VGA_CRTC_V_DISP_END = 0x12
    width = (nv2a.ReadCRTC(VGA_CRTC_H_DISP) + 1) * 8
    height = nv2a.ReadCRTC(VGA_CRTC_V_DISP_END)
    height |= (nv2a.ReadCRTC(VGA_CRTC_OVERFLOW) & 0x02) << 7
    height |= (nv2a.ReadCRTC(VGA_CRTC_OVERFLOW) & 0x40) << 3
    height += 1;

  print(str(width) + " x " + str(height))

  framebuffer_data = read(framebuffer_addr, pitch * height, True)

  # FIXME: Why does this happen?!
  if bytes_per_pixel == 3:
    bytes_per_pixel = 4

  unswizzled = nv2a.Unswizzle(framebuffer_data, bytes_per_pixel * 8, (width, height), pitch)

  screenshot = Image.new('RGB', (width, height))
  pixels = screenshot.load()
  for y in range (0,height):
    for x in range (0,width):
      p = y * pitch + x * bytes_per_pixel
      if bytes_per_pixel == 4:
        b = unswizzled[p + 0]
        g = unswizzled[p + 1]
        r = unswizzled[p + 2]
        a = unswizzled[p + 3]
      else:
        if is_565:
          #FIXME: Untested!
          b = unswizzled[p + 0] & 0x1F
          g = (unswizzled[p + 0] >> 5) & 0x7
          g |= unswizzled[p + 1] & 0x7
          r = (unswizzled[p + 1] >> 3) & 0x1F
          #FIXME: Bring to [0, 255] range?!
          a = 0

          b = int(r / 0x1F * 0xFF)
          g = int(g / 0x1F * 0xFF)
          r = int(b / 0x1F * 0xFF)
          # alpha is zero anyway, needs no rescaling

        else:
          #FIXME: Untested!
          b = unswizzled[p + 0] & 0x1F
          g = (unswizzled[p + 0] >> 5) & 0x7
          g |= unswizzled[p + 1] & 0x3
          r = (unswizzled[p + 1] >> 2) & 0x1F
          a = (unswizzled[p + 1] >> 7) & 0x1

          b = int(r / 0x1F * 0xFF)
          g = int(g / 0x3F * 0xFF)
          r = int(b / 0x1F * 0xFF)
          a = int(a / 0x1 * 0xFF)

      pixels[x, y]=(r,g,b)

  screenshot.save(path)

screenshot("screenshot.png")
