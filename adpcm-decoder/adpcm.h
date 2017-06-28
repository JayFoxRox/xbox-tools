// See https://wiki.multimedia.cx/index.php/IMA_ADPCM for more information

#include <stdint.h>

static int8_t ima_index_table[16] = {
  -1, -1, -1, -1, 2, 4, 6, 8,
  -1, -1, -1, -1, 2, 4, 6, 8
}; 

static uint16_t ima_step_table[89] = { 
      7,     8,     9,    10,    11,    12,    13,    14,    16,    17, 
     19,    21,    23,    25,    28,    31,    34,    37,    41,    45, 
     50,    55,    60,    66,    73,    80,    88,    97,   107,   118, 
    130,   143,   157,   173,   190,   209,   230,   253,   279,   307,
    337,   371,   408,   449,   494,   544,   598,   658,   724,   796,
    876,   963,  1060,  1166,  1282,  1411,  1552,  1707,  1878,  2066, 
   2272,  2499,  2749,  3024,  3327,  3660,  4026,  4428,  4871,  5358,
   5894,  6484,  7132,  7845,  8630,  9493, 10442, 11487, 12635, 13899, 
  15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767 
};

typedef struct {
  int32_t predictor;
  uint8_t step_index;
  uint16_t step;
} ADPCMDecoder;

static void adpcm_initialize(ADPCMDecoder* d, int16_t predictor, uint8_t step_index) {
  d->predictor = predictor;
  d->step_index = step_index;
}

static void adpcm_decode(ADPCMDecoder* d, int16_t* output, const uint8_t* input, size_t samples) {
  for(unsigned int i = 0; i < samples; i++) {

    // Extract low nibble, then high nibble
    uint8_t nibble = input[i / 2];
    if (i % 2 == 1) {
      nibble >>= 4;
    }
    nibble &= 0xF;

    // Get step and prepare index for next sample
    d->step = ima_step_table[d->step_index];
    d->step_index += ima_index_table[nibble];

    // Calculate diff
    int32_t diff = d->step >> 3;
    if (nibble & 1) {
      diff += d->step >> 2;
    }
    if (nibble & 2) {
      diff += d->step >> 1;
    }
    if (nibble & 4) {
      diff += d->step;
    }
    if (nibble & 8) {
      diff = -diff;
    }

    // Update predictor and clamp to signed 16 bit
    d->predictor += diff;
    if (d->predictor < -0x8000) {
      d->predictor = -0x8000;
    } else if (d->predictor > 0x7FFF) {
      d->predictor = 0x7FFF;
    }

    output[i] = d->predictor;
  }
}
