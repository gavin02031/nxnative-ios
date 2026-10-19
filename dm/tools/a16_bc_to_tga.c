// Private offline A16 texture lab: a single linear NVN BC mip -> uncompressed TGA.
// No game files or texture packs live in this repository. Format IDs are NVN values.
// Build: cc -O2 -std=c11 -Wall -Wextra -o a16_bc_to_tga a16_bc_to_tga.c ../gfx/tex/nvn_bcdec.c -lm
#include "../gfx/tex/nvn_bcdec.h"
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static unsigned num(const char *text) {
    char *end; errno = 0;
    unsigned long v = strtoul(text, &end, 0);
    if (errno || !text[0] || *end || !v || v > 16384) { fprintf(stderr, "bad size / scale: %s\n", text); exit(2); }
    return (unsigned)v;
}
static unsigned format(const char *text) {
    char *end; errno = 0;
    unsigned long v = strtoul(text, &end, 0);
    if (errno || !text[0] || *end || v > 0xff) { fprintf(stderr, "bad format: %s\n", text); exit(2); }
    return (unsigned)v;
}
static unsigned rgb_channel(const uint8_t *p, unsigned bpp, unsigned ch) {
    if (bpp == 4) return p[ch];
    if (bpp == 2) return ch < 2 ? p[ch] : ch == 3 ? 255 : 0;
    return ch == 0 ? p[0] : ch == 3 ? 255 : 0;
}
static float linear(float s) {
    float x = s / 255.0f;
    return x <= 0.04045f ? x / 12.92f : powf((x + 0.055f) / 1.055f, 2.4f);
}
static uint8_t srgb(float x) {
    float v = x <= 0.0031308f ? 12.92f * x : 1.055f * powf(x, 1.0f / 2.4f) - 0.055f;
    if (v <= 0) return 0;
    if (v >= 1) return 255;
    return (uint8_t)(v * 255 + 0.5f);
}
int main(int argc, char **argv) {
    if (argc != 7) {
        fprintf(stderr, "usage: a16_bc_to_tga <input.bc> <output.tga> <width> <height> <NVN format 0x41-0x4e> <scale 1|2|4>\n");
        return 2;
    }
    const char *in = argv[1], *out = argv[2];
    unsigned w = num(argv[3]), h = num(argv[4]), f = format(argv[5]), scale = num(argv[6]);
    if (scale != 1 && scale != 2 && scale != 4) { fputs("scale must be 1, 2 or 4\n", stderr); return 2; }
    if (f == 0x4a || f == 0x4c || f == 0x4f || f == 0x50) {
        fputs("signed BC4/5 and BC6H need their own quality-preserving HDR/signed conversion\n", stderr); return 2;
    }
    uint32_t pf; int bpp;
    if (!nvn_bc_unpacked(f, &pf, &bpp) || (bpp != 1 && bpp != 2 && bpp != 4)) {
        fputs("this NVN BC format is not supported for LDR ASTC conversion\n", stderr); return 2;
    }
    size_t bx = (w + 3) / 4, by = (h + 3) / 4;
    int block_bytes = f == 0x41 || f == 0x42 || f == 0x45 || f == 0x46 || f == 0x49 ? 8 : 16;
    size_t insize = bx * by * block_bytes, pixels = (size_t)w * h;
    if (pixels > (size_t)64 * 1024 * 1024) { fputs("single mip too big for offline conversion\n", stderr); return 2; }
    FILE *src = fopen(in, "rb");
    if (!src) { perror(in); return 2; }
    if (fseek(src, 0, SEEK_END) || ftell(src) < 0 || (size_t)ftell(src) != insize || fseek(src, 0, SEEK_SET)) {
        fprintf(stderr, "expected exactly %zu compressed bytes in %s\n", insize, in);
        fclose(src); return 2;
    }
    uint8_t *bc = malloc(insize), *decoded = malloc(pixels * bpp);
    if (!bc || !decoded || fread(bc, 1, insize, src) != insize) {
        fputs("unable to read compressed texture\n", stderr); fclose(src); free(bc); free(decoded); return 2;
    }
    fclose(src);
    if (nvn_bc_decode(f, bc, bx * block_bytes, w, h, decoded, (size_t)w * bpp)) {
        fputs("BC decoder failed\n", stderr); free(bc); free(decoded); return 2;
    }
    free(bc);
    unsigned ow = (w + scale - 1) / scale, oh = (h + scale - 1) / scale;
    FILE *dst = fopen(out, "wb"); if (!dst) { perror(out); free(decoded); return 2; }
    uint8_t header[18] = {0}; header[2] = 2;  // uncompressed truecolor TGA
    header[12] = ow & 0xff; header[13] = ow >> 8;
    header[14] = oh & 0xff; header[15] = oh >> 8;
    header[16] = 32; header[17] = 0x28;  // 8-bit alpha, top-left origin
    int err = fwrite(header, 1, sizeof header, dst) != sizeof header;
    int issrgb = f == 0x45 || f == 0x46 || f == 0x47 || f == 0x48 || f == 0x4e;
    for (unsigned y = 0; y < oh && !err; y++) for (unsigned x = 0; x < ow; x++) {
        float sums[4] = {0, 0, 0, 0}; unsigned n = 0;
        for (unsigned dy = 0; dy < scale && y * scale + dy < h; dy++)
            for (unsigned dx = 0; dx < scale && x * scale + dx < w; dx++) {
                const uint8_t *p = decoded + ((size_t)(y * scale + dy) * w + x * scale + dx) * bpp;
                for (unsigned c = 0; c < 4; c++) {
                    unsigned v = rgb_channel(p, (unsigned)bpp, c);
                    sums[c] += (issrgb && c < 3) ? linear((float)v) : v / 255.0f;
                }
                n++;
            }
        uint8_t rgba[4];
        for (unsigned c = 0; c < 4; c++) {
            float v = sums[c] / (float)n;
            rgba[c] = issrgb && c < 3 ? srgb(v) : (uint8_t)fminf(255.0f, fmaxf(0.0f, v * 255.0f + 0.5f));
        }
        if (f == 0x41 || f == 0x45) rgba[3] = 255;  // RGB_DXT1 is opaque
        uint8_t bgra[4] = {rgba[2], rgba[1], rgba[0], rgba[3]};
        if (fwrite(bgra, 1, 4, dst) != 4) { err = 1; break; }
    }
    err |= fclose(dst) != 0;
    free(decoded);
    if (err) { fputs("error writing TGA\n", stderr); remove(out); return 2; }
    printf("offline NVN BC fmt %#x: %ux%u -> %ux%u TGA, scale %u\n", f, w, h, ow, oh, scale);
    return 0;
}
