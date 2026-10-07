class_name PulseSpecialEnemy
extends CharacterBody3D

signal exploded

@export var model_path := ""
@export var health := 8
@export var damage := 12
@export var attack_interval := 3.0
@export var move_speed := 3.0
@export var hover_height := 1.6
@export var attack_range := 26.0
@export var boss := false

var target: Node3D = null
var dead := false
var attack_timer := 0.0
var base_y := 0.0
var model_root: Node3D = null


func _ready() -> void:
	base_y = global_position.y
	var collision := CollisionShape3D.new()
	var shape := CapsuleShape3D.new()
	shape.radius = 0.9 if not boss else 2.0
	shape.height = 2.6 if not boss else 5.0
	collision.shape = shape
	add_child(collision)

	if ResourceLoader.exists(model_path):
		var packed = load(model_path)
		if packed is PackedScene:
			model_root = packed.instantiate()
			model_root.scale = Vector3.ONE * (1.7 if not boss else 4.0)
			model_root.position.y = -0.2 if not boss else -1.4
			add_child(model_root)

	var light := OmniLight3D.new()
	light.light_color = Color(0.7, 0.1, 1.0) if boss else Color(0.1, 0.75, 1.0)
	light.light_energy = 1.6 if boss else 0.75
	light.omni_range = 10.0 if boss else 5.0
	add_child(light)


func _physics_process(delta: float) -> void:
	if dead or target == null or not is_instance_valid(target):
		return
	attack_timer = maxf(attack_timer - delta, 0.0)
	var to_target := target.global_position - global_position
	var horizontal := Vector3(to_target.x, 0, to_target.z)
	var dist := horizontal.length()
	if dist > 7.0:
		velocity = horizontal.normalized() * move_speed
	else:
		velocity = Vector3.ZERO
	global_position.y = lerpf(global_position.y, base_y + hover_height + sin(Time.get_ticks_msec() * 0.002) * 0.35, delta * 2.0)
	if horizontal.length() > 0.2:
		look_at(global_position + horizontal.normalized(), Vector3.UP)
	move_and_slide()
	if dist <= attack_range and attack_timer <= 0.0:
		attack_timer = attack_interval
		_attack()


func _attack() -> void:
	if target == null or not target.has_method("take_damage"):
		return
	if boss:
		var burst := 2 if health > 18 else 3
		for _i in range(burst):
			if is_instance_valid(target):
				target.take_damage(damage)
	else:
		target.take_damage(damage)


@rpc("call_local")
func hit() -> void:
	hit_damage(1)


func hit_damage(amount: int) -> void:
	if dead:
		return
	health -= maxi(amount, 1)
	if health <= 0:
		_die()


func _die() -> void:
	dead = true
	exploded.emit()
	var tween := create_tween()
	tween.tween_property(self, "scale", Vector3.ONE * 0.05, 0.28)
	tween.tween_callback(queue_free)
