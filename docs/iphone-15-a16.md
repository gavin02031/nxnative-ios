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
