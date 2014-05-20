#!/bin/bash

# Config area

XQEMU_PATH=../xqemu/
XQEMU_BIOS=Complex_4627.bin

# Wanted feature list:
#
# * Make bios an option
# * Support for "QEMU_AUDIO_DRV=none"?
# * Add "debug"
# * Add "make"
#

reset
clear

kvm=1
gdb=0
level=0
x2=0
usb=0
apitrace=0
dvd=""
skip_animation=1
fatal=0
make=0
sw_renderer=0

while [ $# -ne 0 ]; do

  if [ "$1" == "-" ]; then
    shift
    break
  elif [ "$1" == "make" ]; then
    make=1
  elif [ "$1" == "sw" ]; then
    sw_renderer=1
  elif [ "$1" == "tcg" ]; then
    kvm=0
  elif [ "$1" == "gdb" ]; then
    gdb=1
  elif [ "$1" == "fatal" ]; then
    fatal=1
  elif [ "$1" == "logo" ]; then
    skip_animation=0
  elif [ "$1" == "usb" ]; then
    usb=1
  elif [ "$1" == "apitrace" ]; then
    apitrace=1
#  elif [ "$1" == "cachegrind" ]; then
#    cachegrind=1
  elif [ "$1" == "x2" ]; then
    x2=1
  elif [ "${1:0:4}" == "dvd:" ]; then
    dvd="${1:4}"
    echo "Loading <$dvd>"
  elif [ "$1" == "mcpx-hle" ]; then
    level=1
#  elif [ "$1" == "2bl-hle" ]; then
#    level=2
#  elif [ "$1" == "kernel" ]; then
#    level=3
  else
    echo "Unknown argument '$1'"
    exit 1
  fi

  shift

done

if [ $make -ne 0 ]; then
  eval make -C $XQEMU_PATH
  if [ $? -ne 0 ]; then
    exit
  fi
fi

echo "Running level $level, KVM $kvm"

# Construct the command line

PREFIX=""
SUFFIX=""
MACHINE=",xbox_eeprom=eeprom-bunnie.bin"

if [ $sw_renderer -ne 0 ]; then
  export LIBGL_ALWAYS_SOFTWARE=1
fi

if [ $apitrace -ne 0 ]; then
  PREFIX="apitrace trace -a gl $PREFIX"
fi

if [ $gdb -ne 0 ]; then
  SUFFIX="$SUFFIX -s -S"
fi

if [ $kvm -ne 0 ]; then
  ACCEL="kvm,kernel_irqchip=off"
else
  ACCEL="tcg"
fi

# These are probably all wrong because they are from OpenXDK or something [Super Mario War]
# A real Xbox gamepad seems to have an internal hub and the actual gamepad is connected to that!
USB_PORT_P1="bus=usb-bus.1,port=3"
USB_PORT_P2="?"
USB_PORT_P3="?"
USB_PORT_P4="bus=usb-bus.1,port=2"
if [ $usb -ne 0 ]; then
  SUFFIX="$SUFFIX -usb -device usb-host,$USB_PORT_P1,vendorid=0x45e,productid=0x289"
else
  SUFFIX="$SUFFIX -usb -device usb-xbox-gamepad,$USB_PORT_P1"
fi

if [ $x2 -ne 0 ]; then
  MACHINE="$MACHINE,mcpx_xmode=2"
else
  MACHINE="$MACHINE,mcpx_xmode=3"
fi

MACHINE="$MACHINE,xbox_smc_scratch=$((fatal*2+skip_animation*4))"

if [ $level -ge 3 ]; then
  BOOT=",xbox_kernel=xboxkrnl.exe"
elif [ $level -ge 2 ]; then
  BOOT=",xbox_kernel_key=.."
elif [ $level -ge 1 ]; then
#  BOOT=",xbox_bootloader_key="
  BOOT=""
else
  BOOT=",mcpx_rom=mcpx_1.0.bin"
fi

if [ "$dvd" == "" ]; then
  DVDROM=""
else
  if [ -d "$dvd" ]; then
    echo "Creating xiso.."
    #tmpdvd=$(mktemp -u)
    tmpdvd="/tmp/xqemu-dvd.xiso"
    eval extract-xiso -c "$dvd" "$tmpdvd"
    dvd="$tmpdvd"
  fi
  if [ -f "$dvd" ]; then
    DVDROM=",file='$dvd'"
  else
    echo "Unknown DVD type"
  fi
fi

CLI="$PREFIX ${XQEMU_PATH}xbox-softmmu/qemu-system-xbox -cpu pentium3 -m 64 -bios $XQEMU_BIOS -drive file=xbox_harddisk.qcow2,index=0,media=disk,locked=on -drive index=1,media=cdrom$DVDROM$SUFFIX -machine xbox$BOOT$MACHINE,accel=$ACCEL,$*"
echo "Running <$CLI>"
eval $CLI
