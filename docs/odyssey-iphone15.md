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
The owner also confirmed **having `prod.keys` in the iPhone's Files app**.
This is a confirmation of *local presence only*, not a verification of key
correctness or access by this assistant or the build runner. NSP contents,
NCA signatures and actual decryptability remain unverified.
No game file contents or keys have been transferred to the build runner.
Do not require extracting TotK, finding a PC, or redumping Odyssey.
**Status:** source-level A16 Metal syntax tests pass, but no Odyssey IPA has
been built, installed or run on this ordinary iPhone 15 from this branch.

TotK is postponed until Odyssey works. Shared generic renderer fixes are
welcome, but milestones are evaluated against **Odyssey first**.

## GitHub-hosted macOS IPA build feasibility (verified October 19, 2026)

A **real** macOS 26 GitHub Actions runner executed the no-game-data
[Odyssey Mac build feasibility workflow](../../.github/workflows/odyssey-macos-build-feasibility.yml):

- Existing owner's Odyssey NSP sizes: 5.60 GiB combined.
- nxnative's own early extraction disk preflight: about 11.60 GiB.
- Conservative initial staging + packaging planning estimate: 16.60 GiB.
- Actual runner **reported 94.7–95.7 GiB free** in two CI executions,
  and ~95.66 GiB after installing tools. This is an observation, not a
  guaranteed allocation for all future jobs.
- Xcode, `.NET SDK 10.0.401`, `zstd` etc. were already available.
- `brew install xcodegen spirv-cross` succeeded on the runner.
- Python virtualenv installed and imported `lz4`, `capstone`,
  `fontTools`; no original game files, private keys or derived game code.
- **Both resource audit and dependencies install smoke test passed.**
  This supports attempting the full build on GitHub macOS runners instead
  of asking the player to use any Windows PC.

**Blocking work before a real IPA:** Provision isolated **private**
storage/import for the owner's full NSPs, isolate `prod.keys` in a
restricted secret-handling flow, and grant a manual, approved build job
temporary read access. The fork is **public** and is not a safe place
for those files, nor should they appear in any Actions logs, caches,
PRs or artifacts. Apple signing and iPhone 15 runtime still need
verification. The existing stock full-IPA builder takes local file
paths; it cannot read from iPhone Files or Google Drive without a
separately provisioned secure transfer mechanism.

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

## Phone-only NSP preflight (no secrets)

A game-data-free **local browser preflight** is implemented in
`docs/odyssey-preflight/`. It can let the owner choose the base and update
NSPs directly from the iPhone's Files picker, check filenames/title IDs
and the PFS0 archive index, then report structural validity. It reads only
the small header/index and has a strict Content Security Policy disabling
network requests. It **never requests, reads or uploads `prod.keys`**.
The parser is regression-tested with fake files rather than original
Nintendo game data.

The optional GitHub Pages deployment workflow publishes only this
preflight's static HTML/JavaScript (not the user's files). **Do not
claim the webpage is live until its deployment is verified.**

Passing preflight does not prove the actual NCA content can be
decrypted or that the iOS IPA will work. It is a useful preliminary
check for phone-only workflow, **not** a secure remote build service.

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
- [x] Owner supplied iPhone screenshots showing separate **1.0.0 base** and **1.4.1 update v393216** NSP entries and confirmed a local `prod.keys` file. Archive contents/key correctness still unverified.
- [x] Implemented a client-only NSP-header preflight with synthetic regression tests; no keys requested.
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
