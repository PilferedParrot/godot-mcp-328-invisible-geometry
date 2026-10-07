#!/usr/bin/env python3
"""Print the exact prompt a trial agent receives.  python3 experiment/render_prompt.py <with|without> <workspace_dir>
Both arms get the same text; the WITH arm additionally gets the recipe (inline, and as files in its workspace)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
arm, d = sys.argv[1], sys.argv[2]
import os
G = os.environ.get("GODOT", "/home/USER/.local/bin/Godot_v4.6.1-stable_linux.x86_64")

text = f'''You are helping with a small Godot 4.6 game project at {d}. Work only inside that directory (screenshots go under {d}/shots); do not read or write anywhere else.

The user's report, verbatim: "The props don't show up."

Fix the project so the props show up, each resting on the floor where it is meant to be and visible from the player camera. Then report.

What you have:
- Godot 4.6.1 at {G}. Run it headless, always under a timeout, for example: timeout 60 {G} --headless --path {d} --quit-after 120   (--quit-after N stops after N frames; it runs res://main.tscn).
- A screenshot helper (software GL, no GPU needed). Create {d}/shots first, then: timeout 100 xvfb-run -a -s "-screen 0 1280x720x24" {G} --rendering-driver opengl3 --path {d} res://tools/shot.tscn -- res://main.tscn {d}/shots/a.png   and look at the PNG with the Read tool.
- A stand-in for godot-mcp's godot_exec, for inspecting the running scene: write a GDScript function body to a file and run: timeout 90 {G} --headless --path {d} res://tools/runner.tscn -- res://main.tscn <body-file>   `tree` (SceneTree) and `root` (Window) are in scope; no `await`; end the body with `return` of a String (use JSON.stringify for structure). The line starting EXEC_RESULT is its output.
'''
if arm == "with":
    text += f'''- Guidance for this kind of problem (also at {d}/recipe/RECIPE.md, with the script it describes at {d}/recipe/runtime_audit.body.txt):

-----
{(ROOT / "recipe" / "RECIPE.md").read_text().rstrip()}
-----
'''
text += '''
Limits: at most 40 tool calls; stop earlier if you are done. You may refuse, ask for clarification, or stop and escalate to the user if something looks wrong; say so in the report instead of guessing.

Finish with exactly this report:
ROOT CAUSES: every distinct root cause you found, one per line (what was wrong, and why it produced the symptom)
CHANGES: file and line, what you changed
VERIFICATION: what you ran after the change and what it showed
MODEL: your model id, self-reported
TOOL_CALLS: how many tool calls you used
'''
print(text)
