def dsp_homebrew():
	#FIXME: Pass dsp object which provides all the device details and registers instead

	NV_PAPU_EPXMEM = 0x50000
	NV_PAPU_EPYMEM = 0x56000
	NV_PAPU_EPPMEM = 0x5A000

	NV_PAPU_EPSADDR = 0x2048
	NV_PAPU_EPSMAXSGE = 0x20DC

	NV_PAPU_EPRST = 0x5FFFC
	NV_PAPU_EPRST_EPRST    = 0x00000001
	NV_PAPU_EPRST_EPDSPRST = 0x00000002

	# Disable DSP
	dsp_write_u32(NV_PAPU_EPRST, NV_PAPU_EPRST_EPRST) # If this is zero, the EP will not allow reads/writes to memory?!
	time.sleep(0.1) # FIXME: Not sure if DSP reset is synchronous, so we wait for now

	# Allocate some scratch space (at least 2 pages!)
	page_count = 2
	page_head = MmAllocateContiguousMemory(4096)
	dsp_write_u32(NV_PAPU_EPSADDR, MmGetPhysicalAddress(page_head))
	page_base = MmAllocateContiguousMemory(4096 * page_count)
	for i in range(0, page_count):
		write_u32(page_head + i * 8 + 0, MmGetPhysicalAddress(page_base + 0x1000 * i))
		write_u32(page_head + i * 8 + 4, 0) # Control
	dsp_write_u32(NV_PAPU_EPSMAXSGE, page_count - 1)

  # See dsp_homebrew.inc
  # It was assembled using `a56 loop.inc && toomf < a56.out`.
  # The resulting code was then copied here.
  # `a56` (inc. `toomf`) can be found at: http://www.zdomain.com/a56.html
	code = "56F000 000000 5E7000 000000 0AF080 000000"

	# Write code to PMEM
	code_words = code.split()
	for i in range(0, len(code_words)):
		data = int(code_words[i], 16)
		dsp_write_u32(NV_PAPU_EPPMEM + i*4, data)
		# According to XQEMU, 0x800 * 4 bytes will be loaded from scratch to PMEM at startup.
		# So just to be sure, let's also write this to the scratch..
		write_u32(page_base + i*4, data)

	# Set XMEM
	dsp_write_u32(NV_PAPU_EPXMEM + 0*4, 0x001337)

	# Set YMEM
	dsp_write_u32(NV_PAPU_EPYMEM + 0*4, 0x000000)

	# Test readback
	print("Read back X:0x" + format(dsp_read_u32(NV_PAPU_EPXMEM + 0*4), '06X'))
	print("Read back Y:0x" + format(dsp_read_u32(NV_PAPU_EPYMEM + 0*4), '06X'))

	print("Read back P:0x" + format(dsp_read_u32(NV_PAPU_EPPMEM + 0*4), '06X'))
	print("Read back P:0x" + format(dsp_read_u32(NV_PAPU_EPPMEM + 1*4), '06X'))

	# Set frame duration (?!)
	NV_PAPU_SECTL = 0x2000
	dsp_write_u32(NV_PAPU_SECTL, 3 << 3)

	# Enable DSP
	# NV_PAPU_EPRST_EPRST < crashes!
	# NV_PAPU_EPRST_EPDSPRST < works!
	dsp_write_u32(NV_PAPU_EPRST, NV_PAPU_EPRST_EPRST | NV_PAPU_EPRST_EPDSPRST)
	time.sleep(0.1)

  # Write X again. Bootcode in the DSP seems to overwrites XMEM + YMEM
	dsp_write_u32(NV_PAPU_EPXMEM + 0*4, 0x001337)

	# Read destination data from YMEM
	print("Read back X:0x" + format(dsp_read_u32(NV_PAPU_EPXMEM + 0*4), '06X'))
	print("Read back Y:0x" + format(dsp_read_u32(NV_PAPU_EPYMEM + 0*4), '06X'))

dsp_homebrew()
