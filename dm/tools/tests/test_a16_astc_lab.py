"""Private-asset-free regression tests for the experimental Windows-compatible ASTC lab."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "a16_astc_lab.py"
spec = importlib.util.spec_from_file_location("a16_astc_lab", SCRIPT)
lab = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(lab)


class AstcLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("cc") or not shutil.which("astcenc"):
            raise unittest.SkipTest("requires a C compiler and astcenc (installed in CI)")
        cls.bin_folder = tempfile.TemporaryDirectory()
        root = HERE.parents[1]
        cls.decoder = Path(cls.bin_folder.name) / "a16_bc_to_tga"
        subprocess.run(
            ["cc", "-O1", "-std=c11", "-Wall", "-Wextra", "-o", str(cls.decoder),
             str(root / "tools" / "a16_bc_to_tga.c"),
             str(root / "gfx" / "tex" / "nvn_bcdec.c"), "-lm"], check=True
        )

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "bin_folder"):
            cls.bin_folder.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "sample.bc"
        self.output = self.root / "sample.astc"
        self.args = Namespace(
            input=self.source, format=0x41, width=8, height=8,
            out=self.output, tier="balanced", kind="world", block=None,
            scale=1, preset="fast", min_psnr=0.0,
            encoder="astcenc", decoder=str(self.decoder)
        )
        # Four RGB_DXT1 blocks with distinct solid colours, no licensed game data.
        blocks = [
            bytes.fromhex("00f8e00700000000"),  # red
            bytes.fromhex("e00700f800000000"),  # green
            bytes.fromhex("1f0000f800000000"),  # blue
            bytes.fromhex("ffff000000000000"),  # white
        ]
        self.source.write_bytes(b"".join(blocks))

    def test_genuine_astc_roundtrip(self):
        result = lab.run(self.args)
        self.assertEqual(result["output_dimensions"], [8, 8])
        self.assertEqual(result["block"], "5x5")
        self.assertGreater(result["astc_payload_bytes"], 0)
        self.assertEqual(lab.inspect_astc(self.output, 8, 8, "5x5"), 64)
        self.assertTrue(self.output.with_suffix(".json").exists())
        self.assertGreater(result["compression_vs_decoded"], 1)
        self.assertTrue(result["measured_psnr_db"] is None or result["measured_psnr_db"] > 0)

    def test_downscale_world_only(self):
        self.args.scale = 2
        self.args.tier = "small"
        result = lab.run(self.args)
        self.assertEqual(result["output_dimensions"], [4, 4])
        self.assertEqual(result["block"], "6x6")
        self.assertEqual(result["astc_payload_bytes"], 16)
        self.assertEqual(result["estimated_decoded_gpu_bytes_at_output_resolution"], 4 * 4 * 4)

    def test_no_downscale_ui_or_normal(self):
        for kind in ("ui", "normal"):
            self.args.kind = kind
            self.args.scale = 2
            with self.assertRaisesRegex(ValueError, "never downscale"):
                lab.run(self.args)

    def test_reject_swizzled_or_wrong_size_input(self):
        self.source.write_bytes(bytes(100))
        with self.assertRaisesRegex(ValueError, "single linear BC mip"):
            lab.run(self.args)

    def test_reject_signed_and_hdr_without_proper_encoder(self):
        for fmt in (0x4A, 0x4C, 0x4F, 0x50):
            self.args.format = fmt
            with self.assertRaisesRegex(ValueError, "signed"):
                lab.run(self.args)

    def test_tga_decoder_channel_and_dimension(self):
        tga = self.root / "sample.tga"
        subprocess.run([str(self.decoder), str(self.source), str(tga), "8", "8", "0x41", "2"], check=True)
        w, h, pixels = lab.read_tga(tga)
        self.assertEqual((w, h), (4, 4))
        self.assertEqual(len(pixels), 4 * 4 * 4)
        self.assertEqual(pixels[:4], bytes((255, 0, 0, 255)))

    def test_astc_corruption_guard(self):
        self.output.write_bytes(bytes(16 + 16))
        with self.assertRaisesRegex(ValueError, "astcenc"):
            lab.inspect_astc(self.output, 4, 4, "4x4")


if __name__ == "__main__":
    unittest.main()
