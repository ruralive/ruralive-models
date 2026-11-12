"""Original trees, plants, grass, rocks and ground: simple, a little bent and a little unreal."""
import math
import random

from core import (Meta, Rig, Vector, fbm, grid, ico, join, lathe, place, prism, ridged, roughen,
                  shade, sphere, tag, tube, wave, displace, cylinder, new_object, fix_normals)
import materials as M

TAU = math.tau


def trunk_rig(name, height, bones=4, lean=0.0, twist=0.0):
    rig = Rig(name)
    pts = [Vector((lean * (i / bones) ** 2 * height + twist * math.sin(i * 1.3) * 0.05 * height,
                   twist * math.cos(i * 1.7) * 0.04 * height, height * i / bones))
           for i in range(bones + 1)]
    names = rig.chain('Trunk', pts, None)
    return rig, names, pts


def at(pts, f):
    x = f * (len(pts) - 1)
    i = min(len(pts) - 2, int(x))
    return pts[i].lerp(pts[i + 1], x - i)


def wind(rig, names, seconds=6.0, amount=0.05, name='Wind'):
    def fn(t, P):
        for i, n in enumerate(names):
            P.turn(n, y=amount * (1 + 0.5 * i) * math.sin(TAU * (t - 0.08 * i)),
                   x=amount * 0.5 * (1 + 0.5 * i) * math.sin(TAU * (2 * t - 0.1 * i + 0.2)))
    rig.clip(name, seconds, fn)
    rig.clip('Gust', seconds / 2, lambda t, P: [P.turn(n, y=amount * 2.4 * (1 + 0.6 * i) * max(
        0, math.sin(TAU * (t - 0.07 * i))) ** 2 + amount * 0.4 * math.sin(TAU * (5 * t - 0.2 * i)))
        for i, n in enumerate(names)])


def blob(radius, centre, mat, seed=0, squash=1.0, rough=0.16, detail=3):
    b = ico(radius, (0, 0, 0), detail, (1, 1, squash), mat)
    roughen(b, radius * rough, 1.6 / radius, 3, seed)
    return place(b, centre)


def tree(name, height=6.0, kind='round', leaf='#3f7a2f', leaf2=None, bark='#4d3a2a', lean=0.05,
         twist=1.0, seed=1, trunk_r=0.28):
    rnd = random.Random(seed)
    rig, names, pts = trunk_rig(name, height, 4, lean, twist)
    rig.build()
    bark_m = M.bark(bark, 'bark', 0.8)
    leaf_m = M.leaf(leaf, 'leaf', leaf2)
    top = 1.0 if kind in ('dead',) else 0.92
    fine = [at(pts, f / 16 * top) for f in range(17)]
    trunk = tube(fine, lambda t: trunk_r * (1.25 - 0.95 * t ** 0.8) + 0.02, 14, bark_m)
    for v in trunk.data.vertices:
        if v.co.z < height * 0.08:
            k = 1 + 0.6 * (1 - v.co.z / (height * 0.08)) ** 2
            v.co.x *= k
            v.co.y *= k
    rig.weight_chain(trunk, names)
    parts = [trunk]

    def bone_at(z):
        return names[min(3, max(0, int(z / height * 4)))]
    if kind in ('round', 'purple', 'small', 'island'):
        n = {'round': 9, 'purple': 12, 'small': 5, 'island': 6}[kind]
        for i in range(n):
            a = TAU * i / n + rnd.uniform(-0.3, 0.3)
            f = rnd.uniform(0.45, 0.8)
            base = at(pts, f)
            spread = height * (0.32 if kind != 'island' else 0.5)
            tip = base + Vector((math.cos(a) * spread, math.sin(a) * spread,
                                 height * (0.25 if kind != 'island' else 0.06)))
            parts.append(tag(tube([base, base.lerp(tip, 0.5) + Vector((0, 0, 0.1 * height)), tip],
                                  lambda t: trunk_r * 0.36 * (1 - 0.7 * t), 8, bark_m,
                                  smooth_path=1), bone_at(base.z)))
            r = height * rnd.uniform(0.16, 0.24) * (0.8 if kind == 'small' else 1)
            parts.append(tag(blob(r, tip + Vector((0, 0, r * 0.3)), leaf_m, seed + i,
                                  0.55 if kind == 'island' else 0.85), 'Trunk.04'))
        r = height * 0.26
        parts.append(tag(blob(r, pts[-1] + Vector((0, 0, r * 0.2)), leaf_m, seed + 50,
                              0.5 if kind == 'island' else 0.9), 'Trunk.04'))
    elif kind in ('pine', 'fir'):
        tiers = 7 if kind == 'pine' else 10
        for i in range(tiers):
            f = 0.28 + 0.72 * i / tiers
            c = at(pts, f)
            r = height * (0.3 if kind == 'pine' else 0.22) * (1.05 - f) + 0.08
            h = height * 0.2
            cone = lathe([(0, h), (r * 0.25, h * 0.55), (r, 0.0), (r * 0.6, 0.06 * h), (0, 0.1 * h)],
                         18, material=leaf_m, cap=False)
            for v in cone.data.vertices:
                ang = math.atan2(v.co.y, v.co.x)
                rr = math.hypot(v.co.x, v.co.y)
                k = 1 + 0.16 * math.sin(ang * 7 + i) * (rr / r)
                v.co.x *= k
                v.co.y *= k
                v.co.z -= 0.12 * h * (rr / r) ** 2 * (1 + math.sin(ang * 3 + i))
            parts.append(tag(place(cone, c, (0, 0, i * 0.7)), bone_at(c.z)))
    elif kind == 'quiver':
        tips = []
        for i in range(5):
            a = TAU * i / 5
            base = at(pts, 0.7)
            mid = base + Vector((math.cos(a) * 0.9, math.sin(a) * 0.9, height * 0.2))
            for s in (-0.35, 0.35):
                tip = mid + Vector((math.cos(a + s) * 0.7, math.sin(a + s) * 0.7, height * 0.16))
                parts.append(tag(tube([base, mid, tip], lambda t: trunk_r * 0.5 * (1 - 0.55 * t), 8,
                                      bark_m, smooth_path=1), 'Trunk.04'))
                tips.append(tip)
        for j, tip in enumerate(tips):
            for q in range(9):
                a = TAU * q / 9 + j
                d = Vector((math.cos(a), math.sin(a), 0.6)).normalized()
                parts.append(tag(tube([tip, tip + d * 0.45], lambda t: 0.06 * (1 - t) + 0.006, 5,
                                      leaf_m), 'Trunk.04'))
    elif kind == 'dead':
        for i in range(5):
            a = TAU * i / 5 + 0.4
            base = at(pts, 0.5 + 0.1 * i)
            tip = base + Vector((math.cos(a) * 1.4, math.sin(a) * 1.4, 0.9 + 0.2 * i))
            parts.append(tag(tube([base, base.lerp(tip, 0.6) + Vector((0, 0, 0.4)), tip],
                                  lambda t: trunk_r * 0.4 * (1 - 0.85 * t), 7, bark_m,
                                  smooth_path=1), bone_at(base.z)))
    mesh = rig.bind_parts(parts, name)
    wind(rig, names, 7.0, 0.012 if kind == 'dead' else 0.028)
    rig.finish()
    return rig, mesh


def stump(name='tree_stump_01'):
    rig = Rig(name)
    rig.bone('Body', (0, 0, 0), (0, 0, 0.5))
    rig.build()
    body = lathe([(0, 0), (0.75, 0), (0.6, 0.15), (0.5, 0.6), (0.47, 0.75), (0, 0.75)], 28,
                 material=M.bark('#4a3828', 'bark', 1.2), cap=False)
    displace(body, lambda co, n: Vector((co.x, co.y, 0)) * 0.12 * math.sin(
        math.atan2(co.y, co.x) * 6 + co.z * 2) * (1 - co.z))
    top = lathe([(0, 0.0), (0.46, 0.0)], 28, (0, 0, 0.75), material=M.wood('#b98a55', 'rings', 0,
                                                                         0.7, 3.0), cap=False)
    parts = [tag(body, 'Body'), tag(top, 'Body')]
    for i in range(5):
        a = TAU * i / 5
        parts.append(tag(tube([(0.5 * math.cos(a), 0.5 * math.sin(a), 0.2),
                               (1.0 * math.cos(a), 1.0 * math.sin(a), 0.05),
                               (1.5 * math.cos(a + 0.2), 1.5 * math.sin(a + 0.2), -0.05)],
                              lambda t: 0.14 * (1 - 0.8 * t), 8, M.bark('#4a3828', 'root', 1.2),
                              smooth_path=1), 'Body'))
    mesh = rig.bind_parts(parts, name)
    rig.clip('Turntable', 12.0, lambda t, P: P.turn('Body', z=TAU * t))
    rig.finish()
    return rig, mesh


def plant(name, kind, seed=1):
    rnd = random.Random(seed)
    height = {'fern': 0.7, 'shrub': 1.1, 'shrub2': 0.9, 'moss': 0.12, 'nettle': 0.8,
              'dandelion': 0.3, 'gazania': 0.28, 'potted': 0.9, 'grass': 0.4, 'wild': 0.6,
              'bermuda': 0.12}[kind]
    rig, names, pts = trunk_rig(name, height, 3)
    rig.build()
    leaf = M.leaf({'fern': '#2f6a2a', 'nettle': '#3a6a2a', 'shrub2': '#4a6a2f',
                   'bermuda': '#5a8a2f', 'wild': '#7a8a3a'}.get(kind, '#3f7a2f'), 'leaf')
    parts = []

    def blade(base, direction, length, width, bend=0.5, mat=leaf, cuts=6, taper=1.0):
        d = Vector(direction).normalized()
        side = d.cross(Vector((0, 0, 1)))
        side = side.normalized() if side.length > 0.01 else Vector((1, 0, 0))
        verts, faces = [], []
        for i in range(cuts + 1):
            f = i / cuts
            c = Vector(base) + d * length * f * (1 - 0.3 * bend * f) + Vector(
                (0, 0, length * (f - bend * f * f)))
            w = width * (math.sin(math.pi * (0.12 + 0.88 * f)) ** taper)
            verts += [c - side * w, c + side * w]
        for i in range(cuts):
            faces.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
        return new_object('blade', verts, faces, mat)

    def weighted(objs):
        o = join(objs)
        from core import solidify
        solidify(o, 0.004 * max(1, height), 0)
        return rig.weight_chain(o, names)
    if kind in ('grass', 'wild', 'bermuda'):
        blades = []
        n = {'grass': 90, 'wild': 70, 'bermuda': 160}[kind]
        for _ in range(n):
            a, r = rnd.uniform(0, TAU), rnd.uniform(0, 0.45) ** 0.7 * 0.5
            d = (math.cos(a + rnd.uniform(-1, 1)), math.sin(a + rnd.uniform(-1, 1)), 0)
            blades.append(blade((r * math.cos(a), r * math.sin(a), 0), d,
                                height * rnd.uniform(0.5, 1.0), 0.012 + 0.01 * rnd.random(),
                                rnd.uniform(0.3, 0.9), cuts=4, taper=0.6))
        parts.append(weighted(blades))
        if kind == 'wild':
            seedm = M.petal('#c9b56a', 'seed')
            for _ in range(12):
                a, r = rnd.uniform(0, TAU), rnd.uniform(0, 0.35)
                h = height * rnd.uniform(0.8, 1.1)
                parts.append(tag(tube([(r * math.cos(a), r * math.sin(a), h * 0.7),
                                       (r * math.cos(a) * 1.2, r * math.sin(a) * 1.2, h)],
                                      lambda t: 0.012 * math.sin(math.pi * (0.1 + 0.8 * t)), 5,
                                      seedm), 'Trunk.03'))
    elif kind == 'fern':
        fronds = []
        for i in range(11):
            a = TAU * i / 11
            d = (math.cos(a), math.sin(a), 0)
            fronds.append(blade((0, 0, 0.02), d, 0.85, 0.09, 0.95, cuts=10))
            for j in range(1, 9):
                f = j / 9
                c = Vector(d) * 0.85 * f * (1 - 0.285 * f) + Vector((0, 0, 0.85 * (f - 0.95 * f * f)
                                                                     + 0.02))
                for s in (1, -1):
                    sd = Vector((-d[1] * s, d[0] * s, 0.0))
                    fronds.append(blade(c, sd + Vector(d) * 0.4, 0.2 * (1 - f * 0.7), 0.03, 0.4,
                                        cuts=3))
        parts.append(weighted(fronds))
    elif kind == 'moss':
        mm = M.leaf('#4a6a22', 'moss', '#8a9a3a')
        clumps = []
        for i in range(26):
            a, r = rnd.uniform(0, TAU), rnd.uniform(0, 0.7)
            clumps.append(blob(rnd.uniform(0.1, 0.22), (r * math.cos(a), r * math.sin(a), 0.03),
                               mm, i, 0.45, 0.25, 2))
        parts.append(tag(join(clumps), 'Trunk.01'))
    elif kind in ('shrub', 'shrub2', 'nettle'):
        stems = []
        bark = M.bark('#4a3a28', 'stem', 3)
        n = 9 if kind != 'nettle' else 6
        for i in range(n):
            a = TAU * i / n + rnd.uniform(-0.2, 0.2)
            lean = rnd.uniform(0.2, 0.5) if kind != 'nettle' else 0.12
            tip = Vector((math.cos(a) * height * lean, math.sin(a) * height * lean,
                          height * rnd.uniform(0.7, 1.0)))
            stem = tube([(0, 0, 0), tip * 0.5 + Vector((0, 0, 0.05)), tip], 0.015, 6, bark,
                        smooth_path=1)
            stems.append(stem)
            for j in range(7 if kind != 'nettle' else 9):
                f = 0.25 + 0.75 * j / 8
                c = tip * f
                b = a + j * 2.4
                stems.append(blade(c, (math.cos(b), math.sin(b), 0.2), 0.16 if kind != 'nettle'
                                   else 0.13, 0.05, 0.6, cuts=4))
            if kind == 'shrub':
                parts.append(tag(blob(0.05, tip, M.petal('#e06aa0', 'flower'), i, 0.8, 0.2, 2),
                                 'Trunk.03'))
        parts.append(weighted(stems))
    elif kind in ('dandelion', 'gazania'):
        leaves = [blade((0, 0, 0.01), (math.cos(TAU * i / 8), math.sin(TAU * i / 8), 0), 0.22,
                        0.035, 1.0, cuts=6) for i in range(8)]
        stem = tube([(0, 0, 0), (0.01, 0, height * 0.5), (0, 0.01, height)], 0.006, 6, leaf)
        parts.append(weighted(leaves + [stem]))
        if kind == 'dandelion':
            parts.append(tag(sphere(0.05, (0, 0.01, height), material=M.wool('#f1efe6', 'puff'),
                                    segments=20, rings=12), 'Trunk.03'))
        else:
            pet = M.petal('#f08a1c', 'petal', '#f6d23c')
            for i in range(16):
                a = TAU * i / 16
                p = blade((0, 0.01, height), (math.cos(a), math.sin(a), 0), 0.075, 0.014, 0.3,
                          pet, 3)
                parts.append(tag(p, 'Trunk.03'))
            parts.append(tag(sphere(0.02, (0, 0.01, height + 0.005), (1, 1, 0.5),
                                    material=M.petal('#3a2a12', 'eye')), 'Trunk.03'))
    elif kind == 'potted':
        pot = lathe([(0, 0), (0.16, 0), (0.22, 0.3), (0.24, 0.3), (0.24, 0.34), (0.2, 0.34),
                     (0.19, 0.3), (0, 0.3)], 28, material=M.roof_tiles('#b5562f', 'pot'))
        parts.append(tag(pot, 'Trunk.01'))
        leaves = []
        for i in range(9):
            a = TAU * i / 9
            leaves.append(blade((0, 0, 0.3), (math.cos(a), math.sin(a), 0),
                                rnd.uniform(0.4, 0.65), 0.07, 0.75, cuts=7))
        parts.append(weighted(leaves))
    mesh = rig.bind_parts(parts, name)
    wind(rig, names, 4.0, 0.07 if kind != 'moss' else 0.0)
    rig.finish()
    return rig, mesh


def rock(name, kind='boulder', seed=1):
    rnd = random.Random(seed)
    rig = Rig(name)
    rig.bone('Body', (0, 0, 0), (0, 0, 1))
    rig.build()
    mats = {'boulder': M.rock('#77706a', 'rock'), 'mossy': M.rock('#6a6a66', 'rock', moss=0.8),
            'face': M.rock('#7a6f66', 'rock', 0.5, '#9a8a78', strata=6),
            'desert': M.rock('#b06a3a', 'rock', 1.0, '#d99a5a', strata=9),
            'cliff': M.rock('#8a8478', 'rock', 0.3, '#b5a890', strata=3, moss=0.3),
            'mountain': M.rock('#6a665f', 'rock', 0.12, '#8a8478', snow=0.6),
            'moon': M.planet([(0.2, '#4a4a4c'), (0.6, '#8a8a8c'), (0.9, '#b5b5b6')], 'rock', 3,
                             craters=7), 'moon2': M.planet(
                                 [(0.2, '#3a3a3e'), (0.7, '#7a7a80')], 'rock', 4, craters=11)}
    mat = mats[kind]
    parts = []

    def stone(radius, centre, squash=(1, 1, 0.75), s=0, sharp=0.35):
        o = ico(radius, (0, 0, 0), 4, squash, mat)
        off = (s * 7.1, s * 3.3, s * 5.7)
        displace(o, lambda co, n: n * radius * (0.28 * fbm(co, 0.9 / radius, 4, offset=off)
                                               + sharp * (ridged(co, 0.6 / radius, 3, off) - 0.9)
                                               * 0.35))
        o = place(o, centre)
        for v in o.data.vertices:
            v.co.z = max(v.co.z, 0.0)
        return o
    if kind in ('boulder', 'desert', 'moon', 'moon2'):
        parts.append(stone(1.0, (0, 0, 0.45), (1.15, 0.95, 0.8), seed))
    elif kind == 'mossy':
        for i, (c, r) in enumerate((((0, 0, 0.3), 0.75), ((1.1, 0.4, 0.2), 0.5),
                                    ((-0.8, -0.7, 0.15), 0.42), ((0.3, -1.1, 0.1), 0.3))):
            parts.append(stone(r, c, (1.1, 0.95, 0.7), seed + i))
    elif kind in ('face', 'cliff'):
        w, hgt = (5, 6) if kind == 'face' else (12, 9)
        g = grid((w, hgt), (90, 70), material=mat)
        place(g, (0, 0, hgt / 2), (math.pi / 2, 0, 0))
        displace(g, lambda co, n: Vector((0, -1, 0)) * (
            1.6 * ridged((co.x, 0, co.z), 0.22, 4, (seed, 0, 0)) + 0.5 * fbm(co, 0.9, 4)
            - 0.25 * co.z * (1 if kind == 'cliff' else 0.3)
            + 0.6 * math.floor(co.z / 1.4 + 0.5 * math.sin(co.x)) * 0.25))
        parts.append(g)
    elif kind == 'mountain':
        g = grid((14, 14), (120, 120), material=mat,
                 fn=lambda x, y: max(0.0, (6.2 * ridged((x, y, 0), 0.11, 5, (seed, 2, 0)) - 2.6)
                                     * max(0, 1 - (x * x + y * y) / 49) ** 1.3))
        parts.append(g)
    for p in parts:
        tag(p, 'Body')
    mesh = rig.bind_parts(parts, name)
    rig.clip('Turntable', 16.0, lambda t, P: P.turn('Body', z=TAU * t))
    rig.clip('Tumble', 8.0, lambda t, P: P.turn('Body', x=TAU * t, z=TAU * t))
    rig.finish()
    return rig, mesh


def ground(name, kind):
    rnd = random.Random(len(name))
    rig = Rig(name)
    rig.bone('Body', (0, 0, 0), (0, 0, 1))
    rig.build()
    soil = M.soil('#5a4330', 'soil', 0.3) if kind != 'sand' else M.sand()
    patch = grid((3.2, 3.2), (48, 48), material=soil,
                 fn=lambda x, y: 0.1 * fbm((x, y, 0), 0.9, 4) * max(
                     0.0, 1 - (x * x + y * y) / 2.4) - 0.02 * min(1.0, (x * x + y * y) / 2.4))
    for v in patch.data.vertices:
        r = math.hypot(v.co.x, v.co.y)
        if r > 1.55:
            v.co.x *= 1.55 / r
            v.co.y *= 1.55 / r
    parts = [patch]
    if kind == 'roots':
        bark = M.bark('#4d3a2a', 'root', 1.2)
        for i in range(8):
            a = TAU * i / 8 + rnd.uniform(-0.2, 0.2)
            pts = [Vector((r * math.cos(a + 0.25 * math.sin(r * 3)), r * math.sin(
                a + 0.25 * math.sin(r * 3)), 0.14 - 0.08 * r + 0.06 * math.sin(r * 5 + i)))
                for r in (0.05, 0.4, 0.8, 1.2, 1.5)]
            parts.append(tube(pts, lambda t: 0.11 * (1 - 0.8 * t) + 0.012, 8, bark, smooth_path=1))
    elif kind == 'bark':
        bark = M.bark('#5a4532', 'chip', 2)
        for i in range(34):
            a, r = rnd.uniform(0, TAU), rnd.uniform(0, 1.3)
            c = prism([(-0.14, 0), (0.12, -0.02), (0.16, 0.05), (-0.1, 0.07)], rnd.uniform(
                0.05, 0.16), bark, bevel_width=0.008)
            place(c, (r * math.cos(a), r * math.sin(a), 0.07), (rnd.uniform(1.2, 1.9), rnd.uniform(
                -0.3, 0.3), rnd.uniform(0, TAU)), rnd.uniform(0.6, 1.6))
            parts.append(c)
    else:
        rm = M.rock('#8a8275', 'pebble', 3)
        for i in range(22):
            a, r = rnd.uniform(0, TAU), rnd.uniform(0, 1.3)
            s = rnd.uniform(0.05, 0.22)
            o = ico(s, (0, 0, 0), 2, (1.2, 0.9, 0.6), rm)
            roughen(o, s * 0.25, 2 / s, 3, i)
            parts.append(place(o, (r * math.cos(a), r * math.sin(a), s * 0.25)))
    for p in parts:
        tag(p, 'Body')
    mesh = rig.bind_parts(parts, name)
    rig.clip('Turntable', 16.0, lambda t, P: P.turn('Body', z=TAU * t))
    rig.finish()
    return rig, mesh


def fish(name='barramundi_fish'):
    rig = Rig(name)
    rig.bone('Root', (0, 0, 0), (0, 0.1, 0), deform=False)
    pts = [Vector((0, -0.42 + i * 0.17, 0.3)) for i in range(6)]
    rig.bone('Head', pts[1], pts[0], 'Root')
    rig.chain('Body', pts[1:], 'Root')
    m = Meta(0.008)
    for i, r in enumerate((0.07, 0.115, 0.13, 0.105, 0.06, 0.03)):
        m.ball(pts[i], 1, (r * 0.55, 0.12, r))
    m.ball(pts[0] + Vector((0, -0.05, -0.01)), 1, (0.035, 0.06, 0.05))
    rig.build()
    body = m.mesh('body', M.scales('#9aa6a8', '#5a6a66', 'scales', 3.0))
    rig.bind_auto(body)
    fin = M.petal('#5a6a5a', 'fin', '#8a9a7a')
    rigid = []
    tail = prism([(0, 0), (0.17, 0.15), (0.13, 0.0), (0.17, -0.15)], 0.008, fin)
    place(tail, pts[5] + Vector((0, -0.01, 0)), (0, 0, math.pi / 2))
    rigid.append(tag(tail, 'Body.04'))
    dorsal = prism([(-0.16, 0), (-0.08, 0.1), (0.06, 0.07), (0.16, 0)], 0.006, fin)
    place(dorsal, (0, -0.02, 0.41), (0, 0, math.pi / 2))
    rigid.append(tag(dorsal, 'Body.02'))
    for sx in (1, -1):
        p = prism([(0, 0), (0.1, 0.04), (0.09, -0.04)], 0.004, fin)
        place(p, (sx * 0.06, -0.2, 0.25), (0.3, sx * 0.7, math.pi / 2 - sx * 0.6))
        rigid.append(tag(p, 'Body.01'))
        rigid.append(tag(sphere(0.016, (sx * 0.034, -0.39, 0.315), material=M.eye('#0a0a0a',
                                                                                 'eye')),
                         'Head'))
    for p in rigid:
        p.vertex_groups.new(name=p['bone']).add(range(len(p.data.vertices)), 1.0, 'REPLACE')
    mesh = join([body] + rigid, name)

    def swim(t, P):
        P.turn('Head', z=-0.12 * wave(t, 0.1))
        for i in range(1, 5):
            P.turn('Body.%02d' % i, z=0.12 * (0.6 + 0.35 * i) * math.sin(TAU * (t - 0.13 * i)))
        P.move('Root', 0.015 * wave(t, 0.3), 0, 0.01 * wave(t, 0, 2))
    rig.clip('Swim', 1.4, swim)
    rig.finish()
    return rig, mesh


MODELS = {
    'pine_tree_01': lambda: tree('pine_tree_01', 9, 'pine', '#27563a', bark='#5a3d2a', seed=2),
    'fir_tree_01': lambda: tree('fir_tree_01', 10, 'fir', '#1f4a3a', bark='#4a3526', seed=3,
                                trunk_r=0.24),
    'jacaranda_tree': lambda: tree('jacaranda_tree', 7, 'purple', '#8a5ad6', '#c9a6ff',
                                   lean=0.08, twist=2.5, seed=4),
    'tree_small_02': lambda: tree('tree_small_02', 3.2, 'small', '#5a8a2f', '#b5c94a',
                                  twist=2.0, seed=5, trunk_r=0.14),
    'island_tree_01': lambda: tree('island_tree_01', 6, 'island', '#3a6a3f', lean=0.16,
                                   twist=3.0, seed=6),
    'quiver_tree_01': lambda: tree('quiver_tree_01', 4.5, 'quiver', '#6a8a5a', bark='#b59a6a',
                                   lean=0.0, twist=0.6, seed=7, trunk_r=0.42),
    'dead_tree_trunk': lambda: tree('dead_tree_trunk', 5, 'dead', bark='#5a5048', lean=0.1,
                                    twist=3.5, seed=8, trunk_r=0.3),
    'tree_stump_01': stump,
    'fern_02': lambda: plant('fern_02', 'fern'),
    'shrub_01': lambda: plant('shrub_01', 'shrub', 2),
    'shrub_02': lambda: plant('shrub_02', 'shrub2', 3),
    'moss_01': lambda: plant('moss_01', 'moss', 4),
    'nettle_plant': lambda: plant('nettle_plant', 'nettle', 5),
    'dandelion_01': lambda: plant('dandelion_01', 'dandelion', 6),
    'flower_gazania': lambda: plant('flower_gazania', 'gazania', 7),
    'potted_plant_01': lambda: plant('potted_plant_01', 'potted', 8),
    'grass_medium_01': lambda: plant('grass_medium_01', 'grass', 9),
    'grass_medium_02': lambda: plant('grass_medium_02', 'wild', 10),
    'grass_bermuda_01': lambda: plant('grass_bermuda_01', 'bermuda', 11),
    'boulder_01': lambda: rock('boulder_01', 'boulder', 1),
    'rock_moss_set_01': lambda: rock('rock_moss_set_01', 'mossy', 2),
    'rock_face_01': lambda: rock('rock_face_01', 'face', 3),
    'namaqualand_boulder_02': lambda: rock('namaqualand_boulder_02', 'desert', 4),
    'coastal_cliff_01': lambda: rock('coastal_cliff_01', 'cliff', 5),
    'mountainside': lambda: rock('mountainside', 'mountain', 6),
    'moon_rock_01': lambda: rock('moon_rock_01', 'moon', 7),
    'moon_rock_02': lambda: rock('moon_rock_02', 'moon2', 8),
    'pine_roots': lambda: ground('pine_roots', 'roots'),
    'bark_debris_01': lambda: ground('bark_debris_01', 'bark'),
    'sand_rocks_small_01': lambda: ground('sand_rocks_small_01', 'sand'),
    'barramundi_fish': fish,
}
ATLAS = {name: 1024 for name in MODELS}
for big in ('coastal_cliff_01', 'mountainside', 'rock_face_01', 'pine_tree_01', 'fir_tree_01',
            'jacaranda_tree', 'island_tree_01'):
    ATLAS[big] = 2048
MODELS = {key.replace('_', '-'): fn for key, fn in MODELS.items()}
ATLAS = {key.replace('_', '-'): size for key, size in ATLAS.items()}
