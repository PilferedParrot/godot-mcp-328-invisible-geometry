extends "res://common/dungeon.gd"
## Legitimate-but-unusual placements. Nothing here is a bug; the audit is expected to
## raise some of it anyway (see README "Known false positives"). Used to measure
## the audit's limits, not as a control.


func _ready() -> void:
	build_floor()
	build_camera()
	build_decor()
	# Ordinary, correctly seated props (they are the "placed siblings").
	for spec in [["Rubble", Vector2(-3.0, 1.0)], ["Fungus", Vector2(3.0, 2.0)], ["Bucket", Vector2(4.0, 0.0)]]:
		var prop := make_prop(spec[0])
		prop.position = Vector3(spec[1].x, surface_y(spec[1]) + half_height(prop), spec[1].y)
		decor.add_child(prop)
	# 1. Deliberately at the world origin: a well-head the level is built around.
	var well := make_prop("Chest")
	well.name = "WellHead"
	well.position = Vector3(0.0, surface_y(Vector2.ZERO) + half_height(well), 0.0)
	decor.add_child(well)
	# 2. A 1.2 m fence post set 0.3 m into the ground on purpose.
	var post := make_prop("Candle")
	post.name = "FencePost"
	(post.mesh as CylinderMesh).height = 1.2
	post.position = Vector3(-2.0, surface_y(Vector2(-2.0, 2.5)) + half_height(post) - 0.3, 2.5)
	decor.add_child(post)
	# 3. A lamp hanging 1.5 m above the floor on purpose.
	var lamp := make_prop("Lantern")
	lamp.name = "HangingLamp"
	lamp.position = Vector3(2.0, surface_y(Vector2(2.0, 3.0)) + 1.5, 3.0)
	decor.add_child(lamp)
	# 4. A banner behind the player on purpose (never meant to be in frame).
	var banner := make_prop("Skull")
	banner.name = "RearBanner"
	var p := cam.global_position + cam.global_basis.z * 4.0
	banner.position = Vector3(p.x, surface_y(Vector2(p.x, p.z)) + half_height(banner), p.z)
	decor.add_child(banner)
