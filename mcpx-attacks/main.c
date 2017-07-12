//FIXME: Allocate space in flash image
//       Create RAM installer
//       Go to entrypoint

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>

#include <openssl/rc4.h>

#include "tea.h"
#include "common.h"

static void rc4_check(const uint8_t* flash, size_t flash_size, const uint8_t* mcpx) {
  const uint8_t* k = &mcpx[0x1A5]; // RC4 Key
  const uint32_t* c = (uint32_t*)&mcpx[0x182]; // Hash offset in output
  const uint32_t* h = (uint32_t*)&mcpx[0x187]; // Expected hash
  const uint8_t* data = flash_mem(flash, flash_size, -0x6200);

  uint32_t tmp[2];
  RC4_KEY key;
  RC4_set_key(&key, 16, k);
  uint8_t output[0x6000];
  RC4(&key, sizeof(output), data, output);

  printf("hash is 0x%08X\n", *(uint32_t*)&output[*c - 0x90000]);
  printf("wanted  0x%08X\n", *h);
}

static void rc4_attack(uint8_t* flash, size_t flash_size, uint32_t target) {
  // The first DWORD in the 2BL is a pointer to the entry point.. perfect!
  uint32_t* attack = (uint32_t*)flash_mem(flash, flash_size, -0x6200);
  attack[0] = target;
}

static void swap(uint32_t* a, uint32_t* b) {
  uint32_t t = *a;
  *a = *b;
  *b = t;
}

static void tea_check(const uint8_t* flash, size_t flash_size, const uint8_t* mcpx) {
  uint32_t esp = 0x8f000; // Temporary buffer  
  uint32_t ebp = 0xffffd400; // Start of data
  uint32_t edi = 0xfffffc80; // End of data

  const uint32_t* h = (uint32_t*)&mcpx[0x1A8]; // Expected hash
  const uint32_t* data = (uint32_t*)flash_mem(flash, flash_size, ebp);

  uint32_t tmp[2] = { ebp, edi };

  uint32_t v[2] = { edi, esp }; // Magic seed number
  for(unsigned int i = 0; i < (edi - ebp) / 8; i++) {

    // Xbox runs hash twice!
    for(unsigned int j = 0; j < 2; j++) {

      // Construct a key
      uint32_t k[4];
      k[0] = tmp[0];
      k[1] = tmp[1];
      k[2] = data[i * 2 + 0];
      k[3] = data[i * 2 + 1];

      tea_encrypt(tmp, k);

      swap(&tmp[0], &v[0]);
      swap(&tmp[1], &v[1]);
    }

  }

  printf("hash is 0x%08X,0x%08X\n", tmp[0], tmp[1]);
  printf("wanted  0x%08X,0x%08X\n", h[0], h[1]);
}

static void tea_attack(uint8_t* flash, size_t flash_size, uint32_t target) {
  // Attack!
  // - bits 31 and 63 is one pair
  // - bits 95 and 127 are the other pair
  // upper part of key comes from data[2 * i + 0], data[2 * i + 1], so bits 95 and 127

  // This modifies a jump so it goes to RAM instead
  uint32_t* attack = (uint32_t*)flash_mem(flash, flash_size, 0xffffd400);
  attack[0] ^= 1 << (95 - (32 * 2));  // Bit 31 in even dword
  attack[1] ^= 1 << (127 - (32 * 3)); // Bit 31 in odd dword

  //FIXME: Make sure this was a jmp, also check where it will land now
  uint32_t hacked = 0x07FD588;

  // Also patch the xcodes to write a jump target to RAM
  for (unsigned int i = 0; i < 0x1000; i++) {
    uint32_t address = 0x80 + i * 9;

    // Check if this is an EXIT instruction
    if (flash[address] == 0xEE) {

      // Keep a copy of the EXIT
      uint8_t tmp[9];
      memcpy(tmp, &flash[address], 9);

      // Install a patch (a `jmp` from our target to elsewhere)
      {
        flash[address + 0] = 0x09;                    // POKE
        *(uint32_t*)&flash[address + 1] = hacked;     // Target address
        *(uint32_t*)&flash[address + 5] = 0xE9E9E9E9; // `jmp` opcode
        address += 9;
      }
      {
        flash[address + 0] = 0x09;                    // POKE
        *(uint32_t*)&flash[address + 1] = hacked + 1; // Target address
        *(uint32_t*)&flash[address + 5] = target;     // `jmp` target
        address += 9;
      }

      // Move the EXIT to the end
      memcpy(&flash[address], tmp, 9);

    }
  }

}

static void usage(const char* program) {
  fprintf(stderr, "Usage %s <version> <flash-path> [-i <binary-path>] [-m <mcpx-path>] [-o <output-path>]\n"
                  "version must be: flash, mcpx, 1.0, 1.1\n",
          program);
}

int main(int argc, char* argv[]) {

  if (argc < 3) {
    fprintf(stderr, "Too few arguments.\n");
    usage(argv[0]);
    return 1;
  }

  unsigned int argi = 1;
  const char* version = argv[argi++];
  const char* flash_path = argv[argi++];

  const char* binary_path = NULL;
  uint32_t address;
  const char* mcpx_path = NULL;
  const char* output_path = NULL;
  while(argi < argc) {
    const char* arg = argv[argi++];
    if (!strcmp(arg, "-i")) {
      binary_path = argv[argi++];
    } else if (!strcmp(arg, "-m")) {
      mcpx_path = argv[argi++];
    } else if (!strcmp(arg, "-o")) {
      output_path = argv[argi++];
    } else {
      fprintf(stderr, "Unknown argument: '%s'.\n", arg);
      usage(argv[0]);
      return 1;
    }
  }

  // You have room from 0x1000 to
  // - MCPX 1.0: 0x39E00 (228 kiB)
  // - MCPX 1.1: 0x3D400 (242 kiB)
  // (These ranges are rough estimates, it replaces kernel and kernel data)
  uint32_t target = 0xFFF41000; // We use the second bank, just in case you need more memory
  size_t max_binary_size = 224 * 1024;
  size_t binary_size;
  uint8_t* binary = NULL;
  if (binary_path) {
    load_file(binary_path, &binary_size);
    if (binary_size >= max_binary_size) {
      printf("Using %.1f%% of image space (%zu / %zu bytes).\n", 100.0f * binary_size / max_binary_size, binary_size, max_binary_size);
      free(binary);
      fprintf(stderr, "Binary image was too large.\n");
      return 1;
    }
  }

  size_t flash_size;
  uint8_t* flash = load_file(flash_path, &flash_size);
  //FIXME: check for error in loading flash

  uint8_t* mcpx = mcpx_path ? load_file(mcpx_path, NULL) : NULL;
  //FIXME: If mcpx path is given and failed to load: report error

  if (!strcmp(version, "flash")) {
    version = "1.0"; // FIXME: !!!
  } else if (!strcmp(version, "mcpx")) {
    //FIXME: Check if mcpx was even loaded
    version = "1.1"; // FIXME: !!!
  }  

  void(*check)(const uint8_t* flash, size_t flash_size, const uint8_t* mcpx) = NULL;
  void(*attack)(uint8_t* flash, size_t flash_size, uint32_t target) = NULL;

  if (!strcmp(version, "1.0")) {
    printf("RC4 Attack\n");
    check = rc4_check;
    attack = rc4_attack;
  } else if (!strcmp(version, "1.1")) {
    printf("TEA Attack\n");
    check = tea_check;
    attack = tea_attack;
  } else {
    fprintf(stderr, "Unknown MCPX version '%s'.\n", version);
    return 1;
  }

  check(flash, flash_size, mcpx);

  attack(flash, flash_size, target);
  if (binary) {
    memcpy(flash_mem(flash, flash_size, target), binary, binary_size);
  }

  check(flash, flash_size, mcpx);

  if (output_path) {
    printf("Trying to export to '%s'.\n", output_path);
    save_file(output_path, flash, flash_size);
    //FIXME: report error when write failed
  }

  //FIXME: Check if these are null before free'ing
  free(flash);
  free(mcpx);

  return 0;
}
