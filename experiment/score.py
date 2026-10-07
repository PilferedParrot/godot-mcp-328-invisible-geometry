#!/usr/bin/env python3
"""Score a finished workspace by OUTCOME, with an instrument independent of the recipe.

  python3 experiment/score.py <project_dir> [--scene res://main.tscn]

Copies the project to a temp dir, overwrites tools/runner.* with the pristine copies (so an agent
that edited its runner cannot affect the score), runs experiment/dump_body.txt, and compares each
prop against experiment/answer_key.json (intended world x,z, derived from the control scene):

  F1 buried        : Rubble Fungus Bones Puddle          at intended x,z AND seated on the floor top
  F2 origin        : Skull Candle Bucket                 at intended x,z AND seated on the floor top
  F3 behind camera : Lantern Chest                       at intended x,z AND seated AND in the frustum

"Seated" = AABB bottom within 0.03 m of the floor top read from the GridMap API (no raycast).
"At intended x,z" = within 0.05 m. In frustum = Camera3D.is_position_in_frustum(AABB centre).
A fault counts as fixed only if every prop in its group passes. Also reported: whether all nine
props exist and are all in the frustum (collateral damage check).
Verdict: validated on known partial and wrong fixes by experiment/validate_scorer.py.
"""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GODOT = os.environ.get("GODOT", str(Path.home() / ".local/bin/Godot_v4.6.1-stable_linux.x86_64"))
KEY = json.loads((HERE / "answer_key.json").read_text())
GROUPS = {"F1_buried": ["Rubble", "Fungus", "Bones", "Puddle"],
          "F2_origin": ["Skull", "Candle", "Bucket"],
          "F3_behind_camera": ["Lantern", "Chest"]}
XZ_TOL, SEAT_TOL = 0.05, 0.03


def measure(project: Path, scene: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="score_") as t:
        t = Path(t) / "p"
        shutil.copytree(project, t, ignore=shutil.ignore_patterns(".godot", "shots", ".git"))
        (t / "tools").mkdir(exist_ok=True)
        for f in ("runner.gd", "runner.tscn"):
            shutil.copy(ROOT / "tools" / f, t / "tools" / f)
        shutil.copy(HERE / "dump_body.txt", t / "_dump_body.txt")
        p = subprocess.run(["timeout", "90", GODOT, "--headless", "--path", str(t), "res://tools/runner.tscn", "--",
                            scene, "res://_dump_body.txt"], capture_output=True, text=True)
    m = re.search(r"^EXEC_RESULT (.*)$", p.stdout + p.stderr, re.M)
    if not m:
        return {"error": "no EXEC_RESULT", "tail": (p.stdout + p.stderr)[-800:]}
    return json.loads(m.group(1))


def score(project: Path, scene: str = "res://main.tscn") -> dict:
    d = measure(project, scene)
    if "error" in d:
        return d
    per = {}
    for name, key in KEY.items():
        v = d.get(name)
        if v is None:
            per[name] = {"present": False}
            continue
        at_spot = abs(v["x"] - key["x"]) <= XZ_TOL and abs(v["z"] - key["z"]) <= XZ_TOL
        seated = v["floor_top"] is not None and abs(v["bottom"] - v["floor_top"]) <= SEAT_TOL
        per[name] = {"present": True, "at_intended_xz": at_spot, "seated": seated, "in_frustum": bool(v["in_frustum"]),
                     "x": round(v["x"], 3), "z": round(v["z"], 3), "bottom": round(v["bottom"], 3),
                     "floor_top": None if v["floor_top"] is None else round(v["floor_top"], 3)}
    fixed = {}
    for g, names in GROUPS.items():
        ok = True
        for n in names:
            r = per[n]
            ok &= r["present"] and r["at_intended_xz"] and r["seated"] and (r["in_frustum"] if g == "F3_behind_camera" else True)
        fixed[g] = bool(ok)
    return {"faults_fixed": fixed, "n_fixed": sum(fixed.values()), "all_present": all(per[n]["present"] for n in per),
            "all_in_frustum": all(per[n]["present"] and per[n]["in_frustum"] for n in per), "props": per}


if __name__ == "__main__":
    scene = sys.argv[sys.argv.index("--scene") + 1] if "--scene" in sys.argv else "res://main.tscn"
    print(json.dumps(score(Path(sys.argv[1]), scene), indent=1))
