"""The Shard family: creatures made of broken grey plates around a light, with a cross for one
eye, a square for the other, a saw of teeth and a red tongue. Derived from the Ruralive mark."""
import math
import random

import bmesh
import bpy
from core import (Rig, Vector, activate, box, ease, from_bmesh, place, prism, pulse, shade, tag,
                  wave, ico, new_object)
import materials as M

TAU = math.tau
DARK = {'preview_dark': False, 'preview_angle': 0, 'preview_elevation': 2}


def mats():
    return dict(plate=M.plastic('#3d3e41', 'plate', 0.62),
                white=M.emissive('#ffffff', 'white', 1.4, '#ffffff'),
                tongue=M.plastic('#b8414c', 'tongue', 0.42),
                core=M.emissive('#ffffff', 'core', 1.3, '#f4f4f2'),
                groove=M.emissive('#ffffff', 'groove', 1.4, '#ffffff'))


# The mark, traced plate by plate: each polygon is in the picture's own pixels (637 wide, y down).
PLATES = [
    [(165, 15), (360, 10), (345, 150)],
    [(385, 5), (530, 85), (370, 65)],
    [(95, 75), (185, 45), (235, 80)],
    [(65, 90), (240, 95), (235, 245), (70, 255)],           # 3: holds the cross
    [(15, 135), (50, 130), (60, 265), (0, 268)],
    [(255, 110), (330, 165), (305, 335), (232, 340)],
    [(478, 100), (548, 240), (335, 255)],                   # 6: holds the square
    [(350, 75), (458, 92), (340, 240)],
    [(510, 95), (595, 110), (575, 255), (545, 160)],
    [(605, 175), (637, 180), (630, 300), (600, 265)],
    [(5, 285), (178, 262), (175, 275), (12, 330)],
    [(85, 325), (200, 290), (222, 355)],
    [(358, 250), (480, 320), (310, 360)],
    [(395, 255), (555, 243), (560, 330), (500, 315)],
    [(570, 270), (622, 320), (570, 325)],
    [(12, 345), (62, 330), (48, 470)],
    [(85, 343), (140, 380), (105, 410)],
    [(75, 400), (150, 480), (78, 470)],
    [(80, 490), (145, 515), (125, 545)],
    [(575, 340), (620, 335), (600, 460)],
    [(500, 430), (560, 410), (565, 440)],
    [(482, 435), (575, 465), (472, 490)],
    [(398, 522), (555, 490), (410, 580)],
    [(345, 535), (380, 540), (378, 578), (285, 592)],
]
TEETH = [
    [(160, 358), (222, 360), (182, 432)],
    [(250, 375), (305, 372), (290, 440)],
    [(318, 368), (378, 360), (352, 418)],
    [(388, 355), (440, 348), (425, 420)],
    [(470, 345), (515, 335), (498, 395)],
    [(522, 390), (560, 372), (545, 440)],
]
TONGUE = [(240, 378), (300, 440), (345, 415), (370, 455), (385, 385), (408, 400), (375, 480),
          (250, 618), (150, 612), (143, 545), (180, 455)]
GROOVE = ((268, 478), [(215, 578), (325, 455), (185, 450)])
LOWER = {15, 16, 17, 18, 19, 20, 21, 22, 23}


def on_ball(p, radius, lift=1.0):
    """A point of the picture laid on the front of a ball."""
    u, v = (p[0] - 318.5) / 330.0, (318.5 - p[1]) / 330.0
    d = min(0.985, math.hypot(u, v))
    if d > 1e-6:
        a = d * 1.22
        u, v = u / d * math.sin(a), v / d * math.sin(a)
        y = -math.cos(a)
    else:
        y = -1.0
    return Vector((u, y, v)) * radius * lift


def plate(points, radius, mat, thick=0.09, lift=1.0, inset=0.0):
    """One flat plate: the outline on the ball, with a back face further in."""
    front = [on_ball(p, radius, lift) for p in points]
    mid = sum(front, Vector()) / len(front)
    front = [mid + (p - mid) * (1 - inset) for p in front]
    back = [p * (1 - thick) for p in front]
    n = len(front)
    faces = [list(range(n)), list(range(2 * n - 1, n - 1, -1))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    o = new_object('plate', front + back, faces, mat, smooth=False)
    from core import fix_normals
    fix_normals(o)
    return shade(o, False), mid.normalized()


def shell(rig, k, centre, radius, parent, prefix='Shard', pieces=30, bones=18, seed=3, gap=0.86,
          mouth=True):
    """The mark on the front of a ball, broken plates behind. Returns (parts, bones, jaw, dirs)."""
    rnd = random.Random(seed)
    c = Vector(centre)
    dirs = [on_ball(sum((Vector((p[0], p[1], 0)) for p in poly), Vector()) / len(poly),
                    1.0).normalized() for poly in PLATES]
    while len(dirs) < len(PLATES) + 8:
        d = Vector((rnd.uniform(-1, 1), rnd.uniform(0.2, 1), rnd.uniform(-1, 1)))
        if 0.3 < d.length < 1:
            dirs.append(d.normalized())
    names = []
    for i, d in enumerate(dirs):
        n = '%s.%02d' % (prefix, i)
        rig.bone(n, c + d * radius * 0.6, c + d * radius, parent)
        names.append(n)
    jaw = prefix + '.Jaw'
    rig.bone(jaw, c + Vector((0, 0.2 * radius, -0.2 * radius)), c + Vector(
        (0, -radius, -0.55 * radius)), parent)
    parts = []
    for i, poly in enumerate(PLATES):
        o, _ = plate(poly, radius, k['plate'])
        parts.append(tag(place(o, c), names[i]))
    for poly in TEETH:
        o, _ = plate(poly, radius, k['plate'], 0.07, 1.012)
        parts.append(tag(place(o, c), parent))
    # the back of the head: plates cut from a ball, as before
    seeds = []
    while len(seeds) < pieces:
        d = Vector((rnd.uniform(-1, 1), rnd.uniform(-0.2, 1), rnd.uniform(-1, 1)))
        if 0.2 < d.length < 1:
            seeds.append(d.normalized())
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=radius * 0.985)
    groups = {}
    for f in bm.faces:
        n = f.calc_center_median().normalized()
        if n.y < -0.36:
            continue
        groups.setdefault(max(range(pieces), key=lambda i: seeds[i].dot(n)), []).append(
            [v.co.copy() for v in f.verts])
    bm.free()
    for i, faces in groups.items():
        mid = sum((sum(f, Vector()) / 3 for f in faces), Vector()) / len(faces)
        nd = mid.normalized()
        verts, tris = [], []
        for f in faces:
            base = len(verts)
            verts += [mid + (p - mid) * gap for p in f]
            tris.append((base, base + 1, base + 2))
        o = new_object('plate', verts, tris, k['plate'], smooth=False)
        activate(o)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=1e-4)
        bpy.ops.mesh.dissolve_limited(angle_limit=0.5)
        bpy.ops.object.mode_set(mode='OBJECT')
        mod = o.modifiers.new('s', 'SOLIDIFY')
        mod.thickness = radius * 0.09
        mod.offset = -1
        bpy.ops.object.modifier_apply(modifier='s')
        shade(o, False)
        place(o, c)
        parts.append(tag(o, names[max(range(len(dirs)), key=lambda b: dirs[b].dot(nd))]))
    core = ico(radius * 0.86, c, 3, material=k['core'])
    parts.append(tag(core, parent))
    return parts, names, jaw, dirs


def face(rig, k, centre, radius, parent, jaw, prefix=''):
    """The cross set in its square plate, the square in its triangle, and the tongue."""
    c = Vector(centre)
    r = radius
    parts = []
    cross = [[(98, 122), (126, 100), (212, 205), (184, 228)],
             [(184, 100), (212, 122), (126, 228), (98, 205)]]
    for poly in cross:
        o, _ = plate(poly, r, k['white'], 0.03, 1.012)
        parts.append(tag(place(o, c), prefix + 'Shard.03' if prefix else 'Shard.03'))
    o, _ = plate([(428, 178), (468, 170), (476, 208), (436, 216)], r, k['white'], 0.03, 1.012)
    parts.append(tag(place(o, c), 'Shard.06'))
    # the tongue hangs out of the picture, so it gets real thickness and its own bones
    path = [(300, 395), (290, 440), (268, 490), (240, 540), (212, 585), (190, 622)]

    def hang(q):
        t = min(1.0, max(0.0, (-(q - c).z / r + 0.15) / 0.8))
        return q + Vector((0, -0.34 * r * t * t, -0.06 * r * t))
    pts = [hang(c + on_ball(p, r, 1.02)) for p in path]
    names = rig.chain(prefix + 'Tongue', pts, jaw)
    from core import join, tube
    pieces = []
    for poly in ([(240, 378), (300, 440), (345, 415), (375, 480), (250, 618), (150, 612),
                  (143, 545), (180, 455)], [(345, 415), (385, 385), (408, 400), (375, 480)]):
        o, _ = plate(poly, r, k['tongue'], 0.1, 1.06)
        activate(o)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.quads_convert_to_tris(ngon_method='BEAUTY')
        bpy.ops.mesh.subdivide(number_cuts=2)
        bpy.ops.object.mode_set(mode='OBJECT')
        shade(o, False)
        place(o, c)
        for v in o.data.vertices:
            v.co = hang(v.co)
        pieces.append(o)
    g0, ends = GROOVE
    for e in ends:
        a, b = c + on_ball(g0, r, 1.075), c + on_ball(e, r, 1.075)
        pieces.append(tube([hang(a.lerp(b, f / 4)) for f in range(5)], 0.016 * r, 6, k['groove']))
    tongue_mesh = join(pieces)
    rig.weight_chain(tongue_mesh, names)
    parts.append(tongue_mesh)
    return parts, names


def breathe(P, names, dirs, t, amount, phase=0.0):
    for i, n in enumerate(names):
        d = dirs[i] * amount * (0.5 + 0.5 * math.sin(TAU * (t + phase + i * 0.137)))
        P.move(n, d.x, d.y, d.z)


def burst(P, names, dirs, amount, spin=0.0):
    for i, n in enumerate(names):
        d = dirs[i] * amount * (0.7 + 0.6 * ((i * 37) % 10) / 10)
        P.move(n, d.x, d.y, d.z)
        P.turn(n, x=spin * dirs[i].y, y=spin * dirs[i].z, z=spin * dirs[i].x)


def tongue(P, names, t, out=1.0, wag=0.3, speed=3, curl=0.0, lift=0.0, stretch=1.0):
    """out 0..1 pulls the tongue in; wag swings it; curl rolls the tip; lift raises it."""
    n = len(names)
    for i, name in enumerate(names):
        f = (i + 1) / n
        P.turn(name, x=0.3 * (1 - out) + curl * (0.35 + 0.9 * f) - lift * (1.2 - f) * 0.5
               + 0.08 * out * math.sin(TAU * (t * speed - 0.14 * i)),
               y=wag * out * (0.4 + f) * math.sin(TAU * (t * speed - 0.14 * i)),
               z=0.5 * wag * out * math.sin(TAU * (t * speed - 0.14 * i + 0.25)))
        P.scale(name, 1, (0.3 + 0.7 * out) * stretch, 1)


def head_clips(rig, names, dirs, jaw, tng, r, body='Head', hover=True):
    def base(t, P, amount=0.05, jaw_open=0.08):
        breathe(P, names, dirs, t, amount * r)
        if hover:
            P.move(body, 0, 0, 0.1 * r * wave(t))
        P.turn(jaw, x=jaw_open)

    def idle(t, P):
        base(t, P, 0.06, 0.05 + 0.04 * wave(t, 0, 2))
        P.turn(body, z=0.2 * wave(t, 0.2), y=0.08 * wave(t, 0.4))
        tongue(P, tng, t, 0.85, 0.1, 1)

    def shatter(t, P):
        b = pulse(t, 0.12, 0.2, 0.55, 0.9)
        burst(P, names, dirs, 1.6 * r * b, 2.5 * b)
        P.turn(jaw, x=0.9 * b)
        P.move(jaw, 0, -0.5 * r * b, -0.9 * r * b)
        tongue(P, tng, t, 1.0, 0.5 * b, 5)

    def chomp(t, P):
        c = abs(math.sin(TAU * t * 2))
        base(t, P, 0.03, 0.55 * c)
        P.turn(body, x=-0.12 * c)
        tongue(P, tng, t, 0.3 + 0.2 * c, 0.1, 2)

    def laugh(t, P):
        ha = max(0, math.sin(TAU * t * 5)) ** 2
        breathe(P, names, dirs, t * 5, 0.1 * r * ha)
        P.turn(body, x=-0.25 + 0.1 * ha, y=0.15 * wave(t))
        P.turn(jaw, x=0.35 + 0.2 * ha)
        tongue(P, tng, t, 0.9, 0.25, 5)

    def sad(t, P):
        base(t, P, 0.02, 0.02)
        P.turn(body, x=0.35, y=0.06 * wave(t))
        P.move(body, 0, 0, -0.2 * r)
        tongue(P, tng, t, 0.95, 0.04, 1, curl=-0.1)

    def angry(t, P):
        sh = math.sin(TAU * t * 12)
        breathe(P, names, dirs, t * 6, 0.12 * r)
        P.turn(body, x=-0.15, z=0.05 * sh)
        P.turn(jaw, x=0.6 + 0.1 * sh)
        tongue(P, tng, t, 0.25, 0.1, 6)

    def surprise(t, P):
        hit = pulse(t, 0.1, 0.18, 0.6, 0.9)
        burst(P, names, dirs, 0.35 * r * hit)
        P.move(body, 0, 0.3 * r * hit, 0.25 * r * hit)
        P.turn(jaw, x=0.75 * hit)
        tongue(P, tng, t, 1.0, 0.0, 1, stretch=1 + 0.5 * hit)

    def spin(t, P):
        base(t, P)
        P.turn(body, z=TAU * t)
        tongue(P, tng, t, 1.0, 0.5, 1, lift=0.3)

    # --- the tongue has a life of its own
    def wag(t, P):
        base(t, P, 0.04, 0.3)
        P.turn(body, y=0.12 * wave(t, 0, 3))
        tongue(P, tng, t, 1.0, 0.75, 3)

    def lick_around(t, P):
        base(t, P, 0.04, 0.35)
        a = TAU * t
        for i, name in enumerate(tng):
            f = (i + 1) / len(tng)
            P.turn(name, x=-0.55 * (0.5 + 0.5 * math.cos(a)) * (1.3 - f), y=0.9 * math.sin(a) * f,
                   z=0.4 * math.sin(a))
        P.turn(body, y=0.15 * math.sin(a))

    def flick(t, P):
        f = max(0.0, math.sin(TAU * t * 4)) ** 3
        base(t, P, 0.03, 0.15 + 0.2 * f)
        tongue(P, tng, t, 0.15 + 0.85 * f, 0.15, 8, lift=0.5 * f, stretch=1 + 0.6 * f)

    def roll(t, P):
        c = pulse(t, 0.1, 0.4, 0.6, 0.9)
        base(t, P, 0.03, 0.3)
        tongue(P, tng, t, 1.0, 0.03, 1, curl=-1.1 * c)

    def hang(t, P):
        base(t, P, 0.03, 0.4)
        P.turn(body, x=0.12, y=0.2 * wave(t))
        tongue(P, tng, t, 1.0, 0.22, 1, stretch=1.25)

    def raspberry(t, P):
        buzz = math.sin(TAU * t * 26)
        on = pulse(t, 0.1, 0.2, 0.75, 0.9)
        base(t, P, 0.04, 0.25)
        P.turn(body, x=-0.1 * on)
        for i, name in enumerate(tng):
            P.turn(name, x=-0.25 * on + 0.1 * on * buzz * (i + 1) / len(tng),
                   y=0.05 * on * math.sin(TAU * t * 31 + i))
            P.scale(name, 1 + 0.06 * on * buzz, 1, 1)

    def whip(t, P):
        back = pulse(t, 0.05, 0.3, 0.32, 0.4)
        out = pulse(t, 0.34, 0.42, 0.5, 0.85)
        base(t, P, 0.03, 0.2 + 0.5 * out)
        P.turn(body, x=0.2 * back - 0.25 * out)
        tongue(P, tng, t, 0.3 + 0.7 * max(out, 1 - back), 0.2 * out, 7, lift=0.9 * out
               - 0.4 * back, curl=-0.7 * back, stretch=1 + 1.6 * out)

    def slurp(t, P):
        pull = ease(min(1.0, t / 0.55))
        back = 1 - pulse(t, 0.0, 0.55, 0.75, 1.0)
        base(t, P, 0.03, 0.35 * back + 0.05)
        tongue(P, tng, t, 0.05 + 0.95 * back, 0.3 * back, 6, curl=-0.6 * pull * back)
        P.turn(body, x=-0.1 * (1 - back))

    def taste(t, P):
        base(t, P, 0.04, 0.3)
        P.turn(body, x=-0.2, z=0.3 * wave(t))
        tongue(P, tng, t, 1.0, 0.3, 2, lift=1.0 + 0.2 * wave(t, 0, 3))

    def pant(t, P):
        p = 0.5 + 0.5 * math.sin(TAU * t * 5)
        base(t, P, 0.07 * p, 0.3 + 0.1 * p)
        P.move(body, 0, 0, 0.04 * r * p)
        tongue(P, tng, t, 1.0, 0.05, 5, stretch=1 + 0.12 * p)

    def lick_lips(t, P):
        base(t, P, 0.03, 0.25)
        a = math.sin(TAU * t)
        for i, name in enumerate(tng):
            f = (i + 1) / len(tng)
            P.turn(name, x=-1.1 * (1.2 - f) * 0.6, y=1.2 * a * f, z=0.3 * a)

    def wave_hello(t, P):
        base(t, P, 0.04, 0.35)
        up = pulse(t, 0.08, 0.25, 0.75, 0.92)
        for i, name in enumerate(tng):
            f = (i + 1) / len(tng)
            P.turn(name, x=-0.75 * up * (1.3 - f), y=0.8 * up * f * math.sin(TAU * t * 4))
        P.turn(body, y=0.12 * up * math.sin(TAU * t * 4))

    rig.clip('Hover' if hover else 'Idle', 5.0, idle)
    rig.clip('Tongue Wag', 2.0, wag)
    rig.clip('Tongue Lick Around', 3.0, lick_around)
    rig.clip('Tongue Flick', 2.0, flick)
    rig.clip('Tongue Roll', 4.0, roll)
    rig.clip('Tongue Hang', 4.0, hang)
    rig.clip('Tongue Raspberry', 2.5, raspberry)
    rig.clip('Tongue Whip', 2.4, whip)
    rig.clip('Tongue Slurp', 3.0, slurp)
    rig.clip('Tongue Taste the Air', 4.0, taste)
    rig.clip('Tongue Pant', 1.6, pant)
    rig.clip('Tongue Lick Lips', 2.4, lick_lips)
    rig.clip('Tongue Wave', 3.0, wave_hello)
    rig.clip('Shatter', 5.0, shatter)
    rig.clip('Chomp', 1.6, chomp)
    rig.clip('Laugh', 3.0, laugh)
    rig.clip('Sad', 5.0, sad)
    rig.clip('Angry', 2.0, angry)
    rig.clip('Surprise', 3.0, surprise)
    rig.clip('Spin', 4.0, spin)


def shard_head():
    k = mats()
    rig = Rig('shard-head')
    rig.bone('Root', (0, 0, 0), (0, 0.3, 0), deform=False)
    c = (0, 0, 1.6)
    rig.bone('Head', (0, 0, 1.2), (0, 0, 2.2), 'Root')
    parts, names, jaw, dirs = shell(rig, k, c, 1.0, 'Head')
    fp, tng = face(rig, k, c, 1.0, 'Head', jaw)
    rig.build()
    mesh = rig.bind_parts(parts + fp, 'shard-head')
    head_clips(rig, names, dirs, jaw, tng, 1.0)
    rig.finish()
    return rig, mesh, DARK


def shard_walker():
    """The head on two long legs, like a bird that should not exist."""
    k = mats()
    rig = Rig('shard-walker')
    rig.bone('Root', (0, 0, 0), (0, 0.3, 0), deform=False)
    c = (0, 0, 2.5)
    rig.bone('Head', (0, 0, 2.1), (0, 0, 3.0), 'Root')
    parts, names, jaw, dirs = shell(rig, k, c, 0.9, 'Head', seed=5)
    fp, tng = face(rig, k, c, 0.9, 'Head', jaw)
    legs = []
    for side, sx in (('L', 1), ('R', -1)):
        hip = Vector((sx * 0.4, 0.1, 1.85))
        knee = Vector((sx * 0.5, 0.45, 1.0))
        foot = Vector((sx * 0.5, 0.05, 0.06))
        rig.bone('Leg.Up.' + side, hip, knee, 'Head')
        rig.bone('Leg.Low.' + side, knee, foot, 'Leg.Up.' + side, True)
        rig.bone('Foot.' + side, foot, foot + Vector((0, -0.5, 0)), 'Leg.Low.' + side, True)
        rig.bone('ik.' + side, foot, foot + Vector((0, -0.5, 0)), 'Root', deform=False)
        for a, b, bone, w in ((hip, knee, 'Leg.Up.' + side, 0.11), (knee, foot,
                                                                     'Leg.Low.' + side, 0.08)):
            d = b - a
            o = prism([(-w, 0), (w, 0), (w * 0.5, d.length), (-w * 0.5, d.length)], w * 1.2,
                      k['plate'])
            o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
            o.location = a
            bpy.context.view_layer.update()
            o.data.transform(o.matrix_world)
            o.matrix_world.identity()
            parts.append(tag(shade(o, False), bone))
        for q in (-0.5, 0, 0.5):
            toe = prism([(-0.06, 0), (0.06, 0), (0, 0.5)], 0.07, k['plate'])
            place(toe, foot, (math.pi / 2, 0, q))
            parts.append(tag(shade(toe, False), 'Foot.' + side))
        legs.append(side)
    rig.build()
    for side in legs:
        rig.ik('Leg.Low.' + side, 'ik.' + side, 2)
        rig.copy_rotation('Foot.' + side, 'ik.' + side)
    mesh = rig.bind_parts(parts + fp, 'shard-walker')

    def strut(t, P):
        for side, ph in (('L', 0.0), ('R', 0.5)):
            p = (t + ph) % 1.0
            if p < 0.6:
                y, z, pitch = (-0.5 + p / 0.6) * 1.1, 0.0, 0.0
            else:
                u = (p - 0.6) / 0.4
                y, z, pitch = (0.5 - ease(u)) * 1.1, 0.55 * math.sin(math.pi * u), 0.9 * math.sin(
                    math.pi * u)
            P.move('ik.' + side, 0, y, z)
            P.turn('ik.' + side, x=pitch)
        P.move('Head', 0.1 * wave(t), 0.12 * wave(t, 0.1, 2), -0.2 + 0.12 * math.cos(2 * TAU * t))
        P.turn('Head', x=0.12 * wave(t, 0.3, 2), y=0.1 * wave(t))
        breathe(P, names, dirs, t, 0.05)
        P.turn(jaw, x=0.15 + 0.1 * wave(t, 0, 2))
        tongue(P, tng, t, 1.0, 0.45, 2)
    rig.clip('Strut', 1.2, strut)
    head_clips(rig, names, dirs, jaw, tng, 0.9, hover=False)
    rig.finish()
    return rig, mesh, DARK


def shard_serpent():
    """A head that drags a long tail of plates through the air."""
    k = mats()
    rig = Rig('shard-serpent')
    rig.bone('Root', (0, 0, 0), (0, 0.3, 0), deform=False)
    c = (0, 0, 2.2)
    rig.bone('Head', (0, 0.4, 2.2), (0, -0.6, 2.2), 'Root')
    parts, names, jaw, dirs = shell(rig, k, c, 0.85, 'Head', seed=9, pieces=40, bones=14)
    fp, tng = face(rig, k, c, 0.85, 'Head', jaw)
    n = 12
    pts = [Vector((0, 0.8 + i * 0.75, 2.2 - 0.02 * i * i)) for i in range(n + 1)]
    tail = rig.chain('Tail', pts, 'Root')
    rnd = random.Random(6)
    for i in range(n):
        r = 0.6 * (1 - i / n) + 0.1
        for q in range(5):
            a = TAU * q / 5 + i * 0.5
            o = prism([(-r * 0.5, 0), (r * 0.5, 0), (r * 0.25 * rnd.uniform(0.3, 1.2), r * 1.2)],
                      r * 0.12, k['plate'])
            place(o, (0, 0, 0), (math.pi / 2 - 0.5, 0, 0))
            place(o, pts[i] + Vector((r * 0.7 * math.cos(a), 0.3, r * 0.7 * math.sin(a))),
                  (0, a - math.pi / 2, 0))
            parts.append(tag(shade(o, False), tail[i]))
        parts.append(tag(ico(r * 0.45, pts[i] + Vector((0, 0.35, 0)), 2, material=k['core']),
                         tail[i]))
    rig.build()
    mesh = rig.bind_parts(parts + fp, 'shard-serpent')

    def swim(t, P):
        P.move('Head', 0.35 * wave(t), 0, 0.25 * wave(t, 0.25))
        P.turn('Head', z=0.2 * wave(t, -0.2), x=0.1 * wave(t, 0.1))
        for i, b in enumerate(tail):
            P.turn(b, z=0.14 * math.sin(TAU * (t - 0.09 * (i + 1))), x=0.08 * math.sin(
                TAU * (t - 0.09 * (i + 1) + 0.25)))
        P.move('Tail.01', 0.35 * wave(t, -0.05), 0, 0.25 * wave(t, 0.2))
        breathe(P, names, dirs, t, 0.04)
        P.turn(jaw, x=0.12 + 0.08 * wave(t, 0, 2))
        tongue(P, tng, t, 0.85, 0.3, 2)
    rig.clip('Swim', 4.0, swim)
    head_clips(rig, names, dirs, jaw, tng, 0.85)
    rig.finish()
    return rig, mesh, dict(DARK, preview_angle=55)


MODELS = {'shard-head': shard_head, 'shard-walker': shard_walker, 'shard-serpent': shard_serpent}
ATLAS = {name: 2048 for name in MODELS}
