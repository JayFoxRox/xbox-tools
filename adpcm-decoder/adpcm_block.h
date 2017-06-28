static int16_t adpcm_decode_block_setup(ADPCMDecoder* decoder, uint32_t word) {
  int16_t predictor = word & 0xFFFF;
  uint8_t step_index = (word >> 16) & 0xFF;
  adpcm_decoder_initialize(decoder, predictor, step_index);
  return predictor;
}

static int16_t* adpcm_decode_word(ADPCMDecoder* decoder, int16_t* samples, uint32_t word, int first, int last) {
  for(int i = 0; i < 8; i++) {
    int16_t sample = adpcm_decoder_step(decoder, word);
    word >>= 4;
    if ((i >= first) && (i <= last)) {
      *samples++ = sample; 
    }
  }
  return samples;
}

// For stereo we decode 2x 32 bit each iteration (as 32 bits).
static void adpcm_decode_stereo_block(int16_t* samples_l, int16_t* samples_r, const uint8_t* data, unsigned int first, unsigned int last) {
  uint32_t* word = (uint32_t*)data;
  ADPCMDecoder decoder_l;
  ADPCMDecoder decoder_r;
  int16_t sample_l = adpcm_decode_block_setup(&decoder_l, *word++);
  int16_t sample_r = adpcm_decode_block_setup(&decoder_r, *word++);
  if (first == 0) {
    *samples_l++ = sample_l;
    *samples_r++ = sample_r;
    first--;
    last--;
  }
  for(unsigned int i = 0; i < 8; i++) {
    for(unsigned int j = 0; j < 2; j++) {
      if (j == 0) {
        samples_l = adpcm_decode_word(&decoder_l, samples_l, *word++, first, last);
      } else {
        samples_r = adpcm_decode_word(&decoder_r, samples_r, *word++, first, last);
      }
    }
    first -= 8;
    last -= 8;
  }
}

// For mono we decode 32 bit at once in each iteration.
// We could do 64 bits here, but if we parallelize this algorithm (later) we
// would limit ourselves to 64 bit operands. However, most of ADPCM is 16 to
// 32 bits (for overflows). So we stick with 32 bit and should even consider
// going back to 16 bit (if enough decoders run at once)!
static void adpcm_decode_mono_block(int16_t* samples, const uint8_t* data, unsigned int first, unsigned int last) {
  uint32_t* word = (uint32_t*)data;
  ADPCMDecoder decoder;
  int16_t sample = adpcm_decode_block_setup(&decoder, *word++);
  if (first == 0) {
    *samples++ = sample;
    first--;
    last--;
  }
  for(unsigned int i = 0; i < 8; i++) {
    samples = adpcm_decode_word(&decoder, samples, *word++, first, last);
    first -= 8;
    last -= 8;
  }
}
