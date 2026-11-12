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
DARK = {'preview_dark': True, 'preview_angle': 12, 'preview_elevation': 6}


def mats():
    return dict(plate=M.metal('#5d5e62', 'plate', 0.55, 0.8, metal=0.3),
                white=M.emissive('#ffffff', 'white', 5.0, '#f2f2f2'),
                tongue=M.flesh('#cf5a66', 'tongue'),
                core=M.emissive('#ffd9c2', 'core', 2.2, '#c98a78'),
                groove=M.emissive('#ffffff', 'groove', 1.5))


def shell(rig, k, centre, radius, parent, prefix='Shard', pieces=46, bones=18, seed=3, gap=0.86,
          mouth=True):
    """A sphere broken into plates. Returns (parts, shard bone names, jaw bone)."""
    rnd = random.Random(seed)
    c = Vector(centre)
    dirs = []
    while len(dirs) < bones:
        d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
        if 0.2 < d.length < 1:
            dirs.append(d.normalized())
    names = []
    for i, d in enumerate(dirs):
        n = '%s.%02d' % (prefix, i)
        rig.bone(n, c + d * radius * 0.6, c + d * radius, parent)
        names.append(n)
    jaw = prefix + '.Jaw'
    rig.bone(jaw, c + Vector((0, 0.2 * radius, -0.2 * radius)), c + Vector(
        (0, -radius, -0.55 * radius)), parent)
    seeds = []
    while len(seeds) < pieces:
        d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
        if 0.2 < d.length < 1:
            seeds.append(d.normalized())
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=radius)
    groups = {}
    for f in bm.faces:
        n = f.calc_center_median().normalized()
        groups.setdefault(max(range(pieces), key=lambda i: seeds[i].dot(n)), []).append(
            [v.co.copy() for v in f.verts])
    bm.free()
    parts = []
    for i, faces in groups.items():
        mid = sum((sum(f, Vector()) / 3 for f in faces), Vector()) / len(faces)
        nd = mid.normalized()
        # the mouth is a gap: plates in front and below the middle are left out
        if mouth and nd.y < -0.55 and -0.5 < nd.z < -0.08 and abs(nd.x) < 0.6:
            continue
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
        mod.thickness = radius * 0.07
        mod.offset = -1
        bpy.ops.object.modifier_apply(modifier='s')
        shade(o, False)
        place(o, c)
        lower = nd.z < -0.45 and nd.y < 0.35
        parts.append(tag(o, jaw if lower else names[max(range(bones),
                                                       key=lambda b: dirs[b].dot(nd))]))
    core = ico(radius * 0.72, c, 3, material=k['core'])
    parts.append(tag(core, parent))
    return parts, names, jaw, dirs


def face(rig, k, centre, radius, parent, jaw, prefix=''):
    """Cross eye, square eye, saw teeth and the tongue with its three-way groove."""
    c = Vector(centre)
    r = radius
    parts = []
    ex = c + Vector((0.42 * r, -0.93 * r, 0.36 * r))
    for a in (0.6, -0.97):
        b = box((0.52 * r, 0.07 * r, 0.13 * r), (0, 0, 0), (0, a, 0), k['white'], 0.004 * r)
        place(b, ex, (0.25, 0, 0.45))
        parts.append(tag(b, parent))
    sq = box((0.2 * r, 0.07 * r, 0.2 * r), (0, 0, 0), (0, 0.2, 0), k['white'], 0.004 * r)
    place(sq, c + Vector((-0.42 * r, -0.93 * r, 0.3 * r)), (0.2, 0, -0.4))
    parts.append(tag(sq, parent))
    for i in range(7):
        x = (i - 3) * 0.15 * r
        y = -math.sqrt(max(0.05, 0.92 - (x / r) ** 2)) * r * 0.97
        t = prism([(-0.07 * r, 0), (0.07 * r, 0), (0.01 * r, -0.2 * r * (1 + 0.25 * (i % 2)))],
                  0.06 * r, k['plate'])
        place(t, c + Vector((x, y, -0.07 * r)), (0, 0, -x / r * 0.9))
        parts.append(tag(shade(t, False), parent))
    t0 = c + Vector((0.02 * r, -0.72 * r, -0.3 * r))
    pts = [t0, t0 + Vector((-0.03 * r, -0.3 * r, -0.16 * r)), t0 + Vector((-0.1 * r, -0.5 * r,
                                                                          -0.5 * r)),
           t0 + Vector((-0.16 * r, -0.55 * r, -0.9 * r))]
    names = rig.chain(prefix + 'Tongue', pts, jaw)
    widths = [0.2, 0.3, 0.28, 0.1]
    for i in range(3):
        a, b = pts[i], pts[i + 1]
        w0, w1 = widths[i] * r, widths[i + 1] * r
        th = 0.07 * r
        side = Vector((1, 0, 0))
        up = (b - a).cross(side).normalized() * th
        v = [a - side * w0 - up, a + side * w0 - up, a + side * w0 * 0.7 + up,
             a - side * w0 * 0.7 + up, b - side * w1 - up, b + side * w1 - up,
             b + side * w1 * 0.7 + up, b - side * w1 * 0.7 + up]
        f = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
        seg = new_object('tongue', v, f, k['tongue'], smooth=False)
        parts.append(tag(seg, names[i]))
    g0 = pts[1].lerp(pts[2], 0.6) + Vector((0, -0.075 * r, 0.03 * r))
    for d in ((0.0, 0.18 * r, 0.3 * r), (0.17 * r, 0.02 * r, -0.05 * r), (-0.1 * r, 0.0,
                                                                         -0.3 * r)):
        from core import tube
        parts.append(tag(tube([g0, g0 + Vector(d)], 0.012 * r, 6, k['groove']), names[1]))
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


def tongue(P, names, t, out=1.0, wag=0.3, speed=3):
    for i, n in enumerate(names):
        P.turn(n, x=-0.25 * (1 - out) * (i + 1), y=wag * out * math.sin(
            TAU * (t * speed - 0.15 * i)), z=0.15 * out * math.sin(TAU * (t * speed + 0.3)))
        P.scale(n, 1, 0.25 + 0.75 * out, 1)


def head_clips(rig, names, dirs, jaw, tng, r, body='Head', hover=True):
    def idle(t, P):
        breathe(P, names, dirs, t, 0.06 * r)
        if hover:
            P.move(body, 0, 0, 0.12 * r * wave(t))
        P.turn(body, z=0.2 * wave(t, 0.2), y=0.08 * wave(t, 0.4))
        P.turn(jaw, x=0.05 + 0.04 * wave(t, 0, 2))
        tongue(P, tng, t, 0.75, 0.12, 1)

    def lick(t, P):
        o = pulse(t, 0.05, 0.25, 0.75, 0.95)
        breathe(P, names, dirs, t, 0.05 * r)
        P.turn(body, y=0.25 * o * wave(t, 0, 2), x=0.1 * o)
        P.turn(jaw, x=0.3 * o)
        tongue(P, tng, t, 0.3 + 0.7 * o, 0.5, 4)

    def shatter(t, P):
        b = pulse(t, 0.12, 0.2, 0.55, 0.9)
        burst(P, names, dirs, 1.6 * r * b, 2.5 * b)
        P.turn(jaw, x=0.9 * b)
        P.move(jaw, 0, -0.5 * r * b, -0.9 * r * b)
        tongue(P, tng, t, 1.0, 0.5 * b, 5)

    def chomp(t, P):
        c = abs(math.sin(TAU * t * 2))
        breathe(P, names, dirs, t, 0.03 * r)
        P.turn(jaw, x=0.55 * c)
        P.turn(body, x=-0.12 * c)
        tongue(P, tng, t, 0.4, 0.1, 2)

    def laugh(t, P):
        ha = max(0, math.sin(TAU * t * 5)) ** 2
        breathe(P, names, dirs, t * 5, 0.1 * r * ha)
        P.turn(body, x=-0.25 + 0.1 * ha, y=0.15 * wave(t))
        P.turn(jaw, x=0.35 + 0.2 * ha)
        tongue(P, tng, t, 0.9, 0.25, 5)
    rig.clip('Hover' if hover else 'Idle', 5.0, idle)
    rig.clip('Lick', 4.0, lick)
    rig.clip('Shatter', 5.0, shatter)
    rig.clip('Chomp', 1.6, chomp)
    rig.clip('Laugh', 3.0, laugh)


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
        tongue(P, tng, t, 0.9, 0.35, 2)
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
