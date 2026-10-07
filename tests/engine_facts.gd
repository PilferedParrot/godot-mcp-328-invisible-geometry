extends Node3D
## Engine facts the audit and the README rely on, measured on whatever Godot runs this.
## Prints one line starting FACTS followed by JSON; tests/run_tests.py asserts on it.
##
##   godot --headless --path <project> res://tests/engine_facts.tscn
##
## Verdict: all facts hold on Godot 4.6.1.

func _ready() -> void:
	var f := {}
	var ident := Node3D.new()
	ident.name = "IdentityParent"
	add_child(ident)
	var off := Node3D.new()
	off.name = "OffsetParent"
	off.position = Vector3(10, 0, 5)
	off.rotation.y = 0.5
	add_child(off)

	# 1. whole-vector write before add_child()
	var want := Vector3(3, 1, -4)
	var a := MeshInstance3D.new()
	a.global_position = want
	f["pre_add_whole_local_after_write"] = _v(a.position)
	ident.add_child(a)
	f["pre_add_whole_global_under_identity_parent"] = _v(a.global_position)
	var b := MeshInstance3D.new()
	b.global_position = want
	off.add_child(b)
	f["pre_add_whole_global_under_offset_parent"] = _v(b.global_position)
	# ...and it resets rotation and scale
	var c := MeshInstance3D.new()
	c.rotation.y = 1.0
	c.scale = Vector3(2, 2, 2)
	c.global_position = want
	ident.add_child(c)
	f["pre_add_whole_rotation_y_after"] = c.rotation.y
	f["pre_add_whole_scale_after"] = _v(c.scale)
	# 2. component write / compound assignment before add_child()
	var d := MeshInstance3D.new()
	d.position = Vector3(4, 0, -3)
	d.global_position.y = 1.05
	ident.add_child(d)
	f["pre_add_component_y_global"] = _v(d.global_position)
	var e := MeshInstance3D.new()
	e.position = Vector3(4, 0, -3)
	e.global_position += Vector3(0, 1.05, 0)
	ident.add_child(e)
	f["pre_add_compound_global"] = _v(e.global_position)
	# 3. the same write after add_child() is fine
	var g := MeshInstance3D.new()
	off.add_child(g)
	g.global_position = want
	f["post_add_global_under_offset_parent"] = _v(g.global_position)

	# 4. GridMap floor: default cell_center_y and the slab top
	var lib := MeshLibrary.new()
	lib.create_item(0)
	var slab := BoxMesh.new()
	slab.size = Vector3(2, 0.1, 2)
	lib.set_item_mesh(0, slab)
	var shape := BoxShape3D.new()
	shape.size = slab.size
	lib.set_item_shapes(0, [shape, Transform3D.IDENTITY])
	var grid := GridMap.new()
	grid.mesh_library = lib
	grid.cell_size = Vector3(2, 2, 2)
	f["gridmap_default_cell_center_y"] = grid.cell_center_y
	grid.set_cell_item(Vector3i(0, 0, 0), 0)
	add_child(grid)
	f["gridmap_slab_top_y"] = snappedf(grid.map_to_local(Vector3i(0, 0, 0)).y + slab.get_aabb().end.y, 0.001)

	for i in 3:
		await get_tree().physics_frame
	await get_tree().process_frame

	# 5. ray semantics the audit depends on
	var space := get_world_3d().direct_space_state
	var q := PhysicsRayQueryParameters3D.create(Vector3(1, 3, 1), Vector3(1, -5, 1))
	var r := space.intersect_ray(q)
	f["ray_from_above_hit_y"] = snappedf(r.position.y, 0.001)
	f["ray_from_above_normal_y"] = r.normal.y
	q = PhysicsRayQueryParameters3D.create(Vector3(1, 1.0, 1), Vector3(1, -5, 1))
	q.hit_from_inside = true
	r = space.intersect_ray(q)
	f["ray_from_inside_normal_is_zero"] = r.has("normal") and r.normal == Vector3.ZERO
	q = PhysicsRayQueryParameters3D.create(Vector3(1, 0.3, 1), Vector3(1, -5, 1))
	q.hit_from_inside = true
	f["ray_down_from_below_slab_hits"] = not space.intersect_ray(q).is_empty()
	q = PhysicsRayQueryParameters3D.create(Vector3(1, 0.3, 1), Vector3(1, 5, 1))
	q.hit_from_inside = true
	r = space.intersect_ray(q)
	f["ray_up_from_below_slab_hit_y"] = snappedf(r.position.y, 0.001)
	f["ray_up_from_below_slab_normal_y"] = r.normal.y

	# 6. frustum plane orientation: inside points have negative distance to every plane
	var cam := Camera3D.new()
	cam.position = Vector3(1, 4.5, 7)
	add_child(cam)
	cam.look_at(Vector3(1, 1, 0))
	cam.current = true
	await get_tree().process_frame
	var planes := cam.get_frustum()
	var inside := Vector3(1, 1, 0)
	var all_neg := true
	for pl in planes:
		all_neg = all_neg and pl.distance_to(inside) < 0.0
	f["frustum_inside_point_negative_on_all_planes"] = all_neg
	f["frustum_inside_point_in_frustum"] = cam.is_position_in_frustum(inside)
	f["frustum_behind_point_in_frustum"] = cam.is_position_in_frustum(Vector3(1, 6, 14))
	print("FACTS ", JSON.stringify(f))
	get_tree().quit()


func _v(v: Vector3) -> Array:
	return [snappedf(v.x, 0.001), snappedf(v.y, 0.001), snappedf(v.z, 0.001)]
