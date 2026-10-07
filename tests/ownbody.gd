extends "res://control/spawner.gd"
## The control scene plus two props that carry their own StaticBody3D: one seated, one buried.
## The audit skips the surface test for nodes with their own collider (they are usually the surface
## itself), so it must stay quiet about both and say how many it skipped. A buried body is therefore a
## KNOWN BLIND SPOT; this scene pins that down.


func _ready() -> void:
	super()
	for spec in [["SeatedBody", 1.05 + 0.25, -1.0], ["BuriedBody", 0.25, -2.0]]:
		var body := StaticBody3D.new()
		body.name = spec[0]
		body.position = Vector3(-1.0, spec[1], spec[2])
		var mesh := MeshInstance3D.new()
		var box := BoxMesh.new()
		box.size = Vector3(0.5, 0.5, 0.5)
		mesh.mesh = box
		body.add_child(mesh)
		var cs := CollisionShape3D.new()
		var shape := BoxShape3D.new()
		shape.size = box.size
		cs.shape = shape
		body.add_child(cs)
		decor.add_child(body)
