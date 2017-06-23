# UGLY! Just use ida instead..

start=""
ignore=1
nextcomment=""
mode="-"

file="$1"; shift

md5=($(md5sum --binary "$file"))

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
  if [ $mode = "b" ]; then printf "%x: " $start; od -w512 -t x1 -A none -j $[start-0xFFFFFE00] -N $length $file; fi
  start=$stop
  comment="$nextcomment"
}

function d() { p $1 "$2" $*; mode="d"; }
function i() { p $1 "$2" $*; mode="i"; }
function b() { p $1 "$2" $*; mode="b"; }
function x() { p $1 "$2" $*; mode="x"; }

options=$*

if [ $md5 = "196a5f59a13382c185636e691d6c323d" ]; then # MCPX 1.0 (Bad dump)
  echo "You dumped the MCPX badly; it's a couple bytes off."
  echo "It should start with '33 c0' and end with '02 ee'."
elif [ $md5 = "d49c52a4102f6df7bcf8d0617ac475ed" ]; then # MCPX 1.0
  d  0xFFFFFE00 "Set segment selectors"
  d  0xFFFFFE0A "X-Code initialize IP"
  d  0xFFFFFE0F "X-Code fetch"
  d  0xFFFFFE17 "X-Code 0x07: PREFIX: EDX=ECX; AL=BL; EBX=ECX; ECX=EDI"
  d  0xFFFFFE23 "X-Code 0x02: EDI = READ32(EBX & 0x0FFFFFFF)"
  d  0xFFFFFE34 "X-Code 0x03: WRITE32(EBX, ECX)"
  d  0xFFFFFE3C "X-Code 0x06: EDI = (EDI & EBX) | ECX"
  d  0xFFFFFE46 "X-Code 0x04: PCI_WRITE32(EBX, ECX)"
  d  0xFFFFFE64 "X-Code 0x05: EDI = PCI_READ32(EBX)"
  d  0xFFFFFE77 "X-Code 0x08: IF (EDI != EBX): ESI += ECX"
  d  0xFFFFFE83 "X-Code 0x09: ESI += ECX"
  d  0xFFFFFE8B "X-Code 0x10: EDI = EBP = (EBP & EBX) | ECX ?"
  d  0xFFFFFE97 "X-Code 0x11: IO_WRITE8(BX, CL)"
  d  0xFFFFFEA2 "X-Code 0x12: EDI = IO_READ8(BX)"
  d  0xFFFFFEAE "X-Code 0xEE: EXIT"
  d  0xFFFFFEB4 "X-Code loop to fetch"
  d  0xFFFFFEBC "MTRR Setup"
  d  0xFFFFFED2 "MTRR Turn on cache"
  d  0xFFFFFEDD "RC4 KSA Initliaze S-Box Loop init"
  d  0xFFFFFEEE "RC4 KSA Initliaze S-Box Loop"
  d  0xFFFFFEFB "RC4 KSA Mix S-Box with key Loop init"
  d  0xFFFFFF12 "RC4 KSA Mix S-Box with key Loop"
  d  0xFFFFFF3C "RC4 PRGA Output Loop init"
  d  0xFFFFFF5A "RC4 PRGA Output Loop"
  d  0xFFFFFF81 "RC4 Success check"
  d  0xFFFFFF8D "RC4 Success check ok: Jump to 2BL"
  d  0xFFFFFF94 "RC4 Success check fail: Disable MCPX ROM + Attempt to double fault"
  b  0xFFFFFFA5 "RC4 Key"
  d  0xFFFFFFB5 "NOP" # Different on 1.1!
  x  0xFFFFFFB8 "Startup Set up global descriptor table"
  x  0xFFFFFFBF "Startup Set up interrupt descriptor table"
  x  0xFFFFFFC6 "Startup Switch to protected mode"
  b  0xFFFFFFD4 "?"
  b  0xFFFFFFD8 "GDT/IDT"
  x  0xFFFFFFF0 "Entrypoint"
  i  0xFFFFFFF2 "Align"
  b  0xFFFFFFF4 "GDT/IDT Pointer"
  d  0xFFFFFFFA "Double fault"
  i 0x100000000 "End"
elif [ $md5 = "2870d58a459c745d7cc4c6122ceb3dcb" ]; then # MCPX 1.1
  d  0xFFFFFE00 "Set segment selectors"
  d  0xFFFFFE0A "X-Code initialize IP"
  d  0xFFFFFE0F "X-Code fetch"
  d  0xFFFFFE17 "X-Code 0x07: PREFIX: EDX=ECX; AL=BL; EBX=ECX; ECX=EDI"
  d  0xFFFFFE23 "X-Code 0x02: EDI = READ32(EBX & 0x0FFFFFFF)"
  d  0xFFFFFE34 "X-Code 0x03: WRITE32(EBX, ECX)"
  d  0xFFFFFE3C "X-Code 0x06: EDI = (EDI & EBX) | ECX"
  d  0xFFFFFE46 "X-Code 0x04: PCI_WRITE32(EBX, ECX)"
  d  0xFFFFFE64 "X-Code 0x05: EDI = PCI_READ32(EBX)"
  d  0xFFFFFE77 "X-Code 0x08: IF (EDI != EBX): ESI += ECX"
  d  0xFFFFFE83 "X-Code 0x09: ESI += ECX"
  d  0xFFFFFE8B "X-Code 0x10: EDI = EBP = (EBP & EBX) | ECX ?"
  d  0xFFFFFE97 "X-Code 0x11: IO_WRITE8(BX, CL)"
  d  0xFFFFFEA2 "X-Code 0x12: EDI = IO_READ8(BX)"
  d  0xFFFFFEAE "X-Code 0xEE: EXIT"
  d  0xFFFFFEB4 "X-Code loop to fetch"
  d  0xFFFFFEBC "MTRR Setup"
  d  0xFFFFFED2 "MTRR Turn on cache"
  d  0xFFFFFEDD "TEA data loop init"
  d  0xFFFFFEFE "TEA data loop body"
  d  0xFFFFFF17 "TEA inner loop count init?"
  d  0xFFFFFF19 "TEA inner loop body"
  d  0xFFFFFF5C "TEA inner loop exit"
  d  0xFFFFFF71 "TEA data loop exit + TEA Success check"
  d  0xFFFFFF86 "TEA Success check ok: Jump to FBL"
  d  0xFFFFFF8B "TEA Success check fail: Disable MCPX ROM + Attempt to double fault"
  b  0xFFFFFF9C "???"
  b  0xFFFFFFA8 "Expected TEA hash"
  x  0xFFFFFFB8 "Startup Set up global descriptor table"
  x  0xFFFFFFBF "Startup Set up interrupt descriptor table"
  x  0xFFFFFFC6 "Startup Switch to protected mode"
  b  0xFFFFFFD4 "?"
  b  0xFFFFFFD8 "GDT/IDT"
  x  0xFFFFFFF0 "Entrypoint"
  i  0xFFFFFFF2 "Align"
  b  0xFFFFFFF4 "GDT/IDT Pointer"
  d  0xFFFFFFFA "Double fault"
  i 0x100000000 "End"
else
  echo "Unknown MCPX version."
fi


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
