#!/usr/bin/env python3

# Takes a screenshot

from xbox import *

# Start tracing
wav = aci.export_wav("pcm_trace.wav")
try:
  import pyaudio
  pya = pyaudio.PyAudio()
  stream = pya.open(format=pya.get_format_from_width(width=2), channels=2, rate=48000, output=True)
except ImportError:
  print("Could not find pyaudio, will only stream to disk.")
  stream = None

# Define the handler which will do the output.
#
# Assuming DirectSound:
# - We get 2 bytes per sample * 2 channels
# - We get 1024 bytes at a time = 256 samples
# - We run at 48000 Hz
#
# 256 / (480000 Hz) = 0.533 ms
#
# So at most you can spend 0.533 ms here. However, there will be network
# and API overhead. So try to spend time wisely

duration = 0
def callback(data):
  global duration
  if stream != None:
    stream.write(data)
  wav.writeframes(data)
  duration += len(data) // (2 * 2)
  return duration >= 10.0 * 48000 # Checks for 10 seconds

# Start tracing
aci.TraceAC97(callback)

# Stop and close all streams
if stream != None:
  stream.stop_stream()
  stream.close()
wav.close()
