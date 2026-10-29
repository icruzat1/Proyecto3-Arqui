"""CLI tests of the production firmware and accelerated, traceable test profile."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_NAMES = ("game.s", "asic_program_rom.v", "game.hex", "timing.json", "manifest.json")


class GameFirmwareTests(unittest.TestCase):
    def setUp(self):
        temporary_root = SOURCE_ROOT / "build/game_generator_tests"
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="fixture-", dir=temporary_root)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for relative in (
            "scripts/generate_game_firmware.py", "scripts/generate_asic_memory.py",
            "firmware/asic/game.s", "baseline/proyecto2/assembler/assemble.py",
        ):
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE_ROOT / relative, destination)
        self.before = self.snapshot(self.root / "baseline")

    def tearDown(self):
        self.assertEqual(self.snapshot(self.root / "baseline"), self.before)

    @staticmethod
    def snapshot(directory):
        return {str(p.relative_to(directory)): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in directory.rglob("*") if p.is_file()}

    def command(self, *args, success=True):
        result = subprocess.run([sys.executable, str(self.root / "scripts/generate_game_firmware.py"), *map(str, args)],
                                cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    @staticmethod
    def constant(words):
        """Independently execute the encoded LUI/ADDI pair, including signed I-immediate."""
        value = 0
        for index, word in enumerate(words):
            instruction = int(word, 16)
            assert (instruction >> 7) & 31 == 9
            if index == 0:
                assert instruction & 127 == 0x37
                value = instruction & 0xfffff000
            else:
                assert instruction & 127 == 0x13
                assert (instruction >> 12) & 7 == 0
                assert (instruction >> 15) & 31 == 9
                immediate = instruction >> 20
                if immediate & 0x800:
                    immediate -= 0x1000
                value = (value + immediate) & 0xffffffff
        return value

    def test_profiles_encode_exact_constants_and_same_control_flow(self):
        programs = {}
        metadata = {}
        for profile, wait, tenth, scale in (("production", 30_000_000, 1_000_000, 1), ("simulation", 3000, 100, 10000)):
            self.command("--profile", profile)
            output = self.root / "build/game_firmware" / profile
            words = (output / "game.hex").read_text().splitlines()
            timing = json.loads((output / "timing.json").read_text())
            self.assertEqual(len(words), 95)
            self.assertEqual(self.constant(words[13:16]), wait)
            index = timing["labels"]["div_l"] // 4
            self.assertEqual(self.constant(words[index - 3:index - 1]), tenth)
            self.assertEqual(timing["wait_ticks"], wait)
            self.assertEqual(timing["tenth_ticks"], tenth)
            self.assertEqual(timing["acceleration_factor"], scale)
            self.assertEqual(wait // tenth, 30)
            self.assertEqual(wait * scale, 30_000_000)
            self.assertEqual(tenth * scale, 1_000_000)
            self.assertEqual(timing["clock_hz"], 10_000_000)
            if profile == "production":
                self.assertEqual((output / "game.s").read_bytes(), (self.root / "firmware/asic/game.s").read_bytes())
            programs[profile] = words
            metadata[profile] = timing
        self.assertEqual(metadata["production"]["labels"], metadata["simulation"]["labels"])
        tenth_index = metadata["production"]["labels"]["div_l"] // 4 - 3
        allowed = {13, 14, 15, tenth_index, tenth_index + 1}
        actual = {i for i, pair in enumerate(zip(programs["production"], programs["simulation"])) if pair[0] != pair[1]}
        self.assertTrue(actual)
        self.assertLessEqual(actual, allowed)

    def test_wait_only_changes_only_wait_and_preserves_production_reaction_unit(self):
        self.command("--profile", "production")
        self.command("--profile", "wait_only")
        production = self.root / "build/game_firmware/production"
        output = self.root / "build/game_firmware/wait_only"
        baseline_words = (production / "game.hex").read_text().splitlines()
        words = (output / "game.hex").read_text().splitlines()
        timing = json.loads((output / "timing.json").read_text())
        production_timing = json.loads((production / "timing.json").read_text())
        self.assertEqual(len(words), 95)
        self.assertEqual(self.constant(words[13:16]), 3000)
        index = timing["labels"]["div_l"] // 4
        self.assertEqual(self.constant(words[index - 3:index - 1]), 1_000_000)
        self.assertEqual(timing["wait_ticks"], 3000)
        self.assertEqual(timing["tenth_ticks"], 1_000_000)
        self.assertIsNone(timing["acceleration_factor"])
        self.assertEqual(timing["wait_acceleration_factor"], 10000)
        self.assertEqual(timing["reaction_acceleration_factor"], 1)
        self.assertEqual(timing["labels"], production_timing["labels"])
        differences = {i for i, pair in enumerate(zip(words, baseline_words)) if pair[0] != pair[1]}
        self.assertTrue(differences)
        self.assertLessEqual(differences, {13, 14, 15})
        before = self.snapshot(output)
        self.command("--profile", "wait_only", "--check")
        self.command("--profile", "wait_only")
        self.assertEqual(self.snapshot(output), before)

    def test_deterministic_outputs_and_exact_provenance(self):
        a, b = self.root / "build/a", self.root / "build/b"
        self.command("--profile", "simulation", "--output-dir", a)
        self.command("--profile", "simulation", "--output-dir", b)
        for name in OUTPUT_NAMES:
            self.assertEqual((a / name).read_bytes(), (b / name).read_bytes())
        manifest = json.loads((a / "manifest.json").read_text())
        timing = json.loads((a / "timing.json").read_text())
        self.assertEqual(manifest["source"]["sha256"], hashlib.sha256((a / "game.s").read_bytes()).hexdigest())
        self.assertEqual(manifest["timing_json_sha256"], hashlib.sha256((a / "timing.json").read_bytes()).hexdigest())
        self.assertEqual(manifest["production_source"]["sha256"], hashlib.sha256((self.root / "firmware/asic/game.s").read_bytes()).hexdigest())
        self.assertEqual(timing["generated_source_sha256"], manifest["source"]["sha256"])
        self.assertNotIn(str(self.root), (a / "manifest.json").read_text() + (a / "timing.json").read_text())
        before = self.snapshot(a)
        self.command("--profile", "simulation", "--output-dir", a, "--check")
        self.command("--profile", "simulation", "--output-dir", a)
        self.assertEqual(self.snapshot(a), before)

    def test_check_detects_each_stale_file_without_writing(self):
        self.command()
        output = self.root / "build/game_firmware/production"
        for name in OUTPUT_NAMES:
            with self.subTest(name=name):
                path = output / name
                old = path.read_bytes()
                path.write_bytes(old + b"tampered\n")
                before = self.snapshot(output)
                self.assertIn(name, self.command("--check", success=False).stderr)
                self.assertEqual(self.snapshot(output), before)
                path.write_bytes(old)

    def test_modified_or_duplicate_markers_fail_before_outputs(self):
        path = self.root / "firmware/asic/game.s"
        source = path.read_text()
        for changed in (source.replace("addi x9, x9, 896", "addi x9, x9, 897"),
                        source + "# ASIC_TIMING WAIT_TICKS BEGIN\n",
                        source.replace("# TIMING_PROFILE production", "# TIMING_PROFILE simulation")):
            path.write_text(changed)
            self.command(success=False)
            self.assertFalse((self.root / "build/game_firmware/production").exists())
        path.write_text(source)

    def test_protected_paths_and_simulation_rtl_guard(self):
        firmware_before = self.snapshot(self.root / "firmware")
        for destination in (self.root / "baseline/proyecto2/assembler", self.root / "firmware/asic", self.root.parent / "Proyecto 2"):
            self.command("--output-dir", destination, success=False)
        for profile in ("simulation", "wait_only"):
            self.command("--profile", profile, "--output-dir", self.root / "rtl/asic/generated", success=False)
        self.assertEqual(self.snapshot(self.root / "firmware"), firmware_before)
        self.assertFalse((self.root / "rtl").exists())


if __name__ == "__main__":
    unittest.main()
