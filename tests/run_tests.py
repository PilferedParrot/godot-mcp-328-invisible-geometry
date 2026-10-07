#!/usr/bin/env python3
"""Tests for the #328 audit recipe. Run from anywhere:  python3 tests/run_tests.py

Every assertion is about a *set of (node, code) findings*, compared for exact equality, so a
missed fault and a false positive both turn a test red. Besides the audit itself the suite runs
  - the plausible-but-wrong NAIVE check (expected: blind to every fault),
  - three MUTANTS of the audit, each breaking exactly one check (expected: that fault goes
    undetected, the others stay detected), so a green result means the check is load-bearing,
  - the exec-compat guard and the empty-scene verdict.

Needs Godot 4.6.x. Override the binary with GODOT=/path/to/godot.
Verdict: passes on Godot 4.6.1 (see README for the recorded run).
"""
import json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GODOT = os.environ.get("GODOT", str(Path.home() / ".local/bin/Godot_v4.6.1-stable_linux.x86_64"))
TMP = ROOT / "tests" / "tmp"
TMP.mkdir(exist_ok=True)
BODY = (ROOT / "recipe" / "runtime_audit.body.txt").read_text()
NAIVE = (ROOT / "recipe" / "naive_audit.body.txt").read_text()

F1 = {f"Decor/{n}": "BURIED" for n in ("Rubble", "Fungus", "Bones", "Puddle")}
F2 = {f"Decor/{n}": "ORIGIN" for n in ("Skull", "Candle", "Bucket")}
F3 = {f"Decor/{n}": "NOT_IN_FRUSTUM" for n in ("Lantern", "Chest")}
BUGGY = {**F1, **F2, **F3}
HAZARDS = {"Decor/FencePost": "SUNK", "Decor/HangingLamp": "FLOATING",
           "Decor/RearBanner": "NOT_IN_FRUSTUM", "Decor/WellHead": "ORIGIN"}


def run(scene, body, name="body"):
    f = TMP / f"{name}.txt"
    f.write_text(body)
    p = subprocess.run(["timeout", "90", GODOT, "--headless", "--path", str(ROOT), "res://tools/runner.tscn",
                        "--", scene, f"res://tests/tmp/{name}.txt"], capture_output=True, text=True)
    out = p.stdout + p.stderr
    m = re.search(r"^EXEC_(RESULT|REFUSED|COMPILE_ERROR)(.*)$", out, re.M)
    if not m:
        raise RuntimeError(f"no EXEC line for {scene} / {name}:\n{out[-1500:]}")
    return m.group(1), m.group(2).strip(), out


def findings(scene, body, name="body"):
    kind, payload, _ = run(scene, body, name)
    assert kind == "RESULT", f"{kind} {payload}"
    d = json.loads(payload)
    got = {}
    for f in d["findings"]:
        key = f["node"]
        assert key not in got or True
        got.setdefault(key, set()).add(f["code"])
    return d, {k: sorted(v) for k, v in got.items()}


def as_single(d):  # {node: [code]} -> {node: code}, requiring one code per node here
    return {k: v[0] for k, v in d.items()}


def mutant_surface(body):
    """M1: 'assume the floor is at y=0' instead of asking the world for the surface."""
    a, b = body.index("	# 2. seated on a surface?"), body.index("	# 3. inside the active camera's frustum?")
    patch = ('	# 2. (mutant) assume the ground is at y = 0\n'
             '	if wb.end.y < 0.0:\n'
             '		add.call("BURIED", "error", g, wb, "mutant: below y=0")\n\n')
    return body[:a] + patch + body[b:]


def mutant_origin(body):
    """M2: exact-zero comparison on the whole position instead of the x,z column."""
    old = "if absf(gp.x) < cfg.origin_eps and absf(gp.z) < cfg.origin_eps:"
    assert old in body
    return body.replace(old, "if gp == Vector3.ZERO:")


def mutant_frustum(body):
    """M3: 'is it within the camera's far distance?' instead of the frustum planes."""
    a = body.index("		for k in planes.size():")
    b = body.index("if colliders_seen == 0")
    patch = ('		if wb.get_center().distance_to(cam.global_position) > cam.far:\n'
             '			add.call("NOT_IN_FRUSTUM", "info", g, wb, "mutant: beyond far")\n\n')
    return body[:a] + patch + body[b:]


results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (("   " + detail) if (detail and not cond) else ""))


# 1. control: zero findings of any severity
d, got = findings("res://control/main.tscn", BODY, "t1")
check("control: audit CLEAN, 9 nodes audited, 0 findings", d["verdict"] == "CLEAN" and d["audited"] == 9 and not got, str(got))
check("control: audit ran at the project's 1280x720 viewport", d["camera"]["viewport"] == [1280.0, 720.0], str(d["camera"]))

# 2. buggy: exactly the planted faults
d, got = findings("res://buggy/main.tscn", BODY, "t2")
check("buggy: exactly the 9 planted findings (4 BURIED, 3 ORIGIN, 2 NOT_IN_FRUSTUM), no extras",
      as_single(got) == BUGGY, f"got {got}")

# 3. hazards: the limits, recorded
d, got = findings("res://hazards/main.tscn", BODY, "t3")
check("hazards: findings are exactly the 4 recorded (1 is a KNOWN false positive: WellHead)",
      as_single(got) == HAZARDS, f"got {got}")

# 4. the naive check must be blind to every fault, and quiet on control
d, got = findings("res://buggy/main.tscn", NAIVE, "t4")
check("naive check on buggy: reports NOTHING (blind to all 9 faulty props)", d["verdict"] == "CLEAN" and not got, str(got))

# 5. mutants: each loses exactly its own fault group
for label, mut, lost in (("M1 floor-at-y=0", mutant_surface, F1), ("M2 exact-zero origin", mutant_origin, F2),
                         ("M3 within-far-distance", mutant_frustum, F3)):
    d, got = findings("res://buggy/main.tscn", mut(BODY), "t5")
    want = {k: v for k, v in BUGGY.items() if k not in lost}
    check(f"mutant {label} on buggy: loses exactly its fault group ({len(lost)} nodes), keeps the other {len(want)}",
          as_single(got) == want, f"got {got}")
    d, got = findings("res://control/main.tscn", mut(BODY), "t5c")
    check(f"mutant {label} on control: still quiet (it is plausible, not simply broken)", not got, str(got))

# 6. exec-compat guard and empty scene
kind, payload, _ = run("res://control/main.tscn", "await tree.process_frame\nreturn 1", "t6a")
check("runner refuses a body containing await (as godot_exec does)", kind == "REFUSED" and payload == "await", f"{kind} {payload}")
kind, payload, _ = run("res://control/main.tscn", 'OS.execute("true", [])\nreturn 1', "t6b")
check("runner refuses OS.execute (godot_exec denylist)", kind == "REFUSED" and payload == "OS.execute", f"{kind} {payload}")
d, got = findings("res://tests/empty.tscn", BODY, "t6c")
check("empty scene: verdict NOTHING_AUDITED, not CLEAN", d["verdict"] == "NOTHING_AUDITED" and d["audited"] == 0, d["verdict"])

# 6b. audit limits that must be stated, not discovered: no collision on the floor; nodes with their own collider
d, got = findings("res://tests/nocollision.tscn", BODY, "t6d")
check("floor without collision: says NO_COLLIDERS, reports no UNSUPPORTED, still finds ORIGIN and NOT_IN_FRUSTUM",
      any("NO_COLLIDERS" in n for n in d["notes"]) and as_single(got) == {**F2, **F3}, f"notes={d['notes']} got={got}")
d, got = findings("res://tests/ownbody.tscn", BODY, "t6e")
check("nodes with their own collider are skipped and counted; a BURIED body is a known blind spot (not flagged)",
      not got and any("2 nodes carry their own collider" in n for n in d["notes"]), f"notes={d['notes']} got={got}")

# 7. engine facts the README states (measured on the Godot that runs the suite)
p = subprocess.run(["timeout", "60", GODOT, "--headless", "--path", str(ROOT), "res://tests/engine_facts.tscn"],
                   capture_output=True, text=True)
out = p.stdout + p.stderr
m = re.search(r"^FACTS (.*)$", out, re.M)
facts = json.loads(m.group(1)) if m else {}
check("engine facts: test ran", bool(facts), out[-600:])
check("engine facts: a pre-add_child() write logs Condition \"!is_inside_tree()\"", 'Condition "!is_inside_tree()" is true' in out)
check("engine facts: whole-vector write before add_child() lands correctly under an identity parent",
      facts.get("pre_add_whole_global_under_identity_parent") == [3.0, 1.0, -4.0])
check("engine facts: ...but is stored as the LOCAL value, so a transformed parent displaces it (not to the origin)",
      facts.get("pre_add_whole_local_after_write") == [3.0, 1.0, -4.0]
      and facts.get("pre_add_whole_global_under_offset_parent") not in ([3.0, 1.0, -4.0], [0.0, 0.0, 0.0]))
check("engine facts: ...and it resets rotation and scale to identity",
      facts.get("pre_add_whole_rotation_y_after") == 0.0 and facts.get("pre_add_whole_scale_after") == [1.0, 1.0, 1.0])
check("engine facts: a component write or += before add_child() lands at x=0, z=0 (the origin column)",
      facts.get("pre_add_component_y_global") == [0.0, 1.05, 0.0] and facts.get("pre_add_compound_global") == [0.0, 1.05, 0.0])
check("engine facts: the same write after add_child() is correct",
      facts.get("post_add_global_under_offset_parent") == [3.0, 1.0, -4.0])
check("engine facts: GridMap cell_center_y defaults to true and a 2 m cell with a 0.1 m slab puts the surface at y=1.05",
      facts.get("gridmap_default_cell_center_y") is True and facts.get("gridmap_slab_top_y") == 1.05)
check("engine facts: ray semantics (above: hit y 1.05 n=+y; inside: zero normal; below slab: down misses, up hits underside y 0.95 n=-y)",
      facts.get("ray_from_above_hit_y") == 1.05 and facts.get("ray_from_above_normal_y") == 1.0
      and facts.get("ray_from_inside_normal_is_zero") is True and facts.get("ray_down_from_below_slab_hits") is False
      and facts.get("ray_up_from_below_slab_hit_y") == 0.95 and facts.get("ray_up_from_below_slab_normal_y") == -1.0)
check("engine facts: frustum planes point outward (inside = negative distance) and agree with is_position_in_frustum",
      facts.get("frustum_inside_point_negative_on_all_planes") is True and facts.get("frustum_inside_point_in_frustum") is True
      and facts.get("frustum_behind_point_in_frustum") is False)

failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
