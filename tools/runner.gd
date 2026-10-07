extends Node
## Headless stand-in for godot-mcp's `godot_exec`: load a scene, let it run a few
## frames, compile a GDScript *function body* the way godot_exec does, run it, and
## print what it returned.
##
##   godot --headless --path <project> res://tools/runner.tscn -- <scene.tscn> <body.txt>
##
## `tree` (SceneTree) and `root` (Window) are in scope inside the body, exactly as in
## godot_exec; the body must be synchronous (no `await`) and avoid the exec denylist.
## The wrapper and the scan below mirror godot-mcp's mcp_exec_guard.gd (v4.1.x), so a
## body that runs here is accepted by godot_exec. The one line you want is the one
## starting EXEC_RESULT.
##
## Verdict: works; the headless stand-in used by the tests.

const DENY := ["await", "OS.execute", "OS.execute_with_pipe", "OS.create_process", "OS.create_instance",
	"OS.kill", "OS.shell_open", "OS.shell_show_in_file_manager", "OS.move_to_trash", "DirAccess",
	"FileAccess.WRITE", "FileAccess.READ_WRITE", "FileAccess.WRITE_READ", "ResourceSaver",
	"ProjectSettings.save", "ProjectSettings.save_custom", "EditorInterface"]
const WARN_IGNORES := "@warning_ignore(\"unused_parameter\", \"shadowed_global_identifier\", \"shadowed_variable\", \"shadowed_variable_base_class\", \"standalone_expression\", \"return_value_discarded\", \"unused_variable\", \"unreachable_code\", \"integer_division\")"


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() < 2:
		printerr("usage: runner.tscn -- <scene.tscn> <body.txt>")
		get_tree().quit(64)
		return
	get_tree().create_timer(45.0).timeout.connect(func(): printerr("RUNNER_TIMEOUT"); get_tree().quit(3))

	var body := FileAccess.get_file_as_string(args[1])
	var scan := _scan(body)
	if scan != "":
		print("EXEC_REFUSED ", scan)
		get_tree().quit(2)
		return

	await get_tree().process_frame  # the parent is busy during _ready; wait before adding the scene
	# The headless display server gives the root window 64x64 (aspect 1:1), which narrows the
	# horizontal FOV. Use the project's configured size so the frustum matches a real window.
	get_tree().root.size = Vector2i(int(ProjectSettings.get_setting("display/window/size/viewport_width")),
		int(ProjectSettings.get_setting("display/window/size/viewport_height")))
	var target: Node = (load(args[0]) as PackedScene).instantiate()
	get_tree().root.add_child(target)
	get_tree().current_scene = target
	for i in 3:
		await get_tree().physics_frame
	for i in 2:
		await get_tree().process_frame

	var lines: PackedStringArray = []
	for line in body.replace("\r\n", "\n").split("\n"):
		lines.append(line if line.strip_edges().is_empty() else "\t" + line)
	var src := "extends RefCounted\n\n%s\nfunc _mcp_run(tree, root):\n%s\n" % [WARN_IGNORES, "\n".join(lines)]
	var gds := GDScript.new()
	gds.source_code = src
	if gds.reload() != OK:
		print("EXEC_COMPILE_ERROR")
		get_tree().quit(2)
		return
	var result = gds.new()._mcp_run(get_tree(), get_tree().root)
	print("EXEC_RESULT ", result)
	get_tree().quit(0)


func _scan(body: String) -> String:
	var no_comments := RegEx.create_from_string("#[^\\n]*").sub(body, "", true)
	for token in DENY:
		if RegEx.create_from_string("\\b" + token.replace(".", "\\.") + "\\b").search(no_comments) != null:
			return token
	return ""
