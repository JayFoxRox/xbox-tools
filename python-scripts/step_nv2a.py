#!/usr/bin/env python3

# <Description here>


from xbox import *

import time
import signal
import sys
from PIL import Image

def signal_handler(signal, frame):
        print('Got SIGINT! Exiting')
        sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

dma_state = 0xFD003228
dma_put_addr = 0xFD003240
dma_get_addr = 0xFD003244
dma_subroutine = 0xFD00324C

put_addr = 0xFD003210
put_state = 0xFD003220
get_addr = 0xFD003270
get_state = 0xFD003250

pgraph_state = 0xFD400720

def pause_fifo_puller():
  # Idle the puller and pusher
  s1 = read_u32(get_state)
  write_u32(get_state, s1 & 0xFFFFFFFE)
  time.sleep(0.001) # FIXME: Loop until puller is stopped instead
  #print("Puller State was 0x" + format(s1, '08X'))

def pause_fifo_pusher():
  s1 = read_u32(put_state)
  write_u32(put_state, s1 & 0xFFFFFFFE)
  time.sleep(0.001) # FIXME: Loop until pusher is stopped instead
  if False:
    s1 = read_u32(0xFD003200)
    write_u32(0xFD003200, s1 & 0xFFFFFFFE)
    time.sleep(0.01) # FIXME: Loop until pusher is stopped instead
    #print("Pusher State was 0x" + format(s1, '08X'))

def resume_fifo_puller():
  # Resume puller and pusher
  s2 = read_u32(get_state)
  write_u32(get_state, (s2 & 0xFFFFFFFE) | 1) # Recover puller state
  time.sleep(0.001) # FIXME: Loop until puller is resumed instead

def resume_fifo_pusher():
  if False:
    s2 = read_u32(0xFD003200)
    write_u32(0xFD003200, s2 & 0xFFFFFFFE | 1)
    time.sleep(0.01) # FIXME: Loop until pusher is resumed instead
  s2 = read_u32(put_state)
  write_u32(put_state, (s2 & 0xFFFFFFFE) | 1) # Recover pusher state
  time.sleep(0.001) # FIXME: Loop until pusher is resumed instead

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

def dumpPB(start, end):
  offset = start
  while(offset != end):
    
    count = parseCommand(offset, True)
    if count == 0:
      break
    offset += count

def dumpPBState():
  v_dma_get_addr = read_u32(dma_get_addr)
  v_dma_put_addr = read_u32(dma_put_addr)
  v_dma_subroutine = read_u32(dma_subroutine)

  print("0x%08X / 0x%08X / 0x%08X" % (v_dma_get_addr, v_dma_put_addr, v_dma_subroutine))
  dumpPB(v_dma_get_addr, v_dma_put_addr)
  print()

def dumpCacheState():
  v_get_addr = read_u32(get_addr)
  v_put_addr = read_u32(put_addr)

  v_get_state = read_u32(get_state)
  v_put_state = read_u32(put_state)

  print("0x%X / 0x%X" % (v_get_addr, v_put_addr))

  print("Put / Pusher enabled: %s" % ("Yes" if (v_put_state & 1) else "No"))
  print("Get / Puller enabled: %s" % ("Yes" if (v_get_state & 1) else "No"))

  print("Cache:")
  for i in range(128):

    cache1_method = read_u32(0xFD003800 + i * 8)
    cache1_data = read_u32(0xFD003804 + i * 8)

    s = "  [0x%02X] 0x%04X (0x%08X)" % (i, cache1_method, cache1_data)
    v_get_offset = i * 8 - v_get_addr
    if v_get_offset >= 0 and v_get_offset < 8:
      s += " < get[%d]" % v_get_offset
    v_put_offset = i * 8 - v_put_addr
    if v_put_offset >= 0 and v_put_offset < 8:
      s += " < put[%d]" % v_put_offset

    print(s)
  print()

  return

def printDMAstate():

  v_dma_state = read_u32(dma_state)
  v_dma_method = v_dma_state & 0x1FFC
  v_dma_subchannel = (v_dma_state >> 13) & 7
  v_dma_method_count = (v_dma_state >> 18) & 0x7ff
  v_dma_method_nonincreasing = v_dma_state & 1
  # higher bits are for error signalling?
  
  print("v_dma_method: 0x%04X (count: %d)" % (v_dma_method, v_dma_method_count))

def parseCommand(addr, display=False):

  size = 0

  word = read_u32(0x80000000 | addr)
  s = "0x%08X: Opcode: 0x%08X" % (addr, word)

  if ((word & 0xe0000003) == 0x20000000):
    print("unhandled opcode type: old jump")
    #state->get_jmp_shadow = control->dma_get;
    #control->dma_get = word & 0x1fffffff;
    #NV2A_DPRINTF("pb OLD_JMP 0x%" HWADDR_PRIx "\n", control->dma_get);
  elif ((word & 3) == 1):
    print("unhandled opcode type: jump")
    #state->get_jmp_shadow = control->dma_get;
    #control->dma_get = word & 0xfffffffc;
  elif ((word & 3) == 2):
    print("unhandled opcode type: call")
    #if (state->subroutine_active) {
    #  state->error = NV_PFIFO_CACHE1_DMA_STATE_ERROR_CALL;
    #  break;
    #}
    #state->subroutine_return = control->dma_get;
    #state->subroutine_active = true;
    #control->dma_get = word & 0xfffffffc;
  elif (word == 0x00020000):
    # return
    print("unhandled opcode type: return")
  elif ((word & 0xe0030003) == 0) or ((word & 0xe0030003) == 0x40000000):
    # methods
    method = word & 0x1fff;
    subchannel = (word >> 13) & 7;
    method_count = (word >> 18) & 0x7ff;
    method_nonincreasing = word & 0x40000000;
    #state->dcount = 0;

    s += "; Method: 0x%04X (%d times)" % (method, method_count)
    size = 4 + method_count * 4

  else:
    print("unknown opcode type")

  if display:
    print(s)

  return size



def main():

  DebugPrint = False

  timeout = 2000


  while True:

    # Pause the puller, so that the CACHE is full and PB stops running
    resume_fifo_puller()
    pause_fifo_puller()

    # Check out where the PB currently is and where it was supposed to go
    v_dma_put_addr_real = read_u32(dma_put_addr)
    v_dma_get_addr = read_u32(dma_get_addr)

    # As there might be unfinished commands in the cache, we finish those
    v_dma_state = read_u32(dma_state)
    v_dma_method_count = (v_dma_state >> 18) & 0x7ff
    v_dma_get_addr += 4 * v_dma_method_count

    # Make sure we have reached a point where the PB has data to run
    if (v_dma_get_addr != v_dma_put_addr_real):
      break

  # Show where we stopped and the full PB
  dumpPBState()
  printDMAstate()

  # Hide all commands from the PB by setting PUT = GET
  v_dma_put_addr_target = v_dma_get_addr
  write_u32(dma_put_addr, v_dma_put_addr_target)

  # Enable puller - nothing bad can happen, as it has no commands to process
  # The PB can't run yet
  resume_fifo_puller()

  # Step through the PB until we finish.
  while(v_dma_get_addr != v_dma_put_addr_real):

    # Get size of current command.
    size = parseCommand(v_dma_get_addr, DebugPrint)

    # If we don't know the size, we have to abort.
    if size == 0:
      print("Aborting due to unknown PB command")

      # Recover the real address as Xbox would get stuck otherwise
      write_u32(dma_put_addr, v_dma_put_addr_real)

      break

    # Check which method it is.
    word = read_u32(0x80000000 | v_dma_get_addr)
    if ((word & 0xe0030003) == 0) or ((word & 0xe0030003) == 0x40000000):
      # methods
      method = word & 0x1fff;
      subchannel = (word >> 13) & 7;
      method_count = (word >> 18) & 0x7ff;
      method_nonincreasing = word & 0x40000000;
      
      for method_index in range(method_count):

        if method == 0x17fc:
          print("Set begin end")
          # Check for texture addresses
          for i in range(4):
            offset = read_u32(0xFD401A24 + i * 4) # NV_PGRAPH_TEXOFFSET0
            pitch = read_u32(0xFD4019DC + i * 4) # NV_PGRAPH_TEXCTL1_0_IMAGE_PITCH
            fmt = read_u32(0xFD401A04 + i * 4) # NV_PGRAPH_TEXFMT0
            fmt_color = (fmt >> 8) & 0x7F
            width_shift = (fmt >> 20) & 0xF
            height_shift = (fmt >> 24) & 0xF
            width = 1 << width_shift
            height = 1 << height_shift
            print("Texture %d [0x%08X, %d x %d (pitch: 0x%X), format %d]" % (i, offset, width, height, pitch, fmt_color))

            if fmt_color == 6:

              data = read(0x80000000 | offset, width * height * 4)
              try:
                img = Image.new( 'RGBA', (width, height)) # create a new black image
                pixels = img.load() # create the pixel map

                pitch = width * 4
                bits_per_pixel = 32
                data = nv2a._Unswizzle(data, bits_per_pixel, (width, height), pitch)

                for x in range(img.size[0]):    # for every col:
                  for y in range(img.size[1]):    # For every row
                    red = data[4 * (y * width + x) + 2]
                    green = data[4 * (y * width + x) + 1]
                    blue = data[4 * (y * width + x) + 0]
                    alpha = data[4 * (y * width + x) + 3]
                    pixels[x, y] = (red, green, blue, 255) # set the colour accordingly

                img.save("tex-%d---timeout_%d.png" % (i, timeout))
              except:
                print("Unexpected error:", sys.exc_info()[0])
                pass

        # Check for texture addresses
        for i in range(4):
          if method == 0x1b00 + 64 * i:
            data = read_u32(0x80000000 | (v_dma_get_addr + (method_index + 1) * 4))
            print("Texture %d [0x%08X]" % (i, data))

        if method == 0x0130:
          print("Flip stall!")
        
        if not method_nonincreasing:
          method += 4

    # Disable PGRAPH, so it can't run anything from CACHE.
    s1 = read_u32(pgraph_state)
    write_u32(pgraph_state, s1 & 0xFFFFFFFE)

    # Calculate address of the next command and set it as PB target.
    # This allows the PB to move into the CACHE.
    v_dma_put_addr_target = v_dma_get_addr + size
    write_u32(dma_put_addr, v_dma_put_addr_target)
    if DebugPrint: print("At 0x%08X, target is 0x%08X (Real: 0x%08X)" % (v_dma_get_addr, v_dma_put_addr_target, v_dma_put_addr_real))

    # We have now moved commands to the CACHE.
    # Disable the cache update now.
    pause_fifo_pusher()

    # Run the commands we have moved to CACHE now, by enabling PGRAPH.
    s1 = read_u32(pgraph_state)
    write_u32(pgraph_state, s1 | 1)

    # See if the PB target was modified and restore if necessary.
    v_dma_put_addr_new_real = read_u32(dma_put_addr)
    if (v_dma_put_addr_new_real != v_dma_put_addr_target):
      print("PB was modified! Restoring.")
      write_u32(dma_put_addr, v_dma_put_addr_target)
      v_dma_put_addr_real = v_dma_put_addr_new_real

    # Get the updated PB address.
    v_dma_get_addr = read_u32(dma_get_addr)

    # Also show that we processed the commands.
    if DebugPrint: dumpPBState()

    # We can continue the cache updates now.
    resume_fifo_pusher()

    timeout = timeout - 1
    print(timeout)
    if timeout == 0:
      write_u32(dma_put_addr, v_dma_put_addr_real)
      break


if __name__ == '__main__':
  main()
