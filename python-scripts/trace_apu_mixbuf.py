#!/usr/bin/env python3

# Fixed in hardware:
# - We get 3 bytes per sample (packed into 4 bytes) * 1 channel
# - We get 128 bytes at a time = 32 samples
# - We run at 48000 Hz
#
# 32 / (480000 Hz) = 0.666 ms
#
# So at most you can spend 0.666 ms in the `callback` below.
# Considering network and API overhead, this forces us to offload work into
# a worker thread.
#
#
# There are 32 different bins you can trace. However, due to the timing
# constraints you could only reliably dump 1 or 2 at a time.
# Due to this, the API can not do parallel dumping.

seconds = 10.0
bin_index = 0


from xboxpy import *

from concurrent.futures import *

# Open outputs
wav = aci.export_wav("mixbuf_trace.wav", channels=1, sample_width=3)
try:
  import pyaudio
  pya = pyaudio.PyAudio()
  stream = pya.open(format=pya.get_format_from_width(width=3), channels=1, rate=48000, output=True)
except ImportError:
  print("Could not find pyaudio, will only stream to disk.")
  stream = None

# Timing is VERY critical with the short APU frames.
# so instead of doing the work instantly, we defer it to another thread.
# This is said asynchronous action
def callback_deferred(duration, data):
  # Do the format conversion (extracting the 3 used bytes from 4 bytes)
  data = dsp.to24(data)
  # Forward to output
  if stream != None:
    stream.write(data)
  wav.writeframes(data)

# This manages the worker we offload work to.
executor = ThreadPoolExecutor(max_workers=1)

# Define the handler which will send data to the worker.
def callback(duration, data):
  global tracked_duration
  global running_thread
  executor.submit(callback_deferred, duration, data)
  tracked_duration = duration
  return duration >= seconds

# Start tracing
apu.TraceMIXBUF(bin_index, callback)

# Report if the simple callback alone was enough to kill us.
# Then wait for our worker to finish, too.
print("Took " + str(tracked_duration * 1000.0) + "ms. Expected " + str(seconds * 1000.0) + "ms")
executor.shutdown(wait=True)

# Stop and close all outputs
if stream != None:
  stream.stop_stream()
  stream.close()
wav.close()
