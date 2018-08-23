#define USE_HTTP
//#define USE_ASYNC //FIXME: This does not work yet

#include <hal/xbox.h>
#include <hal/fileio.h>
#include <xboxkrnl/xboxkrnl.h>
#include <xboxrt/debug.h>

#include <stdbool.h>
#include <assert.h>

#ifdef USE_HTTP
#include "network.h"
#include "http_client.h"
#endif



//#define FIX_BOOL
//#define FIX_ASSERT
#define FIX_STDIO
#include "fixes.h"

#if 0
#define write_log(fmt, ...) debugPrint(fmt, ## __VA_ARGS__)
#else
void write_log(const char* format, ...);
void write_log_crit(const char* format, ...);
#define write_log(fmt, ...) write_log(fmt, ## __VA_ARGS__)
#endif


#include "io.h"






#ifdef USE_HTTP


const char* host = "192.168.177.1";
unsigned short host_port = 8000;
const char* host_path = "/default.iso";



typedef struct {
  char canary[16];
#ifdef USE_ASYNC
  PIRP irp;
#else
  KEVENT event; //FIXME: Should not be necessary in asynchronous mode
#endif
  unsigned char* buffer;
  unsigned long long request_offset;
  unsigned long long request_length;
  unsigned long long message_from;
  unsigned long long message_to;
  unsigned long long total_length;
} DataRequest;



//FIXME: Does not support 64 bit ranges yet!
static void http_header_callback(const char* field, const char* value, void* user) {
  DataRequest* r = user;

//  write_log("header: '%s' = '%s'\n", field, value);
  if (!strcmp(field, "Content-Range")) {
    if(!strcmp(value, "None")) {
      write_log("\nRange not supported\n");
    } else if(!memcmp(value, "bytes ", 6)) {
      write_log("\nRange: %s\n", &value[6]);
      char* split_value = strdup(&value[6]);

      // Get part until '-': from
      char* dash = strchr(split_value, '-');
      assert(dash != NULL);
      *dash = '\0';
      r->message_from = atoi(split_value);

      // Get part until '/': to
      char* slash = strchr(&dash[1], '/');
      assert(slash != NULL);
      *slash = '\0';
      r->message_to = atoi(&dash[1]);

      // Get part until end: len
      r->total_length = atoi(&slash[1]);

      write_log("Range is from: %d to: %d total-len: %d (= %d)\n",
                (int)r->message_from,
                (int)r->message_to,
                (int)r->total_length,
                (int)(r->message_to - r->message_from + 1));
      free(split_value);
    } else {
      assert(false);
    }
  }
}

//FIXME: Add a callback for reporting HTTP status and message length
static void http_message_callback(unsigned long long offset, const void* buffer, unsigned long long length, void* user) {
  DataRequest* r = user;

  // Skip all reads if we don't have a buffer
  if (r->buffer == NULL) {
    return;
  }

  write_log("message %d (%d bytes)\n", (int)offset, (int)length);
#if 0
  unsigned long long new_length = offset + length;
  if (new_length > index_html_length) {
    index_html = realloc(index_html, new_length);
    index_html_length = new_length;
  }
  memcpy(&index_html[offset], buffer, length);
#endif

  //FIXME: If range is not supported, skip reads until we reach the interesting section

  // Skip reads if we are past the interesting section
  if (offset >= r->request_length) {
    return;
  }

  // Only read as many bytes as we support
  unsigned long long bytes_needed = r->request_length - offset;
  if (length > bytes_needed) {
    length = bytes_needed;
  }
  write_log("Is our ");
  write_log(r->canary);
  write_log(" dead?\n");
  write_log("moving %d bytes; needed %d at %d/%d (orig. offset: %d); ", (int)length, (int)bytes_needed, (int)offset, (int)r->request_length, (int)r->request_offset);
  write_log("from 0x%x to 0x%x!\n", (unsigned int)buffer, (unsigned int)&r->buffer[offset]);
  memcpy(&r->buffer[offset], buffer, length);
//  memset(&r->buffer[offset], 'A', length);
  write_log("moved!\n");
}

static void http_close_callback(void* user) {
  DataRequest* r = user;
  write_log("close\n");

#ifdef USE_ASYNC
  r->irp->IoStatus.Status = STATUS_SUCCESS;
  IoCompleteRequest(r->irp, IO_NO_INCREMENT);
#else
  // Mark request as complete
  KeSetEvent(&r->event, 0, FALSE);
#endif
}

static void http_error_callback(void* user) {
  DataRequest* r = user;
  write_log("error\n");

#ifdef USE_ASYNC
  r->irp->IoStatus.Status = STATUS_REQUEST_ABORTED;
  IoCompleteRequest(r->irp, IO_NO_INCREMENT);
#else
  // Mark request as complete
  KeSetEvent(&r->event, 0, FALSE);
#endif
}



static unsigned long long http_client_range_request(PIRP irp, const char* host, unsigned short host_port, const char* abs_path, void* buffer, unsigned long long offset, unsigned long long length) {
  write_log("Starting request\n");
  //memory_statistics();

#if 0
  if (length > 128) {
    unsigned long long total_length = 0;
    total_length = synchronous_http_client_request(host, host_port, abs_path, buffer, 0, 128);
    total_length += synchronous_http_client_request(host, host_port, abs_path, (unsigned int)buffer + 128, offset + 128, length - 128);
    return total_length;
  }
#endif

  // Initialize request and event
  DataRequest r;
  strcpy(r.canary, "CANARY");
  r.buffer = buffer;
  r.request_offset = offset;
  r.request_length = length;
  r.message_from = 0;
  r.message_to = 0;
  r.total_length = 0;
#ifdef USE_ASYNC
  r.irp = irp;
#else
  KeInitializeEvent(&r.event, NotificationEvent, FALSE);
#endif

  // There's a bug in the Python HTTP server, where requesting "0-0" returns the entire file
  if (length < 2) {
    length = 2;
  }

  // Construct a header now
  char header_buffer[128];
  //FIXME: Allow unsigned long long instead!
  sprintf(header_buffer, "Range: bytes=%d-%d\r\n", (int)offset, (int)(offset + length - 1));

  write_log("HTTP Request started; Header:\n%s\n", header_buffer);

  ULONG start_time = KeTickCount;

  // Start request which will handle the event
  http_client_request(host, host_port, abs_path, header_buffer, http_header_callback, http_message_callback, http_close_callback, http_error_callback, &r);

#ifdef USE_ASYNC
  return 0;
#endif

  write_log("HTTP Request pending\n");

  // Wait until event is done and free it
  KeWaitForSingleObject(&r.event, Executive, KernelMode, FALSE, NULL);

  // Calculate length of the received data
  unsigned long long received_length = r.message_to - r.message_from + 1;

  // Generate some statistics and report finish
  ULONG end_time = KeTickCount;
  unsigned int duration = end_time - start_time;
  if (duration == 0) {
    duration = 1;
  }
  unsigned int datarate = (unsigned int)received_length / duration;
  write_log_crit("HTTP Request finished %d bytes in %d milliseconds (%d kB/s)\n", (int)received_length, duration, datarate);

  // If no data is requested, we will return the file length instead
  if ((r.buffer == NULL) && (r.request_offset == 0) && (r.request_length == 0)) {
    return r.total_length;
  }

  //FIXME: Get actual number of bytes read
  return received_length;
}

#else

static int iso_handle;

#endif








_OBJECT_STRING(xiso_driver_device_name, "\\Device\\XIso0");
_OBJECT_STRING(xiso_driver_dos_device_name, "\\??\\XIso0:");


static const unsigned int sector_size = 2048;

static __attribute__((__stdcall__)) NTSTATUS irp_success(IN PDEVICE_OBJECT DeviceObject, IN PIRP Irp) {
  write_log("irp_success IRQL: %d\n", KeGetCurrentIrql());
  Irp->IoStatus.Status = STATUS_SUCCESS;
  IoCompleteRequest(Irp, IO_NO_INCREMENT);
  return STATUS_SUCCESS;
}

static __attribute__((__stdcall__)) NTSTATUS irp_read(IN PDEVICE_OBJECT DeviceObject, IN PIRP Irp) {
//  write_log("irp_read IRQL: %d\n", KeGetCurrentIrql());
  assert(KeGetCurrentIrql() == DISPATCH_LEVEL);

  PIO_STACK_LOCATION IrpSp = IoGetCurrentIrpStackLocation(Irp);

//  write_log("In irp_read %d %d\n", Irp, IrpSp);

//return IoInvalidDeviceRequest(DeviceObject, Irp);
//return irp_success(DeviceObject, Irp);

  bool is_cache_request = IrpSp->Flags & FSC_REQUEST;
  if (is_cache_request) {
    write_log("Doing cache request\n");
  }

  LONGLONG start = IrpSp->Parameters.Read.ByteOffset.QuadPart;
  LONGLONG end = start + IrpSp->Parameters.Read.Length;

  write_log("Attempting to read %d - %d (%d bytes)\n", (int)start, (int)end, (int)IrpSp->Parameters.Read.Length);

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

#if 1

  write_log("reading data to 0x%x (includes offset %d)%s\n", &destination[offset], (int)offset, is_cache_request ? " (Cached)" : "");

#if 0
  if (!is_cache_request) {
    IoLockUserBuffer(Irp, IrpSp->Parameters.Read.Length);
  }
#endif

#ifdef USE_HTTP
  //KIRQL old_irql = KeRaiseIrqlToDpcLevel();
  size_t len = IrpSp->Parameters.Read.Length;
  uint8_t* mapped_destination = &destination[offset];


  if (is_cache_request) {
    //FIXME: A hack like this is necessary, but this seems to fail after a while?
    mapped_destination = MmMapIoSpace(MmGetPhysicalAddress(mapped_destination), len, PAGE_READWRITE);
  }
  unsigned long long numberOfBytesRead = 0;
  numberOfBytesRead = http_client_range_request(Irp, host, host_port, host_path, mapped_destination, start, len);

  unsigned char byte = mapped_destination[0];
  unsigned char bytex = mapped_destination[130];

  if (is_cache_request) {
  //  MmLockUnlockBufferPages(mapped_destination, len, FALSE);
    MmUnmapIoSpace(mapped_destination, len);
  }



#ifdef USE_ASYNC
  // Information should contain how many bytes will be read?
  Irp->IoStatus.Information = IrpSp->Parameters.Read.Length;
  IoMarkIrpPending(Irp);

  write_log("Marked IRP as pending\n");

  return STATUS_PENDING;
#endif

#else

  // Finish synchronously?! absolute madlad style!

  int newFilePointer;
  int r1 = XSetFilePointer(iso_handle, start, &newFilePointer, FILE_BEGIN);

  unsigned int numberOfBytesRead;
  int r2 = XReadFile(iso_handle, &destination[offset], IrpSp->Parameters.Read.Length, &numberOfBytesRead);

  unsigned char byte = &destination[offset+0];
  unsigned char bytex = &destination[offset+130];

#endif
  Irp->IoStatus.Information = numberOfBytesRead;

  write_log("Success: %d-%d; read %d / %d; [0]: 0x%x [130]: 0x%x\n", (int)start, (int)end, (int)numberOfBytesRead, (int)IrpSp->Parameters.Read.Length, byte, bytex);

  Irp->IoStatus.Status = STATUS_SUCCESS;
  IoCompleteRequest(Irp, IO_NO_INCREMENT);
  return STATUS_SUCCESS;
#endif
}

static __attribute__((__stdcall__)) NTSTATUS irp_control(IN PDEVICE_OBJECT DeviceObject, IN PIRP Irp) {
  write_log("irp_control IRQL: %d\n", KeGetCurrentIrql());

  assert(KeGetCurrentIrql() == DISPATCH_LEVEL);

  NTSTATUS status;
  PIO_STACK_LOCATION IrpSp;

  IrpSp = IoGetCurrentIrpStackLocation(Irp);

  switch (IrpSp->Parameters.DeviceIoControl.IoControlCode) {
  //FIXME: Handle these
  case IOCTL_CDROM_GET_DRIVE_GEOMETRY:

    DISK_GEOMETRY* g = Irp->UserBuffer;

#ifdef USE_HTTP
    unsigned long long filesize = http_client_range_request(NULL, host, host_port, host_path, NULL, 0, 0);
    write_log("Got filesize %d\n", (int)filesize);
#else
    //FIXME: Support multi-part ISOs
    unsigned int filesize;
    XGetFileSize(iso_handle, &filesize);
#endif

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
    write_log("Unhandled device control: 0x%x\n", IrpSp->Parameters.DeviceIoControl.IoControlCode);
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

  write_log("start_io\n");

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


#ifdef USE_HTTP

  // Load the HTTP client for testing
  network_setup();
  write_log("Using HTTP! Ignoring '%s'; using '%s' from '%s', port: %d\n", xiso_path, host_path, host, host_port);

#else

  // Open our ISO file
  status = XCreateFile(&iso_handle, xiso_path, GENERIC_READ, 0, OPEN_EXISTING, 0);
  if (status == ERROR_ALREADY_EXISTS) {
    status = STATUS_SUCCESS;
  }
  if (status != STATUS_SUCCESS) {
    write_log("Failed to load ISO\n");
    return status;
  }

#endif

  // Register our driver and the emulated drive
  write_log("Creating device\n");
  status = IoCreateDevice(&iso_driver_object, 0, &xiso_driver_device_name, FILE_DEVICE_CD_ROM, FALSE, &device_object);
  if (status != STATUS_SUCCESS) {
    write_log("Failed to create device\n");
  }

  // This essentialy mounts the device
  write_log("Linking device\n");
  status = IoCreateSymbolicLink(&xiso_driver_dos_device_name, &xiso_driver_device_name);
  if (status != STATUS_SUCCESS) {
    write_log("Failed to link device\n");
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

//FIXME: Do this when the device is destroyed?!
#if 0
#ifdef USE_HTTP
  network_cleanup();
#endif
#endif
