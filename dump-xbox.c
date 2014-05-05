#include <openxdk/openxdk.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <hal/input.h>
#include <hal/video.h>
#include <hal/xbox.h>
#include <hal/io.h>
#include <hal/fileio.h>

#include "common/x86.h"


void resetFlash(volatile uint8_t* flashRom) {
  flashRom[0x555] = 0xAA;
  flashRom[0x2AA] = 0x55;
  flashRom[0x555] = 0xF0;
  KeStallExecutionProcessor(150000);
  return;
}


void setFlashCache(bool enable) {
  uint64_t mtrrType;

  uint32_t cr4 = getCr4();
  disableCache();
  flushCache();
  flushTlb();

  // Disable MTRR
  mtrrType = rdmsr(0x2FF,NULL,NULL);
  wrmsr(0x2FF, 0, 0);

  unsigned int i;
  for (i = 0; i < 8; i++) {
    uint64_t mtrr = rdmsr(0x200+i*2,NULL,NULL);
    uint32_t base = (mtrr >> 12) & 0xFFFFFF;
    uint8_t type = mtrr & 0xFF;

    if (base >= (0xFF000000 >> 12) && type != 0) {
      mtrr = rdmsr(0x201+i*2,NULL,NULL);
      mtrr = enable?(mtrr | 0x800):(mtrr & (~0x800));
      wrmsr(0x201+i*2, mtrr >> 32, mtrr);
    }
  }

  flushCache();
  flushTlb();

  // Reenable MTRR
  wrmsr(0x2FF, mtrrType >> 32, mtrrType);

  enableCache();    
  setCr4(cr4);

  return;

}

bool dumpFile(const uint8_t* data, size_t size, const char* filename) {
  FILE* f = fopen(filename,"w");
  if (f == NULL) {
    return false;
  }
  size_t offset = 0;
  while(size > 0) {
    size_t chunk = size>1024?1024:size;
    size_t written = fwrite(&data[offset],1,chunk,f);
    written = chunk; // Work around OpenXDK issue where it doesn't return the number of elements
    size -= written;
    offset += written;
  }
  fclose(f);  
  return true;
}

void dumpIoFile(volatile uint8_t* io, off_t offset, size_t size, const char* filename) {
  uint8_t* buffer = malloc(size+1);
  disableInterrupts();
  setFlashCache(false);
  unsigned int i;
  for(i = 0; i < size; i += 2) {
    *(uint16_t*)&buffer[i] = *(uint16_t*)&io[(offset & (~1))+i];
  }
  setFlashCache(true);
  enableInterrupts();
  dumpFile(&buffer[offset & 1],size,filename);
  free(buffer);
  return;
}

void XBoxStartup(void) {

  // Open a log file
  const char* log = "log.txt";
  FILE* f = fopen(log,"w");
  fprintf(f,"Failed to log!\n"); fflush(stdout);
  fclose(f);
  freopen(log, "w", stdout);
  
  // Workaround missing OpenXDK function
  void(*MmUnmapIoSpaceFix)(PVOID,SIZE_T) = (void*)&MmUnmapIoSpace;

  // Keep track how many errors we produce..
  unsigned int errors = 0;

  // Dump the flash
  if (1) { 
    // 0xFF000000 - 0xFFFFFFFF is flash
    volatile uint8_t* flashRom = MmMapIoSpace(0xFF000000, 0x1000000, 0x4 /* READWRITE */ | 0x200 /* NOCACHE */);

    unsigned int flashSize = 0x100000;

    //FIXME: Get flash size if possible! Otherwise assume 1MB Flash
    if (0) {
      printf("Flash: preparing\n"); fflush(stdout);

      disableInterrupts();
      setFlashCache(false);

      flashRom[0x555] = 0xAA;
      flashRom[0x2AA] = 0x55;
      flashRom[0x555] = 0x90;

      KeStallExecutionProcessor(1);

      uint8_t manufacturer = flashRom[0x0];
      uint8_t code = flashRom[0x1];
   
      resetFlash(flashRom);

      setFlashCache(true);
      enableInterrupts();

      printf("Flash: Manufacturer 0x%02X, Code 0x%02X\n", manufacturer, code); fflush(stdout);
    }

    dumpIoFile(flashRom,0,flashSize,"flash.bin");

    MmUnmapIoSpaceFix((PVOID)flashRom, 0x1000000);
  }

  // FIXME: Dump the mcpx internal rom [needs a way (bug/glitch/feature) to make this visible]
  if (0) { 
    volatile uint8_t* mcpxRom = MmMapIoSpace(0xFFFFFE00, 0x200, 0x4 /* READWRITE */ | 0x200 /* NOCACHE */);
    MmUnmapIoSpaceFix((PVOID)mcpxRom, 0x200);
  }

  // Dump the eeprom
  if (1) { 
    uint8_t buffer[0x100];
    uint16_t* ptr = (uint16_t*)buffer;
    // Read eeprom words
    unsigned int i;
    for(i = 0; i < sizeof(buffer); i += 2) {
      ULONG value;
      if (!NT_SUCCESS(HalReadSMBusValue(0xA9 /* EEPROM Read */, (UCHAR)i, TRUE, (PCHAR)&value))) {
        printf("EEPROM: Couldn't read address 0x%02X\n",i); fflush(stdout);
      }
      *ptr++ = (uint16_t)value;
    }
    dumpFile(buffer,0x100,"eeprom.bin");
  }

  // Dump HDD stuff
  if (1) { 

    const unsigned int sectorSize = 512;

    ANSI_STRING objectName;
    RtlInitAnsiString(&objectName, "\\Device\\Harddisk0\\partition0");

    OBJECT_ATTRIBUTES objectAttributes = {
      .ObjectName = &objectName,
      .Attributes = OBJ_CASE_INSENSITIVE,
      .RootDirectory = NULL
    };

    IO_STATUS_BLOCK ioStatusBlock;
    NTSTATUS status;

    HANDLE disk;

    status = NtOpenFile(&disk, GENERIC_ALL|SYNCHRONIZE, &objectAttributes, &ioStatusBlock, 0, FILE_SYNCHRONOUS_IO_ALERT);

    unsigned int sector = 0;
    unsigned int sectors = 0x400; // Space until first partition

    void* buffer = malloc(sectors * sectorSize);

    LARGE_INTEGER offset;
    offset.QuadPart = sector * sectorSize;

    status = NtReadFile(disk, 0, NULL, NULL, &ioStatusBlock, buffer, sectors * sectorSize, &offset);
    NtClose(disk);    

    char filename[128];
    sprintf(filename,"hdd_0x%x-0x%x.bin",sector,sector+sectors-1);
    dumpFile(buffer,sectors * sectorSize,filename);

    free(buffer);

  }

  printf("Done! %i error(s)\n",errors); fflush(stdout);

  HalReturnToFirmware(ReturnFirmwareQuickReboot);
  XReboot();

}
