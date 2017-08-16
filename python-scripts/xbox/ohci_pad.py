#/*  File: pad.cpp                                                             */
#/*  bkenwright@xbdev.net  -  www.xbdev.net                                    */

Debug = True


#// These couple of globals are defined in ohci.cpp - there our small group
#// of descriptors which we use to communcate with the ohci-usb

extern __u32 eds[176 + 0x100 + 0x100]; // ohci.cpp
extern __u32 EDA;
extern s_Endpointdescripor * ED;



def OHCI_ED_GET_FA(s):
  return ((s) & 0x7f)
OHCI_ED_ADDRMASK = 0x0000007f
def OHCI_ED_SET_FA(s):
  return (s)
def OHCI_ED_GET_EN(s):
  return (((s) >> 7) & 0xf)
def OHCI_ED_SET_EN(s):
  return ((s) << 7)
OHCI_ED_DIR_MASK = 0x00001800
OHCI_ED_DIR_TD = 0x00000000
OHCI_ED_DIR_OUT = 0x00000800
OHCI_ED_DIR_IN = 0x00001000
OHCI_ED_SPEED = 0x00002000
OHCI_ED_SKIP = 0x00004000
OHCI_ED_FORMAT_GEN = 0x00000000
OHCI_ED_FORMAT_ISO = 0x00008000
def OHCI_ED_GET_MAXP(s):
  return (((s) >> 16) & 0x07ff)
def OHCI_ED_SET_MAXP(s)
  return ((s) << 16)
OHCI_ED_MAXPMASK = (0x7ff << 16)

OHCI_HALTED = 0x00000001
OHCI_TOGGLECARRY = 0x00000002
OHCI_HEADMASK = 0xfffffffc

struct ohci_ed_t_ 
{
        __u32            ed_flags;
        __u32            ed_tailp;
        __u32            ed_headp;
        __u32            ed_nexted;
};


OHCI_TD_R              0x00040000              #/* Buffer Rounding  */
OHCI_TD_DP_MASK        0x00180000              #/* Direction / PID */
OHCI_TD_SETUP          0x00000000
OHCI_TD_OUT            0x00080000
OHCI_TD_IN             0x00100000
def OHCI_TD_GET_DI(x):
  return (((x) >> 21) & 7)       #/* Delay Interrupt */
def OHCI_TD_SET_DI(x):
  return ((x) << 21)
OHCI_TD_NOINTR         0x00e00000
OHCI_TD_INTR_MASK      0x00e00000
OHCI_TD_TOGGLE_CARRY   0x00000000
OHCI_TD_TOGGLE_0       0x02000000
OHCI_TD_TOGGLE_1       0x03000000
OHCI_TD_TOGGLE_MASK    0x03000000
def OHCI_TD_GET_EC(x):
  return (((x) >> 26) & 3)       #/* Error Count */
def OHCI_TD_GET_CC(x):
  return ((x) >> 28)             #/* Condition Code */
OHCI_TD_NOCC = 0xf0000000

struct ohci_td_t_
{
         __u32           td_flags;
         __u32           td_cbp;         /* Current Buffer Pointer */
         __u32           td_nexttd;      /* Next TD */
         __u32           td_be;          /* Buffer End */
} ;


OHCI_CTRL_CLE = (1 << 4)        #/* control list enable */
OHCI_CTRL_BLE = (1 << 5)        #/* bulk list enable */
OHCI_CTRL_HCFS = (3 << 6)       #/* host controller functional state */


OHCI_CLF = (1 << 1)        #/* control list filled */
OHCI_BLF = (1 << 2)        #/* bulk list filled */

OHCI_CTRL_CLE = (1 << 4)        #/* control list enable */
OHCI_CTRL_BLE = (1 << 5)        #/* bulk list enable */
OHCI_CTRL_HCFS = (3 << 6)       #/* host controller functional state */


OHCI_CLF = (1 << 1)        #/* control list filled */
OHCI_BLF = (1 << 2)        #/* bulk list filled */


#/******************************************************************************/



def usb_bulk_msg( usbd_device * dev, data):
	ohci_t * ohci = dev->p_ohci;


  size = len(data)

  _buffer = malloc(256) # FIXME: free later?
	xmemcpy(_buffer, data, size)

	ke.MmLockUnlockBufferPages(_buffer, 0x8, 0)
	real_pcmd = ke.MmGetPhysicalAddress(_buffer)

	#__u8 Descriptors[256] = {0};
  Descriptors = malloc(256) # FIXME: free later?
	ke.MmLockUnlockBufferPages(Descriptors, 256, 0 )
	real_pDescriptors = ke.MmGetPhysicalAddress(Descriptors)

	s_Transferdescriptor *TD;
	TD = (s_Transferdescriptor *)(((__u32 *)ED) + 20);
	__u32 TDA = EDA + 80;
	__u32 realTDA = ke.MmGetPhysicalAddress(TDA)


#////////////////////////////////////////////////////////////////////////
#//   --Transfer Descriptor TD--
#//   Offset	Field		Size	Value		Desc
#//   0                  4       0..17       reserved
#//                              
#//      						18          R  - bufferRounding
#//								19..20      DP - Direction/PID
#//								                 00b SETUP
#//												 01b OUT
#//												 10b IN
#//												 11b reserved
#//								21..23      DI - DelayInterrupt
#//	                            24..25      T  - DataToggle
#//								26..27      EC - ErrorCount
#//								28..31      CC - ConditionCode
#//  4                   4                   CurrentBufferPoinnter (CBP)
#//	8                   4       0..3        Zero
#//	                            4..31       Next TD (NextTD)
#// 12                   4                   Buffer End (BE)
#//                                             
#//(Total Size 16 bytes or 4 dwords)
#//
#////////////////////////////////////////////////////////////////////////


	// 0xE20050CA

	__u32 td_format  = 0;
	td_format        |= OHCI_TD_OUT;        // 0x00080000  e.g. 1<<19
    td_format        |= OHCI_TD_TOGGLE_0;   // 0x02000000  e.g. 2<<24
	                                        /* I've set the data toggle sync here in 
	                                         * the TD by setting the MSB to 1 of Toggle Bits
	                                         * so the ED toggle bit isn't used. 
	                                         */
	td_format        |= OHCI_TD_NOCC;       // 0xf0000000
	                                        /* Set our ConditionCode to no errors */

	
	TD[0].Format     = td_format;
	#//TD[0].Format	 = 0xE20050CA;			// Our Bulk Msg!
	TD[0].Buffer	 = real_pcmd;  
	TD[0].NextTD	 = realTDA + 16; 
	TD[0].BufferEnd	 = real_pcmd + size - 1; 		


	td_format        |= 0;
	td_format        |= OHCI_TD_OUT;
	td_format        |= OHCI_TD_TOGGLE_1;
	td_format        |= OHCI_TD_NOCC;

	TD[1].Format	= td_format;			// Receive Start of Descriptor
	TD[1].Buffer	= real_pDescriptors; 
	TD[1].NextTD	= realTDA + 32;
	TD[1].BufferEnd = real_pDescriptors + 7;


	td_format        |= 0;
	td_format        |= OHCI_TD_OUT;
	td_format        |= OHCI_TD_TOGGLE_0;
	td_format        |= OHCI_TD_NOCC;

	TD[3].Format	 = td_format;
	#//TD[1].Format	 = 0xE30050CB;			// Queue END
	TD[3].Buffer	 = 0;
	TD[3].NextTD	 = 0;
	TD[3].BufferEnd	 = 0;

#	////////////////////////////////////////////////////////////////////////
#//   --EndPoint Descriptor ED--
#//   Offset	Field		Size	Value		Desc
#//   0                  4       Bitmap           
#//	                            0..6        FA - Function Address
#//	 							
#//		                        7..10       EN - EndpointNumber
#//								11..12      D  - Direction
#//								                 00b GetDir From TD
#//												 01b OUT
#//												 10b IN
#//												 11b GetDir From TD
#//								13          S  - Speed (Full Speed=0)
#//								14          K  - sKip
#//								15          F  - Format
#//								                 0 - Control/Bulk/Int********
#//												 1 - Isochronous
#//	                            16..26      MPS  MaximumPacketSize
#//							    27..31      reserved
#//	4                   4       Bitmap
#//	                            0..3        Zero Aligment
#//								4..31       TD Queue Tail Pointer (TailP)
#//	8                   4       Bitmap
#//	                            0           H  - Halted
#//								1           C  - toggleCarry
#//								2..3        reserved
#//								4..31       TD Queue Head Pointer (HeadP)
#//	12                  4       Bitmap
#//	                            0..3        Zero Aligment
#//								4..31       Next Endpoint Descriptor (NextED)
#//
#//(Total Size 16 bytes or 4 dwords)
#//
#////////////////////////////////////////////////////////////////////////

	#//__u32 format = 0x00401801; // 2(OUT) or 82(IN)?
	#// 

	__u32 ed_format =  0x00400000;
	ed_format       |= OHCI_ED_DIR_OUT;    // 0x00000800
	ed_format       |= OHCI_ED_DIR_IN;     // 0x00001000



	__u8 Addr       =  dev->address;
	__u8 EndAddr    =  0x2;

	ED[0].Format    =  ed_format;

	ED[0].Headptr   =  realTDA;
	ED[0].Tailptr   =  realTDA + 16;
	ED[0].Format    &= 0xFFFFFF00;          // Clear old address
	ED[0].Format    += Addr;                // Insert new address

	ED[0].Format    |= (EndAddr << 7 );


	#// have to enable bulk tx
	#//ohci->regs->cmdstatus  |= 2;			         // CommandStatus
	#//ohci->regs->control	   = 0x90;		             // set CLE

	ohci->regs->cmdstatus |= (1<<2); // BLF
	ohci->regs->control = OHCI_CTRL_BLE | (2<<6); // BLF 
	ohci->regs->intrstatus = ohci->regs->intrstatus; // clear all Interruptflags


	#// wait for execution
	#//dbg("waiting for execution\n");

	while(  (ohci->regs->intrstatus & 2)== 0 ):
    pass

	xSleep(10)

	#// ERRORS?
	ohci_hcca *hcca = (ohci_hcca*)ohci->hcca #// HCCA
	hcca->done_head &= 0xfffffffe #// DoneHead in HCCA

	if( (hcca->done_head>>28) !=0 ):
    if Debug:
      print("\nError Occured\n")
		return

	//------------------------------------------------------------------

	#// Where all done and finished now, so we set our ED's to our
	#// Queue END where they behave and wait.
	ED[0].Headptr = realTDA + 48
	ED[0].Tailptr = realTDA + 64

  if Debug:
	  ErrorCount     = OHCI_TD_GET_EC( TD[0].Format )
	  ConditionCode  = OHCI_TD_GET_CC( TD[0].Format )
	  print("ErrorCount: " + str(ErrorCount))
	  print("ConditionCode: " + str(ConditionCode))

	xSleep(10)

	#//xmemcpy( data, Descriptors, size);


	ED[0].Format = 0x00004000




__u8 xbuffer[256] = {0};

def usb_bulk_msg_in( usbd_device * dev, size)
{

	ohci_t * ohci = dev->p_ohci;
	
	xmemset(xbuffer, 0, 256 );


	xMmLockUnlockBufferPages( (__u32)xbuffer, 0x250, 0);
	__u32 real_pbuffer = xMmGetPhysicalAddress( (__u32)xbuffer);


	s_Transferdescriptor *TD;
	TD = (s_Transferdescriptor *)(((__u32 *)ED) + 20);
	__u32 TDA = EDA + 80;
	__u32 realTDA = xMmGetPhysicalAddress( (__u32)TDA );



	// 0xE20050CA

	__u32 td_format  = 0;
	td_format        |= OHCI_TD_IN;         // 0x00100000  e.g. 1<<19
    td_format        |= OHCI_TD_TOGGLE_0;   // 0x02000000  e.g. 2<<24
	                                        /* I've set the data toggle sync here in 
	                                         * the TD by setting the MSB to 1 of Toggle Bits
	                                         * so the ED toggle bit isn't used. 
	                                         */
	td_format        |= OHCI_TD_NOCC;       // 0xf0000000
	                                        /* Set our ConditionCode to no errors */

	TD[0].Format     = td_format;			// Our Bulk Msg!		
	TD[0].Buffer	 = real_pbuffer;  
	TD[0].NextTD	 = realTDA + 16; 
	TD[0].BufferEnd	 = real_pbuffer + size - 1; 		


  if False:
	  td_format        |= 0;
	  td_format        |= OHCI_TD_IN;
	  td_format        |= OHCI_TD_TOGGLE_1;
	  td_format        |= OHCI_TD_NOCC;
	  TD[1].Format	= td_format;			// Receive Start of Descriptor
	  TD[1].Buffer	= real_pbuffer; 
	  TD[1].NextTD	= realTDA + 32;
	  TD[1].BufferEnd = real_pbuffer + size - 1;

	td_format        |= 0;
	td_format        |= OHCI_TD_IN;
	td_format        |= OHCI_TD_TOGGLE_1;
	td_format        |= OHCI_TD_NOCC;
	TD[1].Format	 = td_format;			// Queue END		
	TD[1].Buffer	 = 0;
	TD[1].NextTD	 = 0;
	TD[1].BufferEnd	 = 0;



	__u32 ed_format =  0x00400000;
	ed_format       |= OHCI_ED_DIR_OUT;    // 0x00000800
	ed_format       |= OHCI_ED_DIR_IN;     // 0x00001000



	__u8 Addr       =  dev->address;
	__u8 EndAddr    =  0x2;

	ED[0].Format    =  ed_format;

	ED[0].Headptr   =  realTDA;
	ED[0].Tailptr   =  realTDA + 16;
	ED[0].Format    &= 0xFFFFFF00;          // Clear old address
	ED[0].Format    += Addr;                // Insert new address

	ED[0].Format    |= (EndAddr << 7 );


	xSleep(20);

	#// have to enable bulk tx
	#//ohci->regs->cmdstatus  |= 2;			         // CommandStatus
	#//ohci->regs->control	   = 0x90;		             // set CLE

	ohci->regs->cmdstatus |= (1<<2); // BLF
	ohci->regs->control = OHCI_CTRL_BLE | (2<<6); // BLF 
	ohci->regs->intrstatus = ohci->regs->intrstatus; // clear all Interruptflags


	// wait for execution
	//dbg("waiting for execution\n");
	do
	{
		//dbg("waiting for execution-in loop\n");

	}while(  (ohci->regs->intrstatus & 2)== 0 );

	//dbg("waiting for execution-out loop\n");

	ohci->regs->intrstatus = ohci->regs->intrstatus;

	xSleep(30);

	// ERRORS?
	ohci_hcca *hcca = (ohci_hcca*)ohci->hcca;		// HCCA
	hcca->done_head &= 0xfffffffe;					// DoneHead in HCCA

	if( (hcca->done_head>>28) !=0 ):
    if Debug:
      print("\nError Occured\n")
		return

  #FIXME: Why is this only happening for debug in original code?!?!?! looks like a bug
  #// Where all done and finished now, so we set our ED's to our
  #// Queue END where they behave and wait.
  ED[0].Headptr = realTDA + 48;
  ED[0].Tailptr = realTDA + 64;

  if Debug:
    #FIXME: Why is this only happening for debug ?!?!?!

	  __u32 ErrorCount     = OHCI_TD_GET_EC( TD[0].Format );
	  __u32 ConditionCode  = OHCI_TD_GET_CC( TD[0].Format );


	  if( ErrorCount  || ConditionCode ):
		  print("ErrorCount: " + str(ErrorCount))
      print("ConditionCode: " + str(ConditionCode))

	#//xSleep(50);

  data = bytearray()
	xmemcpy( data, xbuffer, size);


	#//ED[0].Format = 0x00004000;

  return data
