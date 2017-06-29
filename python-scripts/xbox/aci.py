from . import *
from . import memory
from .helper import better_wave
import time

def read_u8(address):
  return memory.read_u8(0xFEC00000 + address)
def read_u16(address):
  return memory.read_u16(0xFEC00000 + address)
def read_u32(address):
  return memory.read_u32(0xFEC00000 + address)

def write_u8(address, value):
  memory.write_u8(0xFEC00000 + address, value)
def write_u16(address, value):
  memory.write_u16(0xFEC00000 + address, value)
def write_u32(address, value):
  memory.write_u32(0xFEC00000 + address, value)


def export_wav(path, channels=2, sample_width=2, sample_rate=48000, fmt=better_wave.WAVE_FORMAT_PCM):
  # Also see https://github.com/Sergeanur/XboxADPCM/blob/master/XboxADPCM/XboxADPCM.cpp for ADPCM
  wav = better_wave.open(path, 'wb')
  wav.setformat(fmt)
  wav.setnchannels(channels)
  wav.setsampwidth(sample_width)
  wav.setframerate(sample_rate)
  return wav

def ac97_status():
  print("global control=0x" + format(read_u32(0x12C), '08X'))
  print("global status=0x" + format(read_u32(0x130), '08X'))
  def dump_buffers(addr,name):
    descriptor = read_u32(addr)
    print("??? desc is p 0x" + format(descriptor, '08X'))
    descriptor |= 0x80000000
    # FIXME: Download all descriptors in one packet and then parse here
    wav = export_wav(format(addr, 'X') + ".wav")
    for i in range(0, 32):
      addr = memory.read_u32(descriptor + i * 8 + 0)
      length = memory.read_u16(descriptor + i * 8 + 4)
      control = memory.read_u16(descriptor + i * 8 + 6)
      if (addr != 0) or (length != 0) or (control != 0):
        print(str(i) + ": 0x" + format(addr, '08X') + " (" + str(length) + " samples); control: 0x" + format(control, '04X'))
        addr |= 0x80000000
        data = memory.read(addr, length * 2)
        wav.writeframes(data)
    wav.close()
    print("CIV=0x" + format(read_u8(addr + 0x4), '02X'))
    print("LVI=0x" + format(read_u8(addr + 0x5), '02X'))
    print("SR=0x" + format(read_u16(addr + 0x6), '04X'))
    print("pos=0x" + format(read_u16(addr + 0x8), '04X'))
    print("piv=0x" + format(read_u16(addr + 0xA), '04X'))
    print("CR=0x" + format(read_u8(addr + 0xB), '02X'))
  dump_buffers(0x110, "pcm.wav")
  dump_buffers(0x170, "spdif.wav")

def TraceAC97(callback):
  descriptor = read_u32(0x110)
  print("??? desc is p 0x" + format(descriptor, '08X'))
  descriptor |= 0x80000000
  for i in range(0, 32):
    addr = memory.read_u32(descriptor + i * 8 + 0)
    length = memory.read_u16(descriptor + i * 8 + 4)
    control = memory.read_u16(descriptor + i * 8 + 6)
    if (addr != 0) or (length != 0) or (control != 0):
      print(str(i) + ": 0x" + format(addr, '08X') + " (" + str(length) + " samples); control: 0x" + format(control, '04X'))
      addr |= 0x80000000
      current_milli_time = lambda: time.time() * 1000.0
      buffer_size = length * 2
      chunk_size = 1024 # Hardare runs at this chunk size
      catchup = 0

      # Wait for start of playback
      sample_rate = 48000.0
      time_for_buffer = (length / 2) / sample_rate * 1000.0
      time_per_chunk = time_for_buffer / (buffer_size / chunk_size)

      #FIXME: This was an experiment on how long it would take to dump the entire buffer
      #        We can probably dump the entire buffer and then just grab the data we need
      #        [as we can follow the write cursor by diff'ing the buffers]
      if False:
        prev_data = None
        start = current_milli_time()
        bt = 0
        min_delta = 999999999
        min_non_delta = 0
        t_last = None
        while(True):
          data = memory.read(addr, buffer_size)
          diff = ""
          blocks = 165
          block_size = buffer_size / blocks
          if prev_data != None:

            if True:
              first = buffer_size - 1
              last = 0
              for i in range(0, buffer_size):
                if data[i] != prev_data[i]:
                  first = min(i, first)
                  last = max(i, last)
              t = (current_milli_time() - start) * 1000
              if t_last:
                delta = t - t_last
                ts = str(int(t)).rjust(7)
                size = max(last - first + 1, 0)
                if size >= 8000:
                  bt = t
                if (size == 0):
                  min_non_delta = max(delta, min_non_delta)
                  msg = ts + ": No changes"
                else:
                  # Find the shortest delta
                  min_delta = min(delta, min_delta)
                  msg = ts + ": From " + str(first) + " to " + str(last) + " (" + str(size) + " bytes)"
                of = t - bt # Offset in frame
                print(msg.ljust(50) + "+" + str(int(of)).ljust(5) + " (dt: " + str(int(delta)).ljust(5) + " min-dt: " + str(int(min_delta)) + " / non-dt: " + str(int(min_non_delta)) + ")")
              t_last = t
            else:
              for i in range(0, blocks):
                idx = int(block_size*i)
                if data[idx:int(idx+block_size)] == prev_data[idx:int(idx+block_size)]:
                  diff += ' '
                else:
                  diff += '#'
              print("[" + diff + "]")
          prev_data = data
          took = current_milli_time() - start
          #print("Took " + str(took) + " / " + str(time_for_buffer) + " ms")


      # This is a poc where I try to find out when buffers are written
      #FIXME: This should sit somewhere in the streaming loop so we can resync
      print("Waiting for playback")
      last = None
      while True:
        new = memory.read_u32(addr)
        if last != None and last != new:
          print("Playback started!")
          time.sleep(time_for_buffer * 0.5 / 1000.0) # Give it another half buffer headstart
          # Playback reached us! Wait until the write cursor reaches the other half of the buffer
          break
        last = new
  
      underruns = 0
      offset = 512 # Hardware buffer starts at 512 byte offset
      
      while True:
        offset %= buffer_size
        start = current_milli_time()

        streamed_data = bytearray()

        to_end = buffer_size - offset
        data = memory.read(addr + offset, min(chunk_size, to_end))
        remaining = chunk_size - len(data)
        if remaining > 0:
          data += memory.read(addr, remaining)

        offset += chunk_size

        # Handle output in callback
        if callback(bytes(data)):
          break

        took = current_milli_time() - start
        remain = time_per_chunk - took
        remain -= catchup
        if remain > 0:
          time.sleep(remain / 1000.0)
          took = current_milli_time() - start
          remain = time_per_chunk - took
        else:
          underruns += 1
        catchup -= remain
          #print("too slow!")

      print("Had " + str(underruns) + " underruns")

