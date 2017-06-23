# Xbox python scripts

This is a collection of scripts to access various Xbox hardware.

## Usage:

Connect GDB to target. For example:

```
$ gdb
...
(gdb) target remote :1234
...
Remote debugging using :1234
```

Now source the python scripts you intend to use (memory.py should always be loaded):

```
(gdb) source memory.py
(gdb) source dsp.py
```

*Note that you have to `source` the files again after modifications*

Run the python functions you need:

```
(gdb) py dsp_status()
Voices SGE stored at 0x03A44000
Voices stored at 0x03A50000
Active List: 1 (2D_TOP)
Top voice: 0x0048
...
```

