// Copyright 2017 Jannik Vogel
// Licensed under GPLv3 or any later version.
// Refer to the LICENSE.txt file included.

// Based on original code by Truman Hy, Jackal and iR0b0t.

//#include "ss.h"

#include <stdbool.h>
#include <stdlib.h>
#include <inttypes.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>

#include <openssl/sha.h>
#include <openssl/rc4.h>

static uint32_t psn_to_lba(uint32_t psn) {
  const uint32_t dvd_layerbreak = 0x030000;
  const int32_t layerbreak_offset = 1913776;
  uint32_t xbox_dvd_layerbreak = dvd_layerbreak + layerbreak_offset;
  if(psn < xbox_dvd_layerbreak) {
    // Layer 0 PSN to LBA.
    return psn - dvd_layerbreak;
  } else {
    // Layer 1 PSN to LBA.
    return (xbox_dvd_layerbreak) * 2 - ((psn ^ 0xFFFFFF) + 1) - dvd_layerbreak;
  }
  return 0;
}

static uint32_t read24(const uint8_t data[3]) {
  return (data[0] << 16) | (data[1] << 8) | data[2];
}

#if 0
SSType get_ss_type(const uint8_t* ss) {
  //Get last layer_0 sector PSN
  uint32_t layer0_last_psn = (ss[13] << 16) | (ss[14] << 8) | ss[15];

  switch(layer0_last_psn) {
  case 0x2033AF: return Xbox;
  case 0x20339F: return Xbox360;
  case 0x238E0F: return Xbox360_XGD3;
  default: break;
  }
  return Unknown;
}
#endif

typedef struct {
  uint8_t valid;
  uint8_t challenge_id;
  uint32_t challenge_value;
  uint8_t response_modifier;
  uint32_t response_value;
} __attribute__((packed)) ChallengeEntry;

typedef struct {
  uint8_t unk1[3];
  uint8_t start[3];
  uint8_t end[3];
} __attribute__((packed)) SectorRange;

typedef struct {
  uint64_t timestamp; // ??
  uint32_t unk1;

  uint8_t unk1b[15]; // Always zero?

  uint8_t unk2;
  uint8_t unk3[16];
} __attribute__((packed)) Unk1;

//FIXME: This must always be 720 bytes
typedef struct {
  uint8_t unk1[720];
} __attribute__((packed)) PFI720;

typedef struct {
  PFI720 pfi;
  uint32_t unk1;

  uint8_t unk1b[44]; // Always zero?

  uint8_t challenge_version; // 1?1
  uint8_t challenge_count; // 23?!
  ChallengeEntry challenges[23]; // Encrypted!

  uint8_t unk1c[32]; // Always zero?

  uint64_t timestamp;

  uint8_t unk1d[20]; // Always zero?

  uint8_t unk2[16];

  uint8_t unk2b[84]; // Always zero?

  Unk1 unk3; // Hash is the encryption key for the challenge_entries
  uint8_t hash[20];
  uint8_t signature[256];

  Unk1 unk4;
  uint8_t hash2[20];
  uint8_t signature2[64];

  uint8_t unk5; // Always zero?

  uint8_t range_count; // 23?!
  SectorRange ranges1[23];
  SectorRange ranges2[23];

  uint8_t unk6; // Always zero?
} __attribute__((packed)) SS;


#define PRINT_OFFSET(type, field) \
  printf("offset of " #type "." #field ": %u\n", (unsigned int)(uintptr_t)&((type*)NULL)->field);

void shax(uint8_t* hash, const uint8_t* data, uint32_t len) {
  SHA_CTX c;
  SHA1_Init(&c);
  uint8_t hash_len[] = {
    len & 0xFF,
    (len >> 8) & 0xFF,
    (len >> 16) & 0xFF,
    (len >> 24) & 0xFF
  };
  SHA1_Update(&c, (const void*)hash_len, sizeof(hash_len));
  SHA1_Update(&c, (const void*)data, len);
  SHA1_Final(hash, &c);
  return;
}

int main(int argc, char* argv[]) {
  
  SS ss;
  FILE* f = fopen(argv[1], "rb");
  size_t read_bytes = fread(&ss, 1, sizeof(ss), f);
  assert(read_bytes == sizeof(ss));
  fclose(f);

  printf("sizeof: %d == %d\n", sizeof(SS), read_bytes);
  PRINT_OFFSET(SS, challenge_count);
  PRINT_OFFSET(SS, timestamp);
  PRINT_OFFSET(SS, unk2);
  PRINT_OFFSET(SS, unk3);
  PRINT_OFFSET(SS, unk4);
  PRINT_OFFSET(SS, range_count);
  PRINT_OFFSET(SS, ranges1);
  PRINT_OFFSET(SS, ranges2);

  printf("0x%02X\n", ((uint8_t*)&ss)[0]);

  PRINT_OFFSET(SS, hash);

//for(unsigned int j = 1000; j < 2000; j++) {
  int j = 1227; //FIXME Does not work yet?!
  uint8_t hash[20];
  shax(hash, (const unsigned char*)&ss, j);
  for(unsigned int i = 0; i < 20; i++) {
    printf("%02X", hash[i]);
  }
  printf(" %d\n", j);

  uint8_t* raw = &ss;
  for(unsigned int i = 0; i < 20; i++) {
    printf("%02X", /*ss.hash[i]*/ raw[j + i]);
  }
  printf("\n\n");
//}

  // Decrypt the challenge table!
  uint8_t sha1_hash[20];
  SHA1(&raw[1183], 44, sha1_hash);

  // Now use the first part of the hash as RC4 key
  RC4_KEY key;
  RC4_set_key(&key, 7, sha1_hash);
  uint8_t output[253];
  RC4(&key, 253, &raw[770], output);

  // Dump out the challenge entries
  ChallengeEntry* challenges = output;
  for(unsigned int i = 0; i < 23; i++) {
    printf("[%2u] %s valid=0x%02X challenge_id=0x%02X challenge_value=0x%08X response_modifier=0x%02X response_value=0x%08X\n",
      i,
      challenges[i].valid == 0x01 ? "***" : "   ",
      challenges[i].valid,
      challenges[i].challenge_id,
      challenges[i].challenge_value,
      challenges[i].response_modifier,
      challenges[i].response_value);
  }

  // The 2048 byte Xbox1 decrypted security sector file contains 2 copies of the table with sector ranges:
  //
  // - table 1: 1633 to 1839 (207 bytes)
  // - table 2: 1840 to 2046 (207 bytes)
  //
  // The entries are 9 bytes wide, so there are 9x23 entries (or rows). The sectors are the last 2x3=6 bytes
  // of each row. On the Xbox1 there is only 16 sector ranges, so you only need to display the first 16 rows.

  for(unsigned int i = 0; i < 23; i++) {
    //Get PSN (Physical Sector Number).
    assert(!memcmp(&ss.ranges1[i], &ss.ranges2[i], sizeof(SectorRange)));
    //FIXME: psn_to_lba
    printf("[%2u] ", i);
    printf("unk: 0x%06X; ", read24(ss.ranges1[i].unk1)); //FIXME: Also print raw as I'm not sure what this is et
    //printf("%u\n", psn_to_lba(read24(ss.ranges1[i].start)));
    printf("start: 0x%06X; ", read24(ss.ranges1[i].start));
    printf("end: 0x%06X\n", read24(ss.ranges1[i].end));
  }

  return 0;
}
