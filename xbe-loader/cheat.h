// This is a fixup for things that xboxkrnl.h messes up

typedef struct _IRPx {
  CSHORT Type; // + 0
  USHORT Size; // + 2
  ULONG Flags; // + 4
  LIST_ENTRY ThreadListEntry; // +8, +12
  IO_STATUS_BLOCK IoStatus; // +16, +20
  CHAR StackCount; // + 24
  CHAR CurrentLocation; // 25
  BOOLEAN PendingReturned; // 26
  BOOLEAN Cancel; // 27
  PIO_STATUS_BLOCK UserIosb; // +28
  PKEVENT UserEvent; // +32 !!!
#if 1
  union {
    struct {
      PIO_APC_ROUTINE UserApcRoutine;
      PVOID UserApcContext;
    } AsynchronousParameters;
    LARGE_INTEGER AllocationSize;
  } Overlay; // +36, +40
#endif
uint8_t pad[4]; //FIXME: Where should this be?!
  PVOID UserBuffer; // + 48
  PFILE_SEGMENT_ELEMENT SegmentArray;
  ULONG LockedBufferLength;
  union {
    struct {
      union {
        KDEVICE_QUEUE_ENTRY DeviceQueueEntry;
        struct {
          PVOID DriverContext[5];
        } ;
      } ;
      PETHREAD Thread;
      struct {
        LIST_ENTRY ListEntry;
        union {
          struct _IO_STACK_LOCATION *CurrentStackLocation; // +92
          ULONG PacketType;
        };
      };
      PFILE_OBJECT OriginalFileObject;
    } Overlay;
    KAPC Apc;
    PVOID CompletionKey;
  } Tail;
} __attribute__((packed)) IRPx, *PIRPx;
