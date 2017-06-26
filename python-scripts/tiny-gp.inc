; Disable all interrupts
  
movep #$FFF, x:$FFFFC5                  ; Clear interrupts

; Register A0 will be used to count the number of frames

move #0, a

mainloop

  ; Keep a framecount in XMEM[0]
  move a0, x0
  move x0, x:$000000

  ; Load constant 1 and increment frame counter
  move #1, b0
  add b, a

  ; 0xFFFFC4 is the control register (in XMEM peripheral space)
  ; * (1 << 0) is the idle pin

  movep #1<<0, x:$FFFFC4                    ; Set idle

  ; 0xFFFFC5 is the interrupt register (in XMEM peripheral space)
  ; * (1 << 1) is the start of frame interrupt

  wait_for_frame
    ; jclr operates on the n-th bit, it's not a mask!
    jclr  #1, x:$FFFFC5, wait_for_frame     ; Keep in tight loop until frame is hit
    movep #1<<1, x:$FFFFC5                  ; Clear interrupts

  ; Normally you'd `rts` here and do whatever you want to do
  jmp mainloop
