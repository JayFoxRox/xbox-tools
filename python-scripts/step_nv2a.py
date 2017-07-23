#!/usr/bin/env python3

# <Description here>


from xbox import *

import time

put_addr = 0xFD003210
put_state = 0xFD003220
get_addr = 0xFD003270
get_state = 0xFD003250

def pause_fifo_puller():
  # Idle the puller and pusher
  s1 = read_u32(get_state)
  write_u32(get_state, s1 & 0xFFFFFFFE)
  time.sleep(0.001) # FIXME: Loop until puller is stopped instead
  print("Puller State was 0x" + format(s1, '08X'))

def pause_fifo_pusher():
  s1 = read_u32(put_state)
  write_u32(put_state, s1 & 0xFFFFFFFE)
  time.sleep(0.01) # FIXME: Loop until pusher is stopped instead
  s1 = read_u32(0xFD003200)
  write_u32(0xFD003200, s1 & 0xFFFFFFFE)
  time.sleep(0.01) # FIXME: Loop until pusher is stopped instead
  print("Pusher State was 0x" + format(s1, '08X'))

def resume_fifo_puller():
  # Resume puller and pusher
  s2 = read_u32(get_state)
  write_u32(get_state, (s2 & 0xFFFFFFFE) | 1) # Recover puller state
  time.sleep(0.001) # FIXME: Loop until puller is resumed instead

def resume_fifo_pusher():
  s2 = read_u32(0xFD003200)
  write_u32(0xFD003200, s2 & 0xFFFFFFFE | 1)
  time.sleep(0.01) # FIXME: Loop until pusher is resumed instead
  s2 = read_u32(put_state)
  write_u32(put_state, (s2 & 0xFFFFFFFE) | 1) # Recover pusher state
  time.sleep(0.01) # FIXME: Loop until pusher is resumed instead

def step_fifo(steps):
  #FIXME: Assert that the puller is stopped!

  pause_fifo_pusher()

  puller = read_u32(get_addr) # Get puller position
  pusher = read_u32(put_addr) # Get pusher position

  print("Pusher: 0x" + format(pusher, '08X'))
  print("Puller: 0x" + format(puller, '08X'))

  # We might have stopped where the puller has processed half of an instruction
  # This aligns it to the full instruction
  target = puller
  #FIXME: Make sure that this does not move the puller beyond the pusher!
  if target & 0x7:
    target = ((target | 7) + 1) % 1024
  print("Target: 0x" + format(target, '08X'))

  # This aligns and also keeps the puller running, so a write to PUT will
  # immediately update the puller now!
  write_u32(put_addr, target)
  resume_fifo_puller()

  while puller != target:
    puller = read_u32(get_addr)

  #FIXME: Why can't I keep the puller running?
  #       There seems to be some weird situation where the data between
  #       puller and pusher is still being updated, even when DMA pushing and
  #       cache1_push is disabled
  pause_fifo_puller()

  while(steps > 0):

    assert(puller % 8 == 0)

    def debug():
      t = read_u32(put_addr)
      print("Pusher now: 0x" + format(t, '08X'))
      t = read_u32(get_addr)
      print("Puller now: 0x" + format(t, '08X'))


    def down(n):
      return n // 8
      
    available_steps = 0
    def update_state():
      debug()
      if pusher >= puller:
        # All data from puller to pusher
        available_steps = down(pusher) - down(puller)
      else:
        # From puller to 127
        # From 0 to pusher
        available_steps = (128 - down(puller)) + down(pusher)
      print(str(available_steps) + " Steps available")
      return available_steps

    # Make sure we have steps available = run pusher for a bit if need be
    available_steps = update_state()
    if available_steps == 0:
      print("")
      pause_fifo_puller()
      write_u32(put_addr, pusher) # Restore real pusher
      resume_fifo_pusher()
      while(available_steps == 0):
        pusher = read_u32(put_addr) # Get new pusher position
        available_steps = update_state()
      pause_fifo_pusher()
      pusher = read_u32(put_addr) # Get final new pusher position
      write_u32(put_addr, target)
      debug()
      print("Pushed until 0x" + format(pusher, '08X'))
      print("Returned to 0x" + format(target, '08X'))
      #resume_fifo_puller()
      print("")

    # Now generate the number of steps we can do
    chunk_steps = min(steps, available_steps)
    print("Will do " + str(chunk_steps) + " / " + str(steps) + " steps")

    # Set the target puller address
    target = ((down(puller) + chunk_steps) % 128) * 8


    # FIXME: Do something here..
    # Test with: magicboot debug title="F:\Games\Burnout 3\default.xbe"

    puller = read_u32(get_addr)
    print("At 0x" + format(puller, '08X') + " and will be at 0x" + format(target, '08X'))

    pc = puller
    skippedverts = False
    while(pc != target):
      method = read_u32(0xFD003800 + pc)
      arg = read_u32(0xFD003804 + pc)
      # Replace triangle strips by line strips
      if (method & 0xFFFC == 0x17FC) and (arg == 6):
        write_u32(0xFD003804 + pc, 4)
      if (method & 0xFFFC == 0x012c):
        print("Frame start!!!111")
        time.sleep(2.0)
      if (method & 0xFFFC != 0x1800) and (method & 0xFFFC != 0x1808) and (method & 0xFFFC != 0x1818):
        if (skippedverts):
          print("Skipped some verts")
        print("0x" + format(pc, '03X') + ": 0x" + format(method, '08X') + "; arg: 0x" + format(arg, '08X'))
      else:
        skippedverts = True
      pc = (pc + 8) % (128 * 8)

    if (skippedverts):
      print("Skipped some verts")

    write_u32(put_addr, target)

    resume_fifo_puller()
    # Verify the puller reached the goal
    while puller != target:
      puller = read_u32(get_addr)
    print("At 0x" + format(puller, '08X') + " and should be at 0x" + format(target, '08X'))
    pause_fifo_puller()

    steps -= chunk_steps


  # We now recover the real pusher position
  write_u32(put_addr, pusher) # Get pusher position

  # We idle the puller again to finish our step
  pause_fifo_puller()

  resume_fifo_pusher()

def main():

  pause_fifo_puller()

  step_fifo(1000)

  resume_fifo_puller()
  

if __name__ == '__main__':
  main()
