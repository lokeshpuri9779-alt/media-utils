class_name PulseMissionBuilder
extends Node3D

const Q_MOD := "res://assets/quaternius/modular_scifi/glTF/"
const Q_ESS := "res://assets/quaternius/scifi_essentials/glTF/"
const Q_SPACE := "res://assets/quaternius/ultimate_space/Environment/GLTF/"
const Q_SHIPS := "res://assets/quaternius/ultimate_space/Vehicles/GLTF/"
const K_STATION := "res://assets/kenney/space_station/"
const K_MODULAR := "res://assets/kenney/modular_space/"

var checkpoints: Array[Transform3D] = []
var spawn_sets: Array[Array] = []
var zone_roots: Array[Node3D] = []
var built := false

var metal_materials := [
	_make_material(Color(0.055, 0.075, 0.11), Color(0.03, 0.35, 0.55)),
	_make_material(Color(0.095, 0.065, 0.05), Color(0.75, 0.18, 0.04)),
	_make_material(Color(0.035, 0.085, 0.08), Color(0.04, 0.68, 0.48)),
	_make_material(Color(0.085, 0.04, 0.095), Color(0.56, 0.12, 0.78)),
]


static func _make_material(base: Color, emission: Color) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = base
	mat.metallic = 0.78
	mat.roughness = 0.27
	mat.emission_enabled = true
	mat.emission = emission
	mat.emission_energy_multiplier = 0.32
	return mat


func build_world() -> void:
	if built:
		return
	built = true
	_build_original_zone()
	_build_industrial_ring(1, Vector3(360, 0, 0))
	_build_dockyard(2, Vector3(740, 0, 0))
	_build_surface(3, Vector3(1130, 0, 0))
	_build_research(4, Vector3(1510, 0, 0))
	_build_biocontainment(5, Vector3(1890, 0, 0))
	_build_command(6, Vector3(2270, 0, 0))
	_build_core(7, Vector3(2650, 0, 0))


func _build_original_zone() -> void:
	var root := Node3D.new()
	root.name = "Zone00_Containment"
	add_child(root)
	zone_roots.append(root)
	var parent := get_parent()
	var checkpoint := Transform3D.IDENTITY
	if parent.has_node("PlayerSpawnpoints"):
		checkpoint = parent.get_node("PlayerSpawnpoints").get_child(0).global_transform
	else:
		checkpoint.origin = Vector3(64.8, -1.0, 78.7)
	checkpoints.append(checkpoint)
	var spawns: Array[Transform3D] = []
	if parent.has_node("RobotSpawnpoints"):
		for marker in parent.get_node("RobotSpawnpoints").get_children():
			spawns.append(marker.global_transform)
	spawn_sets.append(spawns)


func _build_industrial_ring(index: int, origin: Vector3) -> void:
	var root := _base_zone(index, "IndustrialRing", origin, Vector3(70, 1.2, 58), metal_materials[1])
	for x in [-24.0, -8.0, 8.0, 24.0]:
		_add_model(root, Q_MOD + "Columns/Column_Pipes.gltf", origin + Vector3(x, 0.7, -20), Vector3.ONE * 2.1, 0.0)
		_add_model(root, Q_MOD + "Columns/Column_MetalSupport.gltf", origin + Vector3(x, 0.7, 20), Vector3.ONE * 2.1, PI)
	for z in [-13.0, 0.0, 13.0]:
		_add_model(root, Q_MOD + "Props/Prop_Crate4.gltf", origin + Vector3(-20, 1.0, z), Vector3.ONE * 2.0, z)
		_add_model(root, Q_MOD + "Props/Prop_Barrel_Large.gltf", origin + Vector3(20, 1.0, z), Vector3.ONE * 2.0, z)
	_add_model(root, K_MODULAR + "cables.glb", origin + Vector3(0, 0.8, 0), Vector3.ONE * 3.0, 0.0)
	_add_lights(root, origin, Color(1.0, 0.25, 0.08))


func _build_dockyard(index: int, origin: Vector3) -> void:
	var root := _base_zone(index, "DockyardSiege", origin, Vector3(92, 1.2, 72), metal_materials[0])
	_add_model(root, Q_SHIPS + "Spaceship_FernandoTheFlamingo.gltf", origin + Vector3(-22, 1.5, -6), Vector3.ONE * 2.8, 0.35)
	_add_model(root, Q_SHIPS + "Spaceship_RaeTheRedPanda.gltf", origin + Vector3(24, 1.5, 10), Vector3.ONE * 2.6, -0.6)
	for z in [-26.0, -13.0, 0.0, 13.0, 26.0]:
		_add_model(root, K_STATION + "balcony-rail.glb", origin + Vector3(-38, 1.0, z), Vector3.ONE * 2.0, PI * 0.5)
		_add_model(root, K_STATION + "balcony-rail.glb", origin + Vector3(38, 1.0, z), Vector3.ONE * 2.0, -PI * 0.5)
	_add_model(root, Q_ESS + "Prop_Crate_Tarp_Large.gltf", origin + Vector3(0, 1.1, -18), Vector3.ONE * 2.2, 0.0)
	_add_model(root, Q_ESS + "Prop_SatelliteDish.gltf", origin + Vector3(0, 1.1, 24), Vector3.ONE * 2.8, PI)
	_add_lights(root, origin, Color(0.12, 0.62, 1.0))


func _build_surface(index: int, origin: Vector3) -> void:
	var root := _base_zone(index, "SurfaceExile", origin, Vector3(110, 1.0, 92), _make_material(Color(0.07, 0.055, 0.06), Color(0.16, 0.05, 0.22)))
	for pos in [
		Vector3(-34, 0.6, -25), Vector3(-18, 0.6, 26), Vector3(32, 0.6, -22),
		Vector3(38, 0.6, 24), Vector3(0, 0.6, 32), Vector3(8, 0.6, -35)
	]:
		_add_model(root, Q_SPACE + "Rock_Large_2.gltf", origin + pos, Vector3.ONE * 3.0, pos.x)
	_add_model(root, Q_SPACE + "GeodesicDome.gltf", origin + Vector3(-26, 1.0, 4), Vector3.ONE * 3.8, 0.0)
	_add_model(root, Q_SPACE + "House_Long.gltf", origin + Vector3(25, 1.0, 4), Vector3.ONE * 3.2, PI)
	_add_model(root, Q_SPACE + "SolarPanel_Structure.gltf", origin + Vector3(0, 0.8, -24), Vector3.ONE * 3.5, 0.0)
	_add_model(root, Q_SHIPS + "Rover_2.gltf", origin + Vector3(10, 1.0, 18), Vector3.ONE * 2.5, -0.4)
	for p in [Vector3(-12,0.4,-16), Vector3(18,0.4,-13), Vector3(-30,0.4,19), Vector3(31,0.4,30)]:
		_add_model(root, Q_SPACE + "Plant_3.gltf", origin + p, Vector3.ONE * 3.0, p.z)
	_add_lights(root, origin, Color(0.58, 0.28, 1.0))


func _build_research(index: int, origin: Vector3) -> void:
	var root := _base_zone(index, "ResearchBreach", origin, Vector3(78, 1.2, 64), metal_materials[2])
	for x in [-26.0, -13.0, 0.0, 13.0, 26.0]:
		_add_model(root, Q_ESS + "Prop_Desk_Medium.gltf", origin + Vector3(x, 1.0, -18), Vector3.ONE * 1.8, 0.0)
		_add_model(root, Q_ESS + "Prop_Locker.gltf", origin + Vector3(x, 1.0, 20), Vector3.ONE * 1.8, PI)
	_add_model(root, Q_MOD + "Props/Prop_Computer.gltf", origin + Vector3(0, 1.0, 0), Vector3.ONE * 2.5, 0.0)
	_add_model(root, Q_ESS + "Prop_HealthPack_Tube.gltf", origin + Vector3(-17, 1.1, 4), Vector3.ONE * 2.0, 0.0)
	_add_model(root, Q_ESS + "Prop_KeyCard.gltf", origin + Vector3(17, 1.1, 4), Vector3.ONE * 2.8, 0.0)
	_add_lights(root, origin, Color(0.1, 1.0, 0.65))


func _build_biocontainment(index: int, origin: Vector3) -> void:
	var root := _base_zone(index, "BioContainment", origin, Vector3(82, 1.2, 70), metal_materials[3])
	_add_model(root, Q_MOD + "Aliens/Alien_Cyclop.gltf", origin + Vector3(-18, 1.1, -8), Vector3.ONE * 3.8, 0.2)
	_add_model(root, Q_MOD + "Aliens/Alien_Oculichrysalis.gltf", origin + Vector3(18, 1.1, -8), Vector3.ONE * 3.4, -0.2)
	_add_model(root, Q_MOD + "Aliens/Alien_Scolitex.gltf", origin + Vector3(0, 1.1, 18), Vector3.ONE * 3.8, PI)
	for x in [-28.0, -14.0, 14.0, 28.0]:
		_add_model(root, Q_MOD + "Columns/Column_Hollow.gltf", origin + Vector3(x, 1.0, 0), Vector3.ONE * 2.6, 0.0)
	_add_lights(root, origin, Color(0.75, 0.05, 1.0))


func _build_command(index: int, origin: Vector3) -> void:
	var root := _base_zone(index, "CommandGhost", origin, Vector3(86, 1.2, 68), metal_materials[0])
	for x in [-26.0, -13.0, 0.0, 13.0, 26.0]:
		_add_model(root, K_STATION + "chair.glb", origin + Vector3(x, 1.0, 12), Vector3.ONE * 1.8, PI)
	_add_model(root, Q_MOD + "Props/Prop_AccessPoint.gltf", origin + Vector3(0, 1.0, -20), Vector3.ONE * 3.0, 0.0)
	_add_model(root, Q_ESS + "Prop_Shelves_WideTall.gltf", origin + Vector3(-28, 1.0, -16), Vector3.ONE * 2.0, 0.0)
	_add_model(root, Q_ESS + "Prop_Shelves_WideTall.gltf", origin + Vector3(28, 1.0, -16), Vector3.ONE * 2.0, 0.0)
	_add_lights(root, origin, Color(0.15, 0.5, 1.0))


func _build_core(index: int, origin: Vector3) -> void:
	var root := _base_zone(index, "PulseCore", origin, Vector3(96, 1.4, 96), _make_material(Color(0.035, 0.02, 0.06), Color(0.55, 0.05, 0.85)))
	var core := MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = 8.0
	sphere.height = 16.0
	core.mesh = sphere
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.08, 0.15, 0.28, 0.72)
	mat.emission_enabled = true
	mat.emission = Color(0.35, 0.05, 1.0)
	mat.emission_energy_multiplier = 5.5
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	core.material_override = mat
	core.position = origin + Vector3(0, 11, 0)
	root.add_child(core)
	for i in range(8):
		var a := TAU * float(i) / 8.0
		_add_model(root, Q_MOD + "Columns/Column_Astra.gltf", origin + Vector3(cos(a)*30, 1.0, sin(a)*30), Vector3.ONE * 3.4, -a)
	_add_lights(root, origin, Color(0.75, 0.1, 1.0))


func _base_zone(index: int, zone_name: String, origin: Vector3, size: Vector3, material: Material) -> Node3D:
	var root := Node3D.new()
	root.name = "Zone%02d_%s" % [index, zone_name]
	add_child(root)
	zone_roots.append(root)

	var floor_body := StaticBody3D.new()
	floor_body.position = origin + Vector3(0, -0.6, 0)
	root.add_child(floor_body)
	var floor_mesh := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = size
	floor_mesh.mesh = box
	floor_mesh.material_override = material
	floor_body.add_child(floor_mesh)
	var collision := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = size
	collision.shape = shape
	floor_body.add_child(collision)

	_add_wall(root, origin + Vector3(0, 4.5, -size.z*0.5), Vector3(size.x, 9, 1), material)
	_add_wall(root, origin + Vector3(0, 4.5, size.z*0.5), Vector3(size.x, 9, 1), material)
	_add_wall(root, origin + Vector3(-size.x*0.5, 4.5, 0), Vector3(1, 9, size.z), material)
	_add_wall(root, origin + Vector3(size.x*0.5, 4.5, 0), Vector3(1, 9, size.z), material)

	checkpoints.append(Transform3D(Basis.IDENTITY, origin + Vector3(0, 1.0, size.z*0.30)))
	var spawns: Array[Transform3D] = []
	for i in range(10):
		var angle := TAU * float(i) / 10.0
		var radius_x := size.x * 0.34
		var radius_z := size.z * 0.34
		spawns.append(Transform3D(Basis.IDENTITY, origin + Vector3(cos(angle)*radius_x, 0.3, sin(angle)*radius_z)))
	spawn_sets.append(spawns)
	return root


func _add_wall(root: Node3D, position: Vector3, size: Vector3, material: Material) -> void:
	var body := StaticBody3D.new()
	body.position = position
	root.add_child(body)
	var mesh := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = size
	mesh.mesh = box
	mesh.material_override = material
	body.add_child(mesh)
	var collision := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = size
	collision.shape = shape
	body.add_child(collision)


func _add_model(root: Node3D, path: String, position: Vector3, scale_value: Vector3, rotation_y: float) -> void:
	if not ResourceLoader.exists(path):
		return
	var packed = load(path)
	if not packed is PackedScene:
		return
	var instance: Node3D = packed.instantiate()
	instance.position = position
	instance.scale = scale_value
	instance.rotation.y = rotation_y
	root.add_child(instance)


func _add_lights(root: Node3D, origin: Vector3, color: Color) -> void:
	for p in [Vector3(-24, 8, -18), Vector3(24, 8, -18), Vector3(-24, 8, 18), Vector3(24, 8, 18)]:
		var light := OmniLight3D.new()
		light.position = origin + p
		light.light_color = color
		light.light_energy = 2.4
		light.omni_range = 32.0
		light.shadow_enabled = true
		root.add_child(light)


func get_checkpoint(index: int) -> Transform3D:
	if checkpoints.is_empty():
		return Transform3D.IDENTITY
	return checkpoints[clampi(index, 0, checkpoints.size() - 1)]


func get_enemy_spawn(chapter_index: int, marker_index: int, spawn_index: int) -> Transform3D:
	var set_index := clampi(chapter_index, 0, spawn_sets.size() - 1)
	var options: Array = spawn_sets[set_index]
	if options.is_empty():
		return get_checkpoint(set_index)
	return options[(marker_index + spawn_index) % options.size()]


func activate_zone(index: int) -> void:
	for i in range(zone_roots.size()):
		zone_roots[i].visible = (i == 0 or i == index)
