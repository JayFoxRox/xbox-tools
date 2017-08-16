#/******************************************************************************/
#/*                                                                            */
#/* File: xinput.cpp                                                           */
#/* Auth: bkenwright@xbdev.net                                                 */
#/* Desc: GamePad entry code for use on the xbox.                              */
#/*                                                                            */
#/******************************************************************************/

#include "misc.h"
#include "ohci.h"
#include "hub.h"
#include "pad.h"



#/*            http://www.beyondlogic.org/usbnutshell/usb5.htm                 */



Debug = True




extern __u8 found; // declared at the top of ohci.cpp




//extern void InitialiseD3D();
//extern void DisplayText(char * szStr, long xpos=100, long ypos=100 );
//extern void DataDisplay(void* data);


#/*  OHCI Code                                                                 */
#/*                                                                            */
#/*  We use our ohci library functions here, from ohci.h/cpp,...to scan for    */
#/*  devices and changes etc...get how many are plugged in..what type they are */
#/*  simple and sweet.                                                         */

def xInitInput(stXINPUT* p):
	  __u8 Buffer[256];


	  ohci_t * my_ohci = &(p->my_ohci);



  	Ports = FindOHC( my_ohci, (void*)0xFED00000)


    if Debug:
	    if( Ports==0 ):
        print("Error no ports found\n");

    i = 0 # Port number?!
	  int DEV = FindDev(my_ohci, i);

    if Debug:
		  if DEV == 0:
        print("*NO* device found at port " + str(i))
		  elif DEV == 1:
			  print("lowspeed-device found at port " + str(i))
		  elif DEV == 2:
			  print("fullspeed-device found at port " + str(i))
      else:
        print("Unknown device type on port " + str(i))
		#//if( DEV == 0 ) return;

		
		s_USB_Devicedescriptor DD[4] = {0};

		ResetPort(my_ohci, i);
		SetAddres(my_ohci, 0, found);

    if Debug:
		  print("\n\ngood to go\n\n");

		GetDesc(my_ohci, found, 1, 0, 18, Buffer);

		xmemcpy(&(DD[0]), Buffer, 18);

    if Debug:
		  DebugDescriptor( &DD[0] );
		  sprintf(buf, "ConfigNumber:%x\n", DD[0].ConfigNumber ); dbg(buf);

	  s_USB_Configurationdescriptor CD[4][8]={0};
	  s_USB_Interfacedescriptor ID[4][8][8] = {0};
	  s_USB_Endpointdescriptor ED[4][8][8][8]={0};
	
		for j in range(1, DD[i].ConfigNumber + 1)
			index = 0

			SetConfigur(my_ohci, found, j);
			GetDesc(my_ohci, found, 2, 0, 9, Buffer) #// Configdescr.
			xmemcpy(&CD[i][j - 1], Buffer, 9);

    if Debug:
			DebugConfigDescriptor( &(CD[i][j-1]) )

		GetDesc(my_ohci, found, 2, 0, (__u8) *((__u16 *) &Buffer[2]), Buffer) #// Configdescr.
		xmemcpy(&CD[i][j - 1], Buffer, 9);

    if Debug:
			DebugConfigDescriptor( &(CD[i][j-1]) )

		index += 9
		for k in range(0, CD[i][j - 1].NumberofInterfaces):
			
			xmemcpy(&ID[i][j][k], Buffer + index, 9);
      if Debug:
		  	DebugInterfaceDescriptor( &(ID[i][j][k]) );

			if (ID[i][j][k].InterfaceIndex):
			  GetDesc(my_ohci,found, 3, ID[i][j][k].InterfaceIndex, 8, Buffer); // String
			  #//DebugInterfaceDescriptor( &ID[i][j][k] );
			  GetDesc(my_ohci,found, 3, ID[i][j][k].InterfaceIndex, Buffer[0], Buffer); // String
			  
			  for (j = 1; j < (Buffer[0] / 2); j++)
				Buffer[j + 1] = Buffer[2 * j];
			  Buffer[j + 1] = 0;

			  s_USB_Stringdescriptor *SD = malloc(0x4000);
			  xmemcpy((__u8 *) SD, Buffer, Buffer[0]);
        if Debug:
			    print("\nInterface %d: %s\n" % (k + 1, &Buffer[2]));

			index += 9;
			for l in range(0, ID[i][j][k].NumberofEndpoints):
			  #// Causes a link error?
			  #//xmemcpy(&ED[i][j][k][l], Buffer + index, 9);
			
        if Debug:
				  DebugEndPointDescriptor( &ED[i][j][k][l] );

    #// we set the default configuration here 
    #//usb_set_configuration(dev, dev->config[0].bConfigurationValue))
    #//	usb_set_configuration(my_ohci, found, CD[i][j-1].ConfigValue);
    #//CD[i][j-1].ConfigValue;

		set_control_msg(my_ohci, found,
              USB_REQ_SET_CONFIGURATION, 0, CD[i][j-1].ConfigValue, 0, 0, NULL);

	
		#//-----------------------work on the hub!-------------------------/

		#// ref: http://fxr.watson.org/fxr/source/dev/usb/uhub.c
		#///
		#// To have the best chance of success we do things in the exact same
		#// order as Windoze98.  This should not be necessary, but some
		#// devices do not follow the USB specs to the letter.
		#//
		#// These are the events on the bus when a hub is attached:
		#//  Get device and config descriptors (see attach code)
		#//  Get hub descriptor (see above)
		#//  For all ports
		#//     turn on power
		#//     wait for power to become stable
		#// (all below happens in explore code)
		#//  For all ports
		#//     clear C_PORT_CONNECTION
		#//  For all ports
		#//     get port status
		#//     if device connected
		#//        wait 100 ms
		#//        turn on reset
		#//        wait
		#//        clear C_PORT_RESET
		#//        get port status
		#//        proceed with device attachment
		#///


  if Debug:
		print("\n\nHUB INTERIGATION AND SETTING UP\n\n");

	
	xmemset(Buffer, 0, 255);

	//usb_get_device_descriptor(my_ohci, 1, 18, Buffer);
	//DebugDescriptor( (s_USB_Devicedescriptor *)Buffer );

	usbd_device dev;
	dev.p_ohci  = my_ohci;
	dev.address = found; // root hub should be addr 1


	do_hub_work(&dev);




	#// Testing...gamepad 1 is allocated to addr 3

	
	#//Assumptions - for this small test section...I've assumed taht only 
	#//a single gamepad is plugged in.
	

  if Debug:
	  print("\n\n--gamepad_0---\n\n");



	#//Getting Descriptor
	s_USB_Devicedescriptor devdesc = {0};
	dev.address = 3;		

	devrequest req = {0};
	req.requesttype = UT_READ_DEVICE;
	req.request     = UR_GET_DESCRIPTOR;
	req.value = 0;
	req.value |= (0x00ff & 0);
	req.value |= (0xff00 & (UDESC_DEVICE<<8));
	req.index       = 0;
	req.length      = 18;

	#// What is this new function?...why didn't we use the normal
	#// usd_do_request(..)?....hmm...well it seems that the gamepad
	#// max packet size is 0x40...and if we use the 0x8 which I've done upto
	#// now we only get the first 8 bytes of the desciptor...using this slightly
	#// modified version, we get the full descriptor of our gamepad :)
	usbd_do_request_big_packet(&dev, &req, &devdesc);

  if Debug:
  	DebugDescriptor( &devdesc );


	xSleep(10);

	#// USB_REQ_SET_CONFIGURATION, 0, configuration, 0, 0, NULL);

	#// Set the config descriptor for gamepad

	bConfigurationValue = 0x01

	usbd_device dev_temp;
	dev_temp.address  = 3;
	dev_temp.p_ohci   = dev.p_ohci;

	devrequest dr = {0};

	dr.requesttype	= UT_WRITE_DEVICE  #// 0x80
	dr.request		= UR_SET_CONFIG      #// 0x09
	dr.value		= bConfigurationValue  #// 0x01
	dr.index		= 0
	dr.length		= 0

	usbd_do_request_big_packet(&dev_temp, &dr, 0 )

	return 0


devrequest dr = {0};

def xGetPadInput(stXPAD * p, stXINPUT * xin, iWhichPad = 0):   #// 0 is default pad
	usbd_device dev;
	dev.p_ohci  = &(xin->my_ohci);
	dev.address = 3 #// This will choose the first gamepad it finds, only for debug

	stXPAD data_in = {0};



	#// bug
	bConfigurationValue = 0x01

	#//devrequest dr = {0};

	dr.requesttype	= UT_WRITE_DEVICE #// 0x80
	dr.request		= UR_SET_CONFIG     #// 0x09
	dr.value		= bConfigurationValue #// 0x01
	dr.index		= 0
	dr.length		= 0

	

	#// bug
	#//while(true)

	#//usbd_do_request_big_packet(&dev, &dr, 0 );

	usb_bulk_msg_in(&dev, 20, &data_in)
	xmemcpy(p, &data_in, 20)


	#//DataDisplay( (void*) &data_in );



	#//xSleep(100);

	usbd_do_request_big_packet(&dev, &dr, 0 )


	#// Some error checking to be put here!
	#//if( data_in.structsize == 0 )
	#//	break;

	return 0 #// no error checking as of yet
}


def xSetPadInput(stXPAD * p, stXINPUT * xin, iWhichPad = 0):
	usbd_device dev;
	dev.p_ohci  = &(xin->my_ohci);
	dev.address = 3;  #// This will choose the first gamepad it finds, only for debug

	#// Rumbble...lets see if we can make our gamepad rumble :)

	data1 = bytes([0,6,0,120,0,120]) #// rumble data
	usb_bulk_msg(&dev, data1);  #// simple bulk send function (in pad.c/.h)
			
	data2 = bytes([0,6,0,0,  0,0]);
	usb_bulk_msg(&dev, data2);

	return 0


def xReleaseInput(stXINPUT * p):
  assert(False)
	return 0



