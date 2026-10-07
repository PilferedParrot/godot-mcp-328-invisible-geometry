#!/usr/bin/env python3
"""Run godot-mcp's REAL exec guard (scan + function-body wrapper) over our two audit bodies.

Fetches godot/addons/godot_mcp/game_bridge/mcp_exec_guard.gd at the pinned release tag into tests/tmp/
(MIT-licensed upstream file; NOT committed here), loads it under the local Godot, and checks that
scan_source() accepts each body and that build_wrapper() output compiles. Needs network (gh CLI or curl).

  python3 tests/exec_guard_check.py

Verdict: both bodies accepted and compiled by the upstream guard at godot-mcp-v4.1.11 on Godot 4.6.1.
It does not run godot-mcp itself (no editor, no addon, no MCP server): it checks the guard's
acceptance and compilation only.
"""
import hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GODOT = os.environ.get("GODOT", str(Path.home() / ".local/bin/Godot_v4.6.1-stable_linux.x86_64"))
TAG = "godot-mcp-v4.1.11"
URL = f"https://raw.githubusercontent.com/satelliteoflove/godot-mcp/{TAG}/godot/addons/godot_mcp/game_bridge/mcp_exec_guard.gd"
tmp = ROOT / "tests" / "tmp"
tmp.mkdir(exist_ok=True)
guard = tmp / "mcp_exec_guard.gd"
if not guard.exists():
    subprocess.run(["curl", "-fsSL", "-o", str(guard), URL], check=True)
print("guard sha256:", hashlib.sha256(guard.read_bytes()).hexdigest()[:16], "from", TAG)
for name in ("runtime_audit", "naive_audit"):
    shutil.copy(ROOT / "recipe" / f"{name}.body.txt", tmp / f"{name}.body.txt")

(tmp / "guard_check.gd").write_text('''extends SceneTree
func _initialize() -> void:
	var G = load("res://tests/tmp/mcp_exec_guard.gd")
	var out := {}
	for nm in ["runtime_audit", "naive_audit", "bad_await", "bad_exec"]:
		var src := ""
		if nm == "bad_await": src = "await tree.process_frame\\nreturn 1"
		elif nm == "bad_exec": src = "OS.execute('true', [])\\nreturn 1"
		else: src = FileAccess.get_file_as_string("res://tests/tmp/%s.body.txt" % nm)
		var scan: Dictionary = G.scan_source(src)
		var compiled := false
		if scan.get("ok", false):
			var s := GDScript.new()
			s.source_code = G.build_wrapper(src, PackedStringArray(["tree", "root"]))
			compiled = s.reload() == OK
		out[nm] = {"accepted": scan.get("ok", false), "compiled": compiled, "token": scan.get("token", "")}
	print("GUARD ", JSON.stringify(out))
	quit()
''')
p = subprocess.run(["timeout", "60", GODOT, "--headless", "--path", str(ROOT), "--script", "res://tests/tmp/guard_check.gd"],
                   capture_output=True, text=True)
m = re.search(r"^GUARD (.*)$", p.stdout + p.stderr, re.M)
if not m:
    print((p.stdout + p.stderr)[-1500:]); sys.exit(2)
r = json.loads(m.group(1))
for k, v in r.items():
    print(k.ljust(14), v)
ok = (r["runtime_audit"]["accepted"] and r["runtime_audit"]["compiled"] and r["naive_audit"]["accepted"] and r["naive_audit"]["compiled"]
      and not r["bad_await"]["accepted"] and r["bad_await"]["token"] == "await"
      and not r["bad_exec"]["accepted"] and r["bad_exec"]["token"] == "OS.execute")
print("PASS" if ok else "FAIL", "upstream exec guard accepts and compiles both bodies, and refuses await / OS.execute")
sys.exit(0 if ok else 1)
