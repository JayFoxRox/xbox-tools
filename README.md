# dump-xbox.c

Compile using OpenXDK, put in writeable path on xbox HDD with a couple of free MB.
Run and copy bin files back to your PC for analsis / use in xqemu

## Dumped files

* flash.bin: Image of the Flash ROM lower 1MB
* eeprom.bin: Image of the first 256 bytes of EEPROM
* hdd_A-B.bin: Dump of sector number A to sector number B

## Dumping the MCPX / 2BL / RC4 Keys

Dumping the secret southbridge ROM (including the RC4 Key) is very hard and not possible (yet?).
The 2BL is also only ever visible before it could be dumped in software.
You can do it with hardware attacks only at the moment.

# disassemble-mcpx.sh

Disassembles the MCPX using objdump and helps aligning the code. Also adds comments based on addresses.
Only working for MCPX 1.0.
