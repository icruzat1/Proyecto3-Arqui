"""End-to-end checks of ROM generation, boundary handling, and provenance.

Install under sim/asic_stage2, then run:
python3 -m unittest discover -s sim/asic_stage2 -p 'test_generate_asic_memory.py' -v
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_NAMES = ("asic_program_rom.v", "game.hex", "manifest.json")


class MemoryGeneratorTests(unittest.TestCase):
    def setUp(self):
        temporary_root = SOURCE_ROOT / "build/generator_tests"
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="fixture-", dir=temporary_root)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        # Test isolated roots exercise the real CLI and immutable input files.
        for relative in (
            "scripts/generate_asic_memory.py",
            "baseline/proyecto2/assembler/assemble.py",
            "baseline/proyecto2/assembler/game.s",
            "baseline/proyecto2/assembler/game.hex",
            "baseline/proyecto2/pochoco_soc-main/sw/game.hex",
        ):
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE_ROOT / relative, destination)
        self.output = self.root / "rtl/asic/generated"
        self.baseline_before = self.snapshot_tree(self.root / "baseline")

    def tearDown(self):
        self.assertEqual(self.snapshot_tree(self.root / "baseline"), self.baseline_before)

    @staticmethod
    def snapshot_tree(directory):
        return {str(path.relative_to(directory)): (path.read_bytes(), path.stat().st_mtime_ns)
                for path in directory.rglob("*") if path.is_file()}

    def command(self, *arguments, success=True):
        result = subprocess.run(
            [sys.executable, str(self.root / "scripts/generate_asic_memory.py"), *map(str, arguments)],
            cwd=self.root, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def source(self, text):
        path = self.root / "diagnostic.s"
        path.write_text(text)
        return path

    def test_default_program_and_reproducibility_without_writes(self):
        self.command()
        baseline = (self.root / "baseline/proyecto2/assembler/game.hex").read_bytes()
        self.assertEqual((self.output / "game.hex").read_bytes(), baseline)
        manifest = json.loads((self.output / "manifest.json").read_text())
        self.assertEqual(manifest["program_words"], 94)
        self.assertEqual(manifest["reserved_program_words"], 34)
        self.assertEqual(manifest["program_hex_sha256"], hashlib.sha256(baseline).hexdigest())
        self.assertEqual(manifest["rom_verilog_sha256"], hashlib.sha256((self.output / "asic_program_rom.v").read_bytes()).hexdigest())
        self.assertNotIn(str(self.root), (self.output / "manifest.json").read_text())
        before = self.snapshot_tree(self.output)
        self.command("--check")
        self.command()
        self.assertEqual(self.snapshot_tree(self.output), before)

    def test_custom_program_exact_encoding_and_output_directory(self):
        source = self.source("addi x1, x0, 7\njal x0, 0\n")
        output = self.root / "build/custom_image"
        self.command("--source", source, "--output-dir", output)
        self.assertEqual((output / "game.hex").read_text(), "00700093\n0000006f\n")
        verilog = (output / "asic_program_rom.v").read_text()
        self.assertIn("7'd0: rom_word = 32'h00700093;", verilog)
        self.assertIn("7'd1: rom_word = 32'h0000006f;", verilog)
        self.assertIn("default: rom_word = 32'h00000013;", verilog)
        self.assertNotIn("$readmem", verilog)
        self.assertNotIn("initial", verilog)
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertEqual(manifest["program_words"], 2)
        self.assertEqual(manifest["source"]["path"], "diagnostic.s")
        self.command("--source", source, "--output-dir", output, "--check")

    def test_capacity_boundary_and_overflow_preserve_previous_outputs(self):
        source = self.source("\n".join(f"addi x1, x0, {i}" for i in range(128)) + "\n")
        self.command("--source", source)
        self.assertEqual(len((self.output / "game.hex").read_text().splitlines()), 128)
        self.assertIn("7'd127: rom_word = 32'h07f00093;", (self.output / "asic_program_rom.v").read_text())
        self.assertEqual(json.loads((self.output / "manifest.json").read_text())["reserved_program_words"], 0)
        before = self.snapshot_tree(self.output)
        source.write_text(source.read_text() + "addi x0, x0, 0\n")
        result = self.command("--source", source, success=False)
        self.assertIn("got 129", result.stderr)
        self.assertEqual(self.snapshot_tree(self.output), before)

    def test_empty_program_rejected_without_creating_outputs(self):
        source = self.source("# no instructions\n.section .text\n")
        result = self.command("--source", source, success=False)
        self.assertIn("got 0", result.stderr)
        self.assertFalse(self.output.exists())

    def test_check_detects_each_tampered_or_missing_file_without_rewriting(self):
        self.command()
        for name in OUTPUT_NAMES:
            with self.subTest(name=name):
                path = self.output / name
                original = path.read_bytes()
                path.write_bytes(original + b"tampered\n")
                before = self.snapshot_tree(self.output)
                result = self.command("--check", success=False)
                self.assertIn(name, result.stderr)
                self.assertEqual(self.snapshot_tree(self.output), before)
                path.write_bytes(original)
                path.unlink()
                before = self.snapshot_tree(self.output)
                self.command("--check", success=False)
                self.assertEqual(self.snapshot_tree(self.output), before)
                path.write_bytes(original)

    def test_default_game_reference_mismatch_is_rejected_before_output(self):
        # This test deliberately changes the isolated fixture, never real P2.
        reference = self.root / "baseline/proyecto2/assembler/game.hex"
        reference.write_text("00000013\n")
        self.baseline_before = self.snapshot_tree(self.root / "baseline")
        result = self.command(success=False)
        self.assertIn("does not match", result.stderr)
        self.assertFalse(self.output.exists())

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"), "Icarus required for ROM startup regression")
    def test_static_indices_are_defined_without_input_transition(self):
        self.command()
        testbench = self.root / "static_rom.v"
        testbench.write_text("""`timescale 1ns/1ps
module static_rom;
  wire [31:0] word_zero, word_last;
  asic_program_rom first (.word_index_i(7'd0), .word_o(word_zero));
  asic_program_rom last (.word_index_i(7'd127), .word_o(word_last));
  initial begin
    #1;
    if (word_zero !== 32'h80000137 || word_last !== 32'h00000013)
      $fatal(1, "Static ROM inputs must produce defined data without a transition");
    $display("PASS static ROM indices 0 and 127");
    $finish;
  end
endmodule
""")
        executable = self.root / "static_rom.vvp"
        compiled = subprocess.run(["iverilog", "-g2012", "-s", "static_rom", "-o", str(executable),
                                   str(testbench), str(self.output / "asic_program_rom.v")],
                                  capture_output=True, text=True)
        self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
        simulated = subprocess.run(["vvp", str(executable)], capture_output=True, text=True)
        self.assertEqual(simulated.returncode, 0, simulated.stdout + simulated.stderr)
        self.assertIn("PASS static ROM", simulated.stdout)

    def test_protected_output_directory_is_rejected(self):
        self.command("--output-dir", self.root / "baseline/proyecto2/assembler", success=False)
        self.assertEqual(self.snapshot_tree(self.root / "baseline"), self.baseline_before)


if __name__ == "__main__":
    unittest.main()
