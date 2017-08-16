# Original File & Design: Thomas Frei
# Modifications for xbox openxdk by bkenwright (bkenwright@xbdev.net)
# Ported to python by Jannik Vogel

eds = [0] * (176 + 0x100 + 0x100) # __u32
EDA = 0 # u32
ED = 0 # s_Endpointdescripor*
found = 0 # u8

Debug = True

def DisableInterrupts():
  pass #FIXME `cli`

def EnableInterrupts():
  pass #FIXME `sti`

class ohci_roothub_regs_property(object):
  def __init__(self):
    self._base = None

  MAX_ROOT_PORTS = 15

  a = u32_property(0)
  b = u32_property(4)
  status = u32_property(8)
  portstatus = [u32_property(12 + i * 4) for i in range(0, MAX_ROOT_PORTS)]

class OHCI(object):
  def __init__(self):
      self._base = None

  def u32_property(offset, array_size):
    getter = lambda self: read_u32(base + offset)
    setter = lambda self, value: write_u32(self._base + offset, value)
    return property(getter, setter)

  # hcca
  NUM_INTS = 32
  int_table = u16_property(0, NUM_INTS)
  frame_no = u16_property(NUM_INTS * 4 + 0)
  pad1 = u16_property(NUM_INTS * 4 + 2)
  done_head = u32_property(NUM_INTS * 4 + 4)
  reserved_for_hc = u8_property(NUM_INTS * 4 + 8, 116)

  # regs
  #/* control and status registers */
  revision = u32_property(0)
  control = u32_property(4)
  cmdstatus = u32_property(8)
  intrstatus = u32_property(12)
  intrenable = u32_property(16)
  intrdisable = u32_property(20)
  #/* memory pointers */
  hcca = u32_property(24)
  ed_periodcurrent = u32_property(28)
  ed_controlhead = u32_property(32)
  ed_controlcurrent = u32_property(36)
  ed_bulkhead = u32_property(40)
  ed_bulkcurrent = u32_property(44)
  donehead = u32_property(48)
  #/* frame counters */
  fminterval = u32_property(52)
  fmremaining = u32_property(56)
  fmnumber = u32_property(60)
  periodicstart = u32_property(64)
  lsthresh = u32_property(68)
  #/* Root hub ports */
  roothub = ohci_roothub_regs_property(72) #FIXME: Base!!!

def FindOHC(ohci, regbase):

  DisableInterrupts()
    
  xmemset(ohci, 0, sizeof(ohci_t))
  
  ohci.regs = regbase #(ohci_regs*)regbase
  

  # This is where we align or hcca so its 256 byte aligned
  hcca = malloc(0x10000 + 0x100)
  memset(hcca, 0x00, 0x10000 + 0x100)
  ohci.hcca = (hcca + 0x100) & 0xFFFFFF00

  ke.MmLockUnlockBufferPages(hcca, 0x10000 + 0x100, 0)

  ke.MmLockUnlockBufferPages(eds, 0x100, 0)

  # Just make sure our memory for ED's is aligned
  EDA = eds
  EDA += 0x100
  EDA &= 0xFFFFFF00 # e.g was 0x0002ED20, but is now 0x0002EE00, so its
                    # 16 bit memory aligned

  ED = EDA #(s_Endpointdescripor*)EDA

  realEDA = ke.MmGetPhysicalAddress(EDA)


  __u32 * pHCCA = (__u32*)ohci.hcca
  for i in range(0, 32):
    pHCCA[i] = realEDA # EDA

  pHCCA[32] = 0
  pHCCA[33] = 0

  for i in range(0, 5):
    ED[i].Format = AUTOIO | 0x402000 # AUTOIO 0x1800L
    ED[i].NextED = realEDA + (16 * (i + 1)) # EDA + (16*(i+1))
    ED[i].Headptr = 0
    ED[i].Tailptr = 0

  ED[0].Format = 0x4000                            # Should really explain whats happening
  ED[0].NextED = 0                                 # here, ED[0] is going to be the bulkhead descriptor.
  ED[1].NextED = 0                                 # It is setup, but never used - as you'll always see
  ED[4].NextED = 0                                 # ED[1] being set with values in this demo code.
                                                   # As ED's are all 16bit aligned this way.

  # init the hardware

  # what state is the hardware in at the moment?  (usually reset state)
  state = ohci.regs.control & 0xC0
  if state == 0x00: # in reset: a cold boot
    ohci.regs.roothub.a = 0x10000204
    ohci.regs.roothub.b = 0x00020002
    ohci.regs.fminterval = (4096 << 16)| 11999
    ohci.regs.control = ((ohci.regs.control) & (~0xC0)) | 0x80
  else if state == 0x80: # operational already
    pass
  else if state == 0x40 or state == 0xC0: # resume or suspend
    ohci.regs.control = ((ohci.regs.control) & (~0xC0)) | 0x40
    time.sleep(50000)

  fminterval = ohci.regs.fminterval  # stash interval
  ohci.regs.cmdstatus = 1            # host controller reset

  time.sleep(20) # should only take 10us max to reset

  ohci.regs.fminterval = fminterval        # restore our saved interval

  realhcca = ke.MmGetPhysicalAddress(ohci.hcca)
  
  if False:
    ohci.regs.hcca = (__u32)ohci.hcca

  ohci.regs.hcca = realhcca

  if False:
    ohci.regs.intrdisable = ~0x0          # Not sure about this...but turn off any interrupts?

  ohci.regs.intrenable = 0xC000007B        # set HcInterruptEnable


  ohci.regs.control = 0x00000080          # HC operational

  time.sleep(50)

  if Debug:
    # HCFS - usb state (00,01,10,11.reset,resume,operational,suspend)
    # bits 6 and 7 in the control register
    print("USBOPERATIONAL : " + ("yes" if % (((ohci.regs.control >> 6) & 0x3) == 0x2) else "no"))
    print("USBOPERATIONAL : 0x%02X" % ((ohci.regs.control >> 6) & 0x3))

  ohci.regs.fminterval |= 0x27780000        # set FSLargestDataPacket
  
  
  # set HcPeriodicStart to 10% of HcFmInterval
  ohci.regs.periodicstart = (ohci.regs.fminterval & 0xFFFF) / 10

  
  # Global power on
  ohci.regs.roothub.status = 0x10000

  tt = ohci.regs.intrstatus          # clear interrupts
  ohci.regs.intrstatus = tt


  if Debug:
    DebugFile( ohci)

  if False:
    ohci.regs.ed_bulkhead = EDA            # BulkHead
  
  if False:
    __u32 realEDA = ke.MmGetPhysicalAddress(EDA)
  ohci.regs.ed_bulkhead = realEDA

  # link ED's in Queue
  if False:
    ohci.regs.ed_controlhead = EDA + 16        # ControlHead
  ohci.regs.ed_controlhead = realEDA + 16


  # NDP
  NDP = ohci.regs.roothub.a & 0xFF


  # disable all devices
  for i in range(0, 4):
    ohci.regs.roothub.portstatus[i] = 0x11

  return NDP

def FindDev(ohci_t * ohci, Port):
  Speed=0


  s_USB_Devicedescriptor DD
  s_USB_Devicedescriptor * pDD = &DD
  xmemset(pDD, 0, sizeof(DD))

  s_Transferdescriptor * TD

  GetDescr = malloc(8)
  write_u32(GetDescr + 0, 0x01000680)
  write_u32(GetDescr + 4, 0x00080000)

  WG  = GetDescr
  ke.MmLockUnlockBufferPages(WG, 0x8, 0)
  DDA = pDD
  ke.MmLockUnlockBufferPages(DDA, 0x32, 0)

  TD = (s_Transferdescriptor*)(((__u32*)ED)+20)# Same as saying TD = EDA+80)
  TDA = EDA + 80

  realTDA = ke.MmGetPhysicalAddress(TDA)

  TD[0].Format  = 0xE20050C0  # Get DeviceDescriptor
  TD[0].Buffer  = ke.MmGetPhysicalAddress(WG)
  if False:
    TD[0].NextTD  = TDA + 16
  TD[0].NextTD  = realTDA + 16
  TD[0].BufferEnd = ke.MmGetPhysicalAddress(WG + 7)

  TD[1].Format  = 0xE31050C1  # Receive first 8 bytes of DeviceDescriptor
  TD[1].Buffer  = ke.MmGetPhysicalAddress(DDA)
  TD[1].NextTD  = realTDA + 32
  TD[1].BufferEnd = ke.MmGetPhysicalAddress(DDA + 7)

  TD[2].Format  = 0xE20050C2  # Queue END
  TD[2].Buffer  = 0
  TD[2].NextTD  = 0
  TD[2].BufferEnd = 0

  # Power on + Enable Ports
  ohci.regs.roothub.portstatus[Port] = 0x100
  time.sleep(2)

  if( (ohci.regs.roothub.portstatus[Port] & 1)== 0):
    return 0 # No device

  if( ohci.regs.roothub.portstatus[Port] & 0x200): # lowspeed device?
    Speed = 1
  else:
    Speed = 2

  if( ohci.regs.roothub.portstatus[Port] & 0x10000): # Port Power changed?
    ohci.regs.roothub.portstatus[Port] = 0x10000 # Port power Ack

  # Port Reset
  # We will try and do this 4 times
  ohci.regs.roothub.portstatus[Port] = 0x10
  time.sleep(40)
  for i in range(0, 4):
    if( (ohci.regs.roothub.portstatus[Port] & 0x10)== 0):
      break
    
    if Debug:
      print("\tport: %d, reset failed %d times" % (Port, i))

    time.sleep(100)

  ohci.regs.roothub.portstatus[Port] = 0x100000

  if( (ohci.regs.roothub.portstatus[Port] & 7) != 3): # Port disabled?
    ohci.regs.roothub.portstatus[Port] = 2

  # Configure Endpointdescriptor
  if(Speed == 2):
    ED[1].Format &= 0xFFFFDFFF
  else:
    ED[1].Format |= 0x2000

  # determine MPS
  ED[1].Headptr = realTDA
  ED[1].Tailptr = realTDA + 32
  ED[1].Format &= 0xFFFFFF00

  # set CLF
  ohci.regs.cmdstatus |= 2    # CommandStatus

  ohci.regs.control = 0x90    # set CLE

  tt = ohci.regs.intrstatus    # clear all Interruptflags
  ohci.regs.intrstatus = tt

  if Debug:
    DebugFile( ohci)
    # wait for execution
    print("waiting for execution\n")

  while True:
    ohci.regs.intrstatus = 0x4 # SOF
    if ((ohci.regs.intrstatus & 2)== 0):
      break

  time.sleep(10)

  # Errors?
  ohci_hcca *hcca = (ohci_hcca*)ohci.hcca        # HCCA
  hcca.done_head &= 0xFFFFFFFE          # DoneHead in HCCA

  if ((hcca.done_head >> 28)== 0):
    ED[1].Format &= 0xF800FFFF
    ED[1].Format |= DD.MaxPacketSize << 16
    found++
  else:
    return 0

  if Debug:
    print("\nDescriptor.Length: 0x%x" % DD.Length)
    print("Descriptor.DescriptorType: 0x%02X" % DD.DescriptorType)
    print("Descriptor.USB: 0x%04X" % DD.USB)
    print("Descriptor.DeviceClass: 0x%04X" % DD.DeviceClass)
    print("Descriptor.DeviceSubClass: 0x%04X" % DD.DeviceSubClass)
    print("Descriptor.DeviceProtocol: 0x%04X" % DD.DeviceProtocol)
    print("Descriptor.MaxPacketSize: 0x%04X" % DD.MaxPacketSize)
    print("Descriptor.Vendor: 0x%04X" % DD.Vendor)
    print("Descriptor.ProductID: 0x%04X" % DD.ProductID)
    print("Descriptor.Manufacturer: 0x%04X" % DD.Manufacturer)
    print("Descriptor.ProductIndex: 0x%04X" % DD.ProductIndex)
    print("Descriptor.SerialNumber: 0x%04X" % DD.SerialNumber)
    print("Descriptor.ConfigNumber: 0x%04X" % DD.ConfigNumber)

  return Speed

def ResetPort(ohci_t * ohci, Port):
  ohci.regs.roothub.portstatus[ Port*4 ] = 0x10
  time.sleep(40)

  ohci.regs.roothub.portstatus[ Port*4 ] = 0x100000

  return 0


# Port = 8 bit [optional, value = 0]
# AddrNew = 8 bit
#FIXME: SetAddress
def SetAddres(ohci_t * ohci, Port, AddrNew):
  WS = malloc(8)
  write_u32(WS + 0, (AddrNew << 16)| 0x00000500)# ???
  write_u32(WS + 4, 0x00000000)# ???

  if( Port == 0):
    Port = found

  ke.MmLockUnlockBufferPages(WS, 0x8, 0)

  # s_Transferdescriptor *TD

  if False:
    #FIXME: Dead code..
    TD = malloc(4 * 0x1000)
    TD = (s_Transferdescriptor*)((TD + 0x100) & 0xFFFFFF00)
    xmemset(TD, 0, sizeof(s_Transferdescriptor)*4)

  if False:
    # FIXME: Dead code..
    TD = (s_Transferdescriptor *)(((__u32 *)ED)+20)

  TD  = (s_Transferdescriptor *)(EDA + 80)
  TDA = EDA + 80

  realTDA = ke.MmGetPhysicalAddress(TDA)

  TD[0].Format  = 0xE20050C4    # Set Address
  TD[0].Buffer  = ke.MmGetPhysicalAddress(WS)
  TD[0].NextTD  = realTDA + 16 # (__u32)(&TD[1])//TDA + 16
  TD[0].BufferEnd  = ke.MmGetPhysicalAddress(WS + 7)

  TD[1].Format  = 0xE31050C5    # Receive Acknowledge
  TD[1].Buffer  = 0
  TD[1].NextTD  = realTDA + 32 # (__u32)(&TD[2])//TDA + 32
  TD[1].BufferEnd  = 0

  TD[2].Format  = 0xE20050C6    # End Queue
  TD[2].Buffer  = 0
  TD[2].NextTD  = 0
  TD[2].BufferEnd  = 0
  
  if False:
    #FIXME: Dead code
    ED[1].Headptr  = &TD[0] # TDA
    ED[1].Tailptr  = &TD[2] # TDA + 32

  ED[1].Headptr = realTDA
  ED[1].Tailptr = realTDA + 32

  # set CLF
  ohci.regs.cmdstatus |= 2      # CommandStatus

  ohci.regs.control   = 0x90    # set CLE

  ohci.regs.intrstatus = ohci.regs.intrstatus # clear all Interruptflags

  if Debug:
    DebugFile( ohci)
    # wait for execution
    print("waiting for execution\n")

  while((ohci.regs.intrstatus & 2) == 0):
    pass


  time.sleep(10)

  # ERRORS?
  ohci_hcca *hcca = (ohci_hcca*)ohci.hcca  # HCCA
  hcca.done_head &= 0xFFFFFFFE          # DoneHead in HCCA

  if( (hcca.done_head >> 28)!=0)
    return 1

  ED[1].Format &= 0xFFFFFF00
  ED[1].Format += AddrNew

  return 0


def SetConfigur(ohci_t * ohci, __u8 Addr, __u8 Config):
  WC = malloc(8)
  write_u32(WC + 0, (Config << 16)| 0x00000900)
  write_u32(WC + 4, 0x00000000)

  s_Transferdescriptor *TD

  ke.MmLockUnlockBufferPages(WC, 0x8, 0)

  TD = (s_Transferdescriptor *)(((__u32 *)ED)+20)
  TDA = EDA + 80

  realTDA = ke.MmGetPhysicalAddress(TDA)

  TD[0].Format  = 0xE20050C7        # Set Configuration
  TD[0].Buffer  = ke.MmGetPhysicalAddress(WC)
  TD[0].NextTD  = realTDA + 16 # TDA + 16
  TD[0].BufferEnd  = ke.MmGetPhysicalAddress(WC + 7)

  TD[1].Format  = 0xE30050C8
  TD[1].Buffer  = 0
  TD[1].NextTD  = 0
  TD[1].BufferEnd  = 0
  
  ED[1].Headptr  = realTDA # TDA
  ED[1].Tailptr  = realTDA + 16 # TDA + 16
  ED[1].Format  &= 0xFFFFFF00
  ED[1].Format  += Addr


  # set CLF
  ohci.regs.cmdstatus |= 2      # CommandStatus

  ohci.regs.control = 0x90    # set CLE

  ohci.regs.intrstatus = ohci.regs.intrstatus # clear all Interruptflags

  if Debug:
    # wait for execution
    print("waiting for execution\n")

  while((ohci.regs.intrstatus & 2)== 0):
    pass

  time.sleep(10)


  # ERRORS?
  if False:
    #FIXME: Dead code
    ohci_hcca *hcca = (ohci_hcca*)ohci.regs.hcca  # HCCA
  ohci_hcca *hcca = (ohci_hcca*)ohci.hcca
  hcca.done_head &= 0xFFFFFFFE          # DoneHead in HCCA

  if((hcca.done_head >> 28)!= 0):
    return 1

  return 0


def GetDesc(ohci_t * ohci, __u8 Addr, __u8 DescrType, __u8 Index, __u8 Count, __u8 *DBuffer):

  GetDescr = malloc(8)
  write_u32(GetDescr + 0, (DescrType << 24) | (Index << 16) | 0x00000680)
  write_u32(GetDescr + 4, 0x00000000)

  WG = GetDescr

  DA = malloc(256)#__u8 Descriptors[256]

  ke.MmLockUnlockBufferPages( WG, 0x8, 0)
  ke.MmLockUnlockBufferPages( DA, 256, 0)

  realDA = ke.MmGetPhysicalAddress(DA)

  lCount = Count # u8

  s_Transferdescriptor *TD

  TD = (s_Transferdescriptor *)(((__u32 *)ED)+ 20)
  TDA = EDA + 80

  realTDA = ke.MmGetPhysicalAddress(TDA)

  TD[0].Format  = 0xE20050CA    # Get Descriptor
  TD[0].Buffer  = ke.MmGetPhysicalAddress(WG)
  TD[0].NextTD  = realTDA + 16 # TDA + 16
  TD[0].BufferEnd  = ke.MmGetPhysicalAddress(WG+7)

  TD[1].Format  = 0xE31450CB    # Receive Start of Descriptor
  TD[1].Buffer  = realDA # DA
  TD[1].NextTD  = realTDA + 32  # TDA+32
  TD[1].BufferEnd = realDA + 7  # DA + 7


  TD[2].Format  = 0xE21450CC      # Receive Rest of Descriptor
  TD[2].Buffer  = realDA + 8 # DA + 8
  TD[2].NextTD  = realTDA + 48 # TDA + 48
  TD[2].BufferEnd  = 0

  TD[3].Format  = 0xE30050CD      # Queue END
  TD[3].Buffer  = 0
  TD[3].NextTD  = 0
  TD[3].BufferEnd  = 0

  write_u32(GetDescr + 4, lCount << 16)
  ED[1].Headptr = realTDA # TDA
  ED[1].Tailptr = realTDA + 32 # TDA + 32
  ED[1].Format  &= 0xFFFFFF00
  ED[1].Format  += Addr

  if( DescrType == 3)
    tmp = read_u32(GetDescr + 4)
    write_u32(GetDescr + 4, tmp | 0x0409)
  TD[1].BufferEnd = realDA + lCount - 1 # DA + lCount - 1


  # set CLF
  ohci.regs.cmdstatus |= 2      # CommandStatus

  ohci.regs.control = 0x90    # set CLE

  ohci.regs.intrstatus = ohci.regs.intrstatus # clear all Interruptflags


  if Debug:
    # wait for execution
    print("waiting for execution\n")

  while ((ohci.regs.intrstatus & 2)== 0):
    pass

  time.sleep(10)

  # ERRORS?
  if False:
    #FIXME: Dead code
    ohci_hcca *hcca = (ohci_hcca*)ohci.regs.hcca  # HCCA
  else:
    ohci_hcca *hcca = (ohci_hcca*)ohci.hcca
  hcca.done_head &= 0xFFFFFFFE          # DoneHead in HCCA

  if ((hcca.done_head >> 28)!= 0):
    if Debug:
      print("\nError Occured\n")
    return 1

  ED[1].Headptr = realTDA + 48 # TDA + 48
  ED[1].Tailptr = realTDA + 64 # TDA + 64


  #FIXME: This is always False?!
  if((DescrType == 3)&& (lCount < read_u8(DA + 0))&& False):
    # set CLF
    ohci.regs.cmdstatus |= 2      # CommandStatus

    ohci.regs.control   = 0x90    # set CLE

    ohci.regs.intrstatus = ohci.regs.intrstatus # clear all Interruptflags

    if Debug:
      # wait for execution
      print("waiting for execution")

    while((ohci.regs.intrstatus & 2)== 0):
      pass

    time.sleep(10)

    # ERRORS?
    if False:
      #FIXME: Dead code?!
      ohci_hcca *hcca = (ohci_hcca*)ohci.regs.hcca  # HCCA
    else:
      ohci_hcca *hcca = (ohci_hcca*)ohci.hcca

    hcca.done_head &= 0xFFFFFFFE          # DoneHead in HCCA

    if ((hcca.done_head>>28)!= 0):
      return 1


  if (DescrType == 2):
    lCount = min(lCount, Descriptors[2])
  else:
    lCount = min(lCount, Descriptors[0])



  if False:
    print("Descriptors:")
    for i in range(0, lCount)
      print("%X " % Descriptors[i])
    print("")


  time.sleep(10)

  xmemcpy( DBuffer, Descriptors, lCount)

  return 0



# These function are nothing more than debug functions - they are used
# to save the register, or descriptor values back to file, so we can check
# that all is okay and ticking away as we want :)

def DebugFile(ohci_t * ohci):

  print(" revision 0x%08X" % ohci.regs.revision)
  print(" control 0x%08X" % ohci.regs.control)
  print(" cmdstatus 0x%08X" % ohci.regs.cmdstatus)
  print(" intrstatus 0x%08X" % ohci.regs.intrstatus)
  print(" intrenable 0x%08X" % ohci.regs.intrenable)
  print(" intrdisable 0x%08X" % ohci.regs.intrdisable)
  print(" ed_periodcurrent 0x%08X" % ohci.regs.ed_periodcurrent)
  print(" ed_controlhead 0x%08X" % ohci.regs.ed_controlhead)
  print(" ed_controlcurrent 0x%08X" % ohci.regs.ed_controlcurrent)
  print(" ed_bulkhead 0x%08X" % ohci.regs.ed_bulkhead)
  print(" ed_bulkcurrent 0x%08X" % ohci.regs.ed_bulkcurrent)
  print(" donehead 0x%08X" % ohci.regs.donehead)
  print(" fminterval 0x%08X" % ohci.regs.fminterval)
  print(" fmremaining 0x%08X" % ohci.regs.fmremaining)
  print(" periodicstart 0x%08X" % ohci.regs.periodicstart)
  print(" lsthresh 0x%08X" % ohci.regs.lsthresh)
  print(" ohci_roothub_regs.a 0x%08X" % ohci.regs.roothub.a)
  print(" ohci_roothub_regs.b 0x%08X" % ohci.regs.roothub.b)
  print(" ohci_roothub_regs.status 0x%08X" % ohci.regs.roothub.status)


  print(" ohci_roothub_regs.portstatus[0] 0x%08X" % ohci.regs.roothub.portstatus[0])
  print(" ohci_roothub_regs.portstatus[1] 0x%08X" % ohci.regs.roothub.portstatus[1])
  print(" ohci_roothub_regs.portstatus[2] 0x%08X" % ohci.regs.roothub.portstatus[2])
  print(" ohci_roothub_regs.portstatus[3] 0x%08X" % ohci.regs.roothub.portstatus[3])



def DebugDescriptor( s_USB_Devicedescriptor * pDes):
  print("\n*Descriptor*\n")

  print("Descriptor.Length: 0x%x" % pDes.Length)
  print("Descriptor.DescriptorType: 0x%02X" % pDes.DescriptorType)
  print("Descriptor.USB: 0x%04X" % pDes.USB)
  print("Descriptor.DeviceClass: 0x%04X" % pDes.DeviceClass)
  print("Descriptor.DeviceSubClass: 0x%04X" % pDes.DeviceSubClass)
  print("Descriptor.DeviceProtocol: 0x%04X" % pDes.DeviceProtocol)
  print("Descriptor.MaxPacketSize: 0x%04X" % pDes.MaxPacketSize)

  print("Descriptor.Vendor: 0x%04X" % pDes.Vendor)
  print("Descriptor.ProductID: 0x%04X" % pDes.ProductID)
  print("Descriptor.Device: 0x%04X" % pDes.Device)

  print("Descriptor.Manufacturer: 0x%02X" % pDes.Manufacturer)
  print("Descriptor.ProductIndex: 0x%02X" % pDes.ProductIndex)
  print("Descriptor.SerialNumber: 0x%02X" % pDes.SerialNumber)
  print("Descriptor.ConfigNumber: 0x%02X" % pDes.ConfigNumber)


def DebugConfigDescriptor( s_USB_Configurationdescriptor * pDes):
  print("\n+Configuration Descriptor+\n")

  print("ConfDesc.Length: 0x%02X" % pDes.Length)
  print("ConfDescDescriptorType: 0x%02X" % pDes.DescriptorType)
  print("ConfDesc.TotalLength: 0x%04X" % pDes.TotalLength)
  print("ConfDesc.NumberofInterfaces: 0x%02X" % pDes.NumberofInterfaces)

  print("ConfDesc.ConfigValue: 0x%02X" % pDes.ConfigValue)
  print("ConfDesc.Configuration: 0x%02X" % pDes.Configuration)
  print("ConfDesc.Attributes: 0x%02X" % pDes.Attributes)
  print("ConfDesc.MaxPower: 0x%02X" % pDes.MaxPower)


def DebugInterfaceDescriptor( s_USB_Interfacedescriptor * pDes):
  print("\n#Interface Descriptor#\n")
  
  print("InterDesc.Length: 0x%02X" % pDes.Length)
  print("InterDesc.DescriptorType: 0x%02X" % pDes.DescriptorType)
  print("InterDesc.Interfacenumber: 0x%02X" % pDes.Interfacenumber)
  print("InterDesc.AlternateSetting: 0x%02X" % pDes.AlternateSetting)
  print("InterDesc.NumberofEndpoints: 0x%02X" % pDes.NumberofEndpoints)
  print("InterDesc.InterfaceClass: 0x%02X" % pDes.InterfaceClass)
  print("InterDesc.InterfaceSubClass: 0x%02X" % pDes.InterfaceSubClass)
  print("InterDesc.InterfaceProtocol: 0x%02X" % pDes.InterfaceProtocol)
  print("InterDesc.InterfaceIndex: 0x%02X" % pDes.InterfaceIndex)

def DebugEndPointDescriptor( s_USB_Endpointdescriptor * pDes):
  print("\n#EndPointDescriptor Descriptor#\n")

  print("EndPointDes.Length: 0x%02X" % pDes.Length)
  print("EndPointDes.DescriptorType: 0x%02X" % pDes.DescriptorType)
  print("EndPointDes.EndpointAddress: 0x%02X" % pDes.EndpointAddress)
  print("EndPointDes.Attributes: 0x%02X" % pDes.Attributes)
  print("EndPointDes.MaxPacketSize: 0x%02X" % pDes.MaxPacketSize)
  print("EndPointDes.Interval: 0x%02X" % pDes.Interval)
