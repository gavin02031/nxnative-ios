// Game-data-free regression for the legacy A16 BC texture decoding fallback.
// clang -std=c11 -O1 -g -fsanitize=address,undefined t_bcdec.c ../nvn_bcdec.c -o t_bcdec
#include "../nvn_bcdec.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static void formats(void) {
    uint32_t pf = 0; int bpp = 0;
    for (uint32_t f = 0x41; f <= 0x50; f++) {
        assert(nvn_bc_unpacked(f, &pf, &bpp) == 1);
        assert((bpp == 1 || bpp == 2 || bpp == 4 || bpp == 8) && pf);
    }
    assert(nvn_bc_unpacked(0x40, &pf, &bpp) == 0);
    assert(nvn_bc_unpacked(0x51, &pf, &bpp) == 0);
}
static void bc1_red(void) {
    // Red R5G6B5=0xf800, green=0x07e0; index zero = red in all texels.
    uint8_t in[8] = {0x00,0xf8,0xe0,0x07,0,0,0,0};
    uint8_t out[64] = {0};
    assert(nvn_bc_decode(0x41, in, 8, 4, 4, out, 16) == 0);
    for (int n = 0; n < 16; n++) {
        assert(out[4*n+0] == 255 && out[4*n+1] == 0 &&
               out[4*n+2] == 0 && out[4*n+3] == 255);
    }
}
static void bc4_bc5(void) {
    // Channel indices all zero: first endpoint is selected.
    uint8_t bc4[8] = {255,0,0,0,0,0,0,0};
    uint8_t out4[16] = {0};
    assert(nvn_bc_decode(0x49, bc4, 8, 4, 4, out4, 4) == 0);
    for (int i = 0; i < 16; i++) assert(out4[i] == 255);
    uint8_t bc5[16] = {255,0,0,0,0,0,0,0,128,0,0,0,0,0,0,0};
    uint8_t out5[32] = {0};
    assert(nvn_bc_decode(0x4b, bc5, 16, 4, 4, out5, 8) == 0);
    for (int i = 0; i < 16; i++) {
        assert(out5[2*i] == 255 && out5[2*i+1] == 128);
    }
}
static void clipped_rows(void) {
    // A compressed block still covers 4x4 pixels; output is clipped to 3x2.
    // The 16 bytes after the output buffer must remain untouched.
    uint8_t bc1[8] = {0x00,0xf8,0xe0,0x07,0,0,0,0};
    uint8_t out[3*2*4+16]; memset(out, 0xCD, sizeof out);
    assert(nvn_bc_decode(0x41, bc1, 8, 3, 2, out, 3*4) == 0);
    for (int i = 0; i < 6; i++) {
        assert(out[4*i] == 255 && out[4*i+1] == 0 && out[4*i+2] == 0 && out[4*i+3] == 255);
    }
    for (int i = 24; i < 40; i++) assert(out[i] == 0xCD);
}
static void bc6h_alpha(void) {
    // Decoder accepts arbitrary BC6H payload without reading beyond a block.
    // Its expanded output is RGBA16F, with opaque half float alpha.
    uint8_t bc6[16] = {0};
    uint16_t rgba[16*4] = {0};
    assert(nvn_bc_decode(0x50, bc6, 16, 4, 4, (uint8_t *)rgba, 4*8) == 0);
    for (int i = 0; i < 16; i++) assert(rgba[4*i+3] == 0x3c00);
}
int main(void) {
    formats(); bc1_red(); bc4_bc5(); clipped_rows(); bc6h_alpha();
    puts("A16 BC decode synthetic tests passed");
    return 0;
}
