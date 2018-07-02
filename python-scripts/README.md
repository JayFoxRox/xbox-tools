# Xbox python scripts

This is a collection of scripts to access various Xbox hardware.


## Usage for updated scripts

Some code might be using [xboxpy](https://github.com/XboxDev/xboxpy) already.
Please check the respective xboxpy documentation.

Also initialize the submodules to be able use those scripts:

```
git submodule update --init --recursive
```


## Usage for legacy scripts

* All stuff is internally imported by the `xbox` module. So: `import xbox`
* You can define the interface you want to use using environment variable 'XBOX_IF':
  * 'XBDM' (default)
  * 'nxdk-rdt`
  * 'gdb' (auto-detected if the `gdb` module exists)
* Some interfaces will also allow you to specify the target Xbox using the 'XBOX' environment variable ('Host:Port')

Not all interfaces support all functionality at this point.
