extends Node
## Render a scene for a few frames and save the viewport as a PNG. Needs a renderer, so run it
## under xvfb with the Compatibility renderer (software GL is fine, no GPU needed):
##
##   xvfb-run -a -s "-screen 0 1280x720x24" godot --rendering-driver opengl3 --path <project> \
##       res://tools/shot.tscn -- <scene.tscn> <out.png>
##
## Verdict: works with Mesa software GL on this machine.

func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	get_tree().create_timer(60.0).timeout.connect(func(): printerr("SHOT_TIMEOUT"); get_tree().quit(3))
	await get_tree().process_frame
	var target: Node = (load(args[0]) as PackedScene).instantiate()
	get_tree().root.add_child(target)
	get_tree().current_scene = target
	for i in 6:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(args[1])
	print("SHOT_SAVED ", args[1], " ", img.get_size())
	get_tree().quit(0)
