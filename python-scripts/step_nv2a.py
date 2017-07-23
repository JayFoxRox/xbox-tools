#!/usr/bin/env python3

# <Description here>


from xbox import *

import time

def pause_fifo_puller():
  # Idle the puller and pusher
  s1 = read_u32(0xFD003250)
  write_u32(0xFD003250, s1 & 0xFFFFFFFE)
  time.sleep(0.001) # FIXME: Loop until puller is stopped instead
  print("Puller State was 0x" + format(s1, '08X'))

def pause_fifo_pusher():
  s1 = read_u32(0xFD003220)
  write_u32(0xFD003220, s1 & 0xFFFFFFFE)
  time.sleep(0.001) # FIXME: Loop until pusher is stopped instead
  print("Pusher State was 0x" + format(s1, '08X'))

def resume_fifo_puller():
  # Resume puller and pusher
  s2 = read_u32(0xFD003250)
  write_u32(0xFD003250, (s2 & 0xFFFFFFFE) | 1) # Recover puller state
  time.sleep(0.001) # FIXME: Loop until puller is resumed instead

def resume_fifo_pusher():
  s2 = read_u32(0xFD003220)
  write_u32(0xFD003220, (s2 & 0xFFFFFFFE) | 1) # Recover pusher state
  time.sleep(0.001) # FIXME: Loop until pusher is resumed instead

def step_fifo(steps):
  #FIXME: Assert that the puller is stopped!

  pause_fifo_pusher()

  puller = read_u32(0xFD003270) # Get puller position

  while(steps > 0):

    available_steps = 0
    def update_state():
      pusher = read_u32(0xFD003210) # Get pusher position
      print("Pusher: 0x" + format(pusher, '08X'))
      print("Puller: 0x" + format(puller, '08X'))
      if pusher >= puller:
        # All data from puller to pusher
        available_steps = (pusher - puller) // 4
      else:
        # From puller to 1023
        # From 0 to pusher
        available_steps = ((1023 - puller) + pusher) // 4
      print(str(available_steps) + " Steps available")
      return (pusher, available_steps)

    # Get current state and number of steps
    (pusher, available_steps) = update_state()

    # Make sure we have steps available = run pusher for a bit if need be
    while(available_steps == 0):
      resume_fifo_pusher()
      time.sleep(0.01)
      pause_fifo_pusher()
      (pusher, available_steps) = update_state()
      print(available_steps)

    # Now generate the number of steps we can do
    chunk_steps = min(steps, available_steps)
    print("Will do " + str(chunk_steps) + " / " + str(steps) + " steps")

    # Set the target puller address
    target = (puller + chunk_steps * 4) % 1024
    write_u32(0xFD003210, target)
   




    # FIXME: Do something here..
    # Test with: magicboot debug title="F:\Games\Burnout 3\default.xbe"
    
    pc = puller & 0x3F8
    while(pc != (target & 0x3F8)):
      method = read_u32(0xFD003800 + pc)
      arg = read_u32(0xFD003804 + pc)
      # Replace triangle strips by line strips
      if (method & 0xFFFC == 0x17FC) and (arg == 6):
        write_u32(0xFD003804 + pc, 4)
      if (method & 0xFFFC == 0x012c):
        print("Frame start!!!111")
        time.sleep(2.0)
      print("0x" + format(pc, '03X') + ": 0x" + format(method, '08X') + "; arg: 0x" + format(arg, '08X'))
      pc = (pc + 8) % 1024




    # Now we run the puller
    resume_fifo_puller()

    #FIXME: Ensure that there is a little bit of time here (FIXME: Just wait until current is target?!)
    time.sleep(0.001)

    # We idle the puller again to finish our step
    pause_fifo_puller()

    # Verify the puller reached the goal
    puller = read_u32(0xFD003270)
    print("At 0x" + format(puller, '08X') + " and should be at 0x" + format(target, '08X'))


    # We now recover the real pusher position
    write_u32(0xFD003210, pusher) # Get pusher position

    steps -= chunk_steps

  resume_fifo_pusher()

def main():

  pause_fifo_puller()

  step_fifo(10000)

  resume_fifo_puller()
  

if __name__ == '__main__':
  main()
