import os
import tempfile
import subprocess

# 32 bit words to 24 bit words
def to24(data):
  assert(len(data) % 4 == 0)
  out_data = bytearray(data)
  del out_data[3::4]
  return bytes(out_data)

# 24 bit words to 32 bit words
def from24(data, padding=0x00):
  assert(len(data) % 3 == 0)
  out_data = bytearray()
  for i in range(0, len(data) // 3):
    out_data += data[i*3:i*3+3]
    out_data += bytes([padding])
  return bytes(out_data)

# Loads a56 assembled machine code into DSP format
def parse_assembler_output(content):
  code = bytearray()
  curaddr = 0
  for line in content.splitlines():
    s = line.split()
    assert(len(s) >= 1)
    seg = s[0]
    if seg == 'I' or seg == 'F':
      break
    assert(len(s) == 3)
    addr = int(s[1],16)
    data = int(s[2],16)
    assert(addr == curaddr) # Code with gaps not supported
    assert(data >= 0 and data <= 0xFFFFFF)
    #print("Program data [0x" + format(addr, '04X') + "]: 0x" + format(data, '06X'))
    code += int.to_bytes(data, length=3, byteorder='little')
    curaddr = addr + 1
  return code

def assemble(code):
  # Generate input file
  to_a56 = tempfile.NamedTemporaryFile(mode='wb', delete=False)
  to_a56.write(bytes(code, encoding='ascii'))
  to_a56.close()
  
  # Generate output filename
  from_a56 = tempfile.NamedTemporaryFile(mode='rb', delete=False)
  from_a56.close()

  #FIXME: Pipe to variable instead
  a56_command = ["/home/fox/Data/Downloads/dspfoo/a56", "-o", from_a56.name, to_a56.name]

  # Run a56 and remove input file when done
  a56_state = subprocess.run(a56_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  stderr = a56_state.stderr.splitlines()
  print(stderr) # Error messages
  stdout = a56_state.stdout.splitlines()
  print(stdout[-2:]) # Number of errors and warnings
  os.unlink(to_a56.name)

  # Retrieve result and remove output file
  output = open(from_a56.name).read()
  os.unlink(from_a56.name)

  return parse_assembler_output(output)
