# Realistic characters in games (Godot, three.js, Blender)

Each realistic character is one glTF binary, `cinema/real-<id>.glb`, with a manifest beside it,
`cinema/real-<id>.anim.json`. Built by `tools/cinema/real.py`; the game clips come from
`tools/cinema/game_clips.py`.

## What is in the file

- One skinned body plus clothes, hair, beard, eyes (eyeball + clear cornea), teeth, tongue,
  brows and lashes, all on one skeleton. Hair, brows, lashes and beard use alpha **MASK**
  (cut-out); the cornea uses `KHR_materials_transmission` + `KHR_materials_ior`; the skin uses
  `KHR_materials_sheen`. Textures are WebP.
- Skeleton: `Root` (on the floor, at the character's feet; root-motion bone, no skin), `Hips`,
  `Spine`, `Spine1`, `Spine2`, `Neck`, `Head`, `Jaw`, `Shoulder/UpperArm/ForeArm/Hand.L|R`, three
  bones per finger, `UpLeg/Leg/Foot/Toe.L|R`. The character faces **+Z** in glTF (-Y in
  Blender). 1 unit = 1 m. 24 fps.
- Clips: the game set below, plus the older cinematic clips (`Idle`, `Walk in Place`, `Sad`,
  `Terror`, ...) used by Set Film.

## The game clips

| Group | Clips |
|---|---|
| Idles (loop) | `idle_loop`, `idle_look_loop`, `idle_shift_loop`, `idle_tired_loop`, `idle_cold_loop` |
| Locomotion (loop, in place) | `walk_loop`, `walk_fast_loop`, `run_loop`, `sprint_loop` |
| Jumps | `jump`, `jump_high` |
| Ledge | `jump_grab` → `hang_loop` → `climb_up` / `drop_from_hang` |
| Obstacles | `vault_fence` |
| Horse | `mount_horse` → `ride_loop` / `ride_trot_loop` → `dismount_horse` |
| Cart | `climb_into_cart` |
| Work | `chop_tree_loop` (axe), `cook_stir_loop` (spoon), `pick_plant`, `pick_up` |
| Talking | `talk_loop`, `listen_loop`, `gesture_explain`, `gesture_agree`, `gesture_disagree`, `gesture_shrug`, `gesture_beckon`, `gesture_point`, `gesture_wave`, `gesture_bow` |
| Begging | `kneel_down` → `beg_kneel_loop` → `stand_up_from_kneel` |

The manifest gives, for every clip: `seconds`, `loop`, `speed` (m/s the locomotion was made for,
at scale 1 — multiply by the character's scale), `root_motion` (total offset of the Root bone,
Blender axes: X left, -Y forward, Z up), `then` (clips that can follow without a pop; `*` = any),
`markers` (normalised times of foot contacts, take-off, landing, grab, hit), `props` (what to
put in which hand) and `note` (prop sizes: ledge 2.3 m, fence 1.0 m, saddle 1.5 m, cart bed 0.9 m,
all x scale).

### Why transitions are clean

- Every pose is absolute and clips are blended between key poses, so nothing pops inside a clip.
- Every one-shot starts on the first frame of `idle_loop` and ends on it again (or on the first
  frame of the loop it hands over to: `hang_loop`, `ride_loop`, `beg_kneel_loop`).
- Loops are seamless. Cross-fade 0.15–0.25 s between clips (0.3 s into or out of
  `idle_cold_loop`, `chop_tree_loop`, `cook_stir_loop`, which are not idle-shaped).
- Locomotion: keep the gait phase when switching between walk/run/sprint (the left foot lands
  at 0.0 and the right at 0.5 in all of them), or use a 1D blend space on speed.

## Godot 4

1. Drop the `.glb` into the project. Clips named `*_loop` import as looping, and Godot drops the
   suffix: `walk_loop` becomes `walk`, `idle_loop` becomes `idle` (checked with Godot 4.7.2:
   63 clips, loop flags and the Root track as expected).
2. For root motion: AnimationTree → `root_motion_track = "Skeleton3D:Root"` (or the path the
   importer shows); in `_physics_process`:
   ```gdscript
   var motion = anim_tree.get_root_motion_position()
   velocity = (global_basis * motion) / delta
   move_and_slide()
   ```
   With a root-motion track set, Godot removes the Root bone's motion from the pose and gives it
   to you, so `hang_loop` / `ride_loop` (whose Root stays raised) play correctly after
   `jump_grab` / `mount_horse` moved the body up.
3. Locomotion is in place: move the CharacterBody3D at `speed x scale` from the manifest.
4. State machine: use the manifest's `then` lists as transitions; cross-fade 0.2 s.
5. Props: add a `BoneAttachment3D` on `Hand.R` (axe, spoon, stone) / `Hand.L`.

## three.js

```js
const gltf = await new GLTFLoader().loadAsync('real-tomas.glb');
const mixer = new THREE.AnimationMixer(gltf.scene);
const clip = (n) => THREE.AnimationClip.findByName(gltf.animations, n);
const idle = mixer.clipAction(clip('idle_loop')).play();
// one-shot back to idle:
const jump = mixer.clipAction(clip('jump'));
jump.setLoop(THREE.LoopOnce); jump.clampWhenFinished = true;
idle.crossFadeTo(jump.reset().play(), 0.2, false);
```

Root motion: either let the Root track move the model (simple; then after a traversal clip
ends, move `gltf.scene` by the manifest's `root_motion` and switch clips in the same frame), or
strip the Root position track from traversal clips and apply `root_motion` yourself over the
clip's time. Locomotion: move the object at the manifest speed.

## Blender

Import the `.glb`; every clip is an action (Action Editor / NLA). Root motion is on `Root`.
To rebuild: `python3 tools/cinema/real.py <out> <shots> tomas amara mei beggar` (needs the
MPFB 2 extension and the MakeHuman CC0 system assets, see the licence).
