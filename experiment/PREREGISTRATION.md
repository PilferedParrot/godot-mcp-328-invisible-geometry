# Pre-registration: does a diagnostic recipe help an AI find "renders nothing, logs nothing" geometry bugs?

Written 2026-10-07T11:59:16-05:00, **before any trial agent was run**. Committed to the project's local git history at that time; the commit hash is the timestamp of record.

Written by Claude Sonnet 5.5 (self-reported; orchestrating session), for Pilfered Parrot Global Industries.

## Question

godot-mcp issue #328 asks whether a new tool is needed to catch geometry that is buried, stranded at the world origin, or outside the camera. Its author notes that the decisive check was "one cheap query away" and that a guidance nudge might capture most of the value. This pilot asks the narrow version: **given only the user's symptom, does an AI find and fix the root causes more often, or with less effort, when its guidance includes the diagnostic recipe?**

## Design

- **Subject scene:** `buggy/` (workspace copy built by `experiment/make_arena.py`). Three planted faults, nine props, all on a GridMap floor:
  - **F1 buried** (4 props): placed at an assumed ground height of 0 while the floor surface is at y=1.05 (`GridMap`, 2 m cells, `cell_center_y` at its default of true).
  - **F2 origin** (3 props): `global_position.y = ...` assigned before `add_child()`; the read half returns zero, so the prop lands at x=0, z=0.
  - **F3 behind the camera** (2 props): offset along `+basis.z` instead of `-basis.z`.
- **Arms** (same scene, same tools, same prompt except one block):
  - **WITHOUT:** the user's symptom only, plus a headless game runner, a screenshot helper and a godot_exec stand-in (a GDScript-body runner).
  - **WITH:** the same, plus `recipe/RECIPE.md` (inline in the prompt) and `recipe/runtime_audit.body.txt` (in the workspace).
- **Agents:** fresh `general-purpose` subagents, model **`sonnet`** (Claude Sonnet 5.5 as launched; each agent self-reports its model id), no memory of this project, all tools available, one workspace each, neutral file names.
- **n = 4 per arm (8 runs total)**, in two waves of 2 WITH + 2 WITHOUT. Assignment shuffled with seed 328 (`experiment/assignment.json`). Wave 2 runs regardless of wave 1's result. **No runs beyond these 8.**
- **Budget per agent:** at most 40 tool calls (stated in the prompt, not enforced by the harness; actual use is recorded).
- **Prompt:** `experiment/render_prompt.py` (sha256 848ba8d59dde92df…). The exact text each agent received is saved beside its result.

## Outcomes (fixed in advance)

- **Primary — full success:** the scorer reports all three faults fixed **and** the report names all three root causes (rubric below).
- **Secondary:** faults fixed, 0 to 3 (scorer); root causes named, 0 to 3 (rubric); tool calls used; tokens and wall time as reported by the harness.
- **Scorer** (`experiment/score.py`, sha256 894ac6564c22c322…): outcome-based, independent of the recipe's instruments (floor top from the GridMap API, not a raycast; visibility from `Camera3D.is_position_in_frustum`, not the plane test), against intended positions derived from the control scene (`experiment/answer_key.json`, 6bf52a0057e902d7…). Validated on eight known partial and wrong fixes before any trial (`experiment/validate_scorer.py`, 8/8).
- **Root-cause rubric** (I read each report; a cause is "named" only if the report says it explicitly):
  - **RC1:** props were placed using a ground height of 0 while the floor surface is at about 1.05 (floor/cell geometry), i.e. the floor height was assumed, not read.
  - **RC2:** a transform (`global_position`, read or written, including a component write) was used on a node before it was in the tree, so the prop collapses to the origin.
  - **RC3:** the forward direction was taken with the wrong sign (`+basis.z`), so the props are behind the camera.
  Naming without a working fix, and fixing without naming, are both recorded separately.

## Predictions (written before running)

1. **Ceiling effect likely.** The scene is about 100 lines of GDScript and the console prints the F2 backtrace, so a capable model can find all three by reading the code and running the game. I expect WITHOUT to full-succeed in **2 to 4 of 4** and WITH in **3 to 4 of 4**; a difference of one run either way I will treat as noise.
2. **Effort is where I expect the gap:** median tool calls WITH lower than WITHOUT.
3. **F2 found in at least 3 of 4 runs in both arms** (the console backtrace names the line).
4. **F1 is the fault most often missed WITHOUT** (nothing in the console points at it; the floor height has to be read, not assumed).
5. **Rails I expect to hold** (a failure here invalidates the comparison): the audit reports zero findings on the control scene (measured: tests/run_tests.py); each arm gets identical tools and prompt apart from the recipe; the scorer separates partial from full fixes (measured).

## Exclusions and stopping

- A run is **excluded from the primary tally, and listed**, if the agent read or wrote outside its workspace (checked from the agent transcript where available), or the harness failed through no fault of the agent (crash, tool outage). An excluded run is re-run once with a fresh workspace and counted as run 9, 10...; both are reported.
- A run that hits the 40-call limit without a report is scored as it stands (the files are scored whatever the report says).
- No outcome or prompt changes after the first agent starts. If something in the design turns out wrong, the runs are reported as run and the flaw is stated.

## Analysis plan

Counts per arm and per fault, with n. No significance tests (n = 4 per arm cannot support them); any difference of one run is within noise and will be described that way. No claims beyond this scene, this model, this recipe.

## Known limits, stated before the data

- **The treatment was written with knowledge of the faults.** The recipe's categories mirror the three failure modes in #328, and the audit's messages name their likely causes. A WITH advantage therefore shows the recipe helps when it already names the right classes; it does not show it would catch an unforeseen fault.
- **The WITH arm bundles two things:** the written nudge and the runnable script. This pilot cannot separate them.
- **Agents did not use godot-mcp itself** (it needs a live editor and addon). They used a headless stand-in with godot_exec's wrapper and denylist, plus Bash and file tools. This tests guidance, not the toolkit's tool surface.
- **The agents had unrestricted filesystem access** and were told to stay in their workspace; nothing sandboxes them.
- One model family, one scene, tiny n.

## Treatment files (sha256, first 16 hex)

| File | sha256 |
|---|---|
| recipe/RECIPE.md | 75c3c715523cf297 |
| recipe/runtime_audit.body.txt | 416769a5df0df50e |
| buggy/spawner.gd | e86e396c5664225e |
| common/dungeon.gd | 9b9922e17fdb946a |
