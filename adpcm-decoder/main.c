#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <assert.h>
#include <string.h>

#include "adpcm_block.h"


int main(int argc, char* argv[]) {
  if (argc != 3) {
    printf("Usage: %s <in-path> <out-path>\n", argv[0]);
    return 1;
  }

  FILE* in = fopen(argv[1], "rb");

  char riff_chunk_id[4];
  fread(riff_chunk_id, 4, 1, in);
  if (strncmp(riff_chunk_id, "RIFF", 4) != 0) {
    fprintf(stderr, "Unexpected chunk: '%.4s'. Expected 'RIFF'\n", riff_chunk_id);
    return 1;
  }

  uint32_t riff_chunk_size;
  fread(&riff_chunk_size, 4, 1, in);
  printf("RIFF size: %d\n", riff_chunk_size);

  char wave_chunk_id[4];
  fread(wave_chunk_id, 4, 1, in);
  if (strncmp(wave_chunk_id, "WAVE", 4) != 0) {
    fprintf(stderr, "Unexpected chunk: '%.4s'. Expected 'WAVE'\n", wave_chunk_id);
    return 1;
  }

  char fmt_chunk_id[4];
  fread(fmt_chunk_id, 4, 1, in);
  if (strncmp(fmt_chunk_id, "fmt ", 4) != 0) {
    fprintf(stderr, "Unexpected chunk: '%.4s'. Expected 'fmt '\n", fmt_chunk_id);
    return 1;
  }

  uint32_t fmt_chunk_size;
  fread(&fmt_chunk_size, 4, 1, in);
  printf("fmt size: %d\n", fmt_chunk_size);

  uint16_t format;
  fread(&format, 2, 1, in);
  if ((format != 0x0011) && (format != 0x0069)) {
    fprintf(stderr, "Expected WAV format 0x0011 (IMA ADPCM) or 0x0069 (Xbox ADPCM). Got 0x%04X.\n", format);
    return 1;
  }

  uint16_t channels;
  fread(&channels, 2, 1, in);
  printf("Channels: %d\n", channels);
  if (channels != 1 && channels != 2) {
    fprintf(stderr, "Expected mono or stereo file. Got %u channels.\n", channels);
    return 1;
  }

  uint32_t samples_per_sec;
  fread(&samples_per_sec, 4, 1, in);
  printf("Sampling rate: %u Hz\n", samples_per_sec);

  uint32_t bytes_per_sec;
  fread(&bytes_per_sec, 4, 1, in);
  printf("Bandwidth: %u kiB/s\n", bytes_per_sec / 1024);

  uint16_t block_align;
  fread(&block_align, 2, 1, in);
  printf("Block align: %u Bytes\n", block_align);
  //assert(block_align <= 1); // FIXME: Add blockalign support

  uint16_t bits_per_sample;
  fread(&bits_per_sample, 2, 1, in);
  if (bits_per_sample != 4) {
    fprintf(stderr, "Expected 4 bits per sample. Got %u.\n", bits_per_sample);
    return 1;
  }

  uint16_t extra_size;
  fread(&extra_size, 2, 1, in);
  if (extra_size != 2) {
    fprintf(stderr, "Expected 2 bytes of extra data. Got %u.\n", extra_size);
    return 1;
  }

  uint16_t channel_samples_per_block;
  fread(&channel_samples_per_block, 2, 1, in);
  if (channel_samples_per_block != 64) {
    fprintf(stderr, "Expected 64 channel samples per block. Got %u.\n", channel_samples_per_block);
    return 1;
  }
  //FIXME: What's in the extra-data?

  //FIXME: Skip possible fact headers etc

  char data_chunk_id[4];
  fread(data_chunk_id, 4, 1, in);
  if (strncmp(data_chunk_id, "data", 4) != 0) {
    fprintf(stderr, "Unexpected chunk: '%.4s'. Expected 'data'\n", data_chunk_id);
    return 1;
  }

  uint32_t data_chunk_size;
  fread(&data_chunk_size, 4, 1, in);
  printf("Data size: %u Bytes\n", data_chunk_size);

  // Mark start of output
  printf("\n");

  FILE* out = fopen(argv[2], "wb");

  // Calculate the number of samples:
  // * First get the number of blocks.
  // * In each block we have 4 bytes of header per channel.
  // * In each block we have 2 samples per byte.
  // * One sample per channel from initial predictor.
  // (= 65 samples per block).
  uint32_t blocks = data_chunk_size / block_align;
  printf("Duration: %u Blocks\n", blocks);
  uint32_t samples_per_block = (block_align - 4 * channels) * 2 + channels;

  // Check if the header lied to us
  channel_samples_per_block = samples_per_block / channels;
  if (channel_samples_per_block != 65) {
    fprintf(stderr, "Channel samples per block differs from header. Got %u.\n");
    return 1;
  }
  printf("Duration per block: %d Samples\n", channel_samples_per_block);

  uint32_t samples = blocks * samples_per_block;
  printf("Duration: %u Samples\n", samples / channels);

  // Calculate size of decoded data
  uint32_t data_size = samples * 2;

  // Write wave header
  uint8_t header[] = {
     'R',  'I',  'F',  'F', 0x00, 0x00, 0x00, 0x00,  'W',  'A',
     'V',  'E',  'f',  'm',  't',  ' ', 0x10, 0x00, 0x00, 0x00,
    0x01, 0x00, 0x02, 0x00, 0x44, 0xac, 0x00, 0x00, 0x10, 0xb1,
    0x02, 0x00, 0x04, 0x00, 0x10, 0x00,  'd',  'a',  't',  'a',
    0x00, 0x00, 0x00, 0x00
  };

  bits_per_sample = 16;

  *(uint32_t*)&header[4] = data_size + 36;
  *(uint16_t*)&header[22] = channels;
  *(uint32_t*)&header[24] = samples_per_sec;
  *(uint32_t*)&header[28] = channels * bits_per_sample / 8 * samples_per_sec;
  *(uint16_t*)&header[32] = channels * bits_per_sample / 8;
  *(uint16_t*)&header[34] = bits_per_sample;
  *(uint32_t*)&header[40] = data_size;

  fwrite(&header, sizeof(header), 1, out);

  // Allocate space for samples
  uint8_t* block = malloc(block_align);
  int16_t* sample_out = malloc(channel_samples_per_block * channels * 2);

#if 0
  // Chunk data which contains blocks of samples
  for(unsigned int k = 0; k < blocks; k++) {

    // Read and decode the block
    fread(block, block_align, 1, in);
    if (channels == 2) {
      adpcm_decode_stereo_block(&sample_out[0], &sample_out[channel_samples_per_block], block, 0, channel_samples_per_block - 1);
    } else {
      adpcm_decode_mono_block(sample_out, block, 0, channel_samples_per_block - 1);
    }

    // Interleave the 8 samples for PCM out
    for(unsigned int l = 0; l < channel_samples_per_block; l++) {
      for(unsigned int j = 0; j < channels; j++) {
        fwrite(&sample_out[j * channel_samples_per_block + l], 2, 1, out);
      }
    }

  }
#else
  // Chunk data which contains blocks of samples
  for(unsigned int k = 0; k < samples; k++) {

    // Read and decode the block
    unsigned int i = k % 65;
    if (i == 0) {
      fread(block, block_align, 1, in);
    }
    if (channels == 2) {
      adpcm_decode_stereo_block(&sample_out[0], &sample_out[channel_samples_per_block], block, i, i);
    } else {
      adpcm_decode_mono_block(sample_out, block, i, i);
    }

    // Interleave the 8 samples for PCM out
    for(unsigned int j = 0; j < channels; j++) {
      fwrite(&sample_out[j * channel_samples_per_block], 2, 1, out);
    }

  }
#endif

  free(sample_out);
  free(block);

  fclose(in);
  fclose(out);

  return 0;
}
