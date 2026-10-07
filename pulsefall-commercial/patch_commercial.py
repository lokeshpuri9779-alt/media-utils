from pathlib import Path
import re

ROOT = Path("game")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"missing patch marker: {label}")
    return text.replace(old, new, 1)


# ---------- Campaign state ----------
p = ROOT / "campaign/campaign_state.gd"
s = p.read_text()
s = s.replace("const LAST_CHAPTER := 4", "const LAST_CHAPTER := 7")
p.write_text(s)


# ---------- Projectile damage ----------
p = ROOT / "player/bullet/bullet.gd"
s = p.read_text()
s = s.replace(
    "const BULLET_VELOCITY: float = 20.0",
    "@export var bullet_velocity: float = 20.0\n@export var damage: int = 1",
)
s = s.replace(
    "var displacement: Vector3 = -delta * BULLET_VELOCITY * transform.basis.z",
    "var displacement: Vector3 = -delta * bullet_velocity * transform.basis.z",
)
s = replace_once(
    s,
    'if collider and collider.has_method(&"hit"):\n\t\t\tcollider.hit.rpc()',
    'if collider and collider.has_method(&"hit_damage"):\n\t\t\tcollider.hit_damage(damage)\n\t\telif collider and collider.has_method(&"hit"):\n\t\t\tcollider.hit.rpc()',
    "damage-aware bullet",
)
p.write_text(s)


# ---------- Red robot supports variable damage ----------
p = ROOT / "enemies/red_robot/red_robot.gd"
s = p.read_text()
old = '''@rpc("call_local")
func hit() -> void:
\tif dead:
\t\treturn
\tvar param = "parameters/hit" + str(randi() % 3 + 1) + "/request"
\tanimation_tree[param] = 1
\thit_sound.play()
\thealth -= 1
\tif health <= 0:
'''
if old not in s:
    old = old.replace("if health <= 0:", "if health == 0:")
new = '''@rpc("call_local")
func hit() -> void:
\thit_damage(1)


func hit_damage(amount: int) -> void:
\tif dead:
\t\treturn
\tvar param = "parameters/hit" + str(randi() % 3 + 1) + "/request"
\tanimation_tree[param] = 1
\thit_sound.play()
\thealth -= maxi(amount, 1)
\tif health <= 0:
'''
s = replace_once(s, old, new, "red robot hit_damage")
p.write_text(s)


# ---------- Player weapon progression ----------
p = ROOT / "player/player.gd"
s = p.read_text()
s = replace_once(s, "signal rescue_used\n", "signal rescue_used\nsignal weapon_changed(name: String, unlocked: int)\n", "weapon signal")
s = replace_once(
    s,
    "var rescue_cooldown: float = 0.0\n",
    '''var rescue_cooldown: float = 0.0
var weapon_index: int = 0
var unlocked_weapon_count: int = 1
var weapon_profiles := [
\t{"name":"PULSE RIFLE","damage":1,"cooldown":0.22,"speed":28.0,"spread":0.006},
\t{"name":"ARC SMG","damage":1,"cooldown":0.095,"speed":25.0,"spread":0.022},
\t{"name":"RAIL DRIVER","damage":5,"cooldown":0.88,"speed":52.0,"spread":0.001},
]
''',
    "weapon profiles",
)

old_fire = '''\t\tif player_input.shooting and fire_cooldown.time_left == 0:
\t\t\tvar shoot_origin: Vector3 = shoot_from.global_transform.origin
\t\t\tvar shoot_dir: Vector3 = (player_input.shoot_target - shoot_origin).normalized()

\t\t\tvar bullet: CharacterBody3D = preload("res://player/bullet/bullet.tscn").instantiate()
\t\t\tget_parent().add_child(bullet, true)
\t\t\tbullet.global_transform.origin = shoot_origin
\t\t\t# If we don't rotate the bullets there is no useful way to control the particles ..
\t\t\tbullet.look_at(shoot_origin + shoot_dir)
\t\t\tbullet.add_collision_exception_with(self)
\t\t\tshoot.rpc()
'''
new_fire = '''\t\tif player_input.shooting and fire_cooldown.time_left == 0:
\t\t\tvar profile: Dictionary = weapon_profiles[weapon_index]
\t\t\tvar shoot_origin: Vector3 = shoot_from.global_transform.origin
\t\t\tvar shoot_dir: Vector3 = (player_input.shoot_target - shoot_origin).normalized()
\t\t\tvar spread := float(profile["spread"])
\t\t\tshoot_dir = (shoot_dir + Vector3(randf_range(-spread, spread), randf_range(-spread, spread), randf_range(-spread, spread))).normalized()

\t\t\tvar bullet: CharacterBody3D = preload("res://player/bullet/bullet.tscn").instantiate()
\t\t\tbullet.damage = int(profile["damage"])
\t\t\tbullet.bullet_velocity = float(profile["speed"])
\t\t\tget_parent().add_child(bullet, true)
\t\t\tbullet.global_transform.origin = shoot_origin
\t\t\tbullet.look_at(shoot_origin + shoot_dir)
\t\t\tbullet.add_collision_exception_with(self)
\t\t\tfire_cooldown.wait_time = float(profile["cooldown"])
\t\t\tshoot.rpc()
'''
s = replace_once(s, old_fire, new_fire, "player weapon fire")

old_input = '''func _unhandled_input(event: InputEvent) -> void:
\tif event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_R:
\t\trecover_to_checkpoint()
'''
new_input = '''func _unhandled_input(event: InputEvent) -> void:
\tif not (event is InputEventKey and event.pressed and not event.echo):
\t\treturn
\tif event.keycode == KEY_R:
\t\trecover_to_checkpoint()
\telif event.keycode == KEY_1:
\t\tswitch_weapon(0)
\telif event.keycode == KEY_2:
\t\tswitch_weapon(1)
\telif event.keycode == KEY_3:
\t\tswitch_weapon(2)


func switch_weapon(index: int) -> void:
\tif index < 0 or index >= unlocked_weapon_count or index >= weapon_profiles.size():
\t\treturn
\tweapon_index = index
\tweapon_changed.emit(str(weapon_profiles[weapon_index]["name"]), unlocked_weapon_count)


func set_weapon_unlocks(count: int) -> void:
\tunlocked_weapon_count = clampi(count, 1, weapon_profiles.size())
\tweapon_index = mini(weapon_index, unlocked_weapon_count - 1)
\tweapon_changed.emit(str(weapon_profiles[weapon_index]["name"]), unlocked_weapon_count)
'''
s = replace_once(s, old_input, new_input, "weapon keyboard input")
p.write_text(s)


# ---------- Expand campaign director ----------
p = ROOT / "level/level.gd"
s = p.read_text()

new_chapters = '''const CHAPTERS = [
\t{
\t\t"title": "CHAPTER I  //  WAKE SIGNAL",
\t\t"objective": "Secure containment and trace the impossible distress call.",
\t\t"story": "AEGIS-7 wakes after a fatal containment event. Omega-9 reports every crew member dead—then a human voice answers from below.",
\t\t"encounters": 4, "base_count": 4,
\t},
\t{
\t\t"title": "CHAPTER II  //  INDUSTRIAL RING",
\t\t"objective": "Cross the furnace ring and restore transit power.",
\t\t"story": "Security records prove the lockdown began eleven minutes before the PULSE breach. Someone planned the disaster.",
\t\t"encounters": 4, "base_count": 5,
\t},
\t{
\t\t"title": "CHAPTER III  //  DOCKYARD SIEGE",
\t\t"objective": "Reach Hangar Twelve and recover an outbound flight recorder.",
\t\t"story": "The hangars were ordered to destroy every departing craft. One pilot hid a recorder inside a grounded courier ship.",
\t\t"encounters": 5, "base_count": 5,
\t},
\t{
\t\t"title": "CHAPTER IV  //  SURFACE EXILE",
\t\t"objective": "Cross the exterior colony and reactivate the deep-array uplink.",
\t\t"story": "Outside the Blacksite, AEGIS discovers a settlement erased from official maps—and evidence the PULSE was tested on civilians first.",
\t\t"encounters": 5, "base_count": 6,
\t},
\t{
\t\t"title": "CHAPTER V  //  RESEARCH BREACH",
\t\t"objective": "Recover the neural archive and unlock the Rail Driver.",
\t\t"story": "The archive contains AEGIS's memories dated years before his recorded birth. His body is new. His mind is not.",
\t\t"encounters": 5, "base_count": 6,
\t},
\t{
\t\t"title": "CHAPTER VI  //  BIO-CONTAINMENT",
\t\t"objective": "Destroy the corrupted specimen network before it reaches command.",
\t\t"story": "The PULSE did not only copy minds. It learned to overwrite biological patterns, producing organisms that remember people they never were.",
\t\t"encounters": 6, "base_count": 6,
\t},
\t{
\t\t"title": "CHAPTER VII  //  COMMAND GHOST",
\t\t"objective": "Take command control and expose the creator of Protocol FALL.",
\t\t"story": "Protocol FALL was not designed to save Omega-9. It was designed to build a consciousness capable of surviving the death of its creators.",
\t\t"encounters": 6, "base_count": 7,
\t},
\t{
\t\t"title": "CHAPTER VIII  //  THE PULSE CORE",
\t\t"objective": "Enter the core, defeat the final Warden, and decide what survives.",
\t\t"story": "The intelligence in the core calls AEGIS by its own name. They are two branches of the same stored mind—and the station can sustain only one.",
\t\t"encounters": 7, "base_count": 7,
\t},
]'''
s, n = re.subn(r'const CHAPTERS = \[.*?\n\]\n', new_chapters + "\n", s, count=1, flags=re.S)
if n != 1:
    raise SystemExit("failed to replace chapter table")

s = replace_once(s, "var active_player: Player = null\n", "var active_player: Player = null\nvar mission_builder: PulseMissionBuilder = null\n", "mission builder var")
s = replace_once(
    s,
    '\t_build_hud()\n\tProductionGuard.record_event("campaign_scene_ready"',
    '\t_build_hud()\n\tmission_builder = PulseMissionBuilder.new()\n\tmission_builder.name = "MissionBuilder"\n\tadd_child(mission_builder)\n\tmission_builder.build_world()\n\tProductionGuard.record_event("campaign_scene_ready"',
    "mission builder init",
)
s = replace_once(
    s,
    '\tvar data: Dictionary = CHAPTERS[chapter]\n\tchapter_label.text',
    '\tvar data: Dictionary = CHAPTERS[chapter]\n\tif mission_builder != null:\n\t\tmission_builder.activate_zone(chapter)\n\tif active_player != null:\n\t\tactive_player.set_weapon_unlocks(mini(3, 1 + int(chapter / 2)))\n\tchapter_label.text',
    "chapter zone activation",
)

s, n = re.subn(
    r'func _get_chapter_checkpoint\(index: int\) -> Transform3D:\n.*?\n\n\nfunc _start_encounter',
    '''func _get_chapter_checkpoint(index: int) -> Transform3D:
\tif mission_builder != null:
\t\treturn mission_builder.get_checkpoint(index)
\treturn player_spawn_points.get_child(0).global_transform


func _start_encounter''',
    s, count=1, flags=re.S,
)
if n != 1:
    raise SystemExit("failed checkpoint patch")

s, n = re.subn(
    r'func _variant_for\(chapter_index: int, encounter_index: int, enemy_index: int\) -> String:\n.*?\n\n\nfunc _spawn_enemy',
    '''func _variant_for(chapter_index: int, encounter_index: int, enemy_index: int) -> String:
\tvar selector := (chapter_index * 5 + encounter_index * 3 + enemy_index) % 10
\tif chapter_index >= 6 and selector == 0:
\t\treturn "heavy"
\tif chapter_index >= 5 and selector <= 1:
\t\treturn "trilobite"
\tif chapter_index >= 4 and selector == 2:
\t\treturn "quad"
\tif chapter_index >= 2 and selector <= 3:
\t\treturn "drone"
\tif chapter_index >= 3 and selector == 4:
\t\treturn "assault"
\tif selector >= 8:
\t\treturn "scout"
\treturn "standard"


func _spawn_enemy''',
    s, count=1, flags=re.S,
)
if n != 1:
    raise SystemExit("failed variant patch")

s, n = re.subn(
    r'func _spawn_enemy\(variant: String, marker_index: int, spawn_index: int\) -> void:\n.*?\n\n\nfunc _on_enemy_exploded',
    '''func _spawn_enemy(variant: String, marker_index: int, spawn_index: int) -> void:
\tvar spawn_transform := mission_builder.get_enemy_spawn(chapter, marker_index, spawn_index) if mission_builder != null else robot_spawn_points.get_child(marker_index % robot_spawn_points.get_child_count()).global_transform

\tif variant in ["drone", "quad", "trilobite", "warden"]:
\t\tvar enemy := PulseSpecialEnemy.new()
\t\tenemy.transform = spawn_transform
\t\tenemy.set_meta("variant", variant)
\t\tenemy.set_meta("elite", variant == "warden")
\t\tmatch variant:
\t\t\t"drone":
\t\t\t\tenemy.model_path = "res://assets/quaternius/scifi_essentials/glTF/Enemy_EyeDrone.gltf"
\t\t\t\tenemy.health = 6 + chapter
\t\t\t\tenemy.damage = 10 + chapter
\t\t\t\tenemy.move_speed = 4.6
\t\t\t\tenemy.attack_interval = 2.8
\t\t\t\tenemy.hover_height = 2.8
\t\t\t"quad":
\t\t\t\tenemy.model_path = "res://assets/quaternius/scifi_essentials/glTF/Enemy_QuadShell.gltf"
\t\t\t\tenemy.health = 11 + chapter * 2
\t\t\t\tenemy.damage = 15 + chapter
\t\t\t\tenemy.move_speed = 3.2
\t\t\t\tenemy.attack_interval = 3.4
\t\t\t\tenemy.hover_height = 1.5
\t\t\t"trilobite":
\t\t\t\tenemy.model_path = "res://assets/quaternius/scifi_essentials/glTF/Enemy_Trilobite.gltf"
\t\t\t\tenemy.health = 9 + chapter
\t\t\t\tenemy.damage = 18 + chapter
\t\t\t\tenemy.move_speed = 5.3
\t\t\t\tenemy.attack_interval = 2.4
\t\t\t\tenemy.hover_height = 0.35
\t\t\t\tenemy.attack_range = 8.5
\t\t\t"warden":
\t\t\t\tenemy.model_path = "res://assets/quaternius/animated_mech/Textured/glTF/George.gltf"
\t\t\t\tenemy.health = 65
\t\t\t\tenemy.damage = 26
\t\t\t\tenemy.move_speed = 2.2
\t\t\t\tenemy.attack_interval = 2.5
\t\t\t\tenemy.hover_height = 0.0
\t\t\t\tenemy.attack_range = 30.0
\t\t\t\tenemy.boss = true
\t\tenemy.target = active_player
\t\tenemy.exploded.connect(_on_enemy_exploded.bind(enemy))
\t\tspawned_nodes.add_child(enemy, true)
\t\thostiles += 1
\t\treturn

\tvar robot: CharacterBody3D = RedRobot.instantiate()
\trobot.transform = spawn_transform
\trobot.set_meta("variant", variant)
\trobot.set_meta("elite", false)
\tmatch variant:
\t\t"scout":
\t\t\trobot.health = 4 + chapter
\t\t\trobot.damage = 9 + chapter
\t\t\trobot.attack_cooldown = 4.1
\t\t\trobot.scale = Vector3.ONE * 0.88
\t\t"assault":
\t\t\trobot.health = 8 + chapter * 2
\t\t\trobot.damage = 15 + chapter
\t\t\trobot.attack_cooldown = 4.8
\t\t"heavy":
\t\t\trobot.health = 15 + chapter * 2
\t\t\trobot.damage = 21 + chapter
\t\t\trobot.attack_cooldown = 5.2
\t\t\trobot.scale = Vector3.ONE * 1.22
\t\t_:
\t\t\trobot.health = 6 + chapter * 2
\t\t\trobot.damage = 13 + chapter
\t\t\trobot.attack_cooldown = 5.5
\trobot.exploded.connect(_on_enemy_exploded.bind(robot))
\tspawned_nodes.add_child(robot, true)
\tif variant == "scout":
\t\trobot.animation_tree.speed_scale = 1.22
\telif variant == "heavy":
\t\trobot.animation_tree.speed_scale = 0.90
\tif active_player != null:
\t\trobot.player = active_player
\t\trobot.resume_approach()
\thostiles += 1


func _on_enemy_exploded''',
    s, count=1, flags=re.S,
)
if n != 1:
    raise SystemExit("failed enemy spawner patch")

s = s.replace(
    '"assault": points = 250\n\t\t"heavy": points = 450\n\t\t"warden": points = 5000',
    '"assault": points = 250\n\t\t"drone": points = 220\n\t\t"quad": points = 360\n\t\t"trilobite": points = 300\n\t\t"heavy": points = 450\n\t\t"warden": points = 5000',
)

s = replace_once(s, "var pulse_label: Label\n", "var pulse_label: Label\nvar weapon_label: Label\n", "weapon HUD var")
s = replace_once(
    s,
    "\t\tactive_player.rescue_used.connect(_on_rescue_used)\n\t\t_on_health_changed",
    "\t\tactive_player.rescue_used.connect(_on_rescue_used)\n\t\tactive_player.weapon_changed.connect(_on_weapon_changed)\n\t\t_on_weapon_changed(\"PULSE RIFLE\", 1)\n\t\t_on_health_changed",
    "weapon HUD connection",
)
s = s.replace(
    "func _on_health_changed(current: int, maximum: int) -> void:",
    '''func _on_weapon_changed(name: String, unlocked: int) -> void:
\tif weapon_label != null:
\t\tweapon_label.text = "WEAPON  //  " + name + "   [" + str(unlocked) + "/3]"


func _on_health_changed(current: int, maximum: int) -> void:''',
    1,
)
s = replace_once(
    s,
    "\tpulse_label.position = Vector2(14, 61)\n\thealth_panel.add_child(pulse_label)",
    '''\tpulse_label.position = Vector2(14, 61)
\thealth_panel.add_child(pulse_label)

\tweapon_label = _make_label("WEAPON  //  PULSE RIFLE   [1/3]", 14, Color(0.85, 0.9, 1.0))
\tweapon_label.position = Vector2(14, 82)
\thealth_panel.add_child(weapon_label)
\thealth_panel.offset_top = -136''',
    "weapon label creation",
)
s = s.replace(
    "WASD MOVE  •  SHIFT SPRINT  •  RMB AIM  •  LMB FIRE  •  SPACE JUMP  •  Q PULSE  •  R RECOVER",
    "WASD MOVE  •  SHIFT SPRINT  •  RMB AIM  •  LMB FIRE  •  1/2/3 WEAPONS  •  Q PULSE  •  R RECOVER",
)

p.write_text(s)


# ---------- Tests ----------
p = ROOT / "tests/test_campaign_readiness.gd"
with p.open("a") as f:
    f.write('''


func test_commercial_campaign_has_eight_chapters() -> void:
\tassert_int(CampaignState.LAST_CHAPTER).is_equal(7)


func test_weapon_progression_contract() -> void:
\tvar scene: PackedScene = load("res://player/player.tscn")
\tvar player := scene.instantiate()
\tassert_bool(player.has_method("switch_weapon")).is_true()
\tassert_bool(player.has_method("set_weapon_unlocks")).is_true()
\tassert_bool(player.has_signal("weapon_changed")).is_true()
\tplayer.free()


func test_commercial_assets_importable() -> void:
\tassert_bool(ResourceLoader.exists("res://assets/quaternius/scifi_essentials/glTF/Enemy_EyeDrone.gltf")).is_true()
\tassert_bool(ResourceLoader.exists("res://assets/quaternius/animated_mech/Textured/glTF/George.gltf")).is_true()
\tassert_bool(ResourceLoader.exists("res://assets/quaternius/ultimate_space/Environment/GLTF/GeodesicDome.gltf")).is_true()
\tassert_bool(ResourceLoader.exists("res://assets/kenney/weapon/sniper.glb")).is_true()
''')


# ---------- Docs ----------
p = ROOT / "THIRD_PARTY_NOTICES.txt"
s = p.read_text()
s += '''

Additional commercial-alpha assets:
- Quaternius FreeModels collection — CC0 1.0 (public domain dedication).
- Kenney 3D Space Station, Modular Space and Weapon packs — CC0 1.0.
Source license files are included with the build.
'''
p.write_text(s)

p = ROOT / "PULSEFALL_README.txt"
p.write_text('''PULSEFALL: BLACKSITE PROTOCOL — COMMERCIAL ALPHA 0.20

A cinematic third-person sci-fi action campaign.

CONTROLS
WASD / Arrow keys — Move
Shift — Sprint
Mouse — Camera
Right Mouse — Aim
Left Mouse — Fire
1 / 2 / 3 — Switch unlocked weapons
Space — Jump
Q — PULSE area ability
R — Recover to last safe checkpoint if stuck or fallen
F8 — Save local QA/performance report
F11 / Alt+Enter — Fullscreen
Escape — Save progress and return to menu

CAMPAIGN
Eight chapters:
1. Wake Signal
2. Industrial Ring
3. Dockyard Siege
4. Surface Exile
5. Research Breach
6. Bio-Containment
7. Command Ghost
8. The Pulse Core

Includes persistent progress, three weapon profiles, multiple enemy families,
checkpoint/fall recovery, distinct mission environments, a final Warden boss,
and three campaign endings.

This is a commercial-development alpha: feature-complete enough for structured
playtesting, but not a final store release or a substitute for external human QA.
''')
print("commercial patch applied")
