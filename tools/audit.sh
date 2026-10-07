#!/usr/bin/env bash
# Run an audit body on one of the scenes and print it readably.
#   tools/audit.sh buggy|control|hazards [recipe/runtime_audit.body.txt | recipe/naive_audit.body.txt]
# Needs Godot 4.6.x (override with GODOT=/path/to/godot) and python3.
# Verdict: works. Prints how many console lines mention the pre-add_child() error, then the findings.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GODOT="${GODOT:-$HOME/.local/bin/Godot_v4.6.1-stable_linux.x86_64}"
SCENE="${1:?usage: tools/audit.sh buggy|control|hazards [body]}"
BODY="${2:-recipe/runtime_audit.body.txt}"
OUT="$(timeout 90 "$GODOT" --headless --path "$ROOT" res://tools/runner.tscn -- "res://$SCENE/main.tscn" "res://$BODY" 2>&1 || true)"
echo "console: $(grep -c 'Condition "!is_inside_tree()"' <<<"$OUT" || true) line(s) mention Condition \"!is_inside_tree()\""
python3 - "$OUT" <<'PY'
import json, re, sys
m = re.search(r"^EXEC_(RESULT|REFUSED|COMPILE_ERROR)(.*)$", sys.argv[1], re.M)
if not m or m.group(1) != "RESULT":
    print("no result:", m.group(0) if m else sys.argv[1][-400:]); sys.exit(1)
d = json.loads(m.group(2))
cam = d.get("camera")
print(f"scene {d.get('scene', '?')}: audited {d['audited']} nodes" + (f", camera {cam['name']} at {cam['position']} looking {cam['looking']}, viewport {cam['viewport']}" if cam else ""))
print("verdict:", d["verdict"], d.get("counts", ""))
for f in d.get("findings", []):
    if "code" in f:
        print(f"  {f['severity']:7s} {f['code']:15s} {f['node']:16s} y {f['aabb_y']}  {f['detail'][:150]}")
    else:
        print("  ", f)
for n in d.get("notes", []):
    print("  note:", n)
PY
