# Odyssey on-device game-file import (iPhone 15)

**Status: foundation only — not yet a runnable NSP importer.**

## Goal

Mush8-style experience: sideload a relatively small, **already compiled**
Super Mario Odyssey 1.4.1 iOS app, open it, select the player's personally
dumped base NSP, matching v393216 update NSP and `prod.keys` from the iOS
Files document picker, prepare/mount the assets *locally*, then tap Play.
No uploading game dumps or console keys, no cloud conversion at install time,
and no need for a Mac/PC on the user's end.

The native app must be game/version-specific. Importing arbitrary other
Switch games does **not** compile or translate them into native iOS binaries.
On iOS the rewritten Odyssey executable and the iOS Metal shader libraries
must already be compiled, linked and code-signed in the IPA.

Mush8 and Muguet describe this distinction in their own README files:
their iOS native game code is linked at *build time*; imported files are
runtime data. They are GPL-3.0 projects; don't vendor Mush8 code into
MIT-licensed nxnative without evaluating license compatibility and
distribution obligations.

## Completed foundation

- `dm/ios/tools/build_ipa.sh` has a new opt-in `DM_EXTERNAL_ROMFS=1`.
  The build still consumes the correct Odyssey NSPs on the Mac to
  compile/link the native guest modules and shader libraries, but no
  longer copies `RomFS` into `Payload/DmIOS.app/romfs`. It therefore
  produces a smaller unsigned IPA. **Not yet tested with owned NSPs.**
- The existing `dm/ios/Sources/main.m` already prioritizes a
  `Documents/romfs` folder if its game-profile marker is present; this
  lets a pre-extracted Odyssey RomFS work without being in the signed
  application bundle.
- The existing app sets `UIFileSharingEnabled` and
  `LSSupportsOpeningDocumentsInPlace` to support local Files.

## Missing before the desired Mush8-style app is playable

1. **File picker / importer UX.** A first-run full-screen launcher showing
   exact expected base game, update 1.4.1 and console-key status, using
   security-scoped Files URLs and background streaming rather than loading
   multi-gigabyte NSPs into RAM. Show progress, actionable errors and a Play
   button only when the data is ready. Never print key values.
2. **Native on-device NSP reader + update overlay.** The current
   `dm/tools/nx_extract` is .NET tooling built for the Mac build step.
   It is **not** embedded in the iOS app. We must introduce an iOS-compatible
   PFS0/ticket/NCA AES decryption and RomFS reader, including base/update
   overlay, based on responsibly licensed source or a tested clean-room
   implementation. Validate the expected 0100000000010000 base and
   0100000000010800 v393216 update. No iOS JIT or dynamic machine-code
   generation is required.
3. **Asset mount/extraction.** Either expose an efficient read-only
   virtual RomFS to the existing Horizon filesystem host, or stream/decrypt
   the merged RomFS into a private `Documents/romfs.partial` directory,
   validate the required marker and atomic-rename it to
   `Documents/romfs`. Use the existing `main.m` search path; keep game
   data out of the IPA. Account for several GB of additional disk space.
4. **Privacy.** Import `prod.keys` only into the app's private folder,
   exclude sensitive inputs from iOS backups when appropriate, and do not
   send them to GitHub, a remote service or any public repository. Never
   include NSPs, extracted assets or key bytes in git or logs. Add a
   clear option to clear imported files.
5. **A16 compatibility & real device validation.** Test iOS signing and
   installation with GBox, test file import/permissions, key validation,
   first launch, thermal/memory behavior and frame output on **regular
   iPhone 15**. A successful cloud build does not prove gameplay.

## Thin-build opt-in

From the existing Mac builder, run with:

```sh
DM_EXTERNAL_ROMFS=1 python3 scripts/build_ipa_from_nsp.py \
  /path/to/your-odyssey-nsps -k /path/to/private/prod.keys
```

This still reads the user's game files **on the builder** to prepare
the game-specific code and shader libraries; only the bundled RomFS is
omitted. Until the native importer exists, the thin IPA does not
magically accept `.nsp` files, and won't boot without a valid
`Documents/romfs` directory.

## Scope

Keep Candela untouched. Do not enable this flag for other games by default.
Do not claim that anyone can import any Switch ROM and make a new native
port on iPhone, or that Odyssey will necessarily play on A16.
