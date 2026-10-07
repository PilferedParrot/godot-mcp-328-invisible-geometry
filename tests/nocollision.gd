extends "res://buggy/spawner.gd"
## The buggy scene on a floor with NO collision shapes. The surface test cannot work here and
## must say so (NO_COLLIDERS note) instead of reporting every prop as unsupported.


func build_floor() -> void:
	super()
	floor_grid.mesh_library.set_item_shapes(0, [])
