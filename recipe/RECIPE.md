# Recipe: 3D geometry that renders nothing and logs nothing

When a prop, decal or mesh "isn't showing up" and the console is quiet, don't start with
screenshots, or with theories about lights, UI or occlusion. Ask the running scene where the
thing actually is, and compare that with the surface it should rest on and the camera that
should see it. This is the check described in godot-mcp issue #328.

## What to compare

1. **The node's world-space AABB against the surface beneath it.** The AABB is
   `global_transform * get_aabb()`. Ray straight down from its centre; if nothing is below, ray
   straight up. Seated means the AABB bottom sits on the hit. A node with no surface below it and
   one above it is buried.
2. **The node's world position against the world origin.** A node at x=0, z=0 while its siblings
   are elsewhere was placed wrong.
3. **The AABB against the active camera's frustum.** Outside means the node cannot be seen from
   where the camera is. Note which plane it falls outside of.
4. **The game console** for `Condition "!is_inside_tree()"`: a transform was read or written on a
   node that was not in the tree yet.

Compare the numbers with what you *expected*, not with what merely looks plausible.

## How to run it

- With godot-mcp: paste `runtime_audit.body.txt` as the `source` of `godot_exec run` while the
  game is running. It returns one JSON string.
- Without the editor: `godot --headless --path <project> res://tools/runner.tscn -- res://<scene>.tscn res://recipe/runtime_audit.body.txt`
  (the runner wraps and scans the body the way `godot_exec` does). The result is the line that
  starts `EXEC_RESULT`.

## Reading the result

- `findings`: `BURIED` / `UNSUPPORTED` / `INSIDE_COLLIDER` (error), `ORIGIN` (suspect),
  `SUNK` / `FLOATING` (warn), `NOT_IN_FRUSTUM` (info). Each names the node, its world y range and
  what it was compared with. It reports; it never fixes.
- `verdict: CLEAN` only means "nothing found among the nodes audited". Read `audited` and
  `notes`: `NOTHING_AUDITED`, `NO_COLLIDERS` and `NO_ACTIVE_CAMERA` mean part of the check did not
  really run.
- Limits: the surface test needs colliders and skips nodes that carry their own; `ORIGIN` is a
  heuristic and also flags a deliberate origin prop that has placed siblings; `NOT_IN_FRUSTUM` is
  expected for anything behind or beside you, so read it against what you expect to see.
