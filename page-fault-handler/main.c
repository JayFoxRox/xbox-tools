#include <stdint.h>
#include <stdbool.h>

#include <hal/xbox.h>
#include <xboxkrnl/xboxkrnl.h>
#include <xboxrt/debug.h>
#include <pbkit/pbkit.h>
#include <hal/video.h>

typedef uint32_t PageDirectoryEntry;
typedef uint32_t PageTableEntry;

// These are for both, PDEs and PTEs
#define PDE_PRESENT_BIT (1 << 0)
#define PDE_SIZE_BIT (1 << 7)

//FIXME: From MSDN, should probably be in some of our headers?
typedef struct _PCI_COMMON_CONFIG {
  USHORT VendorID;
  USHORT DeviceID;
  USHORT Command; // 4
  USHORT Status;
  UCHAR  RevisionID; // 8
  UCHAR  ProgIf; 
  UCHAR  SubClass; // 10
  UCHAR  BaseClass;
  UCHAR  CacheLineSize; // 12
  UCHAR  LatencyTimer;
  UCHAR  HeaderType; // 14
  UCHAR  BIST;
  union {
    struct {
      ULONG BaseAddresses[6]; // 16, 20, 24, 28, 32, 36
      ULONG Reserved1[2]; // 40, 44
      ULONG ROMBaseAddress; // 48
      ULONG Reserved2[2]; // 52, 56
      UCHAR InterruptLine; // 60
      UCHAR InterruptPin; 
      UCHAR MinimumGrant; // 62
      UCHAR MaximumLatency;
    } type0;
  } u;
  UCHAR  DeviceSpecific[192]; // 64
} __attribute__((packed)) PCI_COMMON_CONFIG;

typedef struct {
  uint16_t offset_lo;
  uint16_t selector;
  uint8_t zero;
  uint8_t type_attr;
  uint16_t offset_hi;
} __attribute__((packed)) IDTEntry;

typedef struct {
  uint32_t edi;
  uint32_t esi;
  uint32_t ebp;
  uint32_t _esp;
  uint32_t ebx;
  uint32_t edx;
  union {
    uint32_t ecx;
    struct {
      union {
        uint16_t cx;
        struct {
          uint8_t cl, ch;
        };
      };
    };
  };
  uint32_t eax;
} __attribute__((packed)) Registers;

typedef struct {
  uint32_t eflags;
  uint16_t _pad;
  uint16_t cs;
  uint32_t eip;
  uint32_t error_code;
} __attribute__((packed)) TrapFrame;


void __stdcall page_fault_handler(uint32_t cr2, TrapFrame* trap_frame, Registers* registers) {

  // This is an interrupt handler, so be careful with what you do.
  // There shouldn't be any float math in here, and you should respect
  // the IRQL requirements!

  //FIXME: Hardware interrupts are still enabled.
  //       We need to ensure that no hardware interrupt hander comes in,
  //       and triggers this handler again?

  debugPrint("\n");

  debugPrint("Illegal access: CR2=0x%x, EIP=0x%x, error-code=0x%x\n", cr2, trap_frame->eip, trap_frame->error_code);
  debugPrint("                EAX=0x%x, ECX=0x%x\n", registers->eax, registers->ecx);

  debugPrint("Instruction:");
  uint8_t* instruction = (uint8_t*)trap_frame->eip;
  for(unsigned int i = 0; i < 16; i++) {
    debugPrint(" %x%x", instruction[i] >> 4, instruction[i] & 0xF);
  }
  debugPrint("\n");

  // Check prefix
  bool data16 = false;
  if (instruction[0] == 0x66) {

    trap_frame->eip += 1;

    data16 = true;
    instruction++;
  }           

  if (instruction[0] == 0x0F) {
    if (instruction[1] == 0xB6) {
      if (instruction[2] == 0x09) {
        // movzx  ecx,BYTE PTR [ecx]

        trap_frame->eip += 3;

        uint32_t src = registers->ecx;

        debugPrint("Reading *(uint8_t*)0x%x to %s\n", src, "ecx");
        registers->ecx = 0x12;
      }
    }
    if (instruction[1] == 0xB7) {
      if (instruction[2] == 0x09) {
        // movzx  ecx,WORD PTR [ecx]

        trap_frame->eip += 3;

        uint32_t src = registers->ecx;

        debugPrint("Reading *(uint16_t*)0x%x to %s\n", src, "ecx");
        registers->ecx = 0x00001234;
      }
    }
  } else if (instruction[0] == 0x8B) {
    if (instruction[1] == 0x09) {
      // mov ecx,DWORD PTR [ecx]

      trap_frame->eip += 2;

      uint32_t src = registers->ecx;

      debugPrint("Reading *(%s*)0x%x to %s\n", data16 ? "uint16_t" : "uint32_t", src, data16 ? "cx" : "ecx");
      if (data16) {
        registers->cx = 0x1234;
      } else {
        registers->ecx = 0x12345678;
      }
    }
  } else if (instruction[0] == 0xC6) {
    if (instruction[1] == 0x01) {
      // mov    BYTE PTR [ecx], <imm8>

      trap_frame->eip += 2;

      uint32_t dest = registers->ecx;

      uint8_t value = *(uint8_t*)&instruction[2];
      trap_frame->eip += 1;

      debugPrint("Writing 0x%x to *(uint8_t*)0x%x\n", value, dest);
    }
  } else if (instruction[0] == 0xC7) {
    if (instruction[1] == 0x01) {
      // mov DWORD PTR [ecx], <imm16/32>

      trap_frame->eip += 2;

      uint32_t dest = registers->ecx;

      uint32_t value;
      if (data16) {
        value = *(uint16_t*)&instruction[2];
        trap_frame->eip += 2;
      } else {
        value = *(uint32_t*)&instruction[2];
        trap_frame->eip += 4;
      }

      debugPrint("Writing 0x%x to *(%s*)0x%x\n", value, data16 ? "uint16_t" : "uint32_t", dest);
    }
  } else {
    debugPrint("Unhandled entirely!\n\n\n");
    XSleep(100000);
  }
 
  //FIXME: Call the original handler if necessary or return a value that signals this has to be done?
}

// This handler will be called for page faults
void __stdcall page_fault_isr(void);
asm("_page_fault_isr@0:\n"

  // Set stack direction
  "cld\n"

  // Keep a copy of all registers
  "pusha\n"

  // Get pointer to all regs (top of stack); push it
  "mov %esp, %eax\n"
  "push %eax\n"

  // Above the regs (28 bytes), there's the trap frame; push it
  "add $28, %eax\n"
  "push %eax\n"

  // Now retrieve the address that triggered the page fault; push it
  "movl %cr2, %eax\n"
  "push %eax\n"

  // Call the C handler
  "call _page_fault_handler@12\n"

  // Retrieve the original registers again
  "popa\n"

  // Pop error code and return from interrupt
  "add $4, %esp\n"
  "iret\n"
); //FIXME: Can this be relocated?!

typedef struct {
  uint16_t length;
  IDTEntry* entries;
} __attribute__((packed)) IDT;

void __stdcall get_idt(IDT* idt);
asm("_get_idt@4:\n"
  "mov +4(%esp), %eax\n"
  "sidtl (%eax)\n"
  "retn $4\n"
);

uint32_t __stdcall get_cr3(void);
asm("_get_cr3@0:\n"
  "mov %cr3, %eax\n"
  "ret\n"
);

void main() {

  // Setup debug output
  XVideoSetMode(640, 480, 32, REFRESH_DEFAULT);
  pb_init();
  pb_show_debug_screen();


  //FIXME: Install trap handler
  //FIXME: This assumes that the IDT is always identity mapped.
  //       We might want to MmMapIoSpace it instead.
  IDT idt;
  get_idt(&idt);
  debugPrint("IDT at 0x%x (size %d)\n", (int)idt.entries, (int)idt.length);
  debugPrint("Replacing IDT entry 0xE: 0x%x (old)\n", (idt.entries[0xE].offset_hi << 16) | idt.entries[0xE].offset_lo);
#if 1
  uintptr_t page_fault_isr_addr = (uintptr_t)page_fault_isr;
  idt.entries[0xE].offset_lo = page_fault_isr_addr & 0xFFFF;
  idt.entries[0xE].offset_hi = (page_fault_isr_addr >> 16) & 0xFFFF;
#endif
  debugPrint("Replacing IDT entry 0xE: 0x%x (new)\n", (idt.entries[0xE].offset_hi << 16) | idt.entries[0xE].offset_lo);


#if 0
  // Test our page fault handler
  *(uint32_t*)0x7ef04000 = 0x12345678; // c7 01 (uint32_t)
  debugPrint("0x7ef04000: 0x%x\n", *(uint32_t*)0x7ef04000); // 8b 09
  *(uint16_t*)0x7ef04000 = 0x1234; // 66 c7 01 (uint16_t)
  debugPrint("0x7ef04000: 0x%x\n", *(uint16_t*)0x7ef04000); // 0f b7 09
  *(uint8_t*)0x7ef04000 = 0x12; // c6 01 12
  debugPrint("0x7ef04000: 0x%x\n", *(uint8_t*)0x7ef04000); // 0f b6 09
#endif


  // Test unmodified NIC
  debugPrint("0xFEF00000: 0x%x\n", *(uint32_t*)0xFEF00000);
  debugPrint("0xFEF00004: 0x%x\n", *(uint32_t*)0xFEF00004);
  debugPrint("0xFEF40000: 0x%x\n", *(uint32_t*)0xFEF40000);
  debugPrint("0xFEF40004: 0x%x\n", *(uint32_t*)0xFEF40004);


#if 1
  // Relocate the original NIC 0x4000 bytes back, so code will not find it
  unsigned int nic_device = 4;
  unsigned int nic_function = 0;
  uint32_t nic_slot = (nic_function << 5) | (nic_device << 0);  // See PCI_SLOT_NUMBER
  PCI_COMMON_CONFIG nic_config;
  HalReadWritePCISpace(0, nic_slot, 0, &nic_config, 256, FALSE);
  debugPrint("NIC is at 0x%x\n", nic_config.u.type0.BaseAddresses[0]);
  nic_config.u.type0.BaseAddresses[0] = 0xFEF40000;
  HalReadWritePCISpace(0, nic_slot, 0, &nic_config, 256, TRUE);
  debugPrint("NIC has been moved to 0x%x\n", nic_config.u.type0.BaseAddresses[0]);
#endif


#if 1
  //FIXME: Split the original NIC region into smaller locked pages
  // The kernel actually hardcodes the PDE / PTE areas, but we don't trust it.
  // We'll just map it temporarily for our hackery.
  uint32_t cr3 = get_cr3();
  PageDirectoryEntry* pde = MmMapIoSpace(cr3, 0x1000, PAGE_READWRITE | PAGE_NOCACHE);

  //FIXME: Flush caches? We want to avoid that there's dangling device data

  // 0xFEC... should be large pages, but we need small pages for NIC isolation
  PageDirectoryEntry pde_fec = pde[0xFEC >> 2];
  ULONG_PTR pte_fec_p;
  if (!(pde_fec & PDE_SIZE_BIT)) {

    debugPrint("Oops! 0xFEC... is already small pages!");

    //FIXME: Shouldn't we also check PDE_PRESENT_BIT?!

    // Get the pte_fec physical address.
    // This is an attempt to fix the existing PTE.
    pte_fec_p = (uintptr_t)pde_fec & 0xFFFFF000;

  } else {

    // Allocate a new page table and fill with PDE like identity map
    PageTableEntry* pte_fec = MmAllocateContiguousMemory(0x1000);
    for(unsigned int i = 0; i < 0x400; i++) {
      pte_fec[i] = 0xFEC00000 + (i << 12);
      pte_fec[i] |= (pde_fec & ~PDE_SIZE_BIT) & 0xFFF;
    }

    // We will loose track of the pte_fec allocation now.
    // RIP 1 page. Press F please!
    // Instead, we keep the physical address and map it manually if necessary.
    pte_fec_p = MmGetPhysicalAddress(pte_fec);

    // Point the PDE at our new page table
    pde_fec = (pte_fec_p & 0xFFFFF000) | (pde_fec & 0xFFF);
    pde_fec &= ~PDE_SIZE_BIT;
    pde_fec |= PDE_PRESENT_BIT;
    pde[0xFEC >> 2] = pde_fec;

  }
  MmUnmapIoSpace(pde, 0x1000);
  debugPrint("PDE has been updated with small pages\n");
#endif

  // Lock the memory page where the NIC used to be
  PageTableEntry* pte_fec = MmMapIoSpace(pte_fec_p, 0x1000, PAGE_READWRITE | PAGE_NOCACHE);
  pte_fec[0xFEF00 - 0xFEC00] &= ~PDE_PRESENT_BIT;
  MmUnmapIoSpace(pte_fec, 0x1000);
  debugPrint("PTE has been updated with NIC lock\n");

  //FIXME: We should probably also modify the page where the new NIC is?
  //       The PTE might have existed before and could be very bad.

  //FIXME: Flush TLB? Don't do bad mappings plox!

  // Test our hackery!
  debugPrint("0xFEF00000: 0x%x\n", *(uint32_t*)0xFEF00000);
  debugPrint("0xFEF00004: 0x%x\n", *(uint32_t*)0xFEF00004);
  debugPrint("0xFEF40000: 0x%x\n", *(uint32_t*)0xFEF40000);
  debugPrint("0xFEF40004: 0x%x\n", *(uint32_t*)0xFEF40004);

  //FIXME: Startup our nxdk network


#if 0
  unsigned int t = 0;
  while(true) {
    debugPrint("Ping %d\n", t++);
    XSleep(1000);
  }
#endif

  XSleep(3000);
  debugPrint("Waiting 10 seconds before reboot\n");
  XSleep(10000);

  HalReturnToFirmware(HalRebootRoutine);
  
}
