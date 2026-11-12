"""Original spacecraft, in a bold and slightly impossible style: no real mission is copied."""
import math

from core import (Rig, Vector, box, cylinder, lathe, place, pulse, sphere, tag, torus, tube,
                  wave, prism, ico, roughen, ease)
import materials as M

TAU = math.tau
DARK = {'preview_dark': True}


def kit():
    return dict(hull=M.hull('#ebe9e3', 'hull'), dark=M.hull('#23262c', 'dark', 0.5),
                foil=M.foil(), solar=M.solar(), metal=M.metal('#aab2b9', 'metal', 0.3, 0.6),
                accent=M.paint('#e0452b', 'accent', 0.35, 0.3, 0.2),
                black=M.plastic('#101216', 'black', 0.5),
                glow=M.emissive('#7fd8ff', 'glow', 5.0), warm=M.emissive('#ffb347', 'warm', 6.0))


def array(k, bone, origin, direction, length, width, segments=3, name='panel'):
    """A solar wing made of framed panels along a boom."""
    d = Vector(direction).normalized()
    side = d.cross(Vector((0, 0, 1)))
    if side.length < 0.1:
        side = Vector((1, 0, 0))
    side.normalize()
    parts = [tag(tube([origin, Vector(origin) + d * length], width * 0.04, 8, k['metal']), bone)]
    seg = length / segments
    rot = d.to_track_quat('X', 'Z').to_euler()
    for i in range(segments):
        c = Vector(origin) + d * (seg * (i + 0.55))
        p = box((seg * 0.9, width, width * 0.02), (0, 0, 0), material=k['solar'],
                bevel_width=width * 0.004)
        place(p, c, rot)
        parts.append(tag(p, bone))
    return parts


def done(rig, parts, name, opts=None):
    mesh = rig.bind_parts(parts, name)
    rig.finish()
    return rig, mesh, dict(DARK, **(opts or {}))


def turn(rig, seconds=24.0, name='Orbital Turn', bone='Body', extra=None):
    def fn(t, P):
        P.turn(bone, z=TAU * t)
        if extra:
            extra(t, P)
    rig.clip(name, seconds, fn)


# ----------------------------------------------------------------------------- vehicles
def moon_rocket():
    k = kit()
    rig = Rig('saturn-v')
    rig.bone('Body', (0, 0, 0), (0, 0, 2))
    rig.bone('Flame', (0, 0, 0.2), (0, 0, -2), 'Body')
    parts = [tag(lathe([(0, 0.4), (1.5, 0.4), (1.6, 0.6), (1.6, 9), (1.25, 10.4), (1.25, 16),
                        (0.9, 17.2), (0.9, 20.5), (0.45, 22), (0.45, 23.2), (0.12, 24.6),
                        (0.06, 27), (0, 27.2)], 48, material=k['hull']), 'Body')]
    for z, h, r in ((8.2, 0.9, 1.62), (15.2, 0.7, 1.27), (20.0, 0.5, 0.92), (3.0, 1.4, 1.62)):
        parts.append(tag(cylinder(r, h, (0, 0, z), material=k['dark'], segments=48), 'Body'))
    for i in range(4):
        a = TAU * i / 4 + TAU / 8
        fin = prism([(0, 0), (1.6, 0), (0.5, 3.2), (0, 3.6)], 0.14, k['accent'], bevel_width=0.03)
        place(fin, (1.5 * math.cos(a), 1.5 * math.sin(a), 0.5), (0, 0, a))
        parts.append(tag(fin, 'Body'))
    for i in range(5):
        a = TAU * i / 4
        r = 0 if i == 4 else 0.95
        parts.append(tag(lathe([(0.2, 0.6), (0.3, 0.3), (0.5, -0.5), (0.46, -0.5), (0.26, 0.3)], 24,
                               (r * math.cos(a), r * math.sin(a), 0.2), material=k['metal'],
                               cap=False), 'Body'))
        parts.append(tag(lathe([(0, 0), (0.42, -0.3), (0.5, -1.8), (0.25, -4.2), (0, -6)], 16,
                               (r * math.cos(a), r * math.sin(a), -0.3), material=M.emissive(
                                   '#ffb347', 'flame%d' % i, 9.0, '#ff5a1c')), 'Flame'))
    parts.append(tag(sphere(0.3, (0, -1.22, 21), (1, 0.3, 1.4), material=k['glow']), 'Body'))

    def launch(t, P):
        burn = pulse(t, 0.0, 0.2, 0.92, 1.0)
        P.scale('Flame', 0.4 + 0.6 * burn + 0.08 * wave(t, 0, 23), 0.3 + 0.7 * burn
                + 0.15 * wave(t, 0.2, 17), 0.4 + 0.6 * burn + 0.08 * wave(t, 0.4, 19))
        P.move('Body', 0.04 * wave(t, 0, 29) * burn, 0.04 * wave(t, 0.3, 31) * burn,
               14 * ease(max(0, (t - 0.3) / 0.7)) ** 2)
    rig.build()
    rig.clip('Liftoff', 8.0, launch, loop=False)
    rig.clip('Engines', 2.0, lambda t, P: P.scale('Flame', 1 + 0.08 * wave(t, 0, 5),
                                                  1 + 0.2 * wave(t, 0.2, 7),
                                                  1 + 0.08 * wave(t, 0.4, 6)))
    turn(rig, 30.0)
    return done(rig, parts, 'saturn-v', {'preview_clip': 1})


def spaceplane():
    k = kit()
    rig = Rig('space-shuttle')
    rig.bone('Body', (0, 0, 0), (0, -2, 0))
    rig.bone('Door.L', (0.9, 0, 1.0), (0.9, 0, 1.9), 'Body')
    rig.bone('Door.R', (-0.9, 0, 1.0), (-0.9, 0, 1.9), 'Body')
    rig.bone('Flame', (0, 5.2, 0.6), (0, 7, 0.6), 'Body')
    tiles = M.concrete('#16181c', 'tiles', 0.35)
    parts = [tag(lathe([(0, -7.2), (0.5, -6.6), (1.05, -5), (1.3, -2.5), (1.3, 4.2), (1.1, 5.2),
                        (0, 5.2)], 40, (0, 0, 0.6), (math.pi / 2, 0, 0), k['hull'],
                       scale=(1, 0.85, 1)), 'Body')]
    wing = prism([(0, -3.6), (0.5, -3.0), (4.4, 3.4), (4.4, 4.6), (0, 4.6)], 0.28, tiles,
                 bevel_width=0.06)
    for sx in (1, -1):
        w = place(wing.copy(), (0, 0, 0)) if False else None
    from core import copy
    for sx in (1, -1):
        w = copy(wing)
        place(w, (0, 0, 0), (math.pi / 2, 0, 0))
        place(w, (sx * 0.9, 0, -0.1), (0, 0, 0), (sx, 1, 1))
        parts.append(tag(w, 'Body'))
        parts.append(tag(lathe([(0.32, 0.8), (0.4, 0.2), (0.62, -0.7), (0.56, -0.7), (0.3, 0.2)],
                               24, (sx * 0.62, 5.3, 0.85), (math.pi / 2, 0, 0), k['metal'],
                               cap=False), 'Body'))
        door = box((0.9, 5.2, 0.08), (sx * 0.47, 0, 1.52), (0, -sx * 0.35, 0), k['hull'], 0.02)
        parts.append(tag(door, 'Door.' + ('L' if sx > 0 else 'R')))
    import bpy
    bpy.data.objects.remove(wing)
    tail = prism([(0, 0), (2.6, 0), (3.1, 2.6), (2.2, 2.8)], 0.22, k['hull'], bevel_width=0.05)
    place(tail, (0, 2.3, 1.5), (0, 0, math.pi / 2))
    parts.append(tag(tail, 'Body'))
    parts.append(tag(sphere(0.75, (0, -5.4, 1.05), (1.05, 1.5, 0.5), material=k['black']), 'Body'))
    parts.append(tag(box((1.4, 4.8, 0.5), (0, 0, 1.05), material=k['foil']), 'Body'))
    parts.append(tag(lathe([(0, 0), (0.5, 0.3), (0.55, 1.8), (0.2, 4.5), (0, 5.5)], 16,
                           (0, 5.6, 0.75), (-math.pi / 2, 0, 0), M.emissive('#9fd8ff', 'flame', 8.0,
                                                                          '#3a6aff')), 'Flame'))
    rig.build()

    def glide(t, P):
        P.turn('Body', y=0.12 * wave(t), x=0.04 * wave(t, 0.2, 2))
        P.move('Body', 0, 0, 0.3 * wave(t, 0.1))
        P.scale('Flame', 1 + 0.1 * wave(t, 0, 9), 1 + 0.25 * wave(t, 0.1, 7), 1 + 0.1 * wave(
            t, 0.3, 8))

    def bay(t, P):
        o = pulse(t, 0.1, 0.4, 0.6, 0.9)
        P.turn('Door.L', y=1.9 * o)
        P.turn('Door.R', y=-1.9 * o)
        P.scale('Flame', 0.05, 0.05, 0.05)
    rig.clip('Glide', 8.0, glide)
    rig.clip('Open Bay', 10.0, bay)
    return done(rig, parts, 'space-shuttle', {'preview_angle': 50})


def mars_rover():
    k = kit()
    rig = Rig('perseverance-rover')
    rig.bone('Body', (0, 0, 0.9), (0, 0, 1.4))
    rig.bone('Mast', (0.5, -0.9, 1.2), (0.5, -0.9, 2.3), 'Body')
    rig.bone('Head', (0.5, -0.9, 2.3), (0.5, -1.3, 2.3), 'Mast')
    rig.bone('Arm.01', (-0.4, -1.3, 0.95), (-0.4, -2.2, 1.3), 'Body')
    rig.bone('Arm.02', (-0.4, -2.2, 1.3), (-0.4, -2.9, 0.7), 'Arm.01', True)
    parts = [tag(box((1.7, 2.6, 0.5), (0, 0, 1.05), material=k['hull'], bevel_width=0.08,
                     segments=3), 'Body'),
             tag(box((1.5, 2.3, 0.06), (0, 0, 1.34), material=k['solar']), 'Body'),
             tag(box((0.7, 0.6, 0.7), (0, 1.5, 1.35), (0.5, 0, 0), k['foil'], 0.05), 'Body'),
             tag(cylinder(0.06, 1.1, (0.5, -0.9, 1.75), material=k['metal']), 'Mast'),
             tag(box((0.5, 0.3, 0.26), (0.5, -1.0, 2.36), material=k['hull'], bevel_width=0.04),
                 'Head'),
             tag(tube([(-0.4, -1.3, 0.95), (-0.4, -2.2, 1.3)], 0.06, 10, k['metal']), 'Arm.01'),
             tag(tube([(-0.4, -2.2, 1.3), (-0.4, -2.9, 0.7)], 0.05, 10, k['metal']), 'Arm.02'),
             tag(cylinder(0.16, 0.3, (-0.4, -2.95, 0.62), (0.9, 0, 0), k['dark'], 16), 'Arm.02')]
    for sx in (0.14, -0.14):
        parts.append(tag(sphere(0.085, (0.5 + sx, -1.16, 2.38), material=k['glow']), 'Head'))
    tyre = M.metal('#8d949b', 'tyre', 0.5, 1.0)
    wheels = []
    for i, y in enumerate((-1.25, 0.05, 1.3)):
        for side, sx in (('L', 1), ('R', -1)):
            name = 'Wheel%d.%s' % (i, side)
            c = Vector((sx * 1.25, y, 0.36))
            rig.bone(name, c, c + Vector((sx * 0.3, 0, 0)), 'Body')
            w = cylinder(0.36, 0.32, c, (0, math.pi / 2, 0), tyre, 28, bevel_width=0.04)
            parts.append(tag(w, name))
            for j in range(12):
                a = TAU * j / 12
                parts.append(tag(box((0.34, 0.04, 0.05), c + Vector((0, 0.37 * math.cos(a),
                                                                  0.37 * math.sin(a))),
                                     (a, 0, 0), k['dark']), name))
            parts.append(tag(tube([c, (sx * 0.85, y * 0.6, 0.95)], 0.045, 8, k['metal']), 'Body'))
            wheels.append(name)
    rig.build()

    def drive(t, P):
        for w in wheels:
            P.rot(w, 0, -TAU * t * 2, 0)
        P.move('Body', 0, 0, 0.03 * wave(t, 0, 3))
        P.turn('Body', x=0.02 * wave(t, 0.2, 2), y=0.025 * wave(t, 0.5, 3))
        P.turn('Mast', z=0.6 * wave(t))

    def survey(t, P):
        P.turn('Mast', z=1.2 * wave(t))
        P.turn('Head', x=0.3 * wave(t, 0.2, 2))
        r = pulse(t, 0.2, 0.45, 0.6, 0.85)
        P.turn('Arm.01', x=0.5 * r)
        P.turn('Arm.02', x=-0.9 * r)
    rig.clip('Drive', 4.0, drive)
    rig.clip('Survey', 10.0, survey)
    return done(rig, parts, 'perseverance-rover', {'preview_dark': False})


def scout_drone():
    k = kit()
    rig = Rig('ingenuity-helicopter')
    rig.bone('Body', (0, 0, 0.5), (0, 0, 0.8))
    rig.bone('Rotor.Top', (0, 0, 1.25), (0, 0, 1.35), 'Body')
    rig.bone('Rotor.Low', (0, 0, 1.05), (0, 0, 1.15), 'Body')
    parts = [tag(box((0.34, 0.34, 0.34), (0, 0, 0.62), material=k['foil'], bevel_width=0.04),
                 'Body'),
             tag(cylinder(0.025, 0.75, (0, 0, 1.1), material=k['metal'], segments=12), 'Body'),
             tag(box((0.3, 0.2, 0.02), (0, 0, 1.5), material=k['solar']), 'Body'),
             tag(sphere(0.05, (0, -0.18, 0.6), material=k['glow']), 'Body')]
    for i in range(4):
        a = TAU * i / 4 + TAU / 8
        parts.append(tag(tube([(0.12 * math.cos(a), 0.12 * math.sin(a), 0.5),
                               (0.5 * math.cos(a), 0.5 * math.sin(a), 0.02)], 0.012, 6,
                              k['black']), 'Body'))
    for bone, z, turn0 in (('Rotor.Top', 1.3, 0), ('Rotor.Low', 1.1, TAU / 4)):
        for s in (0, math.pi):
            blade = box((1.15, 0.11, 0.012), (0.6, 0, 0), material=k['black'], bevel_width=0.004)
            place(blade, (0, 0, z), (0.08, 0, turn0 + s))
            parts.append(tag(blade, bone))
    rig.build()

    def hover(t, P):
        P.rot('Rotor.Top', 0, TAU * t * 6, 0)
        P.rot('Rotor.Low', 0, -TAU * t * 6, 0)
        P.move('Body', 0.05 * wave(t, 0.2), 0, 0.5 + 0.08 * wave(t))
        P.turn('Body', x=0.06 * wave(t, 0.1), y=0.06 * wave(t, 0.4), z=0.3 * wave(t, 0.3))
    rig.clip('Rotor Hover', 3.0, hover)
    return done(rig, parts, 'ingenuity-helicopter', {'preview_dark': False})


def lander(name, legs=4, style='moon'):
    k = kit()
    rig = Rig(name)
    rig.bone('Body', (0, 0, 1.2), (0, 0, 2.2))
    rig.bone('Dish', (0.9, 0, 3.4), (0.9, 0, 4.0), 'Body')
    rig.bone('Flame', (0, 0, 1.0), (0, 0, 0), 'Body')
    parts = []
    if style == 'moon':
        parts.append(tag(lathe([(0, 1.0), (1.7, 1.0), (1.9, 1.25), (1.9, 2.1), (1.7, 2.3), (0, 2.3)],
                               8, material=k['foil']), 'Body'))
        cab = ico(1.15, (0, -0.1, 3.1), 1, (1.1, 1, 0.95), k['hull'])
        from core import shade
        shade(cab, False)
        parts.append(tag(cab, 'Body'))
        for sx in (0.45, -0.45):
            parts.append(tag(prism([(-0.3, 0), (0.3, 0), (0, 0.5)], 0.05, k['black']), 'Body'))
            place(parts[-1], (sx, -1.05, 3.1), (0, 0, 0))
    else:
        parts.append(tag(lathe([(0, 1.0), (1.5, 1.0), (1.8, 1.4), (1.5, 1.9), (0, 1.9)], 3,
                               material=k['hull']), 'Body'))
        parts.append(tag(box((1.0, 1.0, 0.7), (0, 0, 2.2), material=k['foil'], bevel_width=0.06),
                         'Body'))
        parts.append(tag(tube([(-0.6, -0.6, 2.2), (-1.4, -1.7, 1.6), (-1.5, -2.2, 0.8)], 0.05, 8,
                              k['metal']), 'Body'))
    parts.append(tag(lathe([(0.25, 1.05), (0.4, 0.8), (0.75, 0.35), (0.7, 0.35), (0.3, 0.8)], 28,
                           material=k['metal'], cap=False), 'Body'))
    parts.append(tag(lathe([(0, 0), (0.6, 0.1), (0.5, 0.6), (0.2, 1.3), (0, 1.6)], 16, (0, 0, 0.35),
                           (math.pi, 0, 0), M.emissive('#ffb347', 'flame', 8.0, '#ff5a1c')),
                     'Flame'))
    for i in range(legs):
        a = TAU * i / legs + TAU / (legs * 2)
        top = Vector((1.5 * math.cos(a), 1.5 * math.sin(a), 1.9))
        foot = Vector((3.0 * math.cos(a), 3.0 * math.sin(a), 0.1))
        parts.append(tag(tube([top, foot], 0.07, 10, k['metal']), 'Body'))
        parts.append(tag(tube([Vector((1.6 * math.cos(a), 1.6 * math.sin(a), 1.1)), foot], 0.05, 8,
                              k['metal']), 'Body'))
        parts.append(tag(lathe([(0, 0.12), (0.42, 0.06), (0.45, 0), (0, 0)], 20, foot - Vector(
            (0, 0, 0.1)), material=k['foil']), 'Body'))
    parts.append(tag(tube([(0.9, 0, 2.6), (0.9, 0, 3.5)], 0.035, 8, k['metal']), 'Body'))
    parts.append(tag(lathe([(0, 0), (0.3, 0.05), (0.55, 0.2), (0.53, 0.22), (0.3, 0.08), (0, 0.04)],
                           28, (0.9, 0, 3.5), material=k['hull'], cap=False), 'Dish'))
    rig.build()

    def touchdown(t, P):
        d = 1 - ease(min(1, t / 0.7))
        settle = pulse(t, 0.7, 0.76, 0.8, 0.95)
        P.move('Body', 0, 0, 9 * d * d - 0.12 * settle)
        P.scale('Flame', 0.3 + 1.2 * (t < 0.72) * (0.6 + 0.4 * d) + 0.1 * wave(t, 0, 31),
                0.2 + 1.6 * (t < 0.72) * (0.5 + 0.5 * d), 0.3 + 1.2 * (t < 0.72))
        P.turn('Dish', z=TAU * t)

    def idle(t, P):
        P.scale('Flame', 0.02, 0.02, 0.02)
        P.turn('Dish', z=1.5 * wave(t), x=0.3 * wave(t, 0.2, 2))
    rig.clip('Signal Sweep', 10.0, idle)
    rig.clip('Touchdown', 8.0, touchdown, loop=False)
    return done(rig, parts, name)


def probe(name, gold=False, ringed=False):
    k = kit()
    rig = Rig(name)
    rig.bone('Body', (0, 0, 0), (0, 0, 1))
    rig.bone('Dish', (0, 0, 0.9), (0, 0, 1.6), 'Body')
    rig.bone('Boom', (0.9, 0, 0), (4.5, 0, 0), 'Body')
    parts = [tag(lathe([(0, -0.5), (0.9, -0.5), (0.95, -0.4), (0.95, 0.4), (0.9, 0.5), (0, 0.5)],
                       10, material=k['foil'] if gold else k['hull']), 'Body'),
             tag(lathe([(0, 0), (0.7, 0.12), (1.5, 0.5), (1.9, 0.95), (1.87, 0.98), (1.45, 0.55),
                        (0.7, 0.18), (0, 0.06)], 48, (0, 0, 0.9), material=k['hull'], cap=False),
                 'Dish'),
             tag(tube([(0, 0, 0.9), (0, 0, 2.0)], 0.03, 8, k['metal']), 'Dish'),
             tag(sphere(0.12, (0, 0, 2.0), material=k['dark']), 'Dish'),
             tag(tube([(0.9, 0, 0), (4.5, 0, 0)], 0.035, 8, k['metal']), 'Boom'),
             tag(box((0.5, 0.35, 0.35), (4.6, 0, 0), material=k['dark'], bevel_width=0.04),
                 'Boom'),
             tag(tube([(-0.9, 0, 0), (-3.4, 0.6, -0.4)], 0.03, 8, k['metal']), 'Body'),
             tag(cylinder(0.2, 0.9, (-3.5, 0.62, -0.42), (0, math.pi / 2, 0.2), k['dark'], 16,
                          bevel_width=0.03), 'Body')]
    for a in (0.6, -0.6):
        parts.append(tag(tube([(0, 0, -0.5), (3.5 * math.sin(a), 3.5 * math.cos(a) * 0.3,
                                              -3.2)], 0.012, 6, k['metal']), 'Body'))
    if ringed:
        parts.append(tag(lathe([(0.0, 0.0), (0.6, 0.0), (0.72, 0.5), (0.5, 0.95), (0.0, 1.05)], 28,
                               (0, 0, -1.6), material=k['foil']), 'Body'))
        parts.append(tag(torus(1.25, 0.03, (0, 0, 0), material=k['warm']), 'Body'))
    rig.build()

    def cruise(t, P):
        P.turn('Body', z=TAU * t, x=0.15 * wave(t, 0.2))
        P.turn('Dish', x=0.25 * wave(t, 0.1, 2), y=0.25 * wave(t, 0.35, 2))
        P.turn('Boom', z=0.04 * wave(t, 0, 6))
    rig.clip('Orbital Turn', 24.0, cruise)
    rig.clip('Dish Sweep', 8.0, lambda t, P: (P.turn('Dish', x=0.6 * wave(t), y=0.4 * wave(
        t, 0.25))))
    return done(rig, parts, name)


def telescope(name, mirror=False):
    k = kit()
    rig = Rig(name)
    rig.bone('Body', (0, 0, 0), (0, 0, 1))
    rig.bone('Lid', (0, 1.0, 3.2), (0, 1.0, 5.0), 'Body')
    rig.bone('Panel.L', (1.0, 0, 0), (4.0, 0, 0), 'Body')
    rig.bone('Panel.R', (-1.0, 0, 0), (-4.0, 0, 0), 'Body')
    parts = []
    if mirror:
        gold = M.gold('mirror', 0.08)
        for q in range(-2, 3):
            for r in range(-2, 3):
                if abs(q + r) > 2 or (q == 0 and r == 0):
                    continue
                x, z = 0.95 * (q + r / 2), 0.82 * r
                h = cylinder(0.52, 0.08, (x, 0, 2.6 + z), (math.pi / 2, 0, 0), gold, 6)
                from core import shade
                shade(h, False)
                parts.append(tag(h, 'Body'))
        for i in range(5):
            s = 1 - i * 0.07
            parts.append(tag(prism([(-5.2 * s, 0), (0, -2.2 * s), (5.2 * s, 0), (0, 2.2 * s)], 0.03,
                                   k['foil'] if i % 2 else M.foil('#c9c2d6', 'silver', 0.2)),
                             'Body'))
            place(parts[-1], (0, 0.6, -0.2 - i * 0.22), (math.pi / 2, 0, 0))
        parts.append(tag(tube([(0, 0, 0.5), (0, -3.4, 3.2)], 0.04, 8, k['dark']), 'Body'))
        parts.append(tag(cylinder(0.3, 0.1, (0, -3.4, 3.2), (math.pi / 2 + 0.6, 0, 0), gold, 6),
                         'Body'))
        parts.append(tag(box((1.2, 1.0, 0.9), (0, 0.9, 0.5), material=k['hull'], bevel_width=0.06),
                         'Body'))
    else:
        parts.append(tag(lathe([(0, -3.0), (1.15, -3.0), (1.2, -2.8), (1.2, 0.2), (1.0, 0.4),
                                (1.0, 3.2), (0.94, 3.2), (0.94, -2.6), (0, -2.6)], 40,
                               material=M.foil('#c9ced6', 'silver', 0.22)), 'Body'))
        parts.append(tag(cylinder(1.22, 0.5, (0, 0, -1.2), material=k['foil'], segments=40),
                         'Body'))
        lid = lathe([(0, 0), (1.0, 0), (1.02, 0.06), (0, 0.06)], 40, (0, 0, 0),
                    material=k['hull'])
        place(lid, (0, 0.0, 4.2), (math.pi / 2 - 0.2, 0, 0))
        parts.append(tag(lid, 'Lid'))
        parts.append(tag(sphere(0.6, (0, 0, -2.3), (1, 1, 0.25), material=k['glow']), 'Body'))
    for side, sx in (('L', 1), ('R', -1)):
        parts += array(k, 'Panel.' + side, (sx * 1.0, 0, -1.0 if not mirror else 0.4), (sx, 0, 0),
                       3.6, 1.5)
    rig.build()

    def scan(t, P):
        P.turn('Body', z=0.5 * wave(t), x=0.2 * wave(t, 0.25))
        for side, sx in (('L', 1), ('R', -1)):
            P.rot('Panel.' + side, 0, 0.5 * wave(t, 0.1), 0)
        P.turn('Lid', x=0.15 * wave(t, 0, 2))
    turn(rig, 30.0)
    rig.clip('Scan the Sky', 12.0, scan)
    return done(rig, parts, name, {'preview_angle': 150 if mirror else 40})


def station():
    k = kit()
    rig = Rig('space-station')
    rig.bone('Body', (0, 0, 0), (0, 0, 1))
    rig.bone('Ring', (0, 0, 0), (0, 0.6, 0), 'Body')
    parts = [tag(cylinder(0.9, 9, (0, 0, 0), (0, math.pi / 2, 0), k['hull'], 32, bevel_width=0.1),
                 'Body'),
             tag(cylinder(0.75, 5, (0, 0, 0), (math.pi / 2, 0, 0), k['hull'], 32, bevel_width=0.1),
                 'Body'),
             tag(sphere(1.3, (0, 0, 0), material=k['foil']), 'Body'),
             tag(tube([(0, 0, -5.5), (0, 0, 5.5)], 0.18, 10, k['metal']), 'Body')]
    for z in (-4.4, 4.4):
        for side, sx in (('L', 1), ('R', -1)):
            name = 'Array%s%s' % ('A' if z > 0 else 'B', side)
            rig.bone(name, (0, 0, z), (sx * 3, 0, z), 'Body')
            parts += array(k, name, (sx * 0.3, 0, z), (sx, 0, 0), 5.5, 1.9, 4)
    parts.append(tag(torus(3.4, 0.42, (0, 0, 0), (math.pi / 2, 0, 0), k['hull'], 64, 16), 'Ring'))
    for i in range(4):
        a = TAU * i / 4
        parts.append(tag(tube([(0, 0, 0), (3.4 * math.cos(a), 0, 3.4 * math.sin(a))], 0.14, 8,
                              k['metal']), 'Ring'))
    for i in range(16):
        a = TAU * i / 16
        parts.append(tag(box((0.3, 0.05, 0.16), (3.4 * math.cos(a), -0.42, 3.4 * math.sin(a)),
                             (0, -a, 0), k['warm']), 'Ring'))
    rig.build()

    def orbit(t, P):
        P.turn('Body', z=TAU * t / 3 * 0 + 0.3 * wave(t), x=0.12 * wave(t, 0.25))
        P.rot('Ring', 0, TAU * t, 0)
        for n in ('ArrayAL', 'ArrayAR', 'ArrayBL', 'ArrayBR'):
            P.rot(n, 0, 0.6 * wave(t, 0.1), 0)
    rig.clip('Orbital Rotation', 20.0, orbit)
    return done(rig, parts, 'space-station')


def control_room():
    k = kit()
    rig = Rig('mission-control')
    rig.bone('Body', (0, 0, 0), (0, 0, 1))
    rig.bone('Screen', (0, 4.6, 2.6), (0, 4.6, 3.6), 'Body')
    floor = M.concrete('#3a3d44', 'floor', 1.2)
    parts = [tag(box((12, 10, 0.2), (0, 0, -0.1), material=floor), 'Body'),
             tag(box((12, 0.3, 5), (0, 5, 2.5), material=M.plaster('#2a2e36', 'wall', 0.2)),
                 'Body'),
             tag(box((8.4, 0.1, 3.0), (0, 4.8, 3.0), material=M.screen('#3fb6ff', 'bigscreen', 60,
                                                                       3.0)), 'Screen')]
    for sx in (-1, 1):
        parts.append(tag(box((1.7, 0.1, 1.3), (sx * 5.0, 4.8, 3.6), material=M.screen(
            '#ffb347' if sx > 0 else '#7dff9a', 'side%d' % sx, 40, 3.0)), 'Screen'))
    desk = M.plastic('#d9d6cf', 'desk', 0.4)
    for row in range(3):
        y = 2.2 - row * 2.6
        z = row * 0.35
        parts.append(tag(box((10, 2.4, 0.35), (0, y - 0.4, z - 0.17 + 0.0), material=floor),
                         'Body'))
        for i in range(5):
            x = -4 + i * 2
            parts.append(tag(box((1.7, 0.8, 0.75), (x, y, z + 0.38), material=desk,
                                 bevel_width=0.04), 'Body'))
            parts.append(tag(box((0.9, 0.05, 0.5), (x, y + 0.2, z + 1.05), (-0.25, 0, 0),
                                 M.screen(('#3fb6ff', '#7dff9a', '#ffb347')[(i + row) % 3],
                                          'mon%d%d' % (row, i), 90, 2.5)), 'Body'))
            parts.append(tag(box((0.5, 0.5, 0.08), (x, y - 1.0, z + 0.45), material=k['dark'],
                                 bevel_width=0.03), 'Body'))
            parts.append(tag(box((0.5, 0.08, 0.6), (x, y - 1.24, z + 0.75), material=k['dark'],
                                 bevel_width=0.03), 'Body'))
    rig.build()
    rig.clip('Room Details', 6.0, lambda t, P: P.scale('Screen', 1 + 0.004 * wave(t, 0, 3), 1,
                                                       1 + 0.004 * wave(t, 0.3, 2)))
    return done(rig, parts, 'mission-control', {'preview_angle': 200, 'preview_elevation': 22})


MODELS = {
    'saturn-v': moon_rocket,
    'space-shuttle': spaceplane,
    'perseverance-rover': mars_rover,
    'ingenuity-helicopter': scout_drone,
    'apollo-lunar-module': lambda: lander('apollo-lunar-module', 4, 'moon'),
    'viking-lander': lambda: lander('viking-lander', 3, 'mars'),
    'voyager': lambda: probe('voyager'),
    'cassini': lambda: probe('cassini', gold=True, ringed=True),
    'hubble': lambda: telescope('hubble'),
    'james-webb': lambda: telescope('james-webb', mirror=True),
    'space-station': station,
    'mission-control': control_room,
}
ATLAS = {name: 2048 for name in MODELS}
