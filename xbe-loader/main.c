#define QUIET
#define USE_XISO
//#define HOOK_NIC

#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>

#include <hal/xbox.h>
#include <xboxkrnl/xboxkrnl.h>

#ifndef QUIET
#include <xboxrt/debug.h>
#include <pbkit/pbkit.h>
#include <hal/video.h>
#endif

#ifdef USE_XISO
#include "xiso_driver.h"
#endif

#if 0
// We use AllocatePool, to avoid filling up the interesting memory regions
//FIXME: Instead, keep track of all allocations, so we can undo it
//FIXME: This is still very unstable; we should be reserving more space for our own XBE instead
//       The issue is that real NtVirtualAlloc is still being used in the stdlib
#define malloc(x) ExAllocatePool(x)
#define free(x) ExFreePool(x)
char* strdup_moved(const char* x) {
  char* s = ExAllocatePool(strlen(x) + 1);
  strcpy(s, x);
  return s;
}
void* realloc_moved(void* x, size_t v) {
  void* s = malloc(v);
  if (x != NULL) {
    ULONG ov = ExQueryPoolBlockSize(x);
    memcpy(s, x, ov);
    free(x);
  }
  return s;
}
#define strdup(a) strdup_moved(a)
#define realloc(a, b) realloc_moved(a, b)
#endif

#define FIX_STDIO
#define FIX_STRLEN
#define FIX_BOOL
#define FIX_ASSERT
#include "fixes.h"

// Section will be copied to new versions of loader
#define __PERSIST_NAME "!persist"
#define __PERSIST __attribute__((section(__PERSIST_NAME)))

// Section will be removed on first copy
#define __INIT_NAME "!init"
#define __INIT __attribute__((section(__INIT_NAME)))

#define __NO_RETURN

#define DEFAULT_BASE 0x10000

// PE relocation types
#define IMAGE_REL_BASED_HIGHLOW              3

const uint32_t XOR_EP_DEBUG                            = 0x94859D4B; // Entry Point (Debug)
const uint32_t XOR_EP_RETAIL                           = 0xA8FC57AB; // Entry Point (Retail)
const uint32_t XOR_KT_DEBUG                            = 0xEFB1F152; // Kernel Thunk (Debug)
const uint32_t XOR_KT_RETAIL                           = 0x5B6D40B6; // Kernel Thunk (Retail)

// Fix certificate
typedef struct {
  uint32_t size;                          // size of certificate
  uint32_t timedate;                      // timedate stamp
  uint32_t titleid;                       // title id
  uint16_t title_name[40];                // title name (unicode)
  uint32_t alt_title_id[0x10];            // alternate title ids
  uint32_t allowed_media;                 // allowed media types
  uint32_t game_region;                   // game region
  uint32_t game_ratings;                  // game ratings
  uint32_t disk_number;                   // disk number
  uint32_t version;                       // version
  uint8_t lan_key[16];                   // lan key
  uint8_t sig_key[16];                   // signature key
  uint8_t title_alt_sig_key[16][16];     // alternate signature keys
  uint32_t unka;
  uint32_t unkb;
  uint32_t runtime_security_flags;
} XbeCertificate;

#define XBEIMAGE_MEDIA_TYPE_HARD_DISK           0x00000001
#define XBEIMAGE_MEDIA_TYPE_DVD_X2              0x00000002
#define XBEIMAGE_MEDIA_TYPE_DVD_CD              0x00000004
#define XBEIMAGE_MEDIA_TYPE_CD                  0x00000008
#define XBEIMAGE_MEDIA_TYPE_DVD_5_RO            0x00000010
#define XBEIMAGE_MEDIA_TYPE_DVD_9_RO            0x00000020
#define XBEIMAGE_MEDIA_TYPE_DVD_5_RW            0x00000040
#define XBEIMAGE_MEDIA_TYPE_DVD_9_RW            0x00000080
#define XBEIMAGE_MEDIA_TYPE_DONGLE              0x00000100
#define XBEIMAGE_MEDIA_TYPE_MEDIA_BOARD         0x00000200
#define XBEIMAGE_MEDIA_TYPE_NONSECURE_HARD_DISK 0x40000000
#define XBEIMAGE_MEDIA_TYPE_NONSECURE_MODE      0x80000000
#define XBEIMAGE_MEDIA_TYPE_MEDIA_MASK          0x00FFFFFF

typedef struct {
  uint32_t flags;
  uint32_t virtual_address;
  uint32_t virtual_size;
  uint32_t raw_address;
  uint32_t raw_size;
  uint32_t name;
  uint32_t ref_count;
  uint32_t head_page_ref_count_address; // uint16_t*
  uint32_t tail_page_ref_count_address; // uint16_t*
  uint8_t hash[20];
} XbeSection;

typedef struct {
  uint8_t unk0x0[0x104]; //FIXME: Add XBE fields or use an existing XBE struct
  uint32_t image_base;
  uint32_t header_size;
  uint32_t image_size;
  uint32_t unk0x110;
  uint32_t unk0x114;
  uint32_t certificate_address;
  uint32_t section_count;
  uint32_t section_address; // 0x120
  uint32_t unk0x124;
  void(*entry_point)(void); // 0x128
  uint8_t unk0x12C[0x2C];
  uint32_t kernel_thunk; //FIXME: Use struct* datatype which has all kernel exports
} Xbe;

char loader_path[520] __PERSIST = { 0 };
Xbe* old_loader_xbe __PERSIST = NULL;
Xbe* loader_xbe __PERSIST = DEFAULT_BASE;

// We allocate space here, so when our loader is loaded initially, as much
// memory as possible is reserved for us.
// That way, no other code can pollute the lower address space before the main
// game runs.
// However, unfortunately this leads to garbage reservations we can't loose.
uint8_t large_image[8 * 1024 * 1024] __INIT;

static void probe_memory(uint32_t address, uint32_t size);
void write_log(const char* format, ...) {
}
void write_log_crit(const char* format, ...) {
  char buffer[512];
  sprintf(buffer, "%d          ", KeTickCount);
  va_list argList;
  va_start(argList, format);
  vsprintf(&buffer[10], format, argList);
  va_end(argList);

  static LONG skipped_writes __PERSIST = 0;

  //FIXME: Possibly buffer data
  #define PASSIVE_LEVEL 0 // Passive release level
  #define LOW_LEVEL 0 // Lowest interrupt level
  #define APC_LEVEL 1 // APC interrupt level
  #define DISPATCH_LEVEL 2 // Dispatcher level
  if (KeGetCurrentIrql() > PASSIVE_LEVEL) {
    InterlockedIncrement(&skipped_writes);
    return;
  }

  //FIXME: log path might be invalid (if we don't have loader_path for example)
  //       We should also buffer in that case

  // Report that we messed up!
  if (skipped_writes > 0) {
    char buffer[1024];
    sprintf(buffer, "Skipped %d write(s)\n", skipped_writes);
    skipped_writes = 0; //FIXME: Do interlocked exchange
    write_log(buffer);
  }

#if 0
  static bool internal = false;
  if (internal == false) {
    internal = true;
    probe_memory(0x40000, 0x1000);
    internal = false;
  }
#endif

  // Initialize log and pick wether we want to overwrite, or append
  static bool initialize_log __PERSIST = true;
  const char* access;
  if (initialize_log) {
    access = "wb";
    initialize_log = false;
  } else {
    access = "ab";
  }

  // The kernel does not like relocating the RTL_CRITICAL_SECTION
  // That means we have to create a new one
  //FIXME: What happens to the old one?!
  static bool initialize_section = true;
  static RTL_CRITICAL_SECTION log_section;
  if (initialize_section) {
    RtlInitializeCriticalSection(&log_section);
    initialize_section = false;
  }

  // We have to protect the log from access of multiple threads
  RtlEnterCriticalSection(&log_section);

  // Generate the log path
  //FIXME: Do this somewhere else?
  char loader_directory[520];
  strcpy(loader_directory, loader_path);
	char *lastSlash = strrchr(loader_directory, '\\');
  *lastSlash = '\0';
  char log_path[520];
  sprintf(log_path, "%s\\log.txt", loader_directory);

  // Open file and if successful, write to it
  FILE* f = fopen(log_path, access);
  if (f != NULL) {
    fwrite(buffer, 1, strlen(buffer), f);
    fclose(f);
  } else {
#ifndef QUIET
    debugPrint("Failed to open log\n");
#else
    //FIXME: Do some kind of panic here? LED maybe?
#endif
  }

  // Print message to display
#ifndef QUIET
  debugPrint(buffer);
#endif

  // Leave the multi-threading critical section
  RtlLeaveCriticalSection(&log_section);
}

static void memory_statistics() {
  MM_STATISTICS ms;
  ms.Length = sizeof(MM_STATISTICS);
  MmQueryStatistics(&ms);
  write_log("Memory statistics:\n");
	#define PRINT(stat) write_log("- " #stat ": %d\n", ms.stat);
  PRINT(TotalPhysicalPages)
  PRINT(AvailablePages)
  PRINT(VirtualMemoryBytesCommitted)
  PRINT(VirtualMemoryBytesReserved)
  PRINT(CachePagesCommitted)
  PRINT(PoolPagesCommitted)
  PRINT(StackPagesCommitted)
  PRINT(ImagePagesCommitted)
}


static uint32_t LookupKernelExport(unsigned int ordinal) {
  uint32_t image_base = 0x80010000;
  uint32_t tmp = *(uint32_t*)(image_base + 0x3C);
  tmp = *(uint32_t*)(image_base + tmp + 0x78);
  //ExportCount = read_u32(image_base + TempPtr + 0x14);
  uint32_t ExportBase = image_base + *(uint32_t*)(image_base + tmp + 0x1C);
  //#FIXME: Read all exports at once and parse them locally

  //#for i in range(0, ExportCount):
  //#  ordinal = i + 1
  //#  print("@" + str(ordinal) + ": 0x" + format(image_base + read_u32(ExportBase + i * 4), '08X'))

  //index = (ordinal - 1) # Ordinal
  //#assert(index < ExportCount) #FIXME: Off by one?

  unsigned int index = ordinal - 1;

  return image_base + *(uint32_t*)(ExportBase + index * 4);
}



VOID DECLSPEC_NORETURN NTAPI HookedHalReturnToFirmware
(
    IN FIRMWARE_REENTRY Routine
) {
  write_log("Calling HalReturnToFirmware(%d). Won't Return\n", Routine);
  if (LaunchDataPage != NULL) {

    write_log("LaunchDataPage: Path: '%s'; Type %d\n",
              LaunchDataPage->Header.szLaunchPath,
              LaunchDataPage->Header.dwLaunchDataType);

    if (LaunchDataPage->Header.dwLaunchDataType == 0x00000001) {
      struct LaunchData00000001 {
        uint32_t reason;
        uint32_t context;
        uint32_t parameters[2];
        uint8_t padding[3072 - 16];
      };

      struct LaunchData00000001* ld = &LaunchDataPage->LaunchData;

      write_log("LaunchData: Reason: %d; Parameters: { %d, %d }\n",
                ld->reason, ld->parameters[0], ld->parameters[1]);

    }
  }
  HalReturnToFirmware(Routine);
}

NTSTATUS NTAPI HookedHalWriteSMBusValue(
    IN UCHAR SlaveAddress,
    IN UCHAR CommandCode,
    IN BOOLEAN WriteWordValue,
    IN ULONG DataValue
) {

  // Catch SMC access to LED Sequence and swap red and green
  if (SlaveAddress == 0x20 && CommandCode == 0x08 && !WriteWordValue) {
    unsigned int red_seq = (DataValue >> 4) & 0xF;
    unsigned int green_seq = (DataValue >> 0) & 0xF;
    DataValue = (DataValue & ~0xFF) |  (green_seq << 4) | (red_seq << 0);
  }

  NTSTATUS status = HalWriteSMBusValue(SlaveAddress, CommandCode, WriteWordValue, DataValue);
  write_log("Called HalWriteSMBusValue(...). Returned %d\n", status);
  return status;
}

static char* get_ansi_buffer(PANSI_STRING o) {
  char* s = malloc(o->Length + 1);
  memcpy(s, o->Buffer, o->Length);
  s[o->Length] = '\0';
  return s;
}

NTSTATUS NTAPI HookedIoCreateSymbolicLink
(
    IN POBJECT_STRING SymbolicLinkName,
    IN POBJECT_STRING DeviceName
) {
  NTSTATUS status = IoCreateSymbolicLink(SymbolicLinkName, DeviceName);
  char* SymbolicLinkName_str = get_ansi_buffer(SymbolicLinkName);
  char* DeviceName_str = get_ansi_buffer(DeviceName);
  write_log("Called IoCreateSymbolicLink(%s, %s). Returned %d\n", SymbolicLinkName_str, DeviceName_str, status);
  free(DeviceName_str);
  free(SymbolicLinkName_str);
  return status;
}

KIRQL NTAPI HookedKeGetCurrentIrql(void) {
  KIRQL irql = KeGetCurrentIrql();
  write_log("Called KeGetCurrentIrql(). Returned %d\n", irql);
  return irql;
}

PKTHREAD NTAPI HookedKeGetCurrentThread(void) {
  PKTHREAD thread = KeGetCurrentThread();
  write_log("Called KeGetCurrentThread(). Returned %d\n", thread);
  return thread;
}

VOID NTAPI HookedKeInitializeDpc
(
    OUT KDPC *Dpc,
    IN PKDEFERRED_ROUTINE DeferredRoutine,
    IN PVOID DeferredContext OPTIONAL
) {
  KeInitializeDpc(Dpc, DeferredRoutine, DeferredContext);
  write_log("Called KeInitializeDpc(...).\n");
}

BOOLEAN NTAPI HookedKeSetTimer
(
    IN PKTIMER Timer,
    IN LARGE_INTEGER DueTime,
    IN PKDPC Dpc OPTIONAL
) {
  BOOLEAN ret = KeSetTimer(Timer, DueTime, Dpc);
  write_log("Called KeSetTimer(..., DueTime={%d, %d}, ...). Returned %d\n", DueTime.HighPart, DueTime.LowPart, ret);
  return ret;
}

NTSTATUS NTAPI HookedNtAllocateVirtualMemory
(
    IN OUT PVOID *BaseAddress,
    IN ULONG_PTR ZeroBits,
    IN OUT PSIZE_T RegionSize,
    IN ULONG AllocationType,
    IN ULONG Protect
) {

  memory_statistics();

  PVOID BaseAddressIn = *BaseAddress;
  PSIZE_T RegionSizeIn = *RegionSize;
  NTSTATUS status = NtAllocateVirtualMemory(BaseAddress, ZeroBits, RegionSize, AllocationType, Protect);
  write_log("Called NtAllocateVirtualMemory(&%d, %d, &%d, %d, %d). Returned %d\n", BaseAddressIn, ZeroBits, RegionSizeIn, AllocationType, Protect, status);
  return status;
}

NTSTATUS NTAPI HookedNtCreateFile
(
    OUT PHANDLE FileHandle,
    IN ACCESS_MASK DesiredAccess,
    IN POBJECT_ATTRIBUTES ObjectAttributes,
    OUT PIO_STATUS_BLOCK IoStatusBlock,
    IN PLARGE_INTEGER AllocationSize OPTIONAL,
    IN ULONG FileAttributes,
    IN ULONG ShareAccess,
    IN ULONG CreateDisposition,
    IN ULONG CreateOptions
) {
  NTSTATUS status = NtCreateFile(FileHandle, DesiredAccess, ObjectAttributes, IoStatusBlock, AllocationSize, FileAttributes, ShareAccess, CreateDisposition, CreateOptions);
#if 0
  char* path = get_ansi_buffer(ObjectAttributes->ObjectName);
  write_log("Called NtCreateFile(..., ObjectAttributes={%s}, ...). Returned %d\n", path, status);
  free(path);
#endif
  return status;
}

NTSTATUS NTAPI HookedNtQueryVirtualMemory
(
    IN PVOID BaseAddress,
    OUT PMEMORY_BASIC_INFORMATION MemoryInformation
) {
  NTSTATUS status = NtQueryVirtualMemory(BaseAddress, MemoryInformation);
  write_log("Called NtQueryVirtualMemory(%d, %d). Returned %d\n", BaseAddress, MemoryInformation, status);
  return status;
}

DWORD NTAPI HookedPhyGetLinkState(
    BOOLEAN update
) {
#ifdef HOOK_NIC
  // @param update
  // @return Flags describing the status of the NIC
  DWORD ret = PhyGetLinkState(update);
#else
  write_log_crit("Emulating PhyGetLinkState\n");

  // Pretend there's nothing active
  DWORD ret = 0;
#endif
  write_log_crit("Called PhyGetLinkState(%d). Returned %d\n", update, ret);
  return ret;
}

NTSTATUS NTAPI HookedPhyInitialize
(
    BOOLEAN forceReset,
    PVOID param OPTIONAL
) {
#ifdef HOOK_NIC
  // @param forceReset Whether to force a reset
  // @param param Optional parameters (seemingly unused)
  // @return Status code (zero on success)
  NTSTATUS status = PhyInitialize(forceReset, param);
#else
  write_log_crit("Emulating PhyInitialize\n");

  // Pretend there was some error (unknown which one this is, but it's handled by some code)
  NTSTATUS status = 0x801F0001;
#endif
  write_log_crit("Called PhyInitialize(%d, %d). Returned %d\n", forceReset, param, status);
  return status;
}

NTSTATUS NTAPI HookedPsCreateSystemThreadEx
(
    OUT PHANDLE ThreadHandle,
    IN SIZE_T ThreadExtensionSize,
    IN SIZE_T KernelStackSize,
    IN SIZE_T TlsDataSize,
    OUT PHANDLE ThreadId OPTIONAL,
    IN PKSTART_ROUTINE StartRoutine,
    IN PVOID StartContext,
    IN BOOLEAN CreateSuspended,
    IN BOOLEAN DebuggerThread,
    IN PKSYSTEM_ROUTINE SystemRoutine OPTIONAL
) {
  NTSTATUS status = PsCreateSystemThreadEx(ThreadHandle, ThreadExtensionSize, KernelStackSize, TlsDataSize, ThreadId, StartRoutine, StartContext, CreateSuspended, DebuggerThread, SystemRoutine);
  write_log("Called PsCreateSystemThreadEx(...). Returned %d (thread handle: %d)\n", status, *ThreadHandle);
  return status;
}

VOID NTAPI HookedRtlZeroMemory
(
    IN VOID UNALIGNED *Destination,
    IN SIZE_T Length
) {
  RtlZeroMemory(Destination, Length);
  write_log("Called RtlZeroMemory(...).\n");
}

NTSTATUS NTAPI HookedXeLoadSection
(
    IN PXBEIMAGE_SECTION Section
) {
  NTSTATUS status = XeLoadSection(Section);
  write_log("Called XeLoadSection(...). Returned %d\n", status);
  return status;
}

static void xbe_starter_thread(void* _xbe, void* unused) {
  Xbe* xbe = _xbe;
  xbe->entry_point();

  write_log("Panic! Returned from XBE\n");
  while(true);
}

static XbeSection* find_xbe_section(Xbe* xbe, const char* name) {
  for(unsigned int i = 0; i < xbe->section_count; i++) {
    XbeSection* section = xbe->section_address + i * sizeof(XbeSection);
    if (!strcmp(section->name, name)) {
      return section;
    }
  }
  return NULL;
}

static void probe_memory(uint32_t address, uint32_t size) {
  uint32_t info_address = address;
  while(info_address < (address + size)) {
    MEMORY_BASIC_INFORMATION info;
    NtQueryVirtualMemory(info_address, &info);
    if (info.State != MEM_FREE) {
      write_log("- Region %d, %d (%d bytes): %d\n", info.BaseAddress, info.AllocationBase, info.RegionSize, info.State);
    }
    info_address = info.BaseAddress + info.RegionSize;
  }
}

static Xbe* load_xbe(const char* path, uint32_t base_address, bool allow_hooks) {
  NTSTATUS status;
  uint32_t alloc_address;
  uint32_t alloc_size;

  //FIXME: load XBE and parse some fields
  FILE* f = fopen(path, "rb");
  if (f == NULL) {
    write_log("Unable to load '%s'\n", path);
    while(1);
  }

  // These are the important header fields only
  uint8_t headers[0x15C];
  fread(headers, 1, sizeof(headers), f);

  uint32_t image_base = *(uint32_t*)&headers[0x104];
  uint32_t image_size = *(uint32_t*)&headers[0x10C];

  write_log("Image size: %d\n", image_size);
  write_log("Original base address: %d\n", image_base);

  // Reserve memory for the image
  Xbe* xbe = base_address;
  alloc_size = image_size;
  status = NtAllocateVirtualMemory(&xbe, 0, &alloc_size, MEM_RESERVE, PAGE_READWRITE);
  if (status != STATUS_SUCCESS) {
    write_log("Failed to reserve XBE memory\n");

    probe_memory(base_address, image_size);
  }

  write_log("Allocated xbe at: %d (%d bytes for image)\n", xbe, image_size);

  // Load the headers
  uint32_t header_size = *(uint32_t*)&headers[0x108];
  alloc_size = header_size;
  status = NtAllocateVirtualMemory(&xbe, 0, &alloc_size, MEM_COMMIT, PAGE_READWRITE);
  if (status != STATUS_SUCCESS) {
    write_log("Failed to commit XBE memory for headers\n");
  }
  fseek(f, 0, SEEK_SET);
  fread(xbe, 1, header_size, f);

  write_log("Loaded headers at: %d (%d / %d bytes for headers)\n", xbe, header_size, image_size);

  // Relocate certificate pointer
  xbe->certificate_address += (uint32_t)xbe - image_base;

  // Get a pointer to certificate
  XbeCertificate* cert = xbe->certificate_address;

  // Allow all media types
  cert->allowed_media |= XBEIMAGE_MEDIA_TYPE_HARD_DISK;
  cert->allowed_media |= XBEIMAGE_MEDIA_TYPE_DVD_X2;
  cert->allowed_media |= XBEIMAGE_MEDIA_TYPE_DVD_CD;
  cert->allowed_media |= XBEIMAGE_MEDIA_TYPE_CD;
  cert->allowed_media |= XBEIMAGE_MEDIA_TYPE_DVD_5_RO;
  cert->allowed_media |= XBEIMAGE_MEDIA_TYPE_DVD_9_RO;
  cert->allowed_media |= XBEIMAGE_MEDIA_TYPE_DVD_5_RW;
  cert->allowed_media |= XBEIMAGE_MEDIA_TYPE_DVD_5_RW;

  // This bit must be cleared or DVD X2 security is necessary
  if (cert->size >= (offsetof(XbeCertificate, runtime_security_flags) + 4)) {
    cert->runtime_security_flags &= ~1;
  }

  // Relocate section pointer
  xbe->section_address += (uint32_t)xbe - image_base;
  for(unsigned int i = 0; i < xbe->section_count; i++) {

    XbeSection* section = xbe->section_address + i * sizeof(XbeSection);

    // Relocate section pointers
    section->virtual_address += (uint32_t)xbe - image_base;
    section->name += (uint32_t)xbe - image_base;
    section->tail_page_ref_count_address += (uint32_t)xbe - image_base;
    section->head_page_ref_count_address += (uint32_t)xbe - image_base;

    // Dump some section info
    write_log("Section-name: '%s'; virtual address: %d (%d bytes)\n", section->name, section->virtual_address, section->virtual_size);

    // Preload section if requested
    if (section->flags & 2) {

      write_log("Preloading section\n");

      // Commit section pages
      alloc_address = section->virtual_address;
      alloc_size = section->virtual_size;
      status = NtAllocateVirtualMemory(&alloc_address, 0, &alloc_size, MEM_COMMIT, PAGE_EXECUTE_READWRITE);
      if (status != STATUS_SUCCESS) {
        write_log("Failed to commit XBE memory for section '%s'\n", section->name);
      }

      // Load raw section data from file
      fseek(f, section->raw_address, SEEK_SET);
      fread(section->virtual_address, 1, section->raw_size, f);

      // Fill rest of section with zeros
      memset(section->virtual_address + section->raw_size, 0x00, section->virtual_size - section->raw_size);

      // Raise reference counts
      *(uint16_t*)section->head_page_ref_count_address += 1;
      *(uint16_t*)section->tail_page_ref_count_address += 1;

      // Mark section as loaded
      section->ref_count = 1;
    }

  }

  // We can close the file for good now
  fclose(f);

  // Relocate our binary
  //FIXME: Assert that another marker section exists, so we don't do anything accidental
  //FIXME: Unload this section after use
  XbeSection* relocation_section = find_xbe_section(xbe, ".reloc");
  if (relocation_section == NULL) {
    write_log("Unable to find relocation section; will break if image base %d is not %d xbe base\n", image_base, xbe);
  } else {
    write_log("Starting relocations:");

    uint8_t* relocations = (uint8_t*)relocation_section->virtual_address;
    uint8_t* relocations_end = relocations + relocation_section->virtual_size;

    // relocate each relocation block
    while(relocations < relocations_end) {
      uint8_t* block = *(uint32_t*)&relocations[0];
      uint8_t* block_end = relocations + *(uint32_t*)&relocations[4];
      relocations += 8;

#if 1
      write_log("Doing relocation block from %d - %d\n", (uint32_t)block, (uint32_t)block_end);
#endif

      // relocate each rva
      while(relocations < block_end && relocations < relocations_end) {
        uint16_t data = *(uint16_t*)relocations;
        unsigned int type = (data & 0xF000) >> 12;
        relocations += 2;

        if (type == 0) {
          break;
        }

        if(type == IMAGE_REL_BASED_HIGHLOW) {
          uint32_t* target = (uint32_t*)((uint32_t)xbe + (uint32_t)block + (data & 0x0FFF));

#if 0
          write_log("Relocating %d: %d\n", (uint32_t)target, *target);
#endif

          *target += (uint32_t)xbe - image_base;
        } else {
          write_log("Unsupported relocation type %d\n", type);
        }
      }
    }

    write_log("; done\n");

  }

  // Get kernel thunk address
  uint32_t kernel_thunk_address = xbe->kernel_thunk;
  if (kernel_thunk_address & 0x80000000) {
    kernel_thunk_address ^= XOR_KT_DEBUG;
    write_log("Assuming debug kernel-thunk address: %d\n", kernel_thunk_address);
  } else {
    kernel_thunk_address ^= XOR_KT_RETAIL;
    write_log("Assuming retail kernel-thunk address: %d\n", kernel_thunk_address);
  }
  kernel_thunk_address += (uint32_t)xbe - image_base;
  xbe->kernel_thunk = kernel_thunk_address;

  // Resolve kernel imports
  write_log("Importing xboxkrnl:");
  uint32_t* kernel_thunk = (uint32_t*)xbe->kernel_thunk;
  while(*kernel_thunk != 0x00000000) {
    if (*kernel_thunk & 0x80000000) {
      unsigned int ordinal = *kernel_thunk & 0x7FFFFFFF;
      write_log(" @%d", ordinal);
      *kernel_thunk = LookupKernelExport(ordinal);

        //FIXME: Hook those functions which might reboot the Xbox or would make us loose control otherwise

        //FIXME: This would be bad if loader does not persist.
        //       We need to keep track of all modules so we can relocate?
      if (allow_hooks) {

#if 1
        if (ordinal == 49) {
          *kernel_thunk = (uint32_t)HookedHalReturnToFirmware;
        }

        // Do a hook for testing, which swaps LED red and green
        if (ordinal == 50) {
          write_log("Hooking to: %d\n", HookedHalWriteSMBusValue);
          *kernel_thunk = (uint32_t)HookedHalWriteSMBusValue;
        }

        if (ordinal == 67) {
          *kernel_thunk = (uint32_t)HookedIoCreateSymbolicLink;
        }

        if (ordinal == 103) {
          *kernel_thunk = (uint32_t)HookedKeGetCurrentIrql;
        }

        if (ordinal == 104) {
          *kernel_thunk = (uint32_t)HookedKeGetCurrentThread;
        }

        if (ordinal == 107) {
          *kernel_thunk = (uint32_t)HookedKeInitializeDpc;
        }

        if (ordinal == 149) {
          *kernel_thunk = (uint32_t)HookedKeSetTimer;
        }

        if (ordinal == 184) {
          *kernel_thunk = (uint32_t)HookedNtAllocateVirtualMemory;
        }

        if (ordinal == 190) {
          *kernel_thunk = (uint32_t)HookedNtCreateFile;
        }

        if (ordinal == 217) {
          *kernel_thunk = (uint32_t)HookedNtQueryVirtualMemory;
        }

        if (ordinal == 252) {
          *kernel_thunk = (uint32_t)HookedPhyGetLinkState;
        }

        if (ordinal == 253) {
          *kernel_thunk = (uint32_t)HookedPhyInitialize;
        }

        if (ordinal == 255) {
          *kernel_thunk = (uint32_t)HookedPsCreateSystemThreadEx;
        }

        if (ordinal == 320) {
          *kernel_thunk = (uint32_t)HookedRtlZeroMemory;
        }

        if (ordinal == 327) {
          *kernel_thunk = (uint32_t)HookedXeLoadSection;
        }
#endif

      }

    } else {
      write_log("Oops! bad import: %d\n", *kernel_thunk);
    }
    kernel_thunk++;
  }
  write_log("; done\n");

  //FIXME: Mark sections read-only

  // Get entry point
  uint32_t entry_point_address = xbe->entry_point;
  if (entry_point_address & 0x10000000) {
    entry_point_address ^= XOR_EP_DEBUG;
    write_log("Assuming debug entry-point address: %d\n", entry_point_address);
  } else {
    entry_point_address ^= XOR_EP_RETAIL;
    write_log("Assuming retail entry-point address: %d\n", entry_point_address);
  }
  entry_point_address += (uint32_t)xbe - image_base;
  xbe->entry_point = entry_point_address;

  //FIXME: Fixup image base?

  return xbe;
}

static void unload_xbe_section(XbeSection* section) {
  //FIXME: Check ref-count and only unload if in memory / unused
  //FIXME: We might have to align the virtual_address first?
  uint32_t alloc_address = section->virtual_address;
  uint32_t alloc_size = section->virtual_size;
  NTSTATUS status = NtFreeVirtualMemory(&alloc_address, &alloc_size, MEM_DECOMMIT);
  if (status != STATUS_SUCCESS) {
    write_log("Unable to decommit XBE section at %d\n", section->virtual_address);
  }
  //FIXME: Return wether section was unloaded?
}

static void unload_xbe(Xbe* xbe) {
  write_log("Removing allocation at %d (%d bytes)\n", xbe, xbe->image_size);

  //FIXME: This depends on each section having exactly 1 allocation.
  //       Document that this is a requirement for the loader.
  //FIXME: This depends on the XBE headers having exactly 1 allocation.
  //       Document that this is a requirement for the loader.

  //FIXME: Have a section which contains pointers to callback functions.
  //       Those could free dynamically allocated memory of the binary.

  // Unload all sections first, kind of pointless, but we are nice
  for(unsigned int i = 0; i < xbe->section_count; i++) {
    XbeSection* section = xbe->section_address + i * sizeof(XbeSection);
    unload_xbe_section(section);
  }

  // Now also remove the XBE image, this actually releases the reservation
  uint32_t zero = 0;
  NTSTATUS status = NtFreeVirtualMemory(&xbe, &zero, MEM_RELEASE);
  if (status != STATUS_SUCCESS) {
    write_log("Unable to release XBE at %d\n", xbe);
  }
}

static __NO_RETURN void relocate_loader(uint32_t base_address) {
  write_log("Relocating loader '%s' to %d\n", loader_path, base_address);

  // Mark old loader and load the new loader XBE
  old_loader_xbe = loader_xbe;
  loader_xbe = load_xbe(loader_path, base_address, false);

  write_log("Got address %d\n", loader_xbe);

  // Copy the persist data, don't change any of it in old loader afterwards
  XbeSection* old_persist = find_xbe_section(old_loader_xbe, __PERSIST_NAME);
  XbeSection* persist = find_xbe_section(loader_xbe, __PERSIST_NAME);
  uint32_t persist_size = old_persist->virtual_size;
  if (persist->virtual_size < persist_size) {
    write_log("Warning: Virtual size of persist has shrinked!\n");
    persist_size = persist->virtual_size;
  }
  memcpy(persist->virtual_address, old_persist->virtual_address, persist_size);

  write_log("Will jump into new loader: %d!\n", loader_xbe->entry_point);

  // Jump into the new loader XBE
  loader_xbe->entry_point();
}



int main() {

  //FIXME: Allocate the space right behind our binary
  //       We do this, so other code can't mess up the heap of the main game

#ifndef QUIET
  // Setup debug output
  XVideoSetMode(640, 480, 32, REFRESH_DEFAULT);
  pb_init();
  pb_show_debug_screen();
#endif

#if 1
  // Retrieve path to loader. This only happens the first time
  if (strlen(loader_path) == 0) {
    assert(XeImageFileName->Length < sizeof(loader_path));
    memcpy(loader_path, XeImageFileName->Buffer, XeImageFileName->Length);
    loader_path[XeImageFileName->Length] = '\0';
  }
  write_log("Loader is '%s'\n", loader_path);
#endif

  write_log("Loader at %d\n", loader_xbe);
  memory_statistics();

#if 1
  if (loader_xbe == DEFAULT_BASE) {
    // Eventually we'll be able to relocate the loader more often.
    // However, for simplicity we only relocate it once for now.
    // If we relocate more often we need to worry about persisting pages and
    // relocating all our pointers (including synchronization of threads).
    // If we have a collision later.. well.. fucked!
    const uint32_t highest_virtual_address = 0x7FFE0000;
    //relocate_loader(highest_virtual_address - 4 * 1024 * 1024 - sizeof(large_image));
    relocate_loader(0x70000000 + DEFAULT_BASE);
    //relocate_loader(NULL);

    // Relocate_loader will never return
    write_log("Panic! Returned from relocated loader\n");
    while(true);
  }
#endif

  // Beyond this point, no allocations should be done
  // Otherwise we might pollute the address space

#if 1
  // Unloads specified XBE. Only happens while re-locating
  if (old_loader_xbe != NULL) {
    write_log("Unloading old loader XBE\n");
    memory_statistics();
    unload_xbe(old_loader_xbe);
    old_loader_xbe = NULL;
    memory_statistics();
  }

  //FIXME: Reserve memory again until we actually need this space for a new XBE?
#endif

#if 1
  // Unload the "init" section of the current binary
  write_log("Unloading '" __INIT_NAME "' section\n");
  memory_statistics();
  XbeSection* init = find_xbe_section(loader_xbe, __INIT_NAME);
  unload_xbe_section(init);
  memory_statistics();
#if 0
  //FIXME: This is undocumented behaviour?! It splits the memory into 2 sections
  //       That might also mean that unload_xbe can't free it anymore
  //       We'll need a better algorithm then
  //FIXME: Doesn't even work?!
  uint32_t alloc_address = init->virtual_address;
  uint32_t alloc_size = init->virtual_address;
  NTSTATUS status = NtFreeVirtualMemory(&alloc_address, &alloc_size, MEM_RELEASE);
  if (status != STATUS_SUCCESS) {
    write_log("Unable to split and shrink XBE\n");
  }
#endif
#endif


  char* xbe_path_readable;
#ifdef USE_XISO
  // FIXME: Get path for the XBE which is to be loaded

  // Mount an XISO now
  char* iso_path;

//  iso_path = "E:\\apps\\tests\\meshes\\meshes.iso";
//  iso_path = "Smashing Drive.iso";
  iso_path = "default.iso";

  // Create the virtual drive
  write_log("Creating XISO driver\n");
  NTSTATUS status = xiso_driver_create_device(iso_path);
  if (status != STATUS_SUCCESS) {
    write_log("Unable to create XISO driver\n");
  }

  // Mount it where the DVD drive should be
  write_log("Mounting XISO device\n");
  XMountDrive('D', "\\Device\\XIso0");

  // Pick the default.xbe for startup
  xbe_path_readable = "D:\\default.xbe";

#else

//  xbe_path_readable = "E:\\apps\\tests\\led\\default.xbe";
//  xbe_path_readable = "E:\\apps\\tests\\nxdk-mesh\\default.xbe";
//  xbe_path_readable = "E:\\apps\\tests\\CreateDevice\\CreateDevice.xbe";
//  xbe_path_readable = "E:\\apps\\tests\\meshes\\meshes.xbe";
//  xbe_path_readable = "E:\\apps\\tests\\Fog4627\\default.xbe";
//  xbe_path_readable = "F:\\Games\\JSRF SGT\\SegaJSRF.xbe";
  xbe_path_readable = "F:\\Games\\Halo NTSC\\default.xbe";
#endif

  // We need a device path
  char xbe_path[520];
  XConvertDOSFilenameToXBOX(xbe_path_readable, xbe_path);
  write_log("Loading: '%s'\n", xbe_path);

  // Attempt to load a new binary
  Xbe* xbe = load_xbe(xbe_path, DEFAULT_BASE, true);
  write_log("XBE Loaded\n");

  // Setup image file name, so XeLoadSection etc. work
  if (strlen(xbe_path) > XeImageFileName->MaximumLength) {
    write_log("XeImageFileName too short for XBE path: '%s'\n", xbe_path);
  }
  XeImageFileName->Length = strlen(xbe_path);
  memcpy(XeImageFileName->Buffer, xbe_path, XeImageFileName->Length);

#if 0
  // Create a new thread for this XBE
  XCreateThread((void *)xbe_starter_thread, xbe, NULL);
#endif

#ifndef USE_XISO
  //FIXME: This is absolutely necessary when running games from HDD!
  // Remount D: drive
  char xbe_directory[520];
  strcpy(xbe_directory, xbe_path);
	char *lastSlash = strrchr(xbe_directory, '\\');
  *lastSlash = '\0';
  XMountDrive('D', xbe_directory);
  write_log("Remapped DVD drive to '%s'\n", xbe_directory);
#endif

#if 1
  // Run the XBE directly
  xbe->entry_point();
#endif

  write_log("XBE started\n");

#if 0
  // Get rid of this main thread
  //FIXME: This was an attempt to free stack memory etc.
  PsTerminateSystemThread(STATUS_SUCCESS);
#endif

  //FIXME: Put this into a thread?
  int t = 0;
  while(1) {
    write_log("%d; ", t);
    if (t % 10 == 0) {
      memory_statistics();
    }
    XSleep(1000);
    t++;
  }
}
