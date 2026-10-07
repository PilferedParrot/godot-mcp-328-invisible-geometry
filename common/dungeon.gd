extends Node3D
## Shared scaffolding for the #328 fixtures. Primitives only; no external assets.
##
## A 16 x 24 m floor made of GridMap cells (2 m cells, collision on) and one
## camera. Props are single MeshInstance3Ds whose mesh is centred on the node
## origin, so a prop resting on a surface sits at surface + half its height.

const CELL := 2.0
const SLAB := 0.1

const PROPS := {
	"Rubble":  {"shape": "box",    "size": Vector3(0.6, 0.4, 0.6),   "color": Color(0.45, 0.42, 0.38)},
	"Fungus":  {"shape": "cyl",    "size": Vector3(0.2, 0.35, 0.2),  "color": Color(0.35, 0.65, 0.45)},
	"Bones":   {"shape": "box",    "size": Vector3(0.6, 0.1, 0.16),  "color": Color(0.9, 0.88, 0.8)},
	"Puddle":  {"shape": "cyl",    "size": Vector3(0.5, 0.02, 0.5),  "color": Color(0.2, 0.35, 0.7)},
	"Skull":   {"shape": "sphere", "size": Vector3(0.14, 0.28, 0.14), "color": Color(0.95, 0.93, 0.85)},
	"Candle":  {"shape": "cyl",    "size": Vector3(0.05, 0.28, 0.05), "color": Color(0.95, 0.85, 0.45)},
	"Bucket":  {"shape": "cyl",    "size": Vector3(0.2, 0.32, 0.2),  "color": Color(0.55, 0.4, 0.25)},
	"Lantern": {"shape": "sphere", "size": Vector3(0.16, 0.32, 0.16), "color": Color(1.0, 0.7, 0.2)},
	"Chest":   {"shape": "box",    "size": Vector3(0.7, 0.45, 0.45), "color": Color(0.5, 0.3, 0.15)},
}

var floor_grid: GridMap
var cam: Camera3D
var decor: Node3D


func build_floor() -> void:
	var lib := MeshLibrary.new()
	lib.create_item(0)
	var slab := BoxMesh.new()
	slab.size = Vector3(CELL, SLAB, CELL)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.3, 0.32, 0.36)
	slab.material = mat
	lib.set_item_mesh(0, slab)
	var shape := BoxShape3D.new()
	shape.size = slab.size
	lib.set_item_shapes(0, [shape, Transform3D.IDENTITY])
	floor_grid = GridMap.new()
	floor_grid.name = "Floor"
	floor_grid.mesh_library = lib
	floor_grid.cell_size = Vector3(CELL, CELL, CELL)
	for x in range(-4, 4):
		for z in range(-4, 8):
			floor_grid.set_cell_item(Vector3i(x, 0, z), 0)
	add_child(floor_grid)


func build_camera() -> void:
	var sun := DirectionalLight3D.new()
	sun.name = "Sun"
	sun.rotation_degrees = Vector3(-55, 30, 0)
	add_child(sun)
	cam = Camera3D.new()
	cam.name = "Camera3D"
	cam.position = Vector3(1, 4.5, 7)
	cam.fov = 70.0
	add_child(cam)
	cam.look_at(Vector3(1, 1, 0))
	cam.current = true


func build_decor() -> void:
	decor = Node3D.new()
	decor.name = "Decor"
	add_child(decor)


func make_prop(kind: String) -> MeshInstance3D:
	var spec: Dictionary = PROPS[kind]
	var size: Vector3 = spec["size"]
	var mesh: Mesh
	match spec["shape"]:
		"box":
			var b := BoxMesh.new()
			b.size = size
			mesh = b
		"cyl":
			var c := CylinderMesh.new()
			c.top_radius = size.x
			c.bottom_radius = size.x
			c.height = size.y
			mesh = c
		_:
			var s := SphereMesh.new()
			s.radius = size.x
			s.height = size.y
			mesh = s
	var mat := StandardMaterial3D.new()
	mat.albedo_color = spec["color"]
	mesh.material = mat
	var prop := MeshInstance3D.new()
	prop.name = kind
	prop.mesh = mesh
	return prop


func half_height(prop: MeshInstance3D) -> float:
	return prop.mesh.get_aabb().size.y * 0.5


## World Y of the top of the floor slab under a world (x, z), read from the GridMap.
func surface_y(xz: Vector2) -> float:
	var cell := floor_grid.local_to_map(floor_grid.to_local(Vector3(xz.x, 0.0, xz.y)))
	var centre := floor_grid.to_global(floor_grid.map_to_local(cell))
	return centre.y + floor_grid.mesh_library.get_item_mesh(0).get_aabb().end.y
