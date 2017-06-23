//#include <openxdk/openxdk.h>
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

#include <pbkit/pbkit.h>
#include <pbkit/outer.h>

#include <xboxkrnl/xboxkrnl.h>
#include <xboxrt/debug.h>
#include <xboxrt/string.h>

#include "common/x86.h"
#include "common/pe.h"

#define printf debugPrint
#define fflush(x)
#define fclose(x)


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
#if 0
  FILE* f = fopen(filename,"w");
  if (f == NULL) {
    return false;
  }
  size_t offset = 0;
  while(size > 0) {
    size_t chunk = size>1024?1024:size;
    size_t written = fwrite(&data[offset],1,chunk,f); fflush(f);
    written = chunk; // Work around OpenXDK issue where it doesn't return the number of elements
    size -= written;
    offset += written;
  }
  fclose(f);  
#endif
  return true;
}

void dumpIoFile(volatile uint8_t* io, unsigned int offset, size_t size, const char* filename) {
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

int main() {


	pb_init();
	pb_show_debug_screen();

  debugPrint("Hello!");

  // Open a log file
#if 0
  const char* log = "log.txt";
  FILE* f = fopen(log,"w");
  fprintf(f,"Failed to log!\n"); fflush(stdout);
  fclose(f);
  freopen(log, "w", stdout);
#endif
  
  // Workaround missing OpenXDK function
  void(*MmUnmapIoSpaceFix)(PVOID,SIZE_T) = (void*)&MmUnmapIoSpace;

  // Keep track how many errors we produce..
  unsigned int errors = 0;

  // Dump the hardware information to log
  if (1) { 

    // Dump generic details
    IoOutputDword(0xCF8, 0x80000084);
    size_t ramSize = IoInputDword(0xCFC);
    printf("Xbox: %i MB RAM\n",(ramSize+1) / (1024*1024)); fflush(stdout);
  
    // Dump MCPX details
    IoOutputDword(0xCF8, 0x80000808);
    uint32_t mcpxRevision = IoInputDword(0xCFC);
    IoOutputDword(0xCF8, 0x80000880);
    uint32_t mcpxRomEnable = IoInputDword(0xCFC);
    bool mcpxX2 = mcpxRomEnable & 0x1000; //FIXME: Might just indicate DVT4
    printf("MCPX: %s, Revision 0x%02X\n",mcpxX2?"X2":"X3",mcpxRevision & 0xFF); fflush(stdout);

    //FIXME: We should also dump NV2A details for completeness

    // Dump SMC details
    char smcVersion[3];
    HalWriteSMBusValue(0x20 /* SMC Write */, 0x01 /* Version seek */, TRUE, 0);
    unsigned int i;
    for(i = 0; i < 3; i++) {
      HalReadSMBusValue(0x20 /* SMC Read */, 0x01 /* Version read */, TRUE, &smcVersion[i]);
    }
    printf("SMC: Version '%.3s'\n",smcVersion); fflush(stdout);
    uint8_t smcAvPack;  
    HalReadSMBusValue(0x20 /* SMC Read */, 0x04 /* AV Pack read */, TRUE, &smcAvPack);
    printf("SMC: AV Pack 0x%02X\n",smcAvPack); fflush(stdout);

  }  

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

  // Dump xboxkrnl.exe and its arguments
  if (1) {  
    // Dump the kernel image
    {
      void* kernelImage = (void*)0x80010000;
      IMAGE_DOS_HEADER* kernelImageDosHeader = kernelImage;
      IMAGE_NT_HEADERS* kernelImageHeader = (IMAGE_NT_HEADERS*)((uintptr_t)kernelImage+kernelImageDosHeader->e_lfanew);
      IMAGE_FILE_HEADER* kernelImageFileHeader = &kernelImageHeader->FileHeader;
      IMAGE_OPTIONAL_HEADER* kernelImageOptionalHeader = &kernelImageHeader->OptionalHeader;
      // Print some information about data sections
      uint32_t* kernelDataSectionInformation = (uint32_t*)kernelImageDosHeader->e_res2;
      printf("xboxkrnl.exe: Uninitalized data section is 0x%X bytes\n",kernelDataSectionInformation[0]); fflush(stdout);
      printf("xboxkrnl.exe: Initalized data section is 0x%X bytes at 0x%08X (Raw data at 0x%08X)\n",kernelDataSectionInformation[1],kernelDataSectionInformation[3],kernelDataSectionInformation[2]); fflush(stdout);
      // Calculate the kernel size
      size_t length = kernelImageOptionalHeader->SizeOfImage;
      if (0) {
        uint16_t sectionCount = kernelImageFileHeader->NumberOfSections;
        // Navigate to section header of the last section (which should be INIT)
        IMAGE_SECTION_HEADER* sectionHeaders = (IMAGE_SECTION_HEADER*)((uintptr_t)kernelImageOptionalHeader + kernelImageFileHeader->SizeOfOptionalHeader);
        IMAGE_SECTION_HEADER* sectionHeader = &sectionHeaders[sectionCount-1];
        // And calculate the actual length
        printf("xboxkrnl.exe: Found '%.8s', virtual size: 0x%X (at 0x%08X), raw size: 0x%X\n",sectionHeader->Name,sectionHeader->Misc.VirtualSize,sectionHeader->VirtualAddress,sectionHeader->SizeOfRawData); fflush(stdout);
        length = sectionHeader->VirtualAddress + sectionHeader->SizeOfRawData;
        printf("xboxkrnl.exe: Length of 0x%X bytes reported, 0x%X bytes calculated\n",kernelImageOptionalHeader->SizeOfImage,length); fflush(stdout);
      }
      dumpFile(kernelImage,length,"xboxkrnl.exe");
    }
    // Dump keys which were passed to kernel
    {  
      uint8_t keys[16+16];
      // EEPROM Key 
      {
        printf("keys.bin: EEPROM key: "); fflush(stdout);
        unsigned int i;
        for(i = 0; i < 16; i++) {
          printf("%02X",XboxEEPROMKey[i]); fflush(stdout);
        }
        printf("\n"); fflush(stdout);
        memcpy(&keys[0],XboxEEPROMKey,16);
      }
      // CERT key
      {
        uint8_t* XboxCERTKey = &XboxHDKey[-16]; // XboxCERTKey is just infront of XboxHDKey
        printf("keys.bin: CERT key: "); fflush(stdout);
        int i;
        for(i = 0; i < 16; i++) {
          printf("%02X",XboxCERTKey[i]); fflush(stdout);
        }
        printf("\n"); fflush(stdout);
        memcpy(&keys[16],XboxCERTKey,16);
      }
      // Now dump them to file
      dumpFile(keys,sizeof(keys),"keys.bin");
    }
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
