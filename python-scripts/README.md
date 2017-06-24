# Xbox python scripts

This is a collection of scripts to access various Xbox hardware.

## Usage

### GDB Interface

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
(gdb) source memory_gdb.py
(gdb) source audio.py
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

### XBDM Interface

This interface depends on hooking the XBDM `resume` function.

```
gdb -ex "source memory.py" -ex "source pe.py" -ex 'source memory_xbdm.py' -ex "source audio.py" -ex "source dsp.py" -ex "py dsp_status()"
```
