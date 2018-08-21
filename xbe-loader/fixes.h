#ifndef __FIXES_H__
#define __FIXES_H__

#ifdef FIX_ASSERT
#undef assert
#define assert(x) if (!(x)) { debugPrint("Oops: '%s' in %s:%d!\n", #x, __FILE__, __LINE__); while(1); }
#endif

#ifdef FIX_BOOL
typedef _Bool bool;
#endif

#ifdef FIX_STRLEN
// Yup! Even strlen is broken in nxdk..
static size_t fixed_strlen(const char *s1) {
  size_t i = 0;
  while (s1[i] != '\0') { i++; }
  return i;
}
#define strlen(s1) fixed_strlen(s1)
#endif

#ifdef FIX_STDIO

#include <hal/fileio.h>
#include <string.h>
#include <stdlib.h>

#define SEEK_SET 1
#define SEEK_END 2

typedef struct {
  int handle;
} FILE;

static int fread(void* buffer, int chunk_count, int chunk_size, FILE* f) {
  unsigned int numberOfBytesRead;
  int r = XReadFile(f->handle, buffer, chunk_count * chunk_size, &numberOfBytesRead);
  if (r != TRUE) {
    debugPrint("Read failed\n");
    while(1);
  }
  if (numberOfBytesRead != chunk_count * chunk_size) {
    debugPrint("Read too few bytes\n");
    while(1);
  }
  return numberOfBytesRead / chunk_size;
}

static int fwrite(const void* buffer, int chunk_count, int chunk_size, FILE* f) {
  unsigned int numberOfBytesWritten;
  XWriteFile(f->handle, (void*)buffer, chunk_count * chunk_size, &numberOfBytesWritten);
  return numberOfBytesWritten / chunk_size;
}

static int fseek(FILE* f, int offset, int whence) {
  int moveMethod;
  switch(whence) {
  case SEEK_SET:
    break;
  case SEEK_END: {
    // We can't use FILE_END from XSetFilePointer due to bugs; do our own thing
    unsigned int filesize;
    NTSTATUS status = XGetFileSize(f->handle, &filesize);
    if (status != TRUE) {
      debugPrint("Unable to get file-size for fseek\n");
      while(1);
    }
    offset += filesize;
    break;
  }
  default:
    debugPrint("Bad whence: %d\n", whence);
    while(1);
  }

  int newFilePointer;
  XSetFilePointer(f->handle, offset, &newFilePointer, FILE_BEGIN);

  return 0;
}

static FILE* fopen(char* path, char* mode) {
  int handle;

  int create;
  int access;
  int whence;
  if (!strcmp(mode, "rb")) {
    create = OPEN_EXISTING;
    access = GENERIC_READ;
    whence = SEEK_SET;
  } else if (!strcmp(mode, "wb")) {
    create = CREATE_ALWAYS;
    access = GENERIC_WRITE;
    whence = SEEK_SET;
  } else if (!strcmp(mode, "ab")) {
    create = OPEN_ALWAYS;
    access = GENERIC_READ | GENERIC_WRITE;
    whence = SEEK_END;
  } else {
    return NULL;
  }

  NTSTATUS status = XCreateFile(&handle, path, access, 0, create, 0);

  // This is technically not an error for any modes we support
  if (status == ERROR_ALREADY_EXISTS) {
    status = STATUS_SUCCESS;
  }

  // Error out if no file was loaded
  if (status != STATUS_SUCCESS) {
    return NULL;
  }

  // Create a FILE object
  FILE* f = malloc(sizeof(FILE));
  f->handle = handle;

  // Go to the intended location within file
  fseek(f, 0, whence);

  return f;
}

static int fclose(FILE* f) {
  XCloseHandle(f->handle);
  free(f);
  return 0;
}

#endif

#endif
