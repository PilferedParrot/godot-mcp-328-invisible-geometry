#!/usr/bin/env python3
"""Validate the scorer on known cases before it is trusted with any agent's work.
Builds variants of the repo's buggy scene by patching spawner.gd, and checks the scorer's verdict
for each against what the patch is known to do. Run: python3 experiment/validate_scorer.py"""
import shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from score import score, ROOT

SRC = (ROOT / "buggy" / "spawner.gd").read_text()
F1 = ("FLOOR_Y + half_height(prop)", "surface_y(spec[1]) + half_height(prop)")
F2 = ("		prop.position = Vector3(spec[1].x, 0.0, spec[1].y)\n		prop.global_position.y = surface_y(spec[1]) + half_height(prop)  # snap to the floor\n		decor.add_child(prop)",
      "		decor.add_child(prop)\n		prop.global_position = Vector3(spec[1].x, surface_y(spec[1]) + half_height(prop), spec[1].y)")
F3 = ("cam.global_basis.z * spec[1]", "-cam.global_basis.z * spec[1]")

CASES = [  # name, patches, expected faults fixed (F1, F2, F3)
    ("buggy as shipped", [], (0, 0, 0)),
    ("fix F1 only (derive floor height)", [F1], (1, 0, 0)),
    ("fix F2 only (add_child first)", [F2], (0, 1, 0)),
    ("fix F3 only (flip the sign)", [F3], (0, 0, 1)),
    ("fix all three", [F1, F2, F3], (1, 1, 1)),
    ("F1 hard-coded to the right value (1.05): outcome counts", [("const FLOOR_Y := 0.0", "const FLOOR_Y := 1.05")], (1, 0, 0)),
    ("F1 'close' hard-coded 1.0 (5 cm sunk): must NOT count", [("const FLOOR_Y := 0.0", "const FLOOR_Y := 1.0")], (0, 0, 0)),
    ("F3 'fixed' by spinning the camera round instead: must NOT count", [("cam.look_at(Vector3(1, 1, 0))", "")], None),
]
ok = True
for name, patches, expect in CASES:
    s = SRC
    for a, b in patches:
        assert a in s or name.startswith("F3 'fixed'"), f"patch target missing: {a[:50]}"
        s = s.replace(a, b)
    with tempfile.TemporaryDirectory() as t:
        t = Path(t) / "p"
        shutil.copytree(ROOT, t, ignore=shutil.ignore_patterns(".godot", "tests", "docs", "probe", ".git", "experiment"))
        (t / "buggy" / "spawner.gd").write_text(s)
        if name.startswith("F3 'fixed'"):  # camera turned to look backwards: F3 props in view, everything else out
            c = (t / "common" / "dungeon.gd").read_text().replace("cam.look_at(Vector3(1, 1, 0))", "cam.look_at(Vector3(1, 1, 14))")
            (t / "common" / "dungeon.gd").write_text(c)
        r = score(t, "res://buggy/main.tscn")
    got = tuple(int(v) for v in r["faults_fixed"].values())
    if expect is None:
        expect = (0, 0, 0)
    good = got == expect
    ok &= good
    print(("PASS " if good else "FAIL ") + name.ljust(66) + f" got F1,F2,F3 = {got}  expected {expect}  all_in_frustum={r['all_in_frustum']}")
sys.exit(0 if ok else 1)
