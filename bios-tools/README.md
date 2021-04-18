# bios-tools

These tools have been developed out of frustration with existing tools.
However, they aren't meant for out-of-the-box use and just make the situation worse.

---


**Some of these files must be assembled using nasm before the Python scripts work!**


### extract-bios

Extracts an xboxkrnl.exe and the parameters passed to it.

This is done by emulating the Xbox, so it will not work for BFM images.
It doesn't emulate a specific Xbox version, so some bioses might have issues patching their kernel.

This script works.

**Example:**

```
python3 extract-bios.py mcpx_rom.bin flash.bin eeprom.bin
```

The EEPROM image is optional and only some bioses will require it.


### load-2bl

A port of PBL-1.3 to Python / xboxpy.
Includes code-segment resize patch introduced PBL Metoo Edition.

This only works for standard BFM bioses.
Bioses using custom packaging such as "$EvoxRom$" will not work.

There's not always enough room (and in the right locations!) for Loading a 1 MiB bios.
So it's recommended to reboot to a low-memory application (like the XDK launcher).

**Example:**

```
python3 load-2bl.py decrypted_2bl.bin flash.bin rc4_key.bin 
```

The RC4 key (which was used for 2BL encryption) is optional and is used to verify that the 2BL is fine.


### load-xboxkrnl

An tool similar to load-2bl, but able to load xboxkrnl.exe directly.

This tool might depend on some co-operation by the kernels.
Support for non BFM kernels not guaranteed to work.

**Example:**

```
python3 load-xboxkrnl.py xboxkrnl.exe xboxkrnl_parameters.bin xboxkrnl_key.bin
```

---


**(C) 2018 Jannik Vogel**

All rights reserved.
