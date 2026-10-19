# Priority 1 — Super Mario Odyssey on regular iPhone 15

**Target device:** non-Pro iPhone 15, A16, 6 GB RAM, iOS 26+.
**Game:** Super Mario Odyssey, native nxnative profile
`dm/games/0100000000010000/game.tsv`, supported build **1.4.1**
(`v393216`), with `main + subsdk0 + sdk`.
**Game inputs:** The owner confirmed two distinct files on their iPhone via
in-app information screenshots on October 19, 2026:
- **Base:** `Super Mario Odyssey [0100000000010000][v0].nsp`;
  5,611,009,601 bytes; version 1.0.0.
- **Update:** `SUPER MARIO ODYSSEY [0100000000010800][v393216][Update v1.4.1].nsp`;
  397,297,736 bytes; version 1.4.1.

These labels are consistent with the game's existing `v393216` profile.
They verify version information as shown by the iPhone app, **not** archive
cryptographic integrity, decrypted content, or availability of `prod.keys`.
No file contents or keys have been transferred to the developer/build runner.
Do not require extracting TotK, finding a PC, or redumping Odyssey.
**Status:** source-level A16 Metal syntax tests pass, but no Odyssey IPA has
been built, installed or run on this ordinary iPhone 15 from this branch.

TotK is postponed until Odyssey works. Shared generic renderer fixes are
welcome, but milestones are evaluated against **Odyssey first**.

## Phone-only player workflow — non-negotiable

The player wants to use their **iPhone only**. Do not assign them a Windows,
Mac, Xcode, Python, terminal or manual ROM extraction task. Build work can run
on hosted macOS infrastructure, but an actual game build requires a secure
private process for the owner's NSP, matching update and keys. **That build
service does not exist in this repository today.**

Keep game NSPs, `prod.keys`, extracted game code, derived shader libraries,
game-containing IPAs and any signing material **out of public GitHub,
Actions logs/artifacts, pull requests and issues**. Never solicit those
secrets in a public issue or chat. A key or dump existing *on the phone*
does not give a GitHub-hosted runner permission or access to it.

The ideal eventual phone-only flow is: the user selects files in iOS Files
through a secure private import, a trusted isolated Mac builder processes
their own game data, an authenticated signed build is made available for
their device, and the user tests it and shares sanitized runtime logs.
This is a **design target, not a working feature**; do not represent it as
available.

## Implemented compatibility changes

- The iOS compile baseline targets `apple-a16` rather than A18.
- On A16, the Metal renderer detects BC is unsupported and decodes BC1–BC5
  on the GPU plus remaining BC6H/BC7 cases on the CPU.
- A non-BC texture fallback can increase physical GPU memory dramatically.
  Compressed ASTC is a potential way to reduce this footprint.
- The offline ASTC lab is **only a test of synthetic isolated BC texture
  blocks**. It does not parse Odyssey BFRES/BNTX formats or rewrite the
  game's metadata, render-target proxies, shader assumptions, mip chains
  or runtime-generated BC resources.
- No on-device image quality, frame time, RAM usage or gameplay are yet
  verified for this phone.

## Image-quality and performance priorities

1. **Keep UI, map text, character faces and normal maps sharp.** Use ASTC
   4x4 or retain source quality; never blindly downscale these images.
2. **Start world textures at original resolution, ASTC 5x5**, and measure
   fidelity against the source. 4x4 for assets that fail the quality gate;
   6x6 selectively for tolerant terrain/distant scenery.
3. Only reduce **individual oversized scenery textures to half resolution**
   if measurement shows meaningful memory pressure. Preserve mip chains,
   UV coordinates and texture views. Do not introduce an image-looking-bad
   mode by default.
4. Initial rendering target should be stable 30 FPS in handheld settings,
   **not a promise**. Optimize based on real GPU/CPU stalls and memory data.

## Specific next milestones

- [x] Upstream Odyssey **1.4.1** game profile already exists in nxnative.
- [x] Owner supplied iPhone screenshots showing separate **1.0.0 base** and **1.4.1 update v393216** NSP entries. Archive contents and keys still unverified.
- [x] A16 renderer BC fallback built as source, plus synthetic decoder tests.
- [x] A16 native iPhoneOS / Metal 4 compiler check for Odyssey profile.
- [x] Synthetic BC-to-ASTC quality tests (not assets from Odyssey).
- [ ] Inspect actual Odyssey 1.4.1 texture containers and the runtime
  handles using an isolated private input (without sharing game files).
- [ ] Implement **Odyssey-specific** loss-controlled ASTC asset conversion:
  container reader, swizzle/mip handling, manifest and game metadata changes.
- [ ] Verify full iPhoneOS game-specific app **linking** and executable
  signatures in an isolated macOS build using owned files.
- [ ] Provide a real **secure, no-PC** private file/import/build/sign/install
  workflow, with appropriate consent and secrets handling.
- [ ] Test actual first frame on **regular** iPhone 15 A16 (not 15 Pro), then
  memory, shader compilation, gameplay audio, loading and thermal behavior.
- [ ] Optimize until device reports and image comparison show acceptable
  quality and stable play.

## Diagnostic checkpoints once a real build exists

Log the title/version, GPU's `supportsBCTextureCompression` result,
texture format counts, BC upload/decode timings, Metal allocated memory,
resident memory, iOS available-process-memory, stage of loading, GPU
errors and frame time. Prefer sanitized device logs, not Nintendo keys,
private file paths or full game assets.

**No fake test-shell IPA should count as Odyssey running natively.**
