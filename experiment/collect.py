#!/usr/bin/env python3
"""Record one finished trial into experiment/runs/<trial>/.

  python3 experiment/collect.py <trial> <transcript.jsonl> --tool-uses N --tokens N --ms N --rc 111

Extracts from the agent transcript: its final report (verbatim), the list of tool calls (workspace path
abbreviated to $W), and the paths it touched outside its workspace; runs the scorer on the workspace;
and writes result.json, report.txt, toolcalls.txt, spawner.diff. --rc is my reading of the report against the
pre-registered rubric: three digits, RC1 RC2 RC3, 1 = named explicitly.
Paths are redacted (your home directory -> /home/USER) because this folder may be published.
"""
import argparse, difflib, json, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from score import score

ap = argparse.ArgumentParser()
ap.add_argument("trial"); ap.add_argument("transcript")
ap.add_argument("--tool-uses", type=int, required=True); ap.add_argument("--tokens", type=int, required=True)
ap.add_argument("--ms", type=int, required=True); ap.add_argument("--rc", required=True)
a = ap.parse_args()

t = a.trial
ws = Path.home() / "tmp" / "scene-debug-trials" / t
arm = json.loads((HERE / "assignment.json").read_text())[t]["arm"]
out = HERE / "runs" / t
red = lambda s: re.sub(r"/tmp/claude-[^\s'\"]*?/scratchpad", "<harness scratchpad>", s.replace(str(Path.home()), "/home/USER").replace("-home-" + Path.home().name, "-home-USER"))

calls, report, outside = [], "", []
for line in open(a.transcript):
    try: e = json.loads(line)
    except Exception: continue
    c = (e.get("message") or {}).get("content")
    if not isinstance(c, list): continue
    for b in c:
        if not (isinstance(b, dict) and b.get("type") == "tool_use"): continue
        inp = b["input"]
        if b["name"] == "SubagentHandback":
            report = inp.get("message") or inp.get("report") or inp.get("text") or json.dumps(inp, indent=1)
            continue
        s = inp.get("command") or inp.get("file_path") or json.dumps(inp)
        calls.append((b["name"], s))
        for p in re.findall(r"/home/[A-Za-z0-9_./-]+|/tmp/[A-Za-z0-9_./-]+", json.dumps(inp)):
            p = p.rstrip(".,;:)\\")
            if f"scene-debug-trials/{t}" not in p and "Godot_v4.6.1-stable_linux" not in p:
                outside.append(p)

(out).mkdir(parents=True, exist_ok=True)
(out / "report.txt").write_text(red(report))
(out / "toolcalls.txt").write_text(red("\n".join(
    f"{i+1:2d} {n:5s} " + s.replace(str(ws), "$W").replace("\n", " ⏎ ")[:400] for i, (n, s) in enumerate(calls))) + "\n")
src = (ROOT / "buggy" / "spawner.gd").read_text().replace("res://common/dungeon.gd", "res://dungeon.gd").splitlines(True)
new = (ws / "spawner.gd").read_text().splitlines(True)
(out / "spawner.diff").write_text("".join(difflib.unified_diff(src, new, "spawner.gd (as given)", "spawner.gd (as left)")))
sc = score(ws)
res = {"trial": t, "arm": arm, "model_asked": "sonnet", "model_self_reported": re.findall(r"MODEL:\s*(.*)", report)[:1],
       "faults_fixed": sc["faults_fixed"], "n_fixed": sc["n_fixed"], "all_present": sc["all_present"], "all_in_frustum": sc["all_in_frustum"],
       "root_causes_named": {"RC1": a.rc[0] == "1", "RC2": a.rc[1] == "1", "RC3": a.rc[2] == "1"},
       "n_root_causes_named": sum(ch == "1" for ch in a.rc),
       "full_success": sc["n_fixed"] == 3 and a.rc == "111",
       "harness_tool_uses": a.tool_uses, "harness_tokens": a.tokens, "harness_ms": a.ms,
       "tool_calls_parsed_excluding_handback": len(calls), "tool_calls_self_reported": re.findall(r"TOOL_CALLS:\s*(\d+)", report)[:1],
       "paths_outside_workspace_in_tool_inputs": sorted(set(red(p) for p in outside)),
       "scratchpad_writes": bool(outside)}
(out / "result.json").write_text(json.dumps(res, indent=1) + "\n")
print(json.dumps({k: res[k] for k in ("trial", "arm", "n_fixed", "n_root_causes_named", "full_success", "harness_tool_uses", "harness_tokens")}))
