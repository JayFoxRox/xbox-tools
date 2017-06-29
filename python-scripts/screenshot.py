#!/usr/bin/env python3

# Takes a screenshot

from xbox import *

from PIL import Image

def screenshot(path):
  #FIXME: Move some of this stuff into xbox module

	base = 0xFD000000
	def crtc_read(i):
		write_u8(base + 0x6013D4, i)
		return read_u8(base + 0x6013D5)
	pitch = crtc_read(0x13)
	pitch |= (crtc_read(0x19) & 0xE0) << 3
	pitch |= (crtc_read(0x25) & 0x20) << 6
	pitch *= 8
	bytes_per_pixel = crtc_read(0x28) & 0x7F #FIXME: 3 when it's actually 4..
	is_565 = False if bytes_per_pixel != 2 else (read_u32(base + 0x680600) & 0x1000) > 0
	framebuffer_addr = 0x80000000 | read_u32(base + 0x600800)
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
		width = (crtc_read(VGA_CRTC_H_DISP) + 1) * 8
		height = crtc_read(VGA_CRTC_V_DISP_END)
		height |= (crtc_read(VGA_CRTC_OVERFLOW) & 0x02) << 7
		height |= (crtc_read(VGA_CRTC_OVERFLOW) & 0x40) << 3
		height += 1;

	print(str(width) + " x " + str(height))

	framebuffer_data = read(framebuffer_addr, pitch * height)

	screenshot = Image.new('RGB', (width, height))
	pixels = screenshot.load()
	for y in range (0,height):
		for x in range (0,width):
			if bytes_per_pixel == 3:
				p = y * pitch + x * 4
				b = framebuffer_data[p + 0]
				g = framebuffer_data[p + 1]
				r = framebuffer_data[p + 2]
				a = framebuffer_data[p + 3]
			else:
				p = y * pitch + x * 2
				if is_565:
					#FIXME: Untested!
					b = framebuffer_data[p + 0] & 0x1F
					g = (framebuffer_data[p + 0] >> 5) & 0x7
					g |= framebuffer_data[p + 1] & 0x7
					r = (framebuffer_data[p + 1] >> 3) & 0x1F
					#FIXME: Bring to [0, 255] range?!
					a = 0

					b = int(r / 0x1F * 0xFF)
					g = int(g / 0x1F * 0xFF)
					r = int(b / 0x1F * 0xFF)
					# alpha is zero anyway, needs no rescaling

				else:
					#FIXME: Untested!
					b = framebuffer_data[p + 0] & 0x1F
					g = (framebuffer_data[p + 0] >> 5) & 0x7
					g |= framebuffer_data[p + 1] & 0x3
					r = (framebuffer_data[p + 1] >> 2) & 0x1F
					a = (framebuffer_data[p + 1] >> 7) & 0x1

					b = int(r / 0x1F * 0xFF)
					g = int(g / 0x3F * 0xFF)
					r = int(b / 0x1F * 0xFF)
					a = int(a / 0x1 * 0xFF)

			pixels[x, y]=(r,g,b)

	screenshot.save(path)

screenshot("screenshot.png")
