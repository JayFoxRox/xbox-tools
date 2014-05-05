# UGLY! Just use ida instead..

start=""
ignore=1
nextcomment=""
mode="-"

file=$1; shift

function p() {
  stop=$1; shift
  nextcomment="$1"; shift
  length=$[stop-start]
  if [ ! "$comment" = "" ]; then
    echo ""
    echo "$comment ($length bytes)"
  fi
  echo ""
  if [ $mode = "d" ]; then objdump -D -bbinary -mi386 --adjust-vma=0xFFFFFE00 --start-address=$start --stop-address=$stop -z -w $file $options | tail -n +8; fi
  if [ $mode = "x" ]; then objdump -D -bbinary -mi8086 --adjust-vma=0xFFFFFE00 --start-address=$start --stop-address=$stop -z -w $file $options | tail -n +8; fi
  if [ $mode = "i" ]; then echo "<ignored>"; fi
  if [ $mode = "b" ]; then od -t x1 -A none -j $[start-0xFFFFFE00] -N $length $file; fi
  start=$stop
  comment="$nextcomment"
}

function d() { p $1 "$2" $*; mode="d"; }
function i() { p $1 "$2" $*; mode="i"; }
function b() { p $1 "$2" $*; mode="b"; }
function x() { p $1 "$2" $*; mode="x"; }

options=$*

# MCPX 1.0
d  0xFFFFFE00 "Set segment selectors"
d  0xfffffe0A "X-Code initialize IP"
d  0xfffffe0f "X-Code fetch"
d  0xFFFFFE17 "X-Code 0x07: PREFIX: EDX=ECX; AL=BL; EBX=ECX; ECX=EDI"
d  0xFFFFFE23 "X-Code 0x02: EDI = READ32(EBX & 0x0FFFFFFF)"
d  0xfffffe34 "X-Code 0x03: WRITE32(EBX, ECX)"
d  0xfffffe3C "X-Code 0x06: EDI = (EDI & EBX) | ECX"
d  0xfffffe46 "X-Code 0x04: PCI_WRITE32(EBX, ECX)"
d  0xfffffe64 "X-Code 0x05: EDI = PCI_READ32(EBX)"
d  0xfffffe77 "X-Code 0x08: IF (EDI != EBX): ESI += ECX"
d  0xfffffe83 "X-Code 0x09: ESI += ECX"
d  0xfffffe8B "X-Code 0x10: EDI = EBP = (EBP & EBX) | ECX ?"
d  0xfffffe97 "X-Code 0x11: IO_WRITE8(BX, CL)"
d  0xfffffea2 "X-Code 0x12: EDI = IO_READ8(BX)"
d  0xfffffeae "X-Code 0xEE: EXIT"
d  0xfffffeb4 "X-Code loop to fetch"
d  0xfffffebc "MTRR Setup"
d  0xFFFFFED2 "MTRR Turn on cache"
d  0xfffffedd "RC4 KSA Initliaze S-Box Loop init"
d  0xfffffeee "RC4 KSA Initliaze S-Box Loop"
d  0xfffffefb "RC4 KSA Mix S-Box with key Loop init"
d  0xffffff12 "RC4 KSA Mix S-Box with key Loop"
d  0xffffff3c "RC4 PRGA Output Loop init"
d  0xffffff5a "RC4 PRGA Output Loop"
d  0xffffff81 "RC4 Success check"
d  0xffffff8d "RC4 Success check ok: Jump to 2BL"
d  0xffffff94 "RC4 Success check fail: Disable MCPX ROM + Attempt to double fault"
b  0xFFFFFFA5 "RC4 Key"
d  0xFFFFFFB5 "NOP" # Different on 1.1!
x  0xFFFFFFB8 "Startup Set up global descriptor table"
x  0xffffffBF "Startup Set up interrupt descriptor table"
x  0xffffffc6 "Startup Switch to protected mode"
b  0xFFFFFFD4 "?"
b  0xFFFFFFD8 "GDT/IDT"
x  0xFFFFFFF0 "Entrypoint"
i  0xFFFFFFF2 "Align"
b  0xFFFFFFF4 "GDT/IDT Pointer"
d  0xFFFFFFFA "Double fault"
i 0x100000000 "End"


# Some notes:
# BIOS = Flash
# 2BL = bldr
# X-Codes = romdec
# MCPX Internal ROM = Secret BR = Southbridge ROM = Bootrom = part of romdec

# General flow:
# - MCPX Internal ROM

# Flow (MCPX 1.0):
# 0. MCPX checks first 0x40 bytes of flash, then resets the CPU
# 1. "Entrypoint" jumps directly to "Startup"
# 2. "Startup" loads GDT from ESI [where is that?!]
#  . ?
#  . X-Code IP set to 0xFF000080
#  . X-Code loops code
#    X-Code format is: { 1 byte opcode, 4 byte EBX, 4 byte ECX }
#  . X-Code 0xEE operations jumpts to MTRR setup
#  . MTRR setup finishes and goes into RC4
#  . RC4 Setup of S-Box (0x0008f000) to 01 02 03 04 05 06 ... FE FF
#...
#  . RC Decrypt 2BL from 0xFFFF9E00 to 0x00090000 [0x6000 bytes]
#  . RC4 is followed by a small success check to see if the last word of the 2BL was decrypted fine
#  .a Crash on fail
#  .b Jump to 2BL
