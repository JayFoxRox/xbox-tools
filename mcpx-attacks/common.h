#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static uint8_t* flash_mem(const uint8_t* flash, size_t flash_size, uint32_t address) {
  assert(address <= 0xFFFFFE00);
  return (uint8_t*)&flash[(address - 0xFFF00000) % flash_size];
}

static uint8_t* load_file(const char* path, size_t* size) {
  FILE* f = fopen(path, "rb");

  if (f == NULL) {
    return NULL;
  }

  fseek(f, 0, SEEK_END);
  size_t buflen = ftell(f);
  fseek(f, 0, SEEK_SET);

  uint8_t* buffer = malloc(buflen);
  fread(buffer, 1, buflen, f);

  fclose(f);

  if (size) {
    *size = buflen;
  }

  return buffer;
}

static void save_file(const char* path, const uint8_t* data, size_t size) {
  FILE* f = fopen(path, "wb");

  if (f == NULL) {
    return;
  }

  fwrite(data, 1, size, f);

  fclose(f);
}
