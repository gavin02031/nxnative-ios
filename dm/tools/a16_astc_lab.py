#!/usr/bin/env python3
"""Offline, private NVN BC->ASTC quality experiment for an individual LINEAR mip.

This DOES NOT patch TotK's archives or teach the iOS replay layer to bind ASTC.
Do not commit the .astc/.tga/.json generated from copyrighted game resources.
It lets an A16 owner test acceptable texture quality + projected GPU residency
before implementing a game-specific offline asset replacement pipeline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

PRESETS = {
    "high": {"world": "4x4", "normal": "4x4", "ui": "4x4"},
    "balanced": {"world": "5x5", "normal": "4x4", "ui": "4x4"},
    "small": {"world": "6x6", "normal": "5x5", "ui": "4x4"},
}
BC8 = {0x41, 0x42, 0x45, 0x46, 0x49}
BC_SRGB = {0x45, 0x46, 0x47, 0x48, 0x4E}
BC_UNSUPPORTED = {0x4A, 0x4C, 0x4F, 0x50}  # signed BC4/5 and BC6H
BC_SUPPORTED = set(range(0x41, 0x4F)) - BC_UNSUPPORTED
BLOCK = {"4x4": (4, 4), "5x5": (5, 5), "6x6": (6, 6)}
MAGIC = bytes.fromhex("13aba15c")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inspect_astc(path: Path, w: int, h: int, block: str) -> int:
    bs = path.read_bytes()
    if len(bs) < 16 or bs[:4] != MAGIC:
        raise ValueError("astcenc did not produce a .astc texture")
    bw, bh = BLOCK[block]
    got_w = int.from_bytes(bs[7:10], "little")
    got_h = int.from_bytes(bs[10:13], "little")
    got_z = int.from_bytes(bs[13:16], "little")
    if (bs[4], bs[5], bs[6], got_w, got_h, got_z) != (bw, bh, 1, w, h, 1):
        raise ValueError(f"ASTC header mismatch: {(got_w, got_h, got_z)}")
    payload = ((w + bw - 1) // bw) * ((h + bh - 1) // bh) * 16
    if len(bs) != payload + 16:
        raise ValueError(f"ASTC payload expected {payload} bytes, got {len(bs) - 16}")
    return payload


def read_tga(path: Path) -> tuple[int, int, bytes]:
    """Read uncompressed 24/32-bit TGA emitted by astcenc; output RGBA top-first."""
    raw = path.read_bytes()
    if len(raw) < 18:
        raise ValueError("short TGA")
    idlen, cmap, kind = raw[:3]
    width, height, bpp, flags = struct.unpack_from("<HHBB", raw, 12)
    if cmap or kind != 2 or bpp not in (24, 32) or not width or not height:
        raise ValueError("unsupported TGA encoding (expected RGB/RGBA uncompressed)")
    nbytes = bpp // 8
    off = 18 + idlen
    n = width * height * nbytes
    if len(raw) < off + n:
        raise ValueError("truncated TGA")
    body = raw[off:off + n]
    top = bool(flags & 0x20)
    right = bool(flags & 0x10)
    rgba = bytearray(width * height * 4)
    for y in range(height):
        sy = y if top else height - 1 - y
        for x in range(width):
            sx = width - 1 - x if right else x
            p = (sy * width + sx) * nbytes
            q = (y * width + x) * 4
            rgba[q:q + 4] = (body[p + 2], body[p + 1], body[p], body[p + 3] if nbytes == 4 else 255)
    return width, height, bytes(rgba)


def psnr(source: Path, actual: Path, fmt: int) -> float:
    w, h, a = read_tga(source)
    dw, dh, b = read_tga(actual)
    if (w, h) != (dw, dh):
        raise ValueError("decoded ASTC changed dimensions")
    channels = (0,) if fmt == 0x49 else (0, 1) if fmt == 0x4B else (0, 1, 2) if fmt in (0x41, 0x45) else (0, 1, 2, 3)
    squared = 0
    for i in range(0, len(a), 4):
        squared += sum((int(a[i + c]) - int(b[i + c])) ** 2 for c in channels)
    if not squared:
        return float("inf")
    return 10 * math.log10(255 * 255 * (w * h) * len(channels) / squared)


def run(args: argparse.Namespace) -> dict:
    if args.format not in BC_SUPPORTED:
        raise ValueError("only unsigned LDR BC1/2/3/4/5/7 supported; signed and BC6H require a different path")
    if args.width <= 0 or args.height <= 0 or max(args.width, args.height) > 16384:
        raise ValueError("width and height must be 1..16384")
    if args.scale not in (1, 2, 4):
        raise ValueError("scale must be 1, 2 or 4")
    if args.kind in ("normal", "ui") and args.scale != 1:
        raise ValueError("never downscale UI or normal maps automatically: small text / lighting artifacts")
    if args.kind == "normal" and args.format not in (0x4B, 0x49):
        raise ValueError("normal-map input currently supports unsigned BC4/BC5 only")
    if not 0 <= args.min_psnr <= 100:
        raise ValueError("min-psnr must be between 0 and 100")
    size = ((args.width + 3) // 4) * ((args.height + 3) // 4) * (8 if args.format in BC8 else 16)
    if args.input.stat().st_size != size:
        raise ValueError(f"input must be a single linear BC mip of exactly {size} bytes; not a swizzled BNTX/BFRES, NSP or RomFS")
    block = args.block or PRESETS[args.tier][args.kind]
    w = (args.width + args.scale - 1) // args.scale
    h = (args.height + args.scale - 1) // args.scale
    encoder = shutil.which(str(args.encoder))
    decoder = shutil.which(str(args.decoder))
    if not decoder:
        raise ValueError("missing a16_bc_to_tga executable; compile the bundled C helper locally")
    if not encoder:
        raise ValueError("missing astcenc executable; install Arm astcenc separately")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.suffix.lower() != ".astc":
        raise ValueError("--out must end in .astc")
    manifest = args.out.with_suffix(".json")
    if args.out.exists() or manifest.exists():
        raise ValueError("output or manifest already exists: choose a fresh output to avoid accidental overwrite")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        source = root / "source.tga"
        decoded = root / "decoded.tga"
        subprocess.run([decoder, str(args.input), str(source), str(args.width), str(args.height),
                        hex(args.format), str(args.scale)], check=True)
        # sRGB is only correct for encoded color. Data/normal maps stay linear.
        srgb = args.format in BC_SRGB and args.kind not in ("normal",)
        cmd = [encoder, "-cs" if srgb else "-cl", str(source), str(args.out),
               block, "-" + args.preset]
        subprocess.run(cmd, check=True)
        payload = inspect_astc(args.out, w, h, block)
        subprocess.run([encoder, "-ds" if srgb else "-dl", str(args.out), str(decoded)], check=True)
        quality = psnr(source, decoded, args.format)
        if quality < args.min_psnr:
            args.out.unlink(missing_ok=True)
            raise ValueError(f"texture quality {quality:.1f} dB is below {args.min_psnr:.1f} dB minimum; use high tier or a less compressed block size")
    decoded_bytes = w * h * (1 if args.format == 0x49 else 2 if args.format == 0x4B else 4)
    metadata = {
        "schema": 1, "purpose": "quality-test-only; NOT automatically loadable by TotK",
        "input_sha256": sha256(args.input), "input_nvn_format": hex(args.format),
        "input_dimensions": [args.width, args.height], "output_dimensions": [w, h],
        "tier": args.tier, "kind": args.kind, "scale": args.scale, "block": block,
        "color_profile": "srgb" if srgb else "linear", "encoder_preset": args.preset,
        "min_psnr_db": args.min_psnr, "measured_psnr_db": None if math.isinf(quality) else round(quality, 2),
        "astc_payload_bytes": payload, "astc_sha256": sha256(args.out),
        "source_bc_bytes": size, "estimated_decoded_gpu_bytes_at_output_resolution": decoded_bytes,
        "compression_vs_decoded": round(decoded_bytes / payload, 3),
        "warning": "single mip only; not a game asset patch; no runtime integration or physical GPU benchmark",
    }
    manifest.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, type=Path, help="private linear NVN BC blocks, exactly one mip")
    ap.add_argument("--format", required=True, type=lambda x: int(x, 0), help="NVN format such as 0x44 (BC3) or 0x4d (BC7)")
    ap.add_argument("--width", type=int, required=True)
    ap.add_argument("--height", type=int, required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--tier", choices=PRESETS, default="balanced")
    ap.add_argument("--kind", choices=("world", "normal", "ui"), default="world")
    ap.add_argument("--block", choices=BLOCK, help="override the preset block size")
    ap.add_argument("--scale", type=int, default=1, help="world textures only: 1,2 or 4")
    ap.add_argument("--preset", choices=("fast", "medium", "thorough", "verythorough"), default="medium")
    ap.add_argument("--min-psnr", type=float, default=28.0)
    ap.add_argument("--encoder", default="astcenc", help="path to Arm astcenc (Windows binaries supported)")
    ap.add_argument("--decoder", default="a16_bc_to_tga", help="path to locally built C helper")
    args = ap.parse_args()
    try:
        result = run(args)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"ASTC quality test failed: {error}", file=sys.stderr)
        return 2
    print(f"PASS {args.out}: {result['block']} quality {result['measured_psnr_db']} dB; "
          f"ASTC {result['astc_payload_bytes']} bytes vs decoded {result['estimated_decoded_gpu_bytes_at_output_resolution']} bytes "
          f"({result['compression_vs_decoded']}x smaller). NOT GAME-LOADABLE YET.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
