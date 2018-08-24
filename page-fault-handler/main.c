#include <stdint.h>
#include <stdbool.h>

#include <hal/xbox.h>
#include <xboxkrnl/xboxkrnl.h>
#include <xboxrt/debug.h>
#include <pbkit/pbkit.h>
#include <hal/video.h>



void payload_main(void);



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
  union {
    uint32_t edi;
    uint16_t di;
  };
  union {
    uint32_t esi;
    uint16_t si;
  };
  uint32_t ebp;
  uint32_t _esp;
  union {
    uint32_t ebx;
    struct {
      union {
        uint16_t bx;
        struct {
          uint8_t bl, bh;
        };
      };
    };
  };
  union {
    uint32_t edx;
    struct {
      union {
        uint16_t dx;
        struct {
          uint8_t dl, dh;
        };
      };
    };
  };
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
  union {
    uint32_t eax;
    struct {
      union {
        uint16_t ax;
        struct {
          uint8_t al, ah;
        };
      };
    };
  };
} __attribute__((packed)) Registers;

typedef struct {
  uint32_t error_code;
  uint32_t eip;
  uint16_t cs;
  uint16_t _pad;
  uint32_t eflags;
} __attribute__((packed)) TrapFrame;


uint32_t __stdcall do_test16(uint16_t a, uint16_t b, uint32_t eflags);
asm("_do_test16@12:\n"
  // Get EFLAGS from stack to ecx
  "mov +12(%esp), %ecx\n"

  // Get current EFLAGS to eax
  "pushfl\n"
  "pop %eax\n"

  // Use lower 12 bit of stack EFLAGS in real EFLAGS
  "mov %ecx, %edx\n"
  "and $0xFFFFF000h, %eax\n"
  "and $0x00000FFFh, %edx\n"
  "or %edx, %eax\n"
  "push %eax\n"
  "popfl\n"

  // Get A and B, then `test` them
  "mov +8(%esp), %dx\n"
  "mov +4(%esp), %ax\n"
  "test %ax, %dx\n"

  // Retrieve updated EFLAGS and update the lower 12 bits of return EFLAGS
  "pushfl\n"
  "pop %eax\n"
  "and $0x00000FFFh, %eax\n"
  "and $0xFFFFF000h, %ecx\n"
  "or %ecx, %eax\n"

  "retn $12\n"
);

uint32_t __stdcall do_test32(uint32_t a, uint32_t b, uint32_t eflags);
asm("_do_test32@12:\n"
  // Get EFLAGS from stack to ecx
  "mov +12(%esp), %ecx\n"

  // Get current EFLAGS to eax
  "pushfl\n"
  "pop %eax\n"

  // Use lower 12 bit of stack EFLAGS in real EFLAGS
  "mov %ecx, %edx\n"
  "and $0xFFFFF000h, %eax\n"
  "and $0x00000FFFh, %edx\n"
  "or %edx, %eax\n"
  "push %eax\n"
  "popfl\n"

  // Get A and B, then `test` them
  "mov +8(%esp), %edx\n"
  "mov +4(%esp), %eax\n"
  "test %eax, %edx\n"

  // Retrieve updated EFLAGS and update the lower 12 bits of return EFLAGS
  "pushfl\n"
  "pop %eax\n"
  "and $0x00000FFFh, %eax\n"
  "and $0xFFFFF000h, %ecx\n"
  "or %ecx, %eax\n"

  "retn $12\n"
);

static uintptr_t remap(uintptr_t address) {
  if ((address >= 0xFEF00000) && (address <= 0xFEF00400)) {
    return 0xFEF40000 + (address - 0xFEF00000);
  }
  return address;
}

static uint8_t read_u8(uintptr_t address) {
  return *(uint8_t*)remap(address);
}
static uint16_t read_u16(uintptr_t address) {
  return *(uint16_t*)remap(address);
}
static uint32_t read_u32(uintptr_t address) {
  return *(uint32_t*)remap(address);
}

static void write_u8(uintptr_t address, uint8_t value) {
  *(uint8_t*)remap(address) = value;
}
static void write_u16(uintptr_t address, uint16_t value) {
  *(uint16_t*)remap(address) = value;
}
static void write_u32(uintptr_t address, uint32_t value) {
  *(uint32_t*)remap(address) = value;
}

void __stdcall page_fault_handler(uint32_t cr2, TrapFrame* trap_frame, Registers* registers) {

  // This is an interrupt handler, so be careful with what you do.
  // There shouldn't be any float math in here, and you should respect
  // the IRQL requirements!

  //FIXME: Hardware interrupts are still enabled.
  //       We need to ensure that no hardware interrupt hander comes in,
  //       and triggers this handler again?

  debugPrint("\n");

  debugPrint("Illegal access: CR2=0x%x, CS=0x%x, EIP=0x%x, EFLAGS=0x%x, error-code=0x%x\n", cr2, trap_frame->cs, trap_frame->eip, trap_frame->eflags, trap_frame->error_code);
  debugPrint("                EAX=0x%x, ECX=0x%x\n", registers->eax, registers->ecx);

  debugPrint("Instruction:");
  uint8_t* instruction = (uint8_t*)trap_frame->eip;
  for(unsigned int i = 0; i < 16; i++) {
    debugPrint(" %x%x", instruction[i] >> 4, instruction[i] & 0xF);
  }
  debugPrint("\n");

  // FIXME: The following instruction parser / emulator could be nicer.
  //        Each case was added when the instruction was ecountered, so
  //        no actual design went into this code, or parsing anything.

  // Check prefix
  bool data16 = false;
  if (instruction[0] == 0x66) {

    trap_frame->eip += 1;

    data16 = true;
    instruction++;
  }




  if (instruction[0] == 0x0F) {
    if (instruction[1] == 0xB6) {
      if (instruction[2] == 0x00) {
        // movzx  eax,BYTE PTR [eax]

        trap_frame->eip += 3;

        uintptr_t src = registers->eax;

        debugPrint("Reading *(uint8_t*)0x%x to %s\n", src, "eax");
        registers->eax = read_u8(src);
      } else if (instruction[2] == 0x09) {
        // movzx  ecx,BYTE PTR [ecx]

        trap_frame->eip += 3;

        uintptr_t src = registers->ecx;

        debugPrint("Reading *(uint8_t*)0x%x to %s\n", src, "ecx");
        registers->ecx = read_u8(src);
      }
    } else if (instruction[1] == 0xB7) {
      if (instruction[2] == 0x09) {
        // movzx  ecx,WORD PTR [ecx]

        trap_frame->eip += 3;

        uintptr_t src = registers->ecx;

        debugPrint("Reading *(uint16_t*)0x%x to %s\n", src, "ecx");
        registers->ecx = read_u16(src);
      }
    }
  } else if (instruction[0] == 0x85) {
    if (instruction[1] == 0xBE) {
      // test DWORD PTR [esi+<signed imm32>],edi

      trap_frame->eip += 2;

      int32_t offset = *(int32_t*)&instruction[2];
      uintptr_t src = registers->esi + offset;
      trap_frame->eip += 4;

      debugPrint("Testing *(%s*)0x%x and %s\n", data16 ? "uint16_t" : "uint32_t", src, data16 ? "di" : "edi");
      debugPrint("Had EFLAGS=0x%x\n", trap_frame->eflags);
      if (data16) {
        trap_frame->eflags = do_test16(read_u16(src), registers->di, trap_frame->eflags);
      } else {
        trap_frame->eflags = do_test32(read_u32(src), registers->edi, trap_frame->eflags);
      }
      debugPrint("Got EFLAGS=0x%x\n", trap_frame->eflags);
    }
  } else if (instruction[0] == 0x89) {
    if (instruction[1] == 0x01) {
      // mov DWORD PTR [ecx],eax

      trap_frame->eip += 2;

      uintptr_t dest = registers->ecx;

      debugPrint("Writing %s to *(%s*)0x%x\n", data16 ? "ax" : "eax", data16 ? "uint16_t" : "uint32_t", dest);
      if (data16) {
        write_u16(dest, registers->ax);
      } else {
        write_u32(dest, registers->eax);
      }
    } else if (instruction[1] == 0x03) {
      // mov DWORD PTR [ebx],eax

      trap_frame->eip += 2;

      uintptr_t dest = registers->ebx;

      debugPrint("Writing %s to *(%s*)0x%x\n", data16 ? "ax" : "eax", data16 ? "uint16_t" : "uint32_t", dest);
      if (data16) {
        write_u16(dest, registers->ax);
      } else {
        write_u32(dest, registers->eax);
      }
    } else if (instruction[1] == 0x08) {
      // mov DWORD PTR [eax],ecx

      trap_frame->eip += 2;

      uintptr_t dest = registers->eax;

      debugPrint("Writing %s to *(%s*)0x%x\n", data16 ? "cx" : "ecx", data16 ? "uint16_t" : "uint32_t", dest);
      if (data16) {
        write_u16(dest, registers->cx);
      } else {
        write_u32(dest, registers->ecx);
      }
    } else if (instruction[1] == 0x11) {
      // mov DWORD PTR [ecx],edx

      trap_frame->eip += 2;

      uintptr_t dest = registers->ecx;

      debugPrint("Writing %s to *(%s*)0x%x\n", data16 ? "dx" : "edx", data16 ? "uint16_t" : "uint32_t", dest);
      if (data16) {
        write_u16(dest, registers->dx);
      } else {
        write_u32(dest, registers->edx);
      }
    } else if (instruction[1] == 0x1F) {
      // mov DWORD PTR [edi],ebx

      trap_frame->eip += 2;

      uintptr_t dest = registers->edi;

      debugPrint("Writing %s to *(%s*)0x%x\n", data16 ? "bx" : "ebx", data16 ? "uint16_t" : "uint32_t", dest);
      if (data16) {
        write_u16(dest, registers->bx);
      } else {
        write_u32(dest, registers->ebx);
      }
    
    } else if (instruction[1] == 0x32) {
      // mov DWORD PTR [edx],esi

      trap_frame->eip += 2;

      uintptr_t dest = registers->edx;

      debugPrint("Writing %s to *(%s*)0x%x\n", data16 ? "si" : "esi", data16 ? "uint16_t" : "uint32_t", dest);
      if (data16) {
        write_u16(dest, registers->si);
      } else {
        write_u32(dest, registers->esi);
      }
    } else if (instruction[1] == 0x3E) {
      // mov DWORD PTR [esi],edi

      trap_frame->eip += 2;

      uintptr_t dest = registers->esi;

      debugPrint("Writing %s to *(%s*)0x%x\n", data16 ? "di" : "edi", data16 ? "uint16_t" : "uint32_t", dest);
      if (data16) {
        write_u16(dest, registers->di);
      } else {
        write_u32(dest, registers->edi);
      }
    } else if (instruction[1] == 0x86) {
      // mov DWORD PTR [esi+<signed imm32>],eax

      trap_frame->eip += 2;

      int32_t offset = *(int32_t*)&instruction[2];
      uintptr_t dest = registers->esi + offset;
      trap_frame->eip += 4;

      debugPrint("Writing %s to *(%s*)0x%x\n", data16 ? "ax" : "eax", data16 ? "uint16_t" : "uint32_t", dest);
      if (data16) {
        write_u16(dest, registers->ax);
      } else {
        write_u32(dest, registers->eax);
      }
    }
  } else if (instruction[0] == 0x8B) {
    if (instruction[1] == 0x00) {
      // mov eax,DWORD PTR [eax]

      trap_frame->eip += 2;

      uintptr_t src = registers->eax;

      debugPrint("Reading *(%s*)0x%x to %s\n", data16 ? "uint16_t" : "uint32_t", src, data16 ? "ax" : "eax");
      if (data16) {
        registers->ax = read_u16(src);
      } else {
        registers->eax = read_u32(src);
      }
    } else if (instruction[1] == 0x08) {
      // mov ecx,DWORD PTR [eax]

      trap_frame->eip += 2;

      uintptr_t src = registers->eax;

      debugPrint("Reading *(%s*)0x%x to %s\n", data16 ? "uint16_t" : "uint32_t", src, data16 ? "cx" : "ecx");
      if (data16) {
        registers->cx = read_u16(src);
      } else {
        registers->ecx = read_u32(src);
      }
    } else if (instruction[1] == 0x09) {
      // mov ecx,DWORD PTR [ecx]

      trap_frame->eip += 2;

      uintptr_t src = registers->ecx;

      debugPrint("Reading *(%s*)0x%x to %s\n", data16 ? "uint16_t" : "uint32_t", src, data16 ? "cx" : "ecx");
      if (data16) {
        registers->cx = read_u16(src);
      } else {
        registers->ecx = read_u32(src);
      }
    } else if (instruction[1] == 0x11) {
      // mov edx,DWORD PTR [ecx]

      trap_frame->eip += 2;

      uintptr_t src = registers->ecx;

      debugPrint("Reading *(%s*)0x%x to %s\n", data16 ? "uint16_t" : "uint32_t", src, data16 ? "dx" : "edx");
      if (data16) {
        registers->dx = read_u16(src);
      } else {
        registers->edx = read_u32(src);
      }
    } else if (instruction[1] == 0x12) {
      // mov edx,DWORD PTR [edx]

      trap_frame->eip += 2;

      uintptr_t src = registers->edx;

      debugPrint("Reading *(%s*)0x%x to %s\n", data16 ? "uint16_t" : "uint32_t", src, data16 ? "dx" : "edx");
      if (data16) {
        registers->dx = read_u16(src);
      } else {
        registers->edx = read_u32(src);
      }
    } else if (instruction[1] == 0x1F) {
      // mov ebx,DWORD PTR [edi]

      trap_frame->eip += 2;

      uintptr_t src = registers->edi;

      debugPrint("Reading *(%s*)0x%x to %s\n", data16 ? "uint16_t" : "uint32_t", src, data16 ? "bx" : "ebx");
      if (data16) {
        registers->bx = read_u16(src);
      } else {
        registers->ebx = read_u32(src);
      }
    } else if (instruction[1] == 0x32) {
      // mov esi,DWORD PTR [edx]

      trap_frame->eip += 2;

      uintptr_t src = registers->edx;

      debugPrint("Reading *(%s*)0x%x to %s\n", data16 ? "uint16_t" : "uint32_t", src, data16 ? "si" : "esi");
      if (data16) {
        registers->si = read_u16(src);
      } else {
        registers->esi = read_u32(src);
      }
    } else if (instruction[1] == 0x3E) {
      // mov edi,DWORD PTR [esi]

      trap_frame->eip += 2;

      uintptr_t src = registers->esi;

      debugPrint("Reading *(%s*)0x%x to %s\n", data16 ? "uint16_t" : "uint32_t", src, data16 ? "di" : "edi");
      if (data16) {
        registers->di = read_u16(src);
      } else {
        registers->edi = read_u32(src);
      }
    } else if (instruction[1] == 0x86) {
      // mov eax, DWORD PTR [esi+<signed imm32>]

      trap_frame->eip += 2;

      int32_t offset = *(int32_t*)&instruction[2];
      uintptr_t src = registers->esi + offset;
      trap_frame->eip += 4;

      debugPrint("Reading *(%s*)0x%x to %s\n", data16 ? "uint16_t" : "uint32_t", src, data16 ? "ax" : "eax");
      if (data16) {
        registers->ax = read_u16(src);
      } else {
        registers->eax = read_u32(src);
      }
    } else if (instruction[1] == 0x8E) {
      // mov ecx, DWORD PTR [esi+<signed imm32>]

      trap_frame->eip += 2;

      int32_t offset = *(int32_t*)&instruction[2];
      uintptr_t src = registers->esi + offset;
      trap_frame->eip += 4;

      debugPrint("Reading *(%s*)0x%x to %s\n", data16 ? "uint16_t" : "uint32_t", src, data16 ? "cx" : "ecx");
      if (data16) {
        registers->cx = read_u16(src);
      } else {
        registers->ecx = read_u32(src);
      }
    }
  } else if (instruction[0] == 0xC6) {
    if (instruction[1] == 0x01) {
      // mov    BYTE PTR [ecx], <imm8>

      trap_frame->eip += 2;

      uintptr_t dest = registers->ecx;

      uint8_t value = *(uint8_t*)&instruction[2];
      trap_frame->eip += 1;

      debugPrint("Writing 0x%x to *(uint8_t*)0x%x\n", value, dest);
      write_u8(dest, value);
    }
  } else if (instruction[0] == 0xC7) {
    if (instruction[1] == 0x00) {
      // mov DWORD PTR [eax], <imm16/32>

      trap_frame->eip += 2;

      uintptr_t dest = registers->eax;

      uint32_t value;
      if (data16) {
        value = *(uint16_t*)&instruction[2];
        trap_frame->eip += 2;
      } else {
        value = *(uint32_t*)&instruction[2];
        trap_frame->eip += 4;
      }

      debugPrint("Writing 0x%x to *(%s*)0x%x\n", value, data16 ? "uint16_t" : "uint32_t", dest);
      if (data16) {
        write_u16(dest, value);
      } else {
        write_u32(dest, value);
      }
    } else if (instruction[1] == 0x01) {
      // mov DWORD PTR [ecx], <imm16/32>

      trap_frame->eip += 2;

      uintptr_t dest = registers->ecx;

      uint32_t value;
      if (data16) {
        value = *(uint16_t*)&instruction[2];
        trap_frame->eip += 2;
      } else {
        value = *(uint32_t*)&instruction[2];
        trap_frame->eip += 4;
      }

      debugPrint("Writing 0x%x to *(%s*)0x%x\n", value, data16 ? "uint16_t" : "uint32_t", dest);
      if (data16) {
        write_u16(dest, value);
      } else {
        write_u32(dest, value);
      }
    } else if (instruction[1] == 0x02) {
      // mov DWORD PTR [edx], <imm16/32>

      trap_frame->eip += 2;

      uintptr_t dest = registers->edx;

      uint32_t value;
      if (data16) {
        value = *(uint16_t*)&instruction[2];
        trap_frame->eip += 2;
      } else {
        value = *(uint32_t*)&instruction[2];
        trap_frame->eip += 4;
      }

      debugPrint("Writing 0x%x to *(%s*)0x%x\n", value, data16 ? "uint16_t" : "uint32_t", dest);
      if (data16) {
        write_u16(dest, value);
      } else {
        write_u32(dest, value);
      }
    } else if (instruction[1] == 0x03) {
      // mov DWORD PTR [ebx], <imm16/32>

      trap_frame->eip += 2;

      uintptr_t dest = registers->ebx;

      uint32_t value;
      if (data16) {
        value = *(uint16_t*)&instruction[2];
        trap_frame->eip += 2;
      } else {
        value = *(uint32_t*)&instruction[2];
        trap_frame->eip += 4;
      }

      debugPrint("Writing 0x%x to *(%s*)0x%x\n", value, data16 ? "uint16_t" : "uint32_t", dest);
      if (data16) {
        write_u16(dest, value);
      } else {
        write_u32(dest, value);
      }
    } else if (instruction[1] == 0x06) {
      // mov DWORD PTR [esi], <imm16/32>

      trap_frame->eip += 2;

      uintptr_t dest = registers->esi;

      uint32_t value;
      if (data16) {
        value = *(uint16_t*)&instruction[2];
        trap_frame->eip += 2;
      } else {
        value = *(uint32_t*)&instruction[2];
        trap_frame->eip += 4;
      }

      debugPrint("Writing 0x%x to *(%s*)0x%x\n", value, data16 ? "uint16_t" : "uint32_t", dest);
      if (data16) {
        write_u16(dest, value);
      } else {
        write_u32(dest, value);
      }
    } else if (instruction[1] == 0x07) {
      // mov DWORD PTR [edi], <imm16/32>

      trap_frame->eip += 2;

      uintptr_t dest = registers->edi;

      uint32_t value;
      if (data16) {
        value = *(uint16_t*)&instruction[2];
        trap_frame->eip += 2;
      } else {
        value = *(uint32_t*)&instruction[2];
        trap_frame->eip += 4;
      }

      debugPrint("Writing 0x%x to *(%s*)0x%x\n", value, data16 ? "uint16_t" : "uint32_t", dest);
      if (data16) {
        write_u16(dest, value);
      } else {
        write_u32(dest, value);
      }
    }
  } else {
    debugPrint("Unhandled entirely!\n\n\n");
    XSleep(100000);
  }

//  XSleep(100);

  //FIXME: Call the original handler if necessary or return a value that signals this has to be done?
}

// This handler will be called for page faults
void __stdcall page_fault_isr(void);
asm("_page_fault_isr@0:\n"

  // Disable interrupts
  "cli\n"

  // Set stack direction
  "cld\n"

  // Keep a copy of all registers
  "pusha\n"

  // Get pointer to all regs (top of stack); push it
  "mov %esp, %eax\n"
  "push %eax\n"

  // Above the regs (32 bytes), there's the trap frame; push it
  "add $32, %eax\n"
  "push %eax\n"

  // Now retrieve the address that triggered the page fault; push it
  "movl %cr2, %eax\n"
  "push %eax\n"

  // Call the C handler
  "call _page_fault_handler@12\n"

  // Retrieve the original registers again
  "popa\n"

  // Re-enable interrupts
  "sti\n"

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

#if 1
  // Install trap handler
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

#endif

  // Startup our nxdk network
  debugPrint("Running payload\n");
  XSleep(1000);
  payload_main();


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
