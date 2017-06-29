# Xbox python scripts

This is a collection of scripts to access various Xbox hardware.

## Usage

* All stuff is internally imported by the `xbox` module. So: `import xbox`
* You can define the interface you want to use using environment variable 'XBOX-IF':
  * 'XBDM' (default)
  * 'NXDK-RDT'
  * 'gdb' (auto-detected if the `gdb` module exists)
* Some interfaces will also allow you to specify the target Xbox using the 'XBOX' environment variable ('Host:Port')

Not all interfaces support all functionality at this point.
