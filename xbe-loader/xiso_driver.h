#ifndef __XISO_DRIVER_H__
#define __XISO_DRIVER_H__

extern OBJECT_STRING xiso_driver_device_name;
extern OBJECT_STRING xiso_driver_dos_device_name;

NTSTATUS xiso_driver_create_device(const char* xiso_path);
//FIXME: xiso_destroy_device();

#endif
