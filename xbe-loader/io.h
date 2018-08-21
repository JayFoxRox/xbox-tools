#ifndef __IO_H__
#define __IO_H__

#include "cheat.h"




// The following is Xbox specific

// Warning! those are different for different platforms
#define IRP_MJ_READ                     0x02
#define IRP_MJ_DEVICE_CONTROL           0x0a

#define DO_DIRECT_IO           0x00000004
#define DO_DEVICE_INITIALIZING 0x00000010

#pragma ms_struct on
typedef struct _IO_STACK_LOCATION {
  UCHAR MajorFunction;
  UCHAR MinorFunction;
  UCHAR Flags;
  UCHAR Control;
  union {
    struct {
      ULONG Length;
      union {
        ULONG BufferOffset;
        PVOID CacheBuffer;
      };
      LARGE_INTEGER ByteOffset;
    } Read;
    struct {
      ULONG OutputBufferLength;
      PVOID InputBuffer;
      ULONG InputBufferLength;
      ULONG IoControlCode;
    } DeviceIoControl;
  } Parameters;
} __attribute__((packed)) IO_STACK_LOCATION;
typedef struct _IO_STACK_LOCATION* PIO_STACK_LOCATION;
#pragma ms_struct reset

#define FSC_REQUEST 0x80





// These are mostly stolen from MSDN

typedef enum _MEDIA_TYPE { 
  RemovableMedia  = 0x0b,
} MEDIA_TYPE;

typedef struct _DISK_GEOMETRY {
  LARGE_INTEGER Cylinders;
  ULONG         MediaType;
  DWORD         TracksPerCylinder;
  DWORD         SectorsPerTrack;
  DWORD         BytesPerSector;
} DISK_GEOMETRY;

#define CTL_CODE(t,f,m,a) (((t)<<16)|((a)<<14)|((f)<<2)|(m))

#define  METHOD_BUFFERED  0

#define  FILE_READ_ACCESS  0x0001

#define FILE_DEVICE_CD_ROM 0x00000002

#define IOCTL_CDROM_BASE FILE_DEVICE_CD_ROM
#define IOCTL_CDROM_CHECK_VERIFY CTL_CODE(IOCTL_CDROM_BASE, 0x0200, METHOD_BUFFERED, FILE_READ_ACCESS)
#define IOCTL_CDROM_GET_DRIVE_GEOMETRY CTL_CODE(IOCTL_CDROM_BASE, 0x0013, METHOD_BUFFERED, FILE_READ_ACCESS)

#define IoCompleteRequest(a, b) IofCompleteRequest((a), (b))
#define IoCallDriver(a, b) IofCallDriver((a), (b))

#define IO_CD_ROM_INCREMENT 1

#define DISPATCH_LEVEL 0

#define IO_NO_INCREMENT 0

#define SL_PENDING_RETURNED 1

#define STATUS_INVALID_DEVICE_REQUEST  ((NTSTATUS)0xC0000010L)
#define STATUS_REQUEST_ABORTED        ((NTSTATUS)0xC0000240L)

//FIXME: Bug in nxdk typedef? This should return PIO_STACK_LOCATION according to MSDN
static PIO_STACK_LOCATION IoGetCurrentIrpStackLocation(PIRPx Irp) {
#if 0
  
  debug_print("\n\n");

  debug_print("UserBuffer: 0x%x [offset: %d != %d == 48?]\n",
              Irp->UserBuffer,
              offsetof(IRP, UserBuffer),
              offsetof(IRPx, UserBuffer));

  debug_print("UserEvent: 0x%x [offset %d != %d == 32?]\n",
              Irp->UserEvent,
              offsetof(IRP, UserEvent),
              offsetof(IRPx, UserEvent));

  debug_print("Irp->Tail.Overlay.CurrentStackLocation: 0x%x [Offset %d != %d == 92?]\n",
              Irp->Tail.Overlay.CurrentStackLocation,
              offsetof(IRP, Tail.Overlay.CurrentStackLocation),
              offsetof(IRPx, Tail.Overlay.CurrentStackLocation));

#endif

#if 0
//FIXME: Move hack upwards after figuring out the important fields
//FIXME: Remove hack, once IRP is fixed upstream
#define PIRP PIRPx
#define IRP IRPx
#endif

  PIO_STACK_LOCATION res = (PIO_STACK_LOCATION)Irp->Tail.Overlay.CurrentStackLocation;

#if 0
  debug_print("Major function: %d (%d, %d, { %d, %d })\n", res->MajorFunction,
              res->Parameters.Read.Length,
              res->Parameters.Read.BufferOffset,
              res->Parameters.Read.ByteOffset.HighPart,
              res->Parameters.Read.ByteOffset.LowPart);
#endif

  return res;
}

static void IoMarkIrpPending(PIRP Irp) {
  PIO_STACK_LOCATION IrpSp = IoGetCurrentIrpStackLocation(Irp);
  IrpSp->Control |= SL_PENDING_RETURNED;
}

#define _OBJECT_STRING(x, str)   \
  OCHAR x ## Buffer[] = str;     \
  OBJECT_STRING x = {            \
    sizeof(str) - sizeof(OCHAR), \
    sizeof(str),                 \
    x ## Buffer                  \
  };














// More Xbox specific stuff:

#define IOCTL_CDROM_XBOX_SECURITY CTL_CODE(IOCTL_CDROM_BASE, 0x0020, METHOD_BUFFERED, FILE_READ_ACCESS)

#endif
