# Build an unsigned iPhone/iPad IPA on GitHub Actions

This fork has a **manual** workflow at [`Build unsigned IPA from private game archive`](../.github/workflows/build-ipa.yml).
It uses GitHub's `macos-26` runner, installs the upstream nxnative tools and invokes
`scripts/build_ipa_from_nsp.py`. It does **not** contain or fetch any Nintendo game or key files
unless you explicitly configure your own encrypted inputs.

## Important limits

- The standard GitHub macOS runner has **14 GB SSD total**. The upstream script needs roughly
  the sum of game NSP sizes plus **6 GB of free work space**, *after* the encrypted archive is
  downloaded and unpacked. Bigger games, especially **Super Mario Odyssey** and **Tears of the Kingdom**,
  may not fit. For these, use a **self-hosted Apple Silicon Mac runner with much more free storage**
  (and change `runs-on` appropriately) or a macOS host with adequate disk.
- GitHub hosted virtual Macs do not provide the GPU environment needed to boot/capture
  shaders from games that require a Mac Metal runtime capture. This workflow may build
  games with entirely offline shader extraction, but it cannot guarantee every game.
- Upstream supports iPhone 15 **Pro** or newer with BC textures, or an M1-or-newer iPad,
  running iOS/iPadOS 26+. A regular iPhone 15 is not currently supported without
  additional BC texture compatibility work.
- The IPA is **unsigned**. After downloading and decrypting it, sign and sideload it
  using your preferred installation tool. A successfully built IPA does not prove the game
  starts or runs correctly on the device.
- GitHub artifact storage, upload size, retention and runner minutes can also limit the build.

## Prepare your game archive on Windows

Use only game files and `prod.keys` that you dumped from your own console.
Do not commit or upload them unencrypted to this public repository.

1. Create a temporary folder whose contents are exactly:
   ```text
   game/                  # One game per build, with its base NSP/XCI and any update/DLC NSPs
     Your Game.nsp
     Your Update.nsp
   prod.keys
   ```
2. In **7-Zip** for Windows, select **both** `game` and `prod.keys` and choose **Add to archive**.
   Choose **7z** format, **AES-256** encryption, a strong random password and **Encrypt file names**.
   Because game files are already compressed, **Store** / no extra compression can save time.
   Call the output `input.7z`. Test that the archive asks for a password.
3. Upload **only** the encrypted `input.7z` to storage that offers a direct HTTPS download URL
   (for example a short-lived, presigned object-storage link). The ordinary browser link to
   a Google Drive folder/file is often **not a direct file download** and may not work with curl.
   Keep the password separate from the archive URL.

## Set two GitHub Actions secrets

Open the **fork** at `gavin02031/nxnative-ios` →
**Settings → Secrets and variables → Actions → New repository secret**.

| Secret | Value |
| --- | --- |
| `NXNATIVE_ARCHIVE_URL` | Direct HTTPS download URL of your encrypted `input.7z` |
| `NXNATIVE_ARCHIVE_PASSWORD` | Strong AES-256 password you used in 7-Zip |

Do not put the keys, the archive password, or URLs containing access tokens in
workflow inputs, issues, commits, README text or Actions logs.

## Start the build

1. Open **Actions** → **Build unsigned IPA from private game archive**.
2. Click **Run workflow** on the `main` branch.
3. Follow the run's logs. The job checks tools, downloads and decrypts the archive on
   its *ephemeral* macOS runner, checks for your game folder and keys, and invokes:
   ```bash
   python scripts/build_ipa_from_nsp.py "<runner>/game" -k "<runner>/prod.keys" \
      --platform ios --no-keep-extracted --gpu none --progress lines
   ```
4. On success, open the completed run → **Artifacts** → `nxnative-unsigned-ipa-encrypted`.
   Download it, extract the inner `unsigned-ipa.7z`, and decrypt that file using the **same**
   password. It contains the unsigned `.ipa`.
5. Sign/sideload the unsigned IPA onto a supported iPhone/iPad. Rotate or expire the
   storage link when finished.

The uploaded GitHub artifact is **always encrypted** because the repository is public:
**never upload the plaintext IPA**, which contains game assets. The workflow does not
upload decrypted NSPs, `prod.keys`, or the unencrypted IPA. The job removes the local
decrypted inputs at the end, and the ephemeral runner is discarded.

## If the job cannot build

- **Disk space**: the standard macOS runner is too small for your game. Do not try to
  split the game into public repository commits. Use a runner with more disk.
- **Input download**: your cloud provider's sharing URL may point to a webpage rather than
  the encrypted archive. Use a direct HTTPS download link.
- **GPU capture**: some games boot on a Mac to collect runtime shaders. Hosted virtual
  runners lack the required GPU environment; use your own Apple Silicon Mac runner.
- **Missing update/profile**: review the game's `dm/games/<title ID>/README.md` and
  ensure the right base/update versions are in your encrypted archive.
- **Artifact too large**: use private external artifact storage or a runner with your own
  controlled output location; never publish the unencrypted IPA.

This workflow is a build *starting point*, not an end-to-end validated IPA: the repo owner
must configure the two secrets and test a small compatible game first.
