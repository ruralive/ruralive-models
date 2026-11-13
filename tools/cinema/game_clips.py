"""Game animation set for the realistic characters: locomotion at several speeds, idles, jumps,
traversal with root motion (ledge grab and climb, fence vault, horse, cart), work tasks and
conversation gestures.

How the clips are made, and why they chain cleanly in Godot, three.js and Blender:
- Poses are *absolute*: a pose function sets every bone it cares about from the rest pose
  (`base` is the standing body). Clips are built by blending key poses in time (`keys`):
  rotations slerp, locations lerp, eased. So a clip is continuous by construction and starts
  and ends exactly where its first and last key say.
- Every one-shot starts on `base(0)`, the first frame of `idle_loop`, and ends on `base(0)` again
  (with the root moved, for traversal) or on the first frame of the loop it hands over to
  (`hang_loop`, `ride_loop`). The `then` list in the manifest names the clips that can follow
  without a pop; a 0.15-0.25 s cross-fade is enough everywhere.
- Loops are seamless and their names end in `_loop` (Godot imports those as looping).
- Locomotion loops play on the spot; the manifest gives the ground speed (m/s at scale 1) each
  was made for, so the game moves the body at that speed and the feet do not slide.
- Traversal clips carry root motion on the `Root` bone (exported, no skin weights). Use it as the
  root motion track (Godot: AnimationTree.root_motion_track = "Skeleton3D:Root"; three.js: read
  the Root track and move the object). The manifest records each clip's total root offset.
"""
import math

from mathutils import Quaternion, Vector

from core import ease, pulse, wave
import human
from human import arm, curl, step

FWD = -1.0          # the model faces -Y


def smooth(t, a, b):
    return ease(min(1.0, max(0.0, (t - a) / (b - a))))


# ----------------------------------------------------------------------------- pose blending
def snapshot(P, fn, *args):
    """Run a pose function on a clean rig and return {bone: (quat, loc, scale)} for every bone it
    touched (others are at rest)."""
    P.begin()
    before = {name: set(kinds) for name, kinds in P.touched.items()}
    P.touched.clear()
    fn(*args, P)
    out = {}
    for name in P.touched:
        pb = P.bones[name]
        out[name] = (pb.rotation_quaternion.copy(), pb.location.copy(), pb.scale.copy())
    P.begin()
    for name, kinds in before.items():
        P.touched.setdefault(name, set()).update(kinds)
    return out


def apply_blend(P, a, b, w):
    ident = (Quaternion(), Vector(), Vector((1, 1, 1)))
    for name in set(a) | set(b):
        qa, la, sa = a.get(name, ident)
        qb, lb, sb = b.get(name, ident)
        if qa.dot(qb) < 0:
            qb = -qb
        pb = P.bones[name]
        pb.rotation_quaternion = qa.slerp(qb, w)
        pb.location = la.lerp(lb, w)
        pb.scale = sa.lerp(sb, w)
        P.touched.setdefault(name, set()).update(('r', 'l', 's'))


def keys(P, t, seq):
    """seq: [(time, pose_fn(t, P)), ...] with times ascending from 0 to 1. Holds the first/last
    key outside its range and eases between neighbours."""
    if t <= seq[0][0]:
        apply_blend(P, snapshot(P, seq[0][1], t), {}, 0.0)
        return
    for (t0, f0), (t1, f1) in zip(seq, seq[1:]):
        if t <= t1:
            w = ease((t - t0) / max(1e-6, t1 - t0))
            apply_blend(P, snapshot(P, f0, t), snapshot(P, f1, t), w)
            return
    apply_blend(P, snapshot(P, seq[-1][1], t), {}, 0.0)


# ----------------------------------------------------------------------------- clips
def add_game_clips(rig, k):
    """Add the game clips to rig; return the manifest entries."""
    manifest = []

    def clip(name, seconds, fn, loop=False, speed=0.0, root=(0.0, 0.0, 0.0), then=('idle_loop',),
             markers=None, props=None, note=''):
        rig.clip(name, seconds, fn, loop=loop)
        manifest.append(dict(name=name, seconds=round(seconds, 3), loop=loop,
                             speed=round(speed, 3), root_motion=[round(v, 3) for v in root],
                             then=list(then), markers=markers or {}, props=props or {},
                             note=note))

    # ------------------------------------------------------------------ the standing body
    def base(t, P, arms=True, hands=True):
        """The idle: breathing, a slow sway, arms hanging, hands relaxed."""
        breath = wave(t, 0, 2)
        sway = wave(t)
        P.move('Hips', 0.012 * k * sway, 0, -0.012 * k)
        P.turn('Hips', y=0.02 * sway)
        P.turn('Spine1', x=0.012 * breath, y=-0.012 * sway)
        P.turn('Spine2', x=0.018 * breath)
        P.turn('Neck', z=0.06 * wave(t, 0.2), x=-0.01 * breath)
        P.turn('Head', z=0.08 * wave(t, 0.25), x=0.02 * wave(t, 0.4))
        for side, sx in (('L', 1), ('R', -1)):
            P.turn('Shoulder.' + side, y=-sx * 0.02 * breath)
            if arms:
                arm(P, side, fwd=0.03 * wave(t, 0.1 * sx), bend=0.14 + 0.03 * breath)
            if hands:
                curl(P, side, 0.45 + 0.05 * breath)
            P.move('ik_foot.' + side, sx * 0.03 * k, 0, 0)

    def rest(t, P):
        base(0.0, P)

    def at(root, fn=None):
        """A pose with the root moved to `root` (x, y, z)."""
        def pose(t, P):
            (fn or rest)(t, P)
            P.move('Root', *root)
        return pose

    # ------------------------------------------------------------------ locomotion
    def locomotion(stride, lift, stance, arm_swing, elbow, lean, bob, fist):
        def fn(t, P):
            for side, ph in (('L', 0.0), ('R', 0.5)):
                step(P, side, t + ph, k, stride, lift, stance)
                swing = math.sin(math.tau * (t + ph + 0.3))
                arm(P, side, fwd=-arm_swing * swing, bend=elbow - 0.16 * swing, out=0.05 * lean)
                curl(P, side, fist)
            P.move('Hips', 0.014 * k * wave(t, 0.1), 0.0,
                   (-0.014 - bob * 0.5 - bob * math.cos(2 * math.tau * (t + 0.02))) * k)
            P.turn('Hips', x=lean * 0.6, y=0.05 * wave(t, 0.1), z=(0.1 + lean * 0.3) * wave(t, 0.05))
            P.turn('Spine1', x=0.03 + lean * 0.5, z=-0.1 * wave(t, 0.05))
            P.turn('Spine2', x=lean * 0.4, z=-0.1 * wave(t, 0.05))
            P.turn('Neck', x=-lean * 0.8, z=0.08 * wave(t, 0.05))
        return fn

    moving = ('idle_loop', 'walk_loop', 'walk_fast_loop', 'run_loop', 'sprint_loop', 'jump',
              'jump_high', 'jump_grab', 'vault_fence')
    for name, seconds, stride, lift, stance, swing, elbow, lean, bob, fist in (
            ('walk_loop', 1.05, 0.62, 0.10, 0.60, 0.42, 0.28, 0.0, 0.016, 0.35),
            ('walk_fast_loop', 0.86, 0.80, 0.12, 0.58, 0.62, 0.45, 0.06, 0.02, 0.5),
            ('run_loop', 0.68, 0.95, 0.30, 0.36, 0.85, 1.45, 0.14, 0.045, 1.0),
            ('sprint_loop', 0.56, 1.25, 0.38, 0.32, 1.15, 1.6, 0.26, 0.05, 1.0)):
        clip(name, seconds, locomotion(stride, lift, stance, swing, elbow, lean, bob, fist),
             loop=True, speed=stride * k / (stance * seconds), then=moving,
             markers=dict(left_foot_down=0.0, right_foot_down=0.5))

    # ------------------------------------------------------------------ idles
    anywhere = ('*',)
    clip('idle_loop', 4.0, base, loop=True, then=anywhere)

    def idle_look(t, P):
        base(t, P)
        yaw = 0.7 * math.sin(math.tau * t) * (0.55 + 0.45 * math.cos(math.tau * t * 2))
        P.turn('Head', z=yaw * 0.55, x=0.06 * wave(t, 0.1, 2))
        P.turn('Neck', z=yaw * 0.3)
        P.turn('Spine2', z=yaw * 0.12)
    clip('idle_look_loop', 6.0, lambda t, P: keys(P, t, [(0.0, rest), (0.08, idle_look),
                                                        (0.92, idle_look), (1.0, rest)]),
         loop=True, then=anywhere)

    def idle_shift(t, P):
        base(t, P)
        w = math.sin(math.tau * t)
        P.move('Hips', (0.012 * wave(t) + 0.035 * w) * k, 0.0, (-0.012 - 0.01 * abs(w)) * k)
        P.turn('Hips', y=0.06 * w)
        P.turn('Spine1', y=-0.05 * w)
        for side, sx in (('L', 1), ('R', -1)):
            relax = max(0.0, -w * sx)
            P.move('ik_foot.' + side, sx * 0.03 * k, -0.02 * relax * k, 0.015 * relax * k)
            P.turn('ik_foot.' + side, x=0.15 * relax)
    clip('idle_shift_loop', 8.0, idle_shift, loop=True, then=anywhere)

    def tired(t, P):
        base(t, P, arms=False, hands=False)
        breath = wave(t, 0, 3)
        P.move('Hips', 0.0, 0.0, -0.03 * k)
        P.turn('Spine1', x=0.1 + 0.03 * breath)
        P.turn('Spine2', x=0.12 + 0.03 * breath)
        P.turn('Neck', x=0.15)
        P.turn('Head', x=0.12 + 0.03 * breath)
        for side in 'LR':
            P.turn('Shoulder.' + side, x=0.08)
            arm(P, side, fwd=0.08, bend=0.1 + 0.04 * breath)
            curl(P, side, 0.25)
    clip('idle_tired_loop', 4.0, lambda t, P: keys(P, t, [(0.0, rest), (0.15, tired), (0.85, tired),
                                                         (1.0, rest)]), loop=True, then=anywhere)

    def cold(t, P):
        base(t, P, arms=False, hands=False)
        shake = math.sin(math.tau * t * 16)
        P.turn('Spine1', x=0.12)
        P.turn('Spine2', x=0.14 + 0.01 * shake)
        P.turn('Head', x=0.12, z=0.015 * shake)
        for side, sx in (('L', 1), ('R', -1)):
            arm(P, side, fwd=0.85, bend=2.0, out=-0.25)
            P.turn('ForeArm.' + side, z=-sx * 0.9)
            curl(P, side, 0.9)
    clip('idle_cold_loop', 2.0, cold, loop=True, then=anywhere,
         note='Not idle-shaped: cross-fade 0.3 s in and out.')

    # ------------------------------------------------------------------ jumps
    def crouch(depth, arms_back=0.9):
        def pose(t, P):
            base(0.0, P, arms=False)
            P.move('Hips', 0.0, 0.05 * k, (-0.012 - depth) * k)
            P.turn('Hips', x=0.35)
            P.turn('Spine1', x=0.25)
            P.turn('Spine2', x=0.15)
            P.turn('Neck', x=-0.3)
            for side in 'LR':
                arm(P, side, fwd=-arms_back, bend=0.6)
        return pose

    def airborne(height, reach=2.4):
        def pose(t, P):
            base(0.0, P, arms=False)
            P.move('Hips', 0.0, 0.0, height * k)
            P.turn('Spine1', x=-0.1)
            P.turn('Spine2', x=-0.08)
            for side, sx in (('L', 1), ('R', -1)):
                arm(P, side, fwd=reach, bend=0.2, out=0.1)
                P.move('ik_foot.' + side, sx * 0.03 * k, 0.05 * k, height * 0.85 * k)
                P.turn('ik_foot.' + side, x=0.6)
        return pose

    def jump_clip(height, depth):
        return lambda t, P: keys(P, t, [(0.0, rest), (0.28, crouch(depth)), (0.36, crouch(depth * 0.6, -0.5)),
                                        (0.52, airborne(height)), (0.68, crouch(depth * 0.7, -0.2)),
                                        (1.0, rest)])
    clip('jump', 1.3, jump_clip(0.42, 0.28), then=('idle_loop', 'walk_loop', 'run_loop'),
         markers=dict(take_off=0.36, land=0.68))
    clip('jump_high', 1.6, jump_clip(0.7, 0.4), then=('idle_loop', 'walk_loop', 'run_loop'),
         markers=dict(take_off=0.36, land=0.68))

    # ------------------------------------------------------------------ ledge: grab, hang, climb
    # The ledge top is 2.3 m x scale above the floor, its face 0.25 m in front.
    ledge = 2.3 * k
    hang_up = 0.42 * k

    def hang(sway=0.0):
        def pose(t, P):
            s = sway * math.sin(math.tau * t)
            P.move('Root', 0, 0, hang_up)
            P.move('Hips', 0, 0.02 * k, 0.0)
            P.turn('Hips', x=0.05 * s)
            P.turn('Spine1', x=-0.05)
            P.turn('Head', x=-0.25, z=0.1 * sway * wave(t, 0.3))
            for side, sx in (('L', 1), ('R', -1)):
                P.turn('UpperArm.' + side, x=-0.25, y=sx * (human.REST_DOWN - 2.95))
                P.turn('ForeArm.' + side, x=-0.15)
                curl(P, side, 1.2, thumb=0.8)
                P.move('ik_foot.' + side, sx * 0.03 * k, (0.05 + 0.03 * s) * k, 0.06 * k)
                P.turn('ik_foot.' + side, x=-0.4)
        return pose

    def reach_up(t, P):
        airborne(0.35, 2.9)(t, P)
        P.move('Root', 0, 0, hang_up * 0.8)
    clip('jump_grab', 1.4, lambda t, P: keys(P, t, [(0.0, rest), (0.28, crouch(0.3)),
                                                    (0.36, crouch(0.18, -0.6)), (0.6, reach_up),
                                                    (0.78, hang(0.6)), (1.0, hang())]),
         root=(0, 0, hang_up), then=('hang_loop', 'climb_up', 'drop_from_hang'),
         markers=dict(take_off=0.36, grab=0.72),
         note='Ledge top 2.3 m x scale above the floor, ledge face 0.25 m in front.')
    clip('hang_loop', 3.0, hang(0.25), loop=True, then=('climb_up', 'drop_from_hang'))

    climb_fwd = 0.45 * k

    def pull(t, P):
        hang()(t, P)
        P.move('Root', 0, FWD * 0.05 * k, hang_up + 0.45 * (ledge - hang_up) * 0.6)
        P.turn('Spine1', x=0.3)
        P.turn('Head', x=0.1)
        for side, sx in (('L', 1), ('R', -1)):
            P.turn('UpperArm.' + side, x=-0.25, y=sx * (human.REST_DOWN - 1.6))
            P.turn('ForeArm.' + side, x=-1.9)

    def mantle(t, P):
        base(0.0, P, arms=False)
        P.move('Root', 0, FWD * 0.2 * k, ledge - 0.55 * k)
        P.move('Hips', 0, 0.08 * k, 0.1 * k)
        P.turn('Hips', x=0.7)
        P.turn('Spine1', x=0.35)
        P.turn('Spine2', x=0.2)
        for side, sx in (('L', 1), ('R', -1)):
            arm(P, side, fwd=0.35, bend=0.2, out=0.15)
            curl(P, side, 0.1)
            knee = 1.0 if side == 'R' else 0.3
            P.move('ik_foot.' + side, sx * 0.05 * k, -0.25 * knee * k, (0.15 + 0.5 * knee) * k)
            P.turn('ik_foot.' + side, x=0.7 * knee)

    def kneel_on_ledge(t, P):
        base(0.0, P, arms=False)
        P.move('Root', 0, FWD * 0.38 * k, ledge)
        P.move('Hips', 0, 0.05 * k, -0.4 * k)
        P.turn('Hips', x=0.4)
        P.turn('Spine1', x=0.25)
        for side, sx in (('L', 1), ('R', -1)):
            arm(P, side, fwd=0.6, bend=0.4)
            P.move('ik_foot.' + side, sx * 0.05 * k, (0.25 if side == 'L' else -0.05) * k,
                   (0.05 if side == 'L' else 0.0) * k)
            P.turn('ik_foot.' + side, x=1.2 if side == 'L' else 0.0)
    clip('climb_up', 2.4, lambda t, P: keys(P, t, [(0.0, hang()), (0.3, pull), (0.55, mantle),
                                                   (0.78, kneel_on_ledge),
                                                   (1.0, at((0, FWD * climb_fwd, ledge)))]),
         root=(0, FWD * climb_fwd, ledge - hang_up), markers=dict(knee_on_ledge=0.55, standing=0.95))

    def falling(t, P):
        airborne(0.05, 2.2)(t, P)
        P.move('Root', 0, 0, hang_up * 0.3)
    clip('drop_from_hang', 1.2, lambda t, P: keys(P, t, [(0.0, hang()), (0.25, falling),
                                                         (0.45, at((0, 0, -0.0), crouch(0.3, -0.3))),
                                                         (1.0, rest)]),
         root=(0, 0, -hang_up), markers=dict(land=0.45),
         note='Ends on the floor under the ledge (root back to 0 from the hang).')

    # ------------------------------------------------------------------ fence vault
    vault_fwd = 1.6 * k

    def plant(t, P):
        base(0.0, P, arms=False)
        P.move('Root', 0, FWD * 0.55 * k, 0.15 * k)
        P.move('Hips', 0, 0.04 * k, -0.15 * k)
        P.turn('Hips', x=0.3)
        P.turn('Spine1', x=0.3, z=0.15)
        arm(P, 'L', fwd=1.1, bend=0.1, out=0.15)
        arm(P, 'R', fwd=-0.3, bend=0.4, out=0.3)
        for side, sx in (('L', 1), ('R', -1)):
            P.move('ik_foot.' + side, sx * 0.05 * k, (0.15 if side == 'R' else -0.05) * k, 0)

    def over(t, P):
        base(0.0, P, arms=False)
        P.move('Root', 0, FWD * 0.9 * k, 0.55 * k)
        P.move('Hips', -0.08 * k, 0, 0.0)
        P.turn('Hips', x=0.4, z=-0.6)
        P.turn('Spine1', x=0.25, z=0.25)
        P.turn('Spine2', z=0.2)
        arm(P, 'L', fwd=1.0, bend=0.05, out=0.25)
        curl(P, 'L', 0.6)
        arm(P, 'R', fwd=0.2, bend=0.5, out=0.8)
        for side, sx in (('L', 1), ('R', -1)):
            P.move('ik_foot.' + side, (sx * 0.03 - 0.3) * k, -0.1 * k, (0.42 if side == 'R' else 0.34) * k)
            P.turn('ik_foot.' + side, x=0.5)

    def land_at(root):
        return at(root, crouch(0.22, -0.4))
    clip('vault_fence', 1.5, lambda t, P: keys(P, t, [(0.0, rest), (0.3, plant), (0.5, over),
                                                      (0.72, land_at((0, FWD * 1.4 * k, 0))),
                                                      (1.0, at((0, FWD * vault_fwd, 0)))]),
         root=(0, FWD * vault_fwd, 0), then=('idle_loop', 'walk_loop', 'run_loop'),
         markers=dict(hand_on_rail=0.3, land=0.72),
         note='Fence or rail about 1.0 m x scale high, 0.6 m in front.')

    # ------------------------------------------------------------------ horse
    # Mount from the horse's left flank: the character faces the same way as the horse, the
    # saddle 0.45 m to the right (-X), the seat 1.5 m x scale up (root rises 0.58 m).
    seat = (-0.45 * k, 0.0, 0.58 * k)

    def ride(trot=0.0):
        def pose(t, P):
            P.move('Root', *seat)
            bounce = abs(math.sin(math.tau * t * 2)) * trot
            P.move('Hips', 0, 0.04 * k, (-0.33 + 0.03 * bounce) * k)
            P.turn('Hips', x=-0.12)
            P.turn('Spine1', x=0.06 + 0.03 * bounce)
            P.turn('Head', z=0.08 * wave(t, 0.2))
            for side, sx in (('L', 1), ('R', -1)):
                arm(P, side, fwd=0.6, bend=1.05, out=0.05)
                curl(P, side, 1.0)
                P.move('ik_foot.' + side, sx * 0.2 * k, -0.15 * k, 0.12 * k)
                P.turn('ik_foot.' + side, x=-0.1, z=sx * 0.2)
        return pose

    def stirrup(t, P):
        base(0.0, P, arms=False)
        P.turn('Spine1', x=0.1, z=-0.15)
        arm(P, 'L', fwd=1.4, bend=0.5, out=-0.1)
        arm(P, 'R', fwd=1.2, bend=0.5, out=-0.25)
        curl(P, 'L', 1.0)
        curl(P, 'R', 0.9)
        P.move('ik_foot.L', 0.0, -0.05 * k, 0.5 * k)
        P.turn('ik_foot.L', x=-0.2)
        P.move('ik_foot.R', -0.03 * k, 0, 0)

    def push_up(t, P):
        base(0.0, P, arms=False)
        P.move('Root', seat[0] * 0.3, 0, seat[2] * 0.85)
        P.turn('Spine1', x=0.3, z=-0.2)
        arm(P, 'L', fwd=0.9, bend=0.2, out=-0.1)
        arm(P, 'R', fwd=0.7, bend=0.2, out=-0.3)
        curl(P, 'L', 1.0)
        curl(P, 'R', 0.9)
        P.move('ik_foot.L', 0.0, -0.05 * k, 0.02 * k)
        P.move('ik_foot.R', -0.05 * k, 0.05 * k, 0.1 * k)

    def leg_over(t, P):
        base(0.0, P, arms=False)
        P.move('Root', seat[0] * 0.7, 0, seat[2] * 0.95)
        P.turn('Spine1', x=0.35, z=-0.1)
        arm(P, 'L', fwd=0.8, bend=0.4)
        arm(P, 'R', fwd=0.8, bend=0.4, out=-0.2)
        curl(P, 'L', 1.0)
        curl(P, 'R', 1.0)
        P.move('ik_foot.L', 0.0, -0.05 * k, 0.02 * k)
        P.move('ik_foot.R', -0.45 * k, 0.2 * k, 0.55 * k)
    mount_keys = [(0.0, rest), (0.25, stirrup), (0.5, push_up), (0.75, leg_over), (1.0, ride())]
    clip('mount_horse', 3.0, lambda t, P: keys(P, t, mount_keys), root=seat,
         then=('ride_loop', 'ride_trot_loop', 'dismount_horse'),
         markers=dict(foot_in_stirrup=0.25, seated=1.0),
         note='Mount from the left flank; seat 0.45 m to the right, 1.5 m x scale high.')
    clip('ride_loop', 2.0, ride(0.2), loop=True, then=('ride_trot_loop', 'dismount_horse'))
    clip('ride_trot_loop', 1.0, ride(1.0), loop=True, then=('ride_loop', 'dismount_horse'))
    back = [(1.0 - tt, fn) for tt, fn in reversed(mount_keys)]
    clip('dismount_horse', 2.4, lambda t, P: keys(P, t, back),
         root=tuple(-v for v in seat), markers=dict(feet_down=0.9))

    # ------------------------------------------------------------------ cart
    bed_up, bed_fwd = 0.9 * k, 0.7 * k

    def tailboard(t, P):
        base(0.0, P, arms=False)
        P.move('Root', 0, FWD * 0.1 * k, 0)
        P.turn('Spine1', x=0.3)
        for side in 'LR':
            arm(P, side, fwd=1.25, bend=0.3)
            curl(P, side, 1.0)

    def knee_up(t, P):
        base(0.0, P, arms=False)
        P.move('Root', 0, FWD * 0.25 * k, 0.35 * k)
        P.move('Hips', 0, 0.06 * k, -0.25 * k)
        P.turn('Hips', x=0.6)
        P.turn('Spine1', x=0.35)
        for side, sx in (('L', 1), ('R', -1)):
            arm(P, side, fwd=0.9, bend=0.15)
            curl(P, side, 0.9)
            P.move('ik_foot.' + side, sx * 0.04 * k, (-0.25 if side == 'R' else 0.0) * k,
                   (0.55 if side == 'R' else -0.35) * k)
            P.turn('ik_foot.' + side, x=0.8 if side == 'R' else 0.0)

    def on_bed(t, P):
        base(0.0, P, arms=False)
        P.move('Root', 0, FWD * 0.5 * k, bed_up)
        P.move('Hips', 0, 0.05 * k, -0.4 * k)
        P.turn('Hips', x=0.5)
        P.turn('Spine1', x=0.25)
        for side, sx in (('L', 1), ('R', -1)):
            arm(P, side, fwd=0.7, bend=0.3)
            P.move('ik_foot.' + side, sx * 0.04 * k, (0.25 if side == 'L' else -0.05) * k,
                   (0.05 if side == 'L' else 0.0) * k)
            P.turn('ik_foot.' + side, x=1.2 if side == 'L' else 0.0)
    clip('climb_into_cart', 2.6, lambda t, P: keys(P, t, [(0.0, rest), (0.2, tailboard),
                                                          (0.45, knee_up), (0.7, on_bed),
                                                          (1.0, at((0, FWD * bed_fwd, bed_up)))]),
         root=(0, FWD * bed_fwd, bed_up),
         markers=dict(hands_on_tailboard=0.2, knee_on_bed=0.45, standing=0.95),
         note='Cart bed 0.9 m x scale high, tailboard 0.3 m in front.')

    # ------------------------------------------------------------------ work tasks
    def axe_up(t, P):
        base(0.0, P, arms=False, hands=False)
        P.move('Hips', 0, 0, -0.06 * k)
        P.turn('Hips', z=0.25)
        P.turn('Spine1', z=0.3, x=0.05)
        P.turn('Spine2', z=0.25, y=-0.15)
        P.turn('Head', z=-0.2)
        arm(P, 'R', fwd=2.5, bend=1.7, out=0.4)
        arm(P, 'L', fwd=2.3, bend=1.7, out=-0.1)
        curl(P, 'R', 1.2, thumb=0.9)
        curl(P, 'L', 1.2, thumb=0.9)
        for side, sx in (('L', 1), ('R', -1)):
            P.move('ik_foot.' + side, sx * 0.14 * k, (0.06 if side == 'R' else -0.06) * k, 0)

    def axe_hit(t, P):
        base(0.0, P, arms=False, hands=False)
        P.move('Hips', 0, 0, -0.08 * k)
        P.turn('Hips', z=0.1, x=0.1)
        P.turn('Spine1', z=-0.05, x=0.35)
        P.turn('Spine2', z=-0.05, x=0.1)
        P.turn('Head', z=0.15, x=0.15)
        arm(P, 'R', fwd=1.2, bend=0.2, out=-0.1)
        arm(P, 'L', fwd=1.3, bend=0.4, out=-0.3)
        curl(P, 'R', 1.2, thumb=0.9)
        curl(P, 'L', 1.2, thumb=0.9)
        for side, sx in (('L', 1), ('R', -1)):
            P.move('ik_foot.' + side, sx * 0.14 * k, (0.06 if side == 'R' else -0.06) * k, 0)
    chop_keys = [(0.0, axe_hit), (0.45, axe_up), (0.55, axe_up), (0.62, axe_hit), (1.0, axe_hit)]
    clip('chop_tree_loop', 1.6, lambda t, P: keys(P, t, chop_keys), loop=True,
         markers=dict(hit=0.62), props=dict(right_hand='axe', left_hand='axe shaft'),
         note='Trunk at waist height, 0.7 m in front, a little to the left. Cross-fade 0.3 s in.')

    def stir(t, P):
        base(t, P, arms=False, hands=False)
        a = math.tau * t * 2
        P.turn('Spine1', x=0.18)
        P.turn('Spine2', x=0.1 + 0.02 * math.sin(a))
        P.turn('Head', x=0.3)
        arm(P, 'R', fwd=0.8 + 0.12 * math.sin(a), bend=1.25 + 0.2 * math.cos(a),
            out=-0.12 + 0.12 * math.cos(a))
        P.turn('Hand.R', x=0.2 * math.sin(a))
        curl(P, 'R', 1.1, thumb=0.8)
        arm(P, 'L', fwd=0.7, bend=1.3, out=-0.2)
        curl(P, 'L', 1.0)
    clip('cook_stir_loop', 3.0, stir, loop=True, props=dict(right_hand='spoon'),
         note='Pot at waist height, 0.4 m in front. Cross-fade 0.3 s in.')

    def stoop(depth, grab):
        def pose(t, P):
            base(0.0, P, arms=False, hands=False)
            P.move('Hips', 0, 0.12 * k, -depth * k)
            P.turn('Hips', x=0.55)
            P.turn('Spine1', x=0.3)
            P.turn('Spine2', x=0.2)
            P.turn('Head', x=0.15)
            arm(P, 'R', fwd=1.0, bend=0.2, out=0.1)
            curl(P, 'R', 0.3 + 0.9 * grab)
            arm(P, 'L', fwd=0.5, bend=0.3, out=0.05)
            curl(P, 'L', 0.4)
            for side, sx in (('L', 1), ('R', -1)):
                P.move('ik_foot.' + side, sx * 0.08 * k, (0.1 if side == 'L' else -0.05) * k, 0)
                P.turn('ik_foot.' + side, x=0.25 if side == 'L' else 0.0)
        return pose

    def holding(t, P):
        base(0.0, P, arms=False, hands=False)
        arm(P, 'R', fwd=0.6, bend=1.3)
        curl(P, 'R', 1.2)
        arm(P, 'L', bend=0.14)
        curl(P, 'L', 0.45)
    clip('pick_plant', 3.0, lambda t, P: keys(P, t, [(0.0, rest), (0.32, stoop(0.55, 0)),
                                                     (0.4, stoop(0.55, 1)), (0.52, stoop(0.5, 1)),
                                                     (0.75, holding), (1.0, rest)]),
         markers=dict(grab=0.4, pull=0.52), props=dict(right_hand='plant, from 0.4'))
    clip('pick_up', 2.2, lambda t, P: keys(P, t, [(0.0, rest), (0.32, stoop(0.45, 0)),
                                                  (0.42, stoop(0.45, 1)), (0.7, holding),
                                                  (1.0, rest)]),
         markers=dict(grab=0.42), props=dict(right_hand='stone or stick, from 0.42'),
         note='Ends at rest with the hand closed round nothing: hide or drop the prop by 0.9.')

    # ------------------------------------------------------------------ conversation
    def talk(t, P):
        base(t, P, arms=False, hands=False)
        g1 = max(0, math.sin(math.tau * t * 2)) ** 2
        g2 = max(0, math.sin(math.tau * (t * 3 + 0.3))) ** 2
        arm(P, 'R', fwd=0.55 + 0.2 * g1, bend=1.2 + 0.3 * g1, out=0.1 + 0.15 * g1)
        arm(P, 'L', fwd=0.3 + 0.25 * g2, bend=0.9 + 0.4 * g2, out=0.05)
        P.turn('Hand.R', z=-0.5 * g1, x=-0.3)
        P.turn('Hand.L', z=0.4 * g2, x=-0.2)
        curl(P, 'R', 0.25 + 0.2 * g2)
        curl(P, 'L', 0.3 + 0.2 * g1)
        P.turn('Head', x=0.07 * math.sin(math.tau * t * 4), z=0.1 * wave(t, 0.1))
        P.turn('Jaw', x=0.12 * abs(math.sin(math.tau * t * 7)) * (0.5 + 0.5 * g1))

    def listen(t, P):
        base(t, P, arms=False, hands=False)
        nod = max(0.0, math.sin(math.tau * t * 2)) ** 3 * pulse(t, 0.1, 0.2, 0.6, 0.7)
        P.turn('Head', x=0.12 * nod, z=0.06 * wave(t, 0.2))
        for side in 'LR':
            arm(P, side, fwd=0.35, bend=1.0, out=-0.15)
            curl(P, side, 0.5)

    def fade_loop(fn, edge=0.12):
        return lambda t, P: keys(P, t, [(0.0, rest), (edge, fn), (1 - edge, fn), (1.0, rest)])
    clip('talk_loop', 4.0, fade_loop(talk), loop=True, then=anywhere)
    clip('listen_loop', 5.0, fade_loop(listen), loop=True, then=anywhere)

    def gesture(arms_fn, head_fn=None):
        def full(t, P):
            base(t * 0.0, P, arms=False, hands=False)
            arms_fn(t, P)
            if head_fn:
                head_fn(t, P)
        return lambda t, P: keys(P, t, [(0.0, rest), (0.2, full), (0.8, full), (1.0, rest)])

    def explain(t, P):
        g = 0.5 + 0.5 * math.sin(math.tau * t * 2.5)
        for side, sx in (('L', 1), ('R', -1)):
            arm(P, side, fwd=0.75, bend=1.3, out=0.05 + 0.15 * g)
            P.turn('Hand.' + side, y=sx * 0.9)
            curl(P, side, 0.15)
        P.turn('Head', x=0.05 * math.sin(math.tau * t * 4))
        P.turn('Jaw', x=0.1 * abs(math.sin(math.tau * t * 6)))

    def agree(t, P):
        P.turn('Head', x=0.18 * math.sin(math.tau * t * 3))
        arm(P, 'R', fwd=0.5, bend=1.2, out=0.15)
        P.turn('Hand.R', y=-0.8)
        curl(P, 'R', 0.15)
        arm(P, 'L', bend=0.14)
        curl(P, 'L', 0.45)

    def disagree(t, P):
        shake = math.sin(math.tau * t * 3.5)
        P.turn('Head', z=0.3 * shake)
        arm(P, 'R', fwd=0.6, bend=1.4, out=0.2 + 0.15 * shake)
        P.turn('Hand.R', z=0.3 * shake)
        curl(P, 'R', 0.1)
        arm(P, 'L', bend=0.14)
        curl(P, 'L', 0.45)

    def shrug(t, P):
        for side, sx in (('L', 1), ('R', -1)):
            P.turn('Shoulder.' + side, y=sx * 0.25)
            arm(P, side, fwd=0.45, bend=1.5, out=0.3)
            P.turn('Hand.' + side, y=sx * 1.2)
            curl(P, side, 0.1)
        P.turn('Head', z=0.15, x=-0.05)

    def beckon(t, P):
        come = max(0.0, math.sin(math.tau * t * 3))
        arm(P, 'R', fwd=1.0, bend=1.1, out=0.1)
        P.turn('Hand.R', y=-1.2, x=-0.6 * come)
        curl(P, 'R', 0.2 + 1.0 * come)
        arm(P, 'L', bend=0.14)
        curl(P, 'L', 0.45)
        P.turn('Head', x=-0.08 * come, z=-0.1)

    def point(t, P):
        arm(P, 'R', fwd=1.45, bend=0.0, out=0.12)
        curl(P, 'R', 1.35)
        for i in (1, 2, 3):
            P.turn('Index%d.R' % i, y=0.0)
        arm(P, 'L', bend=0.14)
        curl(P, 'L', 0.45)
        P.turn('Spine2', z=0.12)
        P.turn('Head', z=0.1)

    def greet(t, P):
        P.turn('UpperArm.R', y=-0.2 + 2.25 - human.REST_DOWN)
        P.turn('ForeArm.R', y=0.5 + 0.45 * math.sin(math.tau * t * 4), x=-0.3)
        curl(P, 'R', 0.05)
        arm(P, 'L', bend=0.14)
        curl(P, 'L', 0.45)
        P.turn('Head', z=-0.12, y=0.06)

    def bow(t, P):
        P.turn('Hips', x=0.35)
        P.turn('Spine1', x=0.25)
        P.turn('Head', x=0.2)
        for side in 'LR':
            arm(P, side, fwd=0.25, bend=0.2)
            curl(P, side, 0.45)

    for name, seconds, fn in (('gesture_explain', 3.2, explain), ('gesture_agree', 2.0, agree),
                              ('gesture_disagree', 2.0, disagree), ('gesture_shrug', 2.0, shrug),
                              ('gesture_beckon', 2.4, beckon), ('gesture_point', 2.6, point),
                              ('gesture_wave', 2.8, greet), ('gesture_bow', 2.4, bow)):
        clip(name, seconds, gesture(fn), then=('idle_loop', 'talk_loop', 'listen_loop'))

    # ------------------------------------------------------------------ begging
    def beg(t, P):
        bob = math.sin(math.tau * t)
        P.move('Hips', 0, -0.12 * k, -0.5 * k)
        P.turn('Hips', x=-0.05)
        P.turn('Spine1', x=0.18 + 0.03 * bob)
        P.turn('Spine2', x=0.12)
        P.turn('Head', x=0.1 - 0.25 * max(0.0, bob), z=0.1 * wave(t, 0.3))
        for side, sx in (('L', 1), ('R', -1)):
            P.move('ik_foot.' + side, sx * 0.04 * k, 0.3 * k, 0.03 * k)
            P.turn('ik_foot.' + side, x=1.35)
        arm(P, 'R', fwd=0.95 + 0.1 * bob, bend=0.5, out=0.15)
        P.turn('Hand.R', y=-1.3)
        curl(P, 'R', 0.25)
        arm(P, 'L', fwd=0.4, bend=1.3, out=-0.1)
        curl(P, 'L', 0.7)
    clip('kneel_down', 1.4, lambda t, P: keys(P, t, [(0.0, rest), (0.5, stoop(0.35, 0)),
                                                     (1.0, beg)]),
         then=('beg_kneel_loop', 'stand_up_from_kneel'))
    clip('beg_kneel_loop', 4.0, beg, loop=True, then=('stand_up_from_kneel',))
    clip('stand_up_from_kneel', 1.4, lambda t, P: keys(P, t, [(0.0, beg), (0.5, stoop(0.35, 0)),
                                                              (1.0, rest)]))
    return manifest
