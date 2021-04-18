;; This is the bootloader for loading an undecrypted 2bl for BFMs
;; 
;; assemble using:
;;
;;   nasm load-2bl.asm
;;

bits 32

start:

  ;; Pop arguments from stack
  pop ebp ;; Pop return address (we don't need it)
  pop edx
  mov eax, [edx + 16] ;; EntryPoint2BL
  mov ecx, [edx + 20] ;; PhysicalRomPos (must be in ecx for EntryPoint2BL)

  ;; Old code for non-shutdown loader
  ;pop eax ;; EntryPoint2BL
  ;pop ecx ;; PhysicalRomPos (must be in ecx for EntryPoint2BL)

  ;; Push entry point to stack and leave space for CS segment
  push eax
  push eax

  ;; Disable interrupts
  cli

  ;; Make room on stack to get GDT pointer to eax
  push eax
  push eax
  sgdt [esp + 0x2]
  pop eax ;; Segment
  pop eax ;; Pointer

  ;; Get address of CS segment in GDT and fixup segment size in GDT;
  ;; Code segment size enlargement is required for 5530+ kernels
  mov edx, cs
  add edx, eax
  mov word [eax], 0xFFFF
  or byte [eax+0x6], 0xB

  ;; Fixup the entry point segment to CS and jump to 2BL BFM routine
  mov [esp + 0x4], cs
  jmp far [esp]
