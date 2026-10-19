# Experimental iPhone 15 (A16, 6 GB RAM) native game support

This branch is a **source-code compatibility experiment**, not a playable
Tears of the Kingdom release. It must not be merged until iPhoneOS compile
checks and actual device gameplay / memory tests pass.

## Why stock nxnative does not support this phone

The regular iPhone 15's A16 GPU does not support Metal's BC texture formats
(`MTLDevice.supportsBCTextureCompression == NO`). nxnative's normal path
requires native BC textures (A17 Pro or newer). The branch restores the older
decoder using `dm/third_party/bcdec` and ports its upload logic into the
current Metal 4 renderer:

- Decode BC1–BC5 on the GPU during texture uploads.
- Decode BC6H/BC7 and unsupported 3D compressed textures on the CPU.
- Convert block-compressed buffer-to-texture updates to decoded pixels when
  the compressed source buffer is CPU-addressable.
- Prevent invalid compressed render-target attachments even though the
  fallback backing texture is now uncompressed.
- Compile native host code with the A16 CPU instruction baseline, not A18.

You do **not** need to set an environment variable to enable decompression
on a non-BC GPU. `DM_TEST_NO_BC=1` optionally forces the same path on a
newer device for comparative debugging; do not use it for normal play.

## Why TotK might still run out of memory

Decoded textures often take **2–8 times** as much memory as their BC blocks.
A 5 GB *virtual reservation* in TotK's profile is not 5 GB of installed RAM
and does not mean the game can use 5 GB physically. The regular iPhone 15
has 6 GB shared system memory, with a smaller per-app budget than that.

The main planned optimization is an **offline, locally generated ASTC 4x4
texture conversion** for textures that can be rewritten without changing
the game's semantics. This should preserve compressed GPU residency instead
of relying on permanent decoded RGBA textures. d2r-mobile's older-device
pipeline illustrates the idea, but its Diablo II-specific asset formats
cannot be applied to TotK unchanged. Need to inventory TotK texture formats,
resources, shader assumptions, and games' runtime-created compressed textures
before changing assets. Only use personal game files, locally.

## Texture quality lab (Windows PC friendly, test-only)

The offline lab is **not a replacement pack builder yet**. It lets us
measure exactly how much video memory and image quality can be saved on a
single *linear, deswizzled BC mip* without uploading your game dumps. It
does not read NSPs, TotK archives, BFRES/BNTX files, or block-linear
textures directly, and it does not change the game's texture bindings.

`dm/tools/a16_bc_to_tga.c` decodes a private BC1/2/3/4/5/7 mip to TGA,
optionally downsampling colours. `dm/tools/a16_astc_lab.py` calls
Arm's independently installed `astcenc`, decodes the resulting ASTC
again, checks actual fidelity in PSNR dB, and writes a JSON manifest
with hashes, format, dimensions and size. A result below the requested
quality gate is rejected. Signed BC4/BC5, BC6H, layers/cubemaps,
dynamically generated textures, mip chains, and game asset patching
need separate handling before device use.

**On Windows**, install Python 3, a C compiler (MSYS2 MinGW GCC or Clang),
and an official Windows build of
[Arm astcenc](https://github.com/ARM-software/astc-encoder).
From the repository root, using PowerShell with `gcc` on `PATH`:

```powershell
gcc -O2 -std=c11 dm/tools/a16_bc_to_tga.c dm/gfx/tex/nvn_bcdec.c -lm -o a16_bc_to_tga.exe
python dm/tools/a16_astc_lab.py --input "C:\\private\\linear-bc-mip.bin" --format 0x44 --width 1024 --height 1024 --kind world --tier balanced --scale 1 --preset thorough --min-psnr 30 --decoder ".\\a16_bc_to_tga.exe" --encoder "C:\\Tools\\astcenc.exe" --out "C:\\private\\world-texture.astc"
```

Replace the paths and dimensions with your own **verified single-mip
linear BC data**. A normal TotK ROM dump is *not* that input; texture
extraction/deswizzling is a future pipeline step. Keep the source,
`.astc` and generated `.json` off GitHub.

Quality defaults, chosen to preserve HUD/text and normal detail:

| Asset class | High quality | Balanced (default) | Smaller |
| --- | --- | --- | --- |
| World / scenery | ASTC 4x4, 8 bpp | ASTC 5x5, 5.12 bpp | ASTC 6x6, 3.56 bpp |
| Normal maps | ASTC 4x4 | ASTC 4x4 | ASTC 5x5 |
| UI / text | ASTC 4x4 | ASTC 4x4 | ASTC 4x4 |

The CLI only permits `--scale 2` or `4` for world textures; text and
normal maps stay at full size. The downscale option applies an averaged
image reduction (sRGB averaging is done in linear light). Compression
uses Arm's official encoder; it is not a homemade ASTC codec.

**Illustrative unpadded GPU payload sizes for a 1024x1024 image** (a
real Metal allocation can differ due to alignment, residency, mips and
other GPU allocations):

- Decoded RGBA8: 4 MiB
- ASTC 4x4: 1 MiB
- ASTC 5x5: about 0.64 MiB
- ASTC 6x6: about 0.45 MiB
- Downscale to 512x512 + ASTC 5x5: about 0.16 MiB

These are per-mip storage sizes, *not* memory budget predictions for the
whole game. BC3 source data itself is also 1 MiB at 1024x1024; an
ASTC 4x4 conversion does not magically beat BC3, but it is readable by
your iPhone's GPU while saving RAM versus decoded RGBA8.

`.github/workflows/a16-bc-decode.yml` tests this offline workflow with
only synthetic coloured BC blocks, real `astcenc` encoding/decoding,
dimensions, rejection rules and quality measurement. This does **not**
prove that any resulting texture can be used inside TotK: the next
milestone is inventorying TotK's assets and wiring a private
asset-specific ASTC conversion + rewritten format metadata, while
avoiding unsafe replacement of runtime-created BC surfaces.

## Tests

No commercial game files are used in automated checks.

- `dm/gfx/tex/tests/t_bcdec.c` validates the restored C decoder with
  synthetic BC blocks, memory bounds at cropped texture edges and BC6H alpha.
- `.github/workflows/a16-bc-decode.yml` runs tests under ASan/UBSan on Linux,
  and checks `nvn_mtl.m` syntax for arm64 iPhoneOS using Xcode 26/Metal 4.
  **Passing these tests does not mean the game boots on an iPhone.**

## First private iPhone experiment (after Xcode source builds pass)

1. On a personally controlled macOS/Xcode build machine, use your
   personally dumped TotK base game and cumulative 1.4.3 update, and
   `scripts/build_ipa_from_nsp.py`, following the official nxnative guide.
   Do **not** upload NSPs, ROMs, keys, extracted files or the compiled game
   IPA to a public repo, PR, issue or Actions artifact.
2. Sign/sideload the resulting game-specific IPA for your device using an
   appropriate Apple signing identity and sideloading flow. This has **not
   been tested** on the ordinary iPhone 15; a signed IPA may still fail.
3. Start with `DM_OPMODE=0` (handheld mode) and `DM_FPS=30` in the app's
   Files → Documents → `env.txt` to reduce rendering cost.
4. Open the app and inspect Files → `log.txt` and `log.prev.txt`.
   Collect the first failure stage, any Metal errors, texture upload costs
   and resident memory/available-memory readouts. Prefer a reproducible
   loading stage over an unqualified FPS claim.

### Known unresolved paths

- GPU-produced compressed blocks in private buffers cannot be decoded by
  the CPU fallback for buffer-to-texture copies; the current implementation
  logs an error for that case.
- Render-to-BC texture aliases (used by some games) still require a correct
  proxy/block-copy implementation.
- Runtime memory pressure and shader compilation have not been profiled on A16.
- The 1.4.3 TotK profile is explicitly in bring-up, and the upstream README
  does **not** list TotK among supported iPhone games.
- A Windows PC alone does not provide Apple's Xcode/iPhoneOS toolchain.
  Source-only CI cannot produce a personalized, verified game IPA without
  the private game-derived inputs and signing.

**Success condition:** A signed, privately built TotK 1.4.3 app reaches real
in-game rendered frames on an ordinary iPhone 15, stays under the app memory
limit during a sustained gameplay scene, and produces reproducible logs.
This has not happened or been verified in this branch.
