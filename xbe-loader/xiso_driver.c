#include <hal/xbox.h>
#include <hal/fileio.h>
#include <xboxkrnl/xboxkrnl.h>
#include <xboxrt/debug.h>

#include <stdbool.h>
#include <assert.h>

#define FIX_BOOL
#define FIX_ASSERT
#define FIX_STDIO
#include "fixes.h"

#if 0
#define debug_print(fmt, ...) debugPrint(fmt, ## __VA_ARGS__)
#else
void write_log(const char* format, ...);
#define debug_print(fmt, ...) write_log(fmt, ## __VA_ARGS__)
#endif










#include "io.h"



_OBJECT_STRING(xiso_driver_device_name, "\\Device\\XIso0");
_OBJECT_STRING(xiso_driver_dos_device_name, "\\??\\XIso0:");

static int iso_handle;

static const unsigned int sector_size = 2048;

static __attribute__((__stdcall__)) NTSTATUS irp_success(IN PDEVICE_OBJECT DeviceObject, IN PIRP Irp) {
  debug_print("irp_success IRQL: %d\n", KeGetCurrentIrql());
  Irp->IoStatus.Status = STATUS_SUCCESS;
  IoCompleteRequest(Irp, IO_NO_INCREMENT);
  return STATUS_SUCCESS;
}

static __attribute__((__stdcall__)) NTSTATUS irp_read(IN PDEVICE_OBJECT DeviceObject, IN PIRP Irp) {
//  debug_print("irp_read IRQL: %d\n", KeGetCurrentIrql());
  assert(KeGetCurrentIrql() == DISPATCH_LEVEL);

  PIO_STACK_LOCATION IrpSp = IoGetCurrentIrpStackLocation(Irp);

  debug_print("In irp_read %d %d\n", Irp, IrpSp);
  debug_print("length: %d\n", (int)IrpSp->Parameters.Read.Length);

//return IoInvalidDeviceRequest(DeviceObject, Irp);
//return irp_success(DeviceObject, Irp);

  bool is_cache_request = IrpSp->Flags & FSC_REQUEST;
  if (is_cache_request) {
    debug_print("Doing cache request\n");
  }

  LONGLONG start = IrpSp->Parameters.Read.ByteOffset.QuadPart;
  LONGLONG end = start + IrpSp->Parameters.Read.Length;

  debug_print("Attempting to read %d - %d\n", (int)start, (int)end);

  //FIXME: How can I disable FSCACHE?
  if (!is_cache_request) {

    //FIXME: which conditions were these?
    if (false) {
      Irp->IoStatus.Status = STATUS_INVALID_PARAMETER;
      IoCompleteRequest(Irp, IO_NO_INCREMENT);
      return STATUS_INVALID_PARAMETER;
    }

  }

  // We don't have to do anything if no data was requested
  if (IrpSp->Parameters.Read.Length == 0) {
    Irp->IoStatus.Information = 0;
    Irp->IoStatus.Status = STATUS_SUCCESS;
    IoCompleteRequest(Irp, IO_NO_INCREMENT);
    return STATUS_SUCCESS;
  }

  //FIXME: Get sector number from start and only do sector requests?

  uint8_t* destination;
  uint64_t offset;
  if (is_cache_request) {
      offset = 0;
      destination = IrpSp->Parameters.Read.CacheBuffer;
  } else {
      offset = IrpSp->Parameters.Read.BufferOffset;
      destination = Irp->UserBuffer;
  }


#if 0
  // Information should contain how many bytes will be read?
  Irp->IoStatus.Information = IrpSp->Parameters.Read.Length;
  IoMarkIrpPending(Irp);

  debug_print("Marked IRP as pending\n");

  return STATUS_PENDING;
#else
#if 0
  //FIXME: Finish synchronously?! absolute madlad style!

  debug_print("Filling buffer at 0x%x\n", Irp->UserBuffer);
  memset(&destination[offset], 'A', IrpSp->Parameters.Read.Length);
  Irp->IoStatus.Information = IrpSp->Parameters.Read.Length;
#else

  int newFilePointer;
  int r1 = XSetFilePointer(iso_handle, start, &newFilePointer, FILE_BEGIN);

  unsigned int numberOfBytesRead;
  int r2 = XReadFile(iso_handle, &destination[offset], IrpSp->Parameters.Read.Length, &numberOfBytesRead);

  Irp->IoStatus.Information = numberOfBytesRead;
#endif


  Irp->IoStatus.Status = STATUS_SUCCESS;
  IoCompleteRequest(Irp, IO_NO_INCREMENT);
  debug_print("Returning from read\n");
  return STATUS_SUCCESS;


#endif

}

static __attribute__((__stdcall__)) NTSTATUS irp_control(IN PDEVICE_OBJECT DeviceObject, IN PIRP Irp) {
  debug_print("irp_control IRQL: %d\n", KeGetCurrentIrql());

  assert(KeGetCurrentIrql() == DISPATCH_LEVEL);

  NTSTATUS status;
  PIO_STACK_LOCATION IrpSp;

  IrpSp = IoGetCurrentIrpStackLocation(Irp);

  switch (IrpSp->Parameters.DeviceIoControl.IoControlCode) {
  //FIXME: Handle these
  case IOCTL_CDROM_GET_DRIVE_GEOMETRY:

    DISK_GEOMETRY* g = Irp->UserBuffer;
    unsigned int filesize;
    XGetFileSize(iso_handle, &filesize);

    //FIXME: Support multi-part ISOs

    g->Cylinders.QuadPart = filesize / sector_size;
    g->MediaType = RemovableMedia;
    g->TracksPerCylinder = 1;
    g->SectorsPerTrack = 1;
    g->BytesPerSector = sector_size;

    status = STATUS_SUCCESS;
    break;
  case IOCTL_CDROM_XBOX_SECURITY:
    status = STATUS_SUCCESS;
    break;
  default:
    debug_print("Unhandled device control: 0x%x\n", IrpSp->Parameters.DeviceIoControl.IoControlCode);
    status = STATUS_INVALID_DEVICE_REQUEST;
    break;
  }

  if (status != STATUS_PENDING) {
    Irp->IoStatus.Status = status;
    IoCompleteRequest(Irp, IO_NO_INCREMENT);
  }

  return status;
}

// FIXME: The following code is for asynchronous I/O?

static void finish_read(PIRP Irp) {
  Irp->IoStatus.Status = STATUS_SUCCESS;
  IoCompleteRequest(Irp, IO_CD_ROM_INCREMENT);
}

static void start_read(PIRP Irp) {
  PIO_STACK_LOCATION IrpSp = IoGetCurrentIrpStackLocation(Irp);

  bool is_scatter_gather = Irp->Flags & IRP_SCATTER_GATHER_OPERATION;
  bool is_cache_request = IrpSp->Flags & FSC_REQUEST;
  if (!is_scatter_gather || is_cache_request) {
    //FIXME: Handle a buffer copy?
  } else {
    //FIXME: Handle scatter gather?
  }

  finish_read(Irp);
}

static __attribute__((__stdcall__)) VOID start_io(IN PDEVICE_OBJECT DeviceObject, IN PIRP Irp) {
  assert(KeGetCurrentIrql() == DISPATCH_LEVEL);

  debug_print("\nstart_io: Yay!\n\n");
  Irp->IoStatus.Status = STATUS_REQUEST_ABORTED;
  IoCompleteRequest(Irp, IO_NO_INCREMENT);

  // Just avoid handling requests during shutdown
  if (HalIsResetOrShutdownPending()) {
    Irp->IoStatus.Status = STATUS_REQUEST_ABORTED;
    IoCompleteRequest(Irp, IO_NO_INCREMENT);
    return;
  }

  PIO_STACK_LOCATION IrpSp = IoGetCurrentIrpStackLocation(Irp);

  switch (IrpSp->MajorFunction) {

  case IRP_MJ_READ:
    start_read(Irp);
    break;
  case IRP_MJ_DEVICE_CONTROL:
    switch (IrpSp->Parameters.DeviceIoControl.IoControlCode) {
    //FIXME: Handle these
    default:
      assert(false)
      break;
    }

    break;
  default:
    assert(false);
    break;
  }
}

static DRIVER_OBJECT iso_driver_object = {
  start_io, // DriverStartIo
  NULL,     // DriverDeleteDevice
  NULL,     // DriverDismountVolume
  {
    irp_success,            // IRP_MJ_CREATE
    irp_success,            // IRP_MJ_CLOSE
    irp_read,               // IRP_MJ_READ
    IoInvalidDeviceRequest, // IRP_MJ_WRITE
    IoInvalidDeviceRequest, // IRP_MJ_QUERY_INFORMATION
    IoInvalidDeviceRequest, // IRP_MJ_SET_INFORMATION
    IoInvalidDeviceRequest, // IRP_MJ_FLUSH_BUFFERS
    IoInvalidDeviceRequest, // IRP_MJ_QUERY_VOLUME_INFORMATION
    IoInvalidDeviceRequest, // IRP_MJ_DIRECTORY_CONTROL
    IoInvalidDeviceRequest, // IRP_MJ_FILE_SYSTEM_CONTROL
    irp_control,            // IRP_MJ_DEVICE_CONTROL
    IoInvalidDeviceRequest, // IRP_MJ_INTERNAL_DEVICE_CONTROL
    IoInvalidDeviceRequest, // IRP_MJ_SHUTDOWN
    IoInvalidDeviceRequest  // IRP_MJ_CLEANUP
  }
};

NTSTATUS xiso_driver_create_device(const char* xiso_path) {
  NTSTATUS status;
  PDEVICE_OBJECT device_object;

  // Open our ISO file
  status = XCreateFile(&iso_handle, xiso_path, GENERIC_READ, 0, OPEN_EXISTING, 0);
  if (status == ERROR_ALREADY_EXISTS) {
    status = STATUS_SUCCESS;
  }
  if (status != STATUS_SUCCESS) {
    debug_print("Failed to load ISO\n");
    return status;
  }

  // Register our driver and the emulated drive
  debug_print("Creating device\n");
  status = IoCreateDevice(&iso_driver_object, 0, &xiso_driver_device_name, FILE_DEVICE_CD_ROM, FALSE, &device_object);
  if (status != STATUS_SUCCESS) {
    debug_print("Failed to create device\n");
  }

  // This essentialy mounts the device
  debug_print("Linking device\n");
  status = IoCreateSymbolicLink(&xiso_driver_dos_device_name, &xiso_driver_device_name);
  if (status != STATUS_SUCCESS) {
    debug_print("Failed to link device\n");
  }

  //FIXME: Understand what exactly this means
  device_object->Flags |= DO_DIRECT_IO;
//  iso_device_object->Flags |= 0x40; // Seems to handle scatter/gather

  // We have a sector alignment requirement
  device_object->AlignmentRequirement = 1;
  device_object->SectorSize = sector_size;

  // Mark our device as no longer initializing
  device_object->Flags &= ~DO_DEVICE_INITIALIZING;

  return STATUS_SUCCESS;
}
