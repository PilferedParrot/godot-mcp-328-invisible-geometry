#!/usr/bin/env python3
"""Build one neutral workspace for one trial.

  python3 experiment/make_arena.py <dest_dir> <with|without>

The workspace holds the buggy dungeon under neutral file names (nothing says buggy, control,
fault or #328), the same tools for both arms (a headless godot_exec stand-in and a screenshot
helper), and, for the WITH arm only, the recipe and the audit script.
"""
import shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
dest, arm = Path(sys.argv[1]), sys.argv[2]
assert arm in ("with", "without")
assert not dest.exists(), f"{dest} exists"
(dest / "tools").mkdir(parents=True)

(dest / "project.godot").write_text('''; Engine configuration file.
config_version=5

[application]

config/name="dungeon"
run/main_scene="res://main.tscn"
config/features=PackedStringArray("4.6", "GL Compatibility")

[display]

window/size/viewport_width=1280
window/size/viewport_height=720

[rendering]

renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
''')

d = (ROOT / "common" / "dungeon.gd").read_text()
d = d.replace("## Shared scaffolding for the #328 fixtures. Primitives only; no external assets.",
              "## Scene scaffolding. Primitives only; no external assets.")
(dest / "dungeon.gd").write_text(d)
s = (ROOT / "buggy" / "spawner.gd").read_text().replace("res://common/dungeon.gd", "res://dungeon.gd")
(dest / "spawner.gd").write_text(s)
m = (ROOT / "buggy" / "main.tscn").read_text().replace("res://buggy/spawner.gd", "res://spawner.gd")
(dest / "main.tscn").write_text(m)
for f in ("runner.gd", "runner.tscn", "shot.gd", "shot.tscn"):
    shutil.copy(ROOT / "tools" / f, dest / "tools" / f)
if arm == "with":
    (dest / "recipe").mkdir()
    shutil.copy(ROOT / "recipe" / "RECIPE.md", dest / "recipe" / "RECIPE.md")
    shutil.copy(ROOT / "recipe" / "runtime_audit.body.txt", dest / "recipe" / "runtime_audit.body.txt")
print(f"arena ready: {dest} ({arm})")
