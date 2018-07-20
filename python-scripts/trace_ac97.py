#!/usr/bin/env python3

# Assuming DirectSound:
# - We get 2 bytes per sample * 2 channels
# - We get 1024 bytes at a time = 256 samples
# - We run at 48000 Hz
#
# 256 / (480000 Hz) = 5.333 ms
#
# So at most you can spend 5.333 ms in the `callback` below.
# However, consider network and API overhead. So try to spend time wisely.

seconds = 10.0


from xboxpy import *

# Open outputs
wav = aci.export_wav("pcm_trace.wav")
try:
  import pyaudio
  pya = pyaudio.PyAudio()
  stream = pya.open(format=pya.get_format_from_width(width=2), channels=2, rate=48000, output=True)
except ImportError:
  print("Could not find pyaudio, will only stream to disk.")
  stream = None

# Define the handler which will do the output.
def callback(duration, data):
  if stream != None:
    stream.write(data)
  wav.writeframes(data)
  return duration >= seconds

# Start tracing
aci.TraceAC97(callback)

# Stop and close all outputs
if stream != None:
  stream.stop_stream()
  stream.close()
wav.close()
