"""Creatures nobody has met: original aliens and monsters, each with its own rig and moods.

They are built to be cast in very different scenes: dread (Void Stalker, Shadow Wraith, Maw
Worm), wonder (Star Jelly, Sky Leviathan, Bloom Titan), play (Glow Sprite) and menace
(Abyss Watcher, Hive Crawler, Tripod Colossus, Crystal Golem).
"""
import math
import random

from core import (Meta, Rig, Vector, ease, join, lathe, place, pulse, sphere, tag, tube, wave,
                  ico, roughen, torus)
import materials as M

DARK = {'preview_dark': True}


def eyeball(centre, radius, forward, iris='#ffb000', glow=4.0, slit=False, bone='Head',
            white='#d9d2c4'):
    """Sclera, a glowing iris and a pupil, aimed along forward."""
    f = Vector(forward).normalized()
    rot = f.to_track_quat('Z', 'Y').to_euler()
    c = Vector(centre)
    parts = [sphere(radius, c, material=M.eye(white, 'sclera'), segments=28, rings=16)]
    a = 0.62
    prof = [(radius * 1.012 * math.sin(a * i / 6), radius * 1.012 * math.cos(a * i / 6))
            for i in range(6, -1, -1)]
    parts.append(lathe(prof, 28, c, rot, M.emissive(iris, 'iris', glow), 'iris', cap=False))
    b = 0.26
    prof = [(radius * 1.022 * math.sin(b * i / 4), radius * 1.022 * math.cos(b * i / 4))
            for i in range(4, -1, -1)]
    pupil = lathe(prof, 20, material=M.eye('#020202', 'pupil'), name='pupil', cap=False,
                  scale=(0.32, 1.25, 1) if slit else (1, 1, 1))
    parts.append(place(pupil, c, rot))
    return [tag(p, bone) for p in parts]


def tentacle(rig, meta, name, points, r0, r1, parent, bones=6, bulb=0.0):
    """A bone chain with a tapering body around it."""
    pts = [Vector(p) for p in points]
    seg = len(pts) - 1

    def at(f):
        x = f * seg
        i = min(seg - 1, int(x))
        return pts[i].lerp(pts[i + 1], x - i)
    names = rig.chain(name, [at(i / bones) for i in range(bones + 1)], parent)
    n = bones * 3
    path = [at(i / n) for i in range(n + 1)]
    radii = [r0 + (r1 - r0) * (i / n) ** 0.8 for i in range(n + 1)]
    if bulb:
        radii[-1] = radii[-2] = bulb
    meta.path(path, radii)
    return names


def sway(P, name, bones, t, amp=0.2, phase=0.0, lag=0.12, axis='x', cycles=1, grow=0.0,
         second=0.0):
    """A wave that travels down a chain, in armature axes."""
    for i in range(1, bones + 1):
        a = amp * (1 + grow * i) * math.sin(math.tau * (t * cycles + phase - lag * i))
        b = second * amp * math.sin(math.tau * (t * cycles * 2 + phase * 1.7 - lag * i))
        P.turn('%s.%02d' % (name, i), **{axis: a, ('z' if axis == 'x' else 'x'): b})


def finish(rig, soft, rigid, name):
    body = join(soft, 'body')
    rig.bind_auto(body)
    for part in rigid:
        part.vertex_groups.new(name=part['bone']).add(range(len(part.data.vertices)), 1.0,
                                                      'REPLACE')
    mesh = join([body] + rigid, name)
    rig.finish()
    return mesh


# ----------------------------------------------------------------------------- 1
def abyss_watcher():
    """A floating eye the size of a house, trailing a skirt of tentacles."""
    rig = Rig('abyss-watcher')
    rig.bone('Root', (0, 0, 0), (0, 0.5, 0), deform=False)
    rig.bone('Body', (0, 0, 3.2), (0, 0, 4.4), 'Root')
    rig.bone('Head', (0, 0, 3.6), (0, -1.3, 3.6), 'Body')
    rig.bone('Lid.Up', (0, -0.4, 4.4), (0, -1.25, 3.9), 'Body')
    rig.bone('Lid.Down', (0, -0.4, 2.8), (0, -1.25, 3.3), 'Body')
    m = Meta(0.05)
    m.ball((0, 0.15, 3.6), 1, (1.35, 1.45, 1.3))
    m.ball((0, -0.95, 3.6), 0.92, negative=True)
    for sx in (1, -1):
        m.ball((sx * 0.9, 0.5, 4.3), 1, (0.5, 0.6, 0.4))
    n = 9
    for i in range(n):
        a = math.tau * i / n + 0.2
        r = 0.85
        base = Vector((r * math.cos(a), 0.15 + r * math.sin(a), 2.6))
        length = 3.0 + 0.9 * math.sin(i * 2.4)
        pts = [base + Vector((0.35 * math.cos(a) * f * 2, 0.35 * math.sin(a) * f * 2 +
                              0.25 * f, -length * f / 3 * (1 - 0.1 * f)))
               for f in range(4)]
        tentacle(rig, m, 'Tentacle%d' % i, pts, 0.24, 0.035, 'Body', 6, bulb=0.07)
    for i in range(5):
        a = math.pi * (0.2 + 0.6 * i / 4)
        base = Vector((1.0 * math.cos(a), 0.4, 3.6 + 1.05 * math.sin(a)))
        pts = [base, base + Vector((0.5 * math.cos(a), 0.5, 0.6 * math.sin(a) + 0.3)),
               base + Vector((0.7 * math.cos(a), 1.3, 1.0 * math.sin(a) + 0.5))]
        tentacle(rig, m, 'Stalk%d' % i, pts, 0.11, 0.05, 'Body', 3, bulb=0.13)
    rig.build()
    body = m.mesh('body', M.alien_skin('#141a2a', '#3a1a44', '#ff3d7a', 'hide', 0.45, 1.0, 5.0))
    rigid = eyeball((0, -0.45, 3.6), 1.02, (0, -1, 0), '#ffb300', 5.0, slit=True)
    for p in rigid:
        p['bone'] = 'Head'
    for i in range(5):
        a = math.pi * (0.2 + 0.6 * i / 4)
        tip = Vector((1.7 * math.cos(a), 1.7, 3.6 + 2.05 * math.sin(a) + 0.5))
        rigid += [tag(sphere(0.1, tip, material=M.emissive('#ff3d7a', 'tip', 6.0)),
                      'Stalk%d.03' % i)]

    def tentacles(t, P, energy=1.0, lash=0.0):
        for i in range(9):
            a = math.tau * i / 9 + 0.2
            sway(P, 'Tentacle%d' % i, 6, t, 0.16 * energy, i * 0.13, 0.13, 'x', 1, 0.15, 0.4)
            if lash:
                for j in range(1, 7):
                    P.turn('Tentacle%d.%02d' % (i, j), x=-lash * 0.2 * math.sin(a),
                           y=lash * 0.2 * math.cos(a))
        for i in range(5):
            sway(P, 'Stalk%d' % i, 3, t, 0.12 * energy, i * 0.21, 0.15, 'z', 2)

    def hover(t, P):
        P.move('Body', 0.05 * wave(t, 0.2), 0, 0.18 * wave(t))
        P.turn('Body', x=0.05 * wave(t, 0.1), z=0.1 * wave(t, 0.3))
        P.turn('Head', z=0.25 * wave(t, 0.15), x=0.1 * wave(t, 0.4, 2))
        blink = max(0, 1 - abs(t - 0.6) * 20)
        P.turn('Lid.Up', x=0.55 * blink)
        P.turn('Lid.Down', x=-0.45 * blink)
        tentacles(t, P)

    def stare(t, P):
        lock = pulse(t, 0.1, 0.25, 0.8, 0.95)
        P.move('Body', 0, -0.5 * lock, 0.1 * wave(t) - 0.3 * lock)
        P.turn('Body', x=0.25 * lock)
        P.scale('Head', 1 + 0.07 * lock * wave(t, 0, 8))
        P.turn('Lid.Up', x=-0.2 * lock)
        P.turn('Lid.Down', x=0.2 * lock)
        tentacles(t, P, 0.4 + 0.6 * (1 - lock))

    def lash(t, P):
        hit = pulse(t, 0.15, 0.3, 0.4, 0.75)
        P.move('Body', 0, 0.3 * hit, 0.4 * hit)
        P.turn('Body', x=-0.3 * hit)
        P.turn('Lid.Up', x=0.3 * hit)
        tentacles(t, P, 1 + 2.5 * hit, lash=hit * 2.2)

    rig.clip('Hover', 6.0, hover)
    rig.clip('Stare', 6.0, stare)
    rig.clip('Lash', 3.0, lash)
    return rig, finish(rig, [body], rigid, 'abyss-watcher'), DARK


# ----------------------------------------------------------------------------- 2
def void_stalker():
    """Too tall and too thin, with a slit of light where a face should be."""
    rig = Rig('void-stalker')
    rig.bone('Root', (0, 0, 0), (0, 0.5, 0), deform=False)
    rig.bone('Hips', (0, 0.1, 3.3), (0, 0.05, 3.7), 'Root')
    rig.bone('Spine.01', (0, 0.05, 3.7), (0, -0.05, 4.4), 'Hips', True)
    rig.bone('Spine.02', (0, -0.05, 4.4), (0, -0.25, 5.0), 'Spine.01', True)
    rig.bone('Neck', (0, -0.25, 5.0), (0, -0.55, 5.5), 'Spine.02', True)
    rig.bone('Head', (0, -0.55, 5.5), (0, -0.95, 5.75), 'Neck', True)
    m = Meta(0.035)
    m.path([(0, 0.1, 3.3), (0, 0.05, 3.9), (0, -0.05, 4.5), (0, -0.25, 5.0)],
           [0.24, 0.17, 0.26, 0.2])
    m.ball((0, -0.05, 4.65), 1, (0.42, 0.3, 0.4))
    m.limb((0, -0.25, 5.0), (0, -0.55, 5.5), 0.11, 0.09)
    m.ball((0, -0.75, 5.62), 1, (0.2, 0.38, 0.24), (0.5, 0, 0))
    for i in range(7):
        f = i / 6
        base = Vector((0, 0.25 - 0.3 * f, 3.9 + 1.3 * f))
        m.limb(base, base + Vector((0, 0.55 + 0.25 * math.sin(f * 3), 0.35)), 0.07, 0.012)
    for side, sx in (('L', 1), ('R', -1)):
        hip = Vector((sx * 0.25, 0.1, 3.3))
        knee = Vector((sx * 0.75, -0.55, 3.9))
        hock = Vector((sx * 0.9, 0.1, 1.5))
        foot = Vector((sx * 0.95, -0.25, 0.08))
        rig.bone('Leg.Up.' + side, hip, knee, 'Hips')
        rig.bone('Leg.Mid.' + side, knee, hock, 'Leg.Up.' + side, True)
        rig.bone('Leg.Low.' + side, hock, foot, 'Leg.Mid.' + side, True)
        rig.bone('Foot.' + side, foot, foot + Vector((0, -0.45, -0.05)), 'Leg.Low.' + side, True)
        rig.bone('ik.Leg.' + side, foot, foot + Vector((0, -0.45, -0.05)), 'Root', deform=False)
        m.path([hip, knee, hock, foot], [0.15, 0.09, 0.07, 0.05])
        m.ball(knee, 0.12)
        m.ball(hock, 0.09)
        for k in (-1, 0, 1):
            m.limb(foot, foot + Vector((k * 0.16, -0.5, -0.04)), 0.05, 0.012)
        sh = Vector((sx * 0.4, -0.1, 4.8))
        el = Vector((sx * 0.85, 0.15, 3.6))
        wr = Vector((sx * 0.8, -0.35, 2.2))
        rig.bone('Arm.Up.' + side, sh, el, 'Spine.02')
        rig.bone('Arm.Low.' + side, el, wr, 'Arm.Up.' + side, True)
        rig.bone('Hand.' + side, wr, wr + Vector((0, -0.1, -0.35)), 'Arm.Low.' + side, True)
        m.path([sh, el, wr], [0.1, 0.06, 0.045])
        for k in range(4):
            tip = wr + Vector(((k - 1.5) * 0.09, -0.12 - 0.05 * (k % 2), -0.75))
            rig.chain('Claw%d.%s' % (k, side), [wr, wr.lerp(tip, 0.5), tip], 'Hand.' + side)
            m.limb(wr, tip, 0.035, 0.006)
    rig.build()
    for side in 'LR':
        rig.ik('Leg.Low.' + side, 'ik.Leg.' + side, 3)
        rig.copy_rotation('Foot.' + side, 'ik.Leg.' + side)
    body = m.mesh('body', M.void_skin('#b8c6ff', 'hide', 0.5, 6.0))
    slit = tag(sphere(0.1, (0, -1.05, 5.56), (0.22, 0.6, 1.5), (0.5, 0, 0),
                      material=M.emissive('#fff2c9', 'slit', 9.0)), 'Head')

    def legs(t, P, stride=1.3, lift=0.7, width=0.0):
        for side, ph, sx in (('L', 0.0, 1), ('R', 0.5, -1)):
            p = (t + ph) % 1.0
            if p < 0.6:
                y, z = (-0.5 + p / 0.6) * stride, 0.0
            else:
                u = (p - 0.6) / 0.4
                y, z = (0.5 - ease(u)) * stride, lift * math.sin(math.pi * u)
            P.move('ik.Leg.' + side, sx * width, y, z)
            P.turn('ik.Leg.' + side, x=0.5 * (z > 0) * math.sin(math.pi * min(1, z / lift))
                   if lift else 0)

    def hands(t, P, reach=0.0, energy=1.0):
        for side, sx in (('L', 1), ('R', -1)):
            P.turn('Arm.Up.' + side, x=-0.15 * energy * wave(t, 0.25 * sx) - 0.9 * reach,
                   y=sx * 0.2 * reach)
            P.turn('Arm.Low.' + side, x=-0.25 - 0.1 * energy * wave(t, 0.1) - 0.5 * reach)
            for k in range(4):
                for j in (1, 2):
                    P.turn('Claw%d.%s.%02d' % (k, side, j),
                           x=0.15 * wave(t, k * 0.2, 2) - 0.5 * reach * (j == 1) + 0.4 * reach)

    def stalk(t, P):
        legs(t, P)
        P.move('Hips', 0.12 * wave(t, 0.1), 0, -0.25 + 0.1 * math.cos(2 * math.tau * t))
        P.turn('Hips', z=0.12 * wave(t), y=0.08 * wave(t, 0.1))
        P.turn('Spine.01', x=0.12, z=-0.1 * wave(t))
        P.turn('Spine.02', x=0.1)
        P.turn('Neck', x=0.15, z=0.2 * wave(t, 0.3))
        P.turn('Head', z=0.25 * wave(t, 0.4), y=0.2 * wave(t, 0.15, 2))
        hands(t, P)

    def idle(t, P):
        P.move('Hips', 0.05 * wave(t), 0, -0.15 + 0.06 * wave(t, 0, 2))
        P.turn('Spine.01', x=0.05 * wave(t, 0.1, 2))
        P.turn('Head', y=0.5 * max(0, math.sin(math.tau * (t * 3))) ** 8 + 0.1 * wave(t),
               z=0.3 * wave(t, 0.2))
        hands(t, P, 0.0, 0.6)

    def loom(t, P):
        d = pulse(t, 0.1, 0.45, 0.6, 0.95)
        P.move('Hips', 0, -0.9 * d, -0.9 * d)
        P.turn('Hips', x=0.5 * d)
        P.turn('Spine.01', x=0.35 * d)
        P.turn('Spine.02', x=0.3 * d)
        P.turn('Neck', x=-0.5 * d)
        P.turn('Head', x=-0.3 * d, y=0.6 * d * wave(t, 0, 3))
        P.scale('Head', 1 + 0.1 * d)
        hands(t, P, d, 0.5)

    def screech(t, P):
        d = pulse(t, 0.1, 0.22, 0.7, 0.9)
        shake = math.sin(math.tau * t * 22) * d
        P.move('Hips', 0, 0.2 * d, 0.15 * d)
        P.turn('Spine.01', x=-0.25 * d)
        P.turn('Spine.02', x=-0.3 * d + 0.02 * shake)
        P.turn('Neck', x=-0.4 * d)
        P.turn('Head', x=-0.5 * d + 0.05 * shake, z=0.06 * shake)
        P.scale('Head', 1 + 0.25 * d, 1 + 0.1 * d, 1 + 0.25 * d)
        for side, sx in (('L', 1), ('R', -1)):
            P.turn('Arm.Up.' + side, y=sx * -1.1 * d, x=0.3 * d)
            P.turn('Arm.Low.' + side, x=-0.6 * d)
            for k in range(4):
                P.turn('Claw%d.%s.01' % (k, side), x=-0.6 * d, y=(k - 1.5) * 0.25 * d)

    rig.clip('Stalk', 2.6, stalk)
    rig.clip('Idle', 6.0, idle)
    rig.clip('Loom', 6.0, loom)
    rig.clip('Screech', 3.0, screech)
    return rig, finish(rig, [body], [slit], 'void-stalker'), DARK


# ----------------------------------------------------------------------------- 3
def hive_crawler():
    """Eight legs, a segmented shell and sacs of light along its back."""
    rig = Rig('hive-crawler')
    rig.bone('Root', (0, 0, 0), (0, 0.5, 0), deform=False)
    spine = [Vector((0, 1.6 - i * 0.65, 0.95 + 0.12 * math.sin(i * 0.9))) for i in range(6)]
    rig.bone('Body.01', spine[0] + Vector((0, 0.4, 0)), spine[0], 'Root')
    for i in range(1, 6):
        rig.bone('Body.%02d' % (i + 1), spine[i - 1], spine[i], 'Body.%02d' % i, True)
    rig.bone('Head', spine[5], spine[5] + Vector((0, -0.6, -0.05)), 'Body.06', True)
    m = Meta(0.03)
    for i, c in enumerate(spine):
        r = 0.42 + 0.14 * math.sin(i * 0.8 + 0.6)
        m.ball(c, 1, (r * 1.25, 0.42, r * 0.85))
    m.ball(spine[5] + Vector((0, -0.45, -0.05)), 1, (0.36, 0.42, 0.26))
    m.limb(spine[0], spine[0] + Vector((0, 1.0, 0.5)), 0.3, 0.05)
    legs = []
    for i in range(4):
        for side, sx in (('L', 1), ('R', -1)):
            c = spine[1 + i]
            a = (0.9 - i * 0.55) * 0.5
            hip = c + Vector((sx * 0.4, 0, 0))
            knee = hip + Vector((sx * 0.8 * math.cos(a), -0.8 * math.sin(a) * 1.0, 0.75))
            foot = hip + Vector((sx * 1.55 * math.cos(a), -1.5 * math.sin(a), -c.z + 0.04))
            name = 'Leg%d.%s' % (i, side)
            rig.bone(name + '.Up', hip, knee, 'Body.%02d' % (i + 2))
            rig.bone(name + '.Low', knee, foot, name + '.Up', True)
            rig.bone('ik.' + name, foot, foot + Vector((0, 0, -0.2)), 'Root', deform=False)
            m.path([hip, knee, foot], [0.13, 0.085, 0.02])
            m.ball(knee, 0.11)
            legs.append((name, i, sx))
    for side, sx in (('L', 1), ('R', -1)):
        b0 = spine[5] + Vector((sx * 0.22, -0.7, -0.12))
        rig.chain('Mandible.' + side, [b0, b0 + Vector((sx * 0.12, -0.3, -0.05)),
                                       b0 + Vector((-sx * 0.05, -0.55, -0.08))], 'Head')
        m.path([b0, b0 + Vector((sx * 0.12, -0.3, -0.05)), b0 + Vector((-sx * 0.05, -0.55,
                                                                       -0.08))],
               [0.09, 0.06, 0.012])
    rig.build()
    for name, _, _ in legs:
        rig.ik(name + '.Low', 'ik.' + name, 2)
    body = m.mesh('body', M.chitin('#17121c', '#2f5a52', '#b6ff3d', 'shell', 0.6))
    rigid = []
    for i, c in enumerate(spine[:5]):
        for sx in (0.5, -0.5):
            rigid.append(tag(sphere(0.17, c + Vector((sx * 0.45, -0.05, 0.3)),
                                    material=M.emissive('#b6ff3d', 'sac', 5.0, '#3a5a10')),
                             'Body.%02d' % (i + 2)))
    for k in range(6):
        a = (k - 2.5) * 0.3
        rigid += eyeball(spine[5] + Vector((0.3 * math.sin(a), -0.72 - 0.08 * math.cos(a) + 0.1,
                                            0.12)), 0.055, (math.sin(a), -1, 0.4), '#ff4d2a',
                         6.0, bone='Head', white='#1a0a0a')

    def crawl_legs(t, P, stride=0.8, lift=0.35, speed=1.0):
        for name, i, sx in legs:
            ph = (t * speed + (0.5 if (i % 2 == 0) == (sx > 0) else 0.0) + i * 0.08) % 1.0
            if ph < 0.6:
                y, z = (-0.5 + ph / 0.6) * stride, 0.0
            else:
                u = (ph - 0.6) / 0.4
                y, z = (0.5 - ease(u)) * stride, lift * math.sin(math.pi * u)
            P.move('ik.' + name, 0, y, z)

    def jaws(t, P, amount):
        for side, sx in (('L', 1), ('R', -1)):
            P.turn('Mandible.%s.01' % side, z=-sx * amount)
            P.turn('Mandible.%s.02' % side, z=-sx * amount * 0.6)

    def crawl(t, P):
        crawl_legs(t, P)
        for i in range(1, 7):
            P.turn('Body.%02d' % i, z=0.09 * wave(t, -0.12 * i), x=0.03 * wave(t, 0.1 * i, 2))
        P.move('Body.01', 0, 0, 0.04 * wave(t, 0, 2))
        P.turn('Head', z=0.15 * wave(t, 0.3))
        jaws(t, P, 0.25 + 0.2 * wave(t, 0, 3))

    def idle(t, P):
        P.move('Body.01', 0, 0, 0.05 * wave(t))
        for i in range(2, 7):
            P.scale('Body.%02d' % i, 1 + 0.03 * wave(t, i * 0.15), 1, 1 + 0.03 * wave(t, i * 0.15))
        P.turn('Head', z=0.3 * wave(t, 0.1), x=0.1 * wave(t, 0.3, 2))
        jaws(t, P, 0.15 + 0.12 * wave(t, 0, 4))
        P.move('ik.Leg0.L', 0, -0.25 * max(0, wave(t, 0.2)), 0.3 * max(0, wave(t, 0.2)))

    def rear(t, P):
        d = pulse(t, 0.1, 0.35, 0.65, 0.92)
        for i in (4, 5, 6):
            P.turn('Body.%02d' % i, x=-0.42 * d)
        P.turn('Head', x=-0.3 * d)
        for name, i, sx in legs:
            if i >= 2:
                continue
            P.move('ik.' + name, sx * 0.3 * d, -0.6 * d, (2.0 - i * 0.8) * d
                   + 0.2 * d * wave(t, i * 0.3 + sx * 0.2, 5))
        jaws(t, P, 0.2 + 0.6 * d + 0.15 * d * wave(t, 0, 9))

    rig.clip('Crawl', 1.3, crawl)
    rig.clip('Idle', 5.0, idle)
    rig.clip('Rear Up', 4.0, rear)
    return rig, finish(rig, [body], rigid, 'hive-crawler'), DARK


# ----------------------------------------------------------------------------- 4
def star_jelly():
    """A drifting bell of light with a mile of ribbon behind it."""
    rig = Rig('star-jelly')
    rig.bone('Root', (0, 0, 0), (0, 0.5, 0), deform=False)
    rig.bone('Bell', (0, 0, 4.0), (0, 0, 5.4), 'Root')
    rig.bone('Rim', (0, 0, 4.0), (0, 0, 3.5), 'Bell')
    m = Meta(0.045)
    m.ball((0, 0, 4.4), 1, (1.6, 1.6, 1.15))
    m.ball((0, 0, 3.85), 1, (1.35, 1.35, 0.75), negative=True)
    m.ball((0, 0, 4.2), 1, (0.55, 0.55, 0.8))
    rnd = random.Random(4)
    arms = []
    for i in range(5):
        a = math.tau * i / 5
        base = Vector((0.3 * math.cos(a), 0.3 * math.sin(a), 3.7))
        pts = [base + Vector((0.25 * math.cos(a + f), 0.25 * math.sin(a + f), -0.75 * f))
               for f in range(5)]
        tentacle(rig, m, 'Arm%d' % i, pts, 0.2, 0.09, 'Bell', 5)
        arms.append(('Arm%d' % i, 5))
    for i in range(10):
        a = math.tau * i / 10 + 0.1
        base = Vector((1.3 * math.cos(a), 1.3 * math.sin(a), 3.75))
        ln = rnd.uniform(2.6, 3.9)
        pts = [base + Vector((0.1 * math.cos(a) * f, 0.1 * math.sin(a) * f, -ln * f / 4))
               for f in range(5)]
        tentacle(rig, m, 'Thread%d' % i, pts, 0.05, 0.02, 'Rim', 6, bulb=0.05)
        arms.append(('Thread%d' % i, 6))
    rig.build()
    body = m.mesh('body', M.biolum('#1a1040', '#7af0ff', 'bell', 0.5, 7.0, 10))
    rigid = [tag(sphere(0.5, (0, 0, 4.55), (1, 1, 0.8), material=M.emissive('#ff9de1', 'heart',
                                                                         8.0, '#5a1a4a')),
                 'Bell')]
    for i in range(10):
        a = math.tau * i / 10 + 0.1
        rigid.append(tag(sphere(0.07, (1.48 * math.cos(a), 1.48 * math.sin(a), 4.05),
                                material=M.emissive('#fff0a6', 'bead', 8.0)), 'Rim'))

    def swim(t, P, power=1.0):
        beat = math.sin(math.tau * t)
        squeeze = max(0, beat) ** 1.5
        P.scale('Bell', 1 - 0.16 * squeeze * power, 1 + 0.14 * squeeze * power,
                1 - 0.16 * squeeze * power)
        P.scale('Rim', 1 - 0.2 * squeeze * power, 1, 1 - 0.2 * squeeze * power)
        P.move('Bell', 0, 0, 0.35 * power * math.sin(math.tau * (t - 0.18)))
        P.turn('Bell', x=0.06 * wave(t, 0.3), y=0.06 * wave(t, 0.55))
        for i, (name, n) in enumerate(arms):
            sway(P, name, n, t, 0.16 * power, i * 0.17, 0.16, 'x' if i % 2 else 'y', 1, 0.12,
                 0.5)

    def bloom(t, P):
        swim(t, P, 0.35)
        open_ = pulse(t, 0.15, 0.45, 0.6, 0.95)
        P.scale('Rim', 1 + 0.35 * open_, 1, 1 + 0.35 * open_)
        for i in range(5):
            a = math.tau * i / 5
            P.turn('Arm%d.01' % i, x=-0.7 * open_ * math.sin(a), y=0.7 * open_ * math.cos(a))

    rig.clip('Swim', 3.2, swim)
    rig.clip('Drift', 9.0, lambda t, P: swim(t, P, 0.4))
    rig.clip('Bloom', 7.0, bloom)
    return rig, finish(rig, [body], rigid, 'star-jelly'), DARK


# ----------------------------------------------------------------------------- 5
def maw_worm():
    """It comes up out of the ground and it is mostly mouth."""
    rig = Rig('maw-worm')
    rig.bone('Root', (0, 0, 0), (0, 0.5, 0), deform=False)
    n = 10
    pts = [Vector((0, 0.9 * math.sin(i * 0.42) - 0.4 * (i / n) ** 2 * 4, -1.5 + i * 0.95))
           for i in range(n + 1)]
    rig.chain('Body', pts, 'Root')
    top = pts[-1]
    d = (pts[-1] - pts[-2]).normalized()
    rig.bone('Head', top, top + d * 1.0, 'Body.%02d' % n, True)
    m = Meta(0.06)
    for i, p in enumerate(pts):
        r = 0.95 + 0.12 * math.sin(i * 2.1) - 0.02 * i
        m.ball(p, r)
        if i < n:
            m.ball(p.lerp(pts[i + 1], 0.5), r * 0.86)
    m.ball(top + d * 0.6, 1.25)
    m.ball(top + d * 1.35, 0.95, negative=True)
    side = d.cross(Vector((1, 0, 0))).normalized()
    petals = []
    for i in range(6):
        a = math.tau * i / 6
        out = (Vector((1, 0, 0)) * math.cos(a) + side * math.sin(a))
        base = top + d * 1.0 + out * 0.95
        tip = base + d * 1.5 + out * 0.5
        mid = base.lerp(tip, 0.5) + out * 0.25
        rig.chain('Petal%d' % i, [base, mid, tip], 'Head')
        m.path([base, mid, tip], [0.42, 0.3, 0.06])
        petals.append(('Petal%d' % i, out))
    rig.build()
    body = m.mesh('body', M.flesh('#5a2a34', 'hide'))
    roughen(body, 0.05, 2.5)
    rigid = []
    tooth = M.horn('#e9dfc6', 'tooth')
    for ring, (rr, depth, count) in enumerate(((0.8, 0.9, 16), (0.6, 0.55, 12), (0.4, 0.25, 9))):
        for i in range(count):
            a = math.tau * i / count + ring * 0.2
            out = Vector((1, 0, 0)) * math.cos(a) + side * math.sin(a)
            b = top + d * depth + out * rr
            rigid.append(tag(tube([b, b - out * 0.3 + d * 0.12], lambda t: 0.07 * (1 - t) + 0.004,
                                  8, tooth), 'Head'))
    rigid.append(tag(sphere(0.5, top + d * 0.1, material=M.emissive('#ff5a1c', 'throat', 7.0,
                                                                  '#3a0a05')), 'Head'))

    def mouth(t, P, open_):
        for name, out in petals:
            for j in (1, 2):
                axis = d.cross(out)
                P.turn('%s.%02d' % (name, j), x=axis.x * open_, y=axis.y * open_,
                       z=axis.z * open_)

    def weave(t, P, amp=0.1, speed=1):
        for i in range(1, n + 1):
            P.turn('Body.%02d' % i, y=amp * math.sin(math.tau * (t * speed - i * 0.11)),
                   x=amp * 0.7 * math.sin(math.tau * (t * speed - i * 0.11 + 0.25)))

    def sway_clip(t, P):
        weave(t, P)
        mouth(t, P, 0.25 + 0.2 * wave(t, 0, 2))

    def rise(t, P):
        up = pulse(t, 0.0, 0.55, 0.8, 1.0)
        P.move('Body.01', 0, 0, -7.5 * (1 - up))
        weave(t, P, 0.06 + 0.1 * up, 2)
        mouth(t, P, 0.1 + 0.6 * pulse(t, 0.45, 0.6, 0.7, 0.85))

    def roar(t, P):
        r = pulse(t, 0.12, 0.25, 0.7, 0.9)
        shake = math.sin(math.tau * t * 18) * r
        weave(t, P, 0.05)
        for i in (8, 9, 10):
            P.turn('Body.%02d' % i, x=-0.16 * r + 0.012 * shake)
        P.scale('Head', 1 + 0.12 * r + 0.02 * shake)
        mouth(t, P, 0.15 + 0.85 * r + 0.04 * shake)

    def strike(t, P):
        back = pulse(t, 0.05, 0.3, 0.32, 0.42)
        hit = pulse(t, 0.36, 0.46, 0.55, 0.9)
        for i in range(4, n + 1):
            P.turn('Body.%02d' % i, x=-0.12 * back + 0.2 * hit)
        mouth(t, P, 0.2 + 0.8 * back - 0.5 * hit)

    rig.clip('Sway', 5.0, sway_clip)
    rig.clip('Rise', 5.0, rise, loop=False)
    rig.clip('Roar', 3.5, roar)
    rig.clip('Strike', 2.4, strike)
    return rig, finish(rig, [body], rigid, 'maw-worm'), DARK


# ----------------------------------------------------------------------------- 6
def sky_leviathan():
    """A whale that swims between stars, lit from inside along its flanks."""
    rig = Rig('sky-leviathan')
    rig.bone('Root', (0, 0, 0), (0, 0.5, 0), deform=False)
    n = 8
    pts = [Vector((0, -4.5 + i * 1.5, 3.0 + 0.25 * math.sin(i * 0.5))) for i in range(n + 1)]
    rig.bone('Head', pts[1], pts[0] + Vector((0, -0.6, -0.1)), 'Root')
    rig.bone('Jaw', pts[1] + Vector((0, 0, -0.7)), pts[0] + Vector((0, -0.3, -0.9)), 'Head')
    rig.chain('Body', pts[1:], 'Root')
    m = Meta(0.07)
    radii = [1.1, 1.6, 1.85, 1.8, 1.5, 1.1, 0.7, 0.4, 0.18]
    for i, p in enumerate(pts):
        m.ball(p, 1, (radii[i] * 0.95, 1.1, radii[i] * 0.85))
    m.ball(pts[0] + Vector((0, -0.4, -0.15)), 1, (0.95, 1.0, 0.7))
    fins = []
    for side, sx in (('L', 1), ('R', -1)):
        b = pts[2] + Vector((sx * 1.5, 0, -0.5))
        fp = [b, b + Vector((sx * 1.6, 0.9, -0.3)), b + Vector((sx * 3.2, 2.2, -0.2)),
              b + Vector((sx * 4.2, 3.9, 0.1))]
        rig.chain('Fin.' + side, fp, 'Body.01')
        for i in range(len(fp) - 1):
            mid = fp[i].lerp(fp[i + 1], 0.5)
            m.ball(mid, 1, (0.95 - i * 0.2, 1.1 - i * 0.15, 0.14), (0.05, 0, -sx * 0.5))
        fins.append('Fin.' + side)
        t0 = pts[-1]
        tp = [t0, t0 + Vector((sx * 1.2, 0.9, 0.1)), t0 + Vector((sx * 2.4, 1.3, 0.3))]
        rig.chain('Fluke.' + side, tp, 'Body.%02d' % (n - 1))
        m.path(tp, [0.3, 0.26, 0.05])
        m.ball(tp[1], 1, (0.75, 0.5, 0.1))
        for k in range(3):
            w0 = pts[0] + Vector((sx * 0.6, 0.2 + k * 0.25, -0.75))
            wp = [w0, w0 + Vector((sx * 0.5, 1.2, -0.9)), w0 + Vector((sx * 0.7, 3.0, -1.3)),
                  w0 + Vector((sx * 0.6, 5.2 + k, -1.2))]
            tentacle(rig, m, 'Whisker%d.%s' % (k, side), wp, 0.09, 0.02, 'Head', 5)
    dorsal = [pts[4] + Vector((0, 0, 1.4)), pts[4] + Vector((0, 0.9, 2.5)),
              pts[4] + Vector((0, 2.0, 3.0))]
    m.path(dorsal, [0.5, 0.3, 0.06])
    rig.build()
    body = m.mesh('body', M.biolum('#16263a', '#6fe3ff', 'hide', 0.22, 6.0, 9, stripes=True))
    rigid = []
    for sx in (1, -1):
        rigid += eyeball(pts[1] + Vector((sx * 1.25, -0.9, 0.2)), 0.2, (sx, -0.4, 0), '#ffe08a',
                         5.0, bone='Head', white='#0a1420')
        for k in range(7):
            rigid.append(tag(sphere(0.14, pts[1] + Vector((sx * (1.5 + 0.1 * math.sin(k)),
                                                           0.6 + k * 1.3, -0.5 + 0.15 * k)),
                                    material=M.emissive('#6fe3ff', 'port', 7.0)),
                             'Body.%02d' % min(n - 1, 1 + int(k * 0.9))))

    def swim(t, P, power=1.0):
        for i in range(1, n):
            P.turn('Body.%02d' % i, x=0.07 * power * (1 + 0.25 * i) * math.sin(
                math.tau * (t - i * 0.09)))
        P.move('Head', 0, 0, 0.25 * power * wave(t, 0.2))
        P.turn('Head', x=0.05 * power * wave(t, 0.3))
        P.turn('Jaw', x=0.06 + 0.04 * wave(t, 0.1))
        for side, sx in (('L', 1), ('R', -1)):
            for j in (1, 2, 3):
                P.turn('Fin.%s.%02d' % (side, j), y=sx * 0.22 * power * math.sin(
                    math.tau * (t - 0.1 * j)))
            for j in (1, 2):
                P.turn('Fluke.%s.%02d' % (side, j), x=0.2 * power * math.sin(
                    math.tau * (t - 0.75 - 0.1 * j)))
            for k in range(3):
                sway(P, 'Whisker%d.%s' % (k, side), 5, t, 0.1, k * 0.2, 0.14, 'x', 1, 0.2, 0.4)

    def call(t, P):
        swim(t, P, 0.5)
        c = pulse(t, 0.2, 0.35, 0.7, 0.9)
        P.turn('Head', x=-0.25 * c)
        P.turn('Jaw', x=0.5 * c)
        P.scale('Body.02', 1 + 0.06 * c)

    rig.clip('Swim', 6.0, swim)
    rig.clip('Glide', 10.0, lambda t, P: swim(t, P, 0.35))
    rig.clip('Call', 7.0, call)
    return rig, finish(rig, [body], rigid, 'sky-leviathan'), DARK


# ----------------------------------------------------------------------------- 7
def shadow_wraith():
    """A robe with nothing in it but two lights."""
    rig = Rig('shadow-wraith')
    rig.bone('Root', (0, 0, 0), (0, 0.5, 0), deform=False)
    rig.bone('Body', (0, 0, 1.7), (0, 0, 2.3), 'Root')
    rig.bone('Chest', (0, 0, 2.3), (0, -0.05, 2.9), 'Body', True)
    rig.bone('Head', (0, -0.05, 2.9), (0, -0.2, 3.45), 'Chest', True)
    m = Meta(0.03)
    m.ball((0, 0, 2.55), 1, (0.5, 0.36, 0.5))
    m.ball((0, -0.06, 3.15), 1, (0.34, 0.38, 0.42))
    m.ball((0, -0.34, 3.1), 1, (0.22, 0.26, 0.28), negative=True)
    m.limb((0, 0.12, 3.35), (0, 0.5, 2.9), 0.3, 0.1)
    rnd = random.Random(11)
    strips = []
    for i in range(11):
        a = math.tau * i / 11
        base = Vector((0.36 * math.cos(a), 0.28 * math.sin(a), 2.2))
        ln = rnd.uniform(1.5, 2.4)
        pts = [base + Vector((0.16 * math.cos(a) * f, 0.16 * math.sin(a) * f + 0.06 * f * f,
                              -ln * f / 4)) for f in range(5)]
        tentacle(rig, m, 'Tatter%d' % i, pts, 0.24, 0.03, 'Body', 5)
        strips.append('Tatter%d' % i)
    for side, sx in (('L', 1), ('R', -1)):
        sh = Vector((sx * 0.5, 0, 2.75))
        el = Vector((sx * 0.95, -0.15, 2.1))
        wr = Vector((sx * 0.85, -0.6, 1.55))
        rig.bone('Arm.Up.' + side, sh, el, 'Chest')
        rig.bone('Arm.Low.' + side, el, wr, 'Arm.Up.' + side, True)
        m.path([sh, el, wr], [0.2, 0.14, 0.16])
        for k in range(4):
            tip = wr + Vector(((k - 1.5) * 0.09, -0.3, -0.5 - 0.06 * (k % 2)))
            rig.chain('Finger%d.%s' % (k, side), [wr, wr.lerp(tip, 0.5), tip],
                      'Arm.Low.' + side)
    rig.build()
    body = m.mesh('robe', M.cloth('#07070a', 'robe', 90, 0.95, 0.6))
    rigid = []
    bone = M.horn('#cfc8b4', 'bone')
    for side, sx in (('L', 1), ('R', -1)):
        wr = Vector((sx * 0.85, -0.6, 1.55))
        for k in range(4):
            tip = wr + Vector(((k - 1.5) * 0.09, -0.3, -0.5 - 0.06 * (k % 2)))
            mid = wr.lerp(tip, 0.5)
            rigid.append(tag(tube([wr, mid], lambda t: 0.022 - 0.006 * t, 8, bone),
                             'Finger%d.%s.01' % (k, side)))
            rigid.append(tag(tube([mid, tip], lambda t: 0.016 * (1 - t) + 0.002, 8, bone),
                             'Finger%d.%s.02' % (k, side)))
        rigid.append(tag(sphere(0.045, (sx * 0.1, -0.36, 3.16), material=M.emissive(
            '#bfe9ff', 'eye', 12.0)), 'Head'))

    def cloth(t, P, energy=1.0):
        for i, name in enumerate(strips):
            sway(P, name, 5, t, 0.14 * energy, i * 0.23, 0.15, 'x' if i % 2 else 'y', 1, 0.25,
                 0.5)

    def arms(t, P, reach=0.0):
        for side, sx in (('L', 1), ('R', -1)):
            P.turn('Arm.Up.' + side, x=-0.1 * wave(t, 0.2 * sx) - 1.1 * reach,
                   y=sx * 0.35 * reach)
            P.turn('Arm.Low.' + side, x=-0.2 - 0.5 * reach)
            for k in range(4):
                P.turn('Finger%d.%s.01' % (k, side), x=0.25 * wave(t, k * 0.17, 2) + 0.6 * reach,
                       y=(k - 1.5) * 0.2 * reach)
                P.turn('Finger%d.%s.02' % (k, side), x=0.3 * wave(t, k * 0.17 + 0.1, 2))

    def hover(t, P):
        P.move('Body', 0.06 * wave(t, 0.3), 0, 0.14 * wave(t))
        P.turn('Body', x=0.06 * wave(t, 0.2))
        P.turn('Head', z=0.25 * wave(t, 0.1), x=0.1)
        cloth(t, P)
        arms(t, P)

    def reach(t, P):
        d = pulse(t, 0.1, 0.45, 0.6, 0.95)
        P.move('Body', 0, -0.7 * d, 0.1 * wave(t) + 0.1 * d)
        P.turn('Body', x=0.3 * d)
        P.turn('Chest', x=0.2 * d)
        P.turn('Head', x=-0.35 * d, y=0.3 * d)
        cloth(t, P, 1 + d)
        arms(t, P, d)

    def scream(t, P):
        d = pulse(t, 0.1, 0.2, 0.7, 0.9)
        shake = math.sin(math.tau * t * 20) * d
        P.move('Body', 0.02 * shake, 0, 0.3 * d)
        P.turn('Chest', x=-0.35 * d)
        P.turn('Head', x=-0.5 * d + 0.04 * shake)
        P.scale('Head', 1 + 0.12 * d, 1 + 0.35 * d, 1 + 0.12 * d)
        cloth(t, P, 1 + 3 * d)
        for side, sx in (('L', 1), ('R', -1)):
            P.turn('Arm.Up.' + side, y=-sx * 1.2 * d, x=0.3 * d)
            P.turn('Arm.Low.' + side, x=-0.5 * d)
            for k in range(4):
                P.turn('Finger%d.%s.01' % (k, side), x=-0.5 * d, y=(k - 1.5) * 0.3 * d)

    rig.clip('Hover', 6.0, hover)
    rig.clip('Reach', 6.0, reach)
    rig.clip('Scream', 3.0, scream)
    return rig, finish(rig, [body], rigid, 'shadow-wraith'), DARK


# ----------------------------------------------------------------------------- 8
def bloom_titan():
    """A walking reef: slow, enormous and kind."""
    rig = Rig('bloom-titan')
    rig.bone('Root', (0, 0, 0), (0, 0.5, 0), deform=False)
    rig.bone('Trunk.01', (0, 0, 0.2), (0, 0, 2.2), 'Root')
    rig.bone('Trunk.02', (0, 0, 2.2), (0, -0.2, 4.2), 'Trunk.01', True)
    rig.bone('Trunk.03', (0, -0.2, 4.2), (0, -0.5, 6.0), 'Trunk.02', True)
    rig.bone('Head', (0, -0.5, 6.0), (0, -0.9, 7.3), 'Trunk.03', True)
    m = Meta(0.06)
    m.path([(0, 0, 0.2), (0, 0, 2.2), (0, -0.2, 4.2), (0, -0.5, 6.0), (0, -0.8, 6.9)],
           [1.5, 1.05, 1.15, 0.85, 0.7])
    m.ball((0, -0.25, 4.3), 1, (1.5, 1.2, 1.3))
    rnd = random.Random(2)
    roots = []
    for i in range(7):
        a = math.tau * i / 7 + 0.3
        base = Vector((1.0 * math.cos(a), 1.0 * math.sin(a), 0.9))
        pts = [base, base + Vector((1.0 * math.cos(a), 1.0 * math.sin(a), -0.5)),
               base + Vector((2.3 * math.cos(a), 2.3 * math.sin(a), -0.8)),
               base + Vector((3.4 * math.cos(a + 0.3), 3.4 * math.sin(a + 0.3), -0.85))]
        tentacle(rig, m, 'Root%d' % i, pts, 0.5, 0.1, 'Trunk.01', 4)
        roots.append('Root%d' % i)
    for side, sx in (('L', 1), ('R', -1)):
        sh = Vector((sx * 1.3, -0.2, 5.0))
        pts = [sh, sh + Vector((sx * 1.2, -0.3, -0.9)), sh + Vector((sx * 1.6, -0.8, -2.4)),
               sh + Vector((sx * 1.4, -1.3, -3.6))]
        tentacle(rig, m, 'Arm.' + side, pts, 0.5, 0.24, 'Trunk.03', 4, bulb=0.4)
    rig.build()
    body = m.mesh('body', M.bark('#3a4a44', 'trunk', 0.35))
    roughen(body, 0.07, 1.6)
    rigid = []
    caps = [((0, -0.9, 7.6), 1.9, 'Head'), ((1.3, 0.2, 6.2), 0.9, 'Trunk.03'),
            ((-1.2, 0.5, 5.6), 0.75, 'Trunk.03'), ((0.9, 0.9, 3.4), 0.6, 'Trunk.02'),
            ((-1.25, -0.3, 2.9), 0.7, 'Trunk.02'), ((0.2, 1.2, 4.6), 0.55, 'Trunk.02')]
    cap_mat = M.cap('#c93f7a', '#ffe1a6', '#ffd27a', 'cap')
    gill = M.emissive('#7affc9', 'gill', 5.0, '#1a4a3a')
    for c, r, bone in caps:
        rigid.append(tag(lathe([(0, r * 0.55), (r * 0.5, r * 0.5), (r * 0.9, r * 0.25),
                                (r, 0.0), (r * 0.92, -r * 0.06), (r * 0.5, r * 0.08), (0, r * 0.1)],
                               40, c, material=cap_mat, cap=False), bone))
        rigid.append(tag(lathe([(r * 0.9, -r * 0.03), (r * 0.5, r * 0.06), (r * 0.12, r * 0.02)],
                               40, c, material=gill, cap=False), bone))
    for sx in (1, -1):
        rigid += eyeball((sx * 0.38, -1.42, 6.55), 0.2, (sx * 0.2, -1, 0.05), '#7affc9', 4.0,
                         bone='Head', white='#10201c')
    for i in range(40):
        a, z = rnd.uniform(0, math.tau), rnd.uniform(1.0, 6.2)
        r = 1.2 + 0.2 * math.sin(z)
        rigid.append(tag(ico(rnd.uniform(0.05, 0.13), (r * math.cos(a), r * math.sin(a) - 0.1 * z
                                                       / 3, z), 2,
                             material=M.emissive(rnd.choice(['#7affc9', '#ffd27a', '#ff9de1']),
                                                 'spore%d' % (i % 3), 6.0)),
                         'Trunk.0%d' % (1 if z < 2.2 else 2 if z < 4.2 else 3)))

    def sway_clip(t, P, power=1.0):
        for i, b in enumerate(('Trunk.01', 'Trunk.02', 'Trunk.03', 'Head')):
            P.turn(b, y=0.035 * power * (1 + i * 0.4) * wave(t, -0.08 * i),
                   x=0.02 * power * wave(t, 0.2 - 0.08 * i, 2))
        for i, name in enumerate(roots):
            sway(P, name, 4, t, 0.05 * power, i * 0.14, 0.2, 'x')
        for side, sx in (('L', 1), ('R', -1)):
            sway(P, 'Arm.' + side, 4, t, 0.09 * power, 0.25 * sx, 0.14, 'y', 1, 0.2, 0.3)
        P.scale('Head', 1 + 0.02 * wave(t, 0, 2))

    def walk(t, P):
        sway_clip(t, P, 1.6)
        for i, name in enumerate(roots):
            ph = (t + i / 7 * 3) % 1.0
            lift = max(0, math.sin(math.pi * min(1, ph / 0.35))) if ph < 0.35 else 0
            for j in (2, 3):
                P.turn('%s.%02d' % (name, j), z=0.0, x=-0.5 * lift * math.sin(
                    math.tau * i / 7 + 0.3), y=0.5 * lift * math.cos(math.tau * i / 7 + 0.3))
        P.move('Trunk.01', 0, 0, 0.12 * abs(wave(t, 0, 1.5)))

    def bloom(t, P):
        sway_clip(t, P, 0.6)
        o = pulse(t, 0.1, 0.4, 0.6, 0.95)
        P.scale('Head', 1 + 0.18 * o, 1 - 0.08 * o, 1 + 0.18 * o)
        P.turn('Head', x=-0.2 * o)
        for side, sx in (('L', 1), ('R', -1)):
            for j in (1, 2):
                P.turn('Arm.%s.%02d' % (side, j), y=-sx * 0.55 * o)

    rig.clip('Sway', 8.0, sway_clip)
    rig.clip('Walk', 4.0, walk)
    rig.clip('Bloom', 8.0, bloom)
    return rig, finish(rig, [body], rigid, 'bloom-titan'), DARK


# ----------------------------------------------------------------------------- 9
def crystal_golem():
    """Shards held in the shape of a giant by the light at their centre."""
    rig = Rig('crystal-golem')
    rig.bone('Root', (0, 0, 0), (0, 0.5, 0), deform=False)
    rig.bone('Hips', (0, 0, 2.0), (0, 0, 2.5), 'Root')
    rig.bone('Chest', (0, 0, 2.5), (0, 0, 3.5), 'Hips', True)
    rig.bone('Head', (0, 0, 3.7), (0, 0, 4.4), 'Chest')
    rig.bone('Core', (0, 0, 2.9), (0, 0, 3.2), 'Chest')
    limbs = {}
    for side, sx in (('L', 1), ('R', -1)):
        pts = [Vector((sx * 0.95, 0, 3.3)), Vector((sx * 1.5, 0, 2.3)), Vector((sx * 1.6, -0.2,
                                                                               1.2))]
        rig.bone('Arm.Up.' + side, pts[0], pts[1], 'Chest')
        rig.bone('Arm.Low.' + side, pts[1], pts[2], 'Arm.Up.' + side)
        limbs['Arm.Up.' + side], limbs['Arm.Low.' + side] = (pts[0], pts[1]), (pts[1], pts[2])
        pts = [Vector((sx * 0.5, 0, 1.9)), Vector((sx * 0.6, -0.1, 1.0)), Vector((sx * 0.6, 0,
                                                                                 0.0))]
        rig.bone('Leg.Up.' + side, pts[0], pts[1], 'Hips')
        rig.bone('Leg.Low.' + side, pts[1], pts[2], 'Leg.Up.' + side, True)
        rig.bone('ik.Leg.' + side, pts[2], pts[2] + Vector((0, -0.4, 0)), 'Root', deform=False)
        limbs['Leg.Up.' + side], limbs['Leg.Low.' + side] = (pts[0], pts[1]), (pts[1], pts[2])
    rnd = random.Random(8)
    shards_bones = []
    for i in range(8):
        a = math.tau * i / 8
        c = Vector((1.7 * math.cos(a), 1.7 * math.sin(a), 3.2 + 0.8 * math.sin(i * 2.2)))
        rig.bone('Orbit%d' % i, c, c + Vector((0, 0, 0.4)), 'Core')
        shards_bones.append(('Orbit%d' % i, c))
    rig.build()
    for side in 'LR':
        rig.ik('Leg.Low.' + side, 'ik.Leg.' + side, 2)
    mats = [M.crystal('#5a3dff', '#c9a6ff', 'crystal_a', 2.0),
            M.crystal('#1fb6c9', '#a6fff2', 'crystal_b', 2.0),
            M.rock('#2a2a33', 'slate', 1.5)]

    def shard(a, b, width, mat, bone, twist=0.0):
        a, b = Vector(a), Vector(b)
        length = (b - a).length
        prof = [(0.0, 0.0), (width, length * 0.2), (width * 0.85, length * 0.7), (0.0, length)]
        s = lathe(prof, rnd.choice([5, 6, 7]), material=mat, cap=False)
        from core import shade
        shade(s, False)
        s.rotation_euler = (b - a).to_track_quat('Z', 'Y').to_euler()
        s.location = a
        import bpy
        bpy.context.view_layer.update()
        s.data.transform(s.matrix_world)
        s.matrix_world.identity()
        return tag(s, bone)
    parts = []
    for bone, (a, b) in limbs.items():
        d = (b - a)
        for k in range(4):
            off = Vector((rnd.uniform(-0.12, 0.12), rnd.uniform(-0.12, 0.12), 0))
            parts.append(shard(a + off - d * 0.08, b + off * 0.5 + d * 0.05,
                               rnd.uniform(0.14, 0.24), mats[k % 3], bone))
    for i in range(16):
        a = math.tau * i / 16
        r = 0.55 + 0.2 * rnd.random()
        base = Vector((r * math.cos(a), r * 0.7 * math.sin(a), 2.2 + rnd.uniform(-0.2, 0.2)))
        parts.append(shard(base, base + Vector((0.4 * math.cos(a), 0.3 * math.sin(a),
                                                rnd.uniform(1.2, 1.9))),
                           rnd.uniform(0.2, 0.32), mats[i % 3], 'Chest' if i % 3 else 'Hips'))
    for i in range(7):
        a = math.tau * i / 7
        parts.append(shard((0.2 * math.cos(a), 0.2 * math.sin(a), 3.7),
                           (0.45 * math.cos(a), 0.45 * math.sin(a), 4.3 + 0.4 * rnd.random()),
                           0.15, mats[i % 2], 'Head'))
    for name, c in shards_bones:
        parts.append(shard(c - Vector((0, 0, 0.35)), c + Vector((0, 0, 0.45)), 0.14,
                           mats[rnd.randrange(2)], name))
    parts.append(tag(ico(0.42, (0, 0, 3.0), 3, material=M.emissive('#fff3d0', 'core', 12.0)),
                     'Core'))
    for sx in (1, -1):
        parts.append(tag(ico(0.08, (sx * 0.16, -0.3, 3.95), 2,
                             material=M.emissive('#fff3d0', 'eye', 12.0)), 'Head'))
    mesh = rig.bind_parts(parts, 'crystal-golem')

    def orbit(t, P, speed=1.0, spread=0.0):
        P.turn('Core', z=math.tau * t * speed)
        P.scale('Core', 1 + spread)
        for i, (name, _) in enumerate(shards_bones):
            P.move(name, 0, 0, 0.2 * wave(t, i * 0.13, 2))
            P.turn(name, z=math.tau * t * 2, x=0.3 * wave(t, i * 0.2))

    def idle(t, P):
        orbit(t, P)
        P.move('Hips', 0, 0, 0.08 * wave(t, 0, 2))
        P.turn('Chest', z=0.08 * wave(t), x=0.03 * wave(t, 0.2, 2))
        P.turn('Head', z=0.2 * wave(t, 0.15))
        for side, sx in (('L', 1), ('R', -1)):
            P.turn('Arm.Up.' + side, y=sx * 0.08 * wave(t, 0.1, 2))
            P.move('Arm.Low.' + side, 0, 0, 0.06 * wave(t, 0.3 * sx, 2))

    def walk(t, P):
        orbit(t, P, 1.0)
        for side, ph, sx in (('L', 0.0, 1), ('R', 0.5, -1)):
            p = (t + ph) % 1.0
            if p < 0.6:
                y, z = (-0.5 + p / 0.6) * 0.9, 0.0
            else:
                u = (p - 0.6) / 0.4
                y, z = (0.5 - ease(u)) * 0.9, 0.35 * math.sin(math.pi * u)
            P.move('ik.Leg.' + side, 0, y, z)
            P.turn('Arm.Up.' + side, x=0.35 * math.sin(math.tau * (t + ph)))
        P.move('Hips', 0.1 * wave(t), 0, -0.12 + 0.08 * math.cos(2 * math.tau * t))
        P.turn('Hips', z=0.1 * wave(t))
        P.turn('Chest', z=-0.14 * wave(t))

    def awaken(t, P):
        up = pulse(t, 0.05, 0.5, 0.75, 0.98)
        orbit(t, P, 0.3 + 2.0 * up, 0.6 * up)
        P.move('Hips', 0, 0, -1.1 * (1 - up))
        P.turn('Chest', x=0.6 * (1 - up) - 0.15 * up)
        P.turn('Head', x=0.7 * (1 - up) - 0.3 * up)
        for side, sx in (('L', 1), ('R', -1)):
            P.turn('Arm.Up.' + side, y=sx * -1.0 * up, x=0.4 * (1 - up))
            P.turn('Arm.Low.' + side, y=sx * -0.4 * up)

    rig.clip('Idle', 6.0, idle)
    rig.clip('Walk', 2.4, walk)
    rig.clip('Awaken', 7.0, awaken)
    rig.finish()
    return rig, mesh, DARK


# ----------------------------------------------------------------------------- 10
def glow_sprite():
    """Small, curious and delighted by everything."""
    rig = Rig('glow-sprite')
    rig.bone('Root', (0, 0, 0), (0, 0.2, 0), deform=False)
    rig.bone('Body', (0, 0, 0.5), (0, 0, 0.85), 'Root')
    rig.bone('Head', (0, 0, 0.85), (0, 0, 1.3), 'Body', True)
    m = Meta(0.012)
    m.ball((0, 0, 0.62), 1, (0.2, 0.19, 0.24))
    m.ball((0, -0.01, 1.0), 1, (0.3, 0.28, 0.27))
    for side, sx in (('L', 1), ('R', -1)):
        a0 = Vector((sx * 0.18, 0, 0.72))
        pts = [a0, a0 + Vector((sx * 0.14, -0.03, -0.08)), a0 + Vector((sx * 0.2, -0.06, -0.2))]
        tentacle(rig, m, 'Arm.' + side, pts, 0.055, 0.04, 'Body', 2, bulb=0.05)
        l0 = Vector((sx * 0.09, 0, 0.45))
        pts = [l0, l0 + Vector((sx * 0.02, -0.02, -0.14)), l0 + Vector((sx * 0.03, -0.07, -0.26))]
        tentacle(rig, m, 'Leg.' + side, pts, 0.06, 0.045, 'Body', 2, bulb=0.06)
        e0 = Vector((sx * 0.14, 0.02, 1.22))
        pts = [e0, e0 + Vector((sx * 0.1, 0.02, 0.2)), e0 + Vector((sx * 0.22, 0.05, 0.36)),
               e0 + Vector((sx * 0.3, 0.1, 0.44))]
        tentacle(rig, m, 'Antenna.' + side, pts, 0.035, 0.018, 'Head', 3, bulb=0.05)
        w0 = Vector((sx * 0.1, 0.17, 0.75))
        rig.bone('Wing.' + side, w0, w0 + Vector((sx * 0.5, 0.2, 0.25)), 'Body')
    tp = [Vector((0, 0.16, 0.5)), Vector((0, 0.32, 0.42)), Vector((0, 0.46, 0.52)),
          Vector((0, 0.5, 0.7))]
    tentacle(rig, m, 'Tail', tp, 0.06, 0.03, 'Body', 3, bulb=0.07)
    rig.build()
    body = m.mesh('body', M.biolum('#2a6a8a', '#fff7a6', 'skin', 3.0, 3.0, 26))
    rigid = []
    for sx in (1, -1):
        rigid += eyeball((sx * 0.13, -0.2, 1.03), 0.095, (sx * 0.15, -1, 0.05), '#2a1a4a', 0.5,
                         bone='Head', white='#f4f1ea')
        rigid.append(tag(sphere(0.022, (sx * 0.115, -0.292, 1.065), material=M.emissive(
            '#ffffff', 'glint', 4.0)), 'Head'))
        rigid.append(tag(sphere(0.055, (sx * 0.44, 0.12, 1.66), material=M.emissive(
            '#fff7a6', 'bulb', 9.0)), 'Antenna.%s.03' % ('L' if sx > 0 else 'R')))
        wing = lathe([(0.0, 0.0), (0.16, 0.12), (0.2, 0.34), (0.12, 0.52), (0.0, 0.58)], 20,
                     material=M.emissive('#9dfff0', 'wing', 2.5, '#2a8a8a'), cap=False,
                     scale=(1, 0.06, 1))
        place(wing, (sx * 0.1, 0.17, 0.75), (0.5, sx * 1.1, 0))
        rigid.append(tag(wing, 'Wing.' + ('L' if sx > 0 else 'R')))
    rigid.append(tag(sphere(0.07, (0, 0.5, 0.74), material=M.emissive('#fff7a6', 'tailbulb',
                                                                    9.0)), 'Tail.03'))
    rigid.append(tag(torus(0.035, 0.008, (0, -0.275, 0.92), (math.pi / 2, 0, 0),
                           M.eye('#3a1020', 'smile'), 16, 6, scale=(1.6, 1, 0.6)), 'Head'))

    def wings(t, P, speed=10, amp=0.7):
        for side, sx in (('L', 1), ('R', -1)):
            P.turn('Wing.' + side, y=sx * amp * math.sin(math.tau * t * speed))

    def limbs(t, P, energy=1.0):
        for side, sx in (('L', 1), ('R', -1)):
            sway(P, 'Arm.' + side, 2, t, 0.25 * energy, 0.2 * sx, 0.2, 'y', 2)
            sway(P, 'Leg.' + side, 2, t, 0.2 * energy, 0.3 * sx, 0.2, 'x', 2)
            sway(P, 'Antenna.' + side, 3, t, 0.18 * energy, 0.1 * sx, 0.18, 'x', 2)
        sway(P, 'Tail', 3, t, 0.2 * energy, 0, 0.2, 'z', 1)

    def bob(t, P):
        P.move('Body', 0.03 * wave(t, 0.25), 0, 0.3 + 0.08 * wave(t, 0, 2))
        P.turn('Head', y=0.15 * wave(t), z=0.2 * wave(t, 0.2))
        wings(t, P, 16)
        limbs(t, P)

    def spin(t, P):
        j = pulse(t, 0.1, 0.3, 0.6, 0.9)
        P.move('Body', 0, 0, 0.3 + 0.35 * j)
        P.turn('Body', z=math.tau * ease(min(1, max(0, (t - 0.2) / 0.5))))
        P.scale('Head', 1 + 0.08 * j)
        wings(t, P, 14, 0.9)
        limbs(t, P, 2.5)

    def giggle(t, P):
        g = max(0, math.sin(math.tau * t * 6)) ** 2
        P.move('Body', 0, 0, 0.3 + 0.03 * g)
        P.turn('Body', x=-0.12)
        P.turn('Head', x=-0.2 + 0.08 * g, y=0.1 * wave(t))
        P.scale('Body', 1 + 0.05 * g, 1 + 0.05 * g, 1 - 0.04 * g)
        for side, sx in (('L', 1), ('R', -1)):
            P.turn('Arm.%s.01' % side, y=-sx * 1.2)
            P.turn('Arm.%s.02' % side, y=-sx * 0.8)
        wings(t, P, 14, 0.4)
        sway(P, 'Tail', 3, t, 0.3, 0, 0.2, 'z', 3)

    def sad(t, P):
        P.move('Body', 0, 0, 0.02 * wave(t))
        P.turn('Body', x=0.2)
        P.turn('Head', x=0.45, y=0.08 * wave(t))
        for side, sx in (('L', 1), ('R', -1)):
            for j in (1, 2, 3):
                P.turn('Antenna.%s.%02d' % (side, j), y=sx * 0.5, x=0.35)
            P.turn('Wing.' + side, y=sx * -0.5)
        for j in (1, 2, 3):
            P.turn('Tail.%02d' % j, x=0.4)

    rig.clip('Bob', 2.0, bob)
    rig.clip('Spin', 2.4, spin)
    rig.clip('Giggle', 2.0, giggle)
    rig.clip('Sad', 5.0, sad)
    return rig, finish(rig, [body], rigid, 'glow-sprite'), DARK


# ----------------------------------------------------------------------------- 11
def tripod_colossus():
    """Three legs as tall as towers and a cluster of eyes that never all blink."""
    rig = Rig('tripod-colossus')
    rig.bone('Root', (0, 0, 0), (0, 0.5, 0), deform=False)
    rig.bone('Body', (0, 0, 8.6), (0, 0, 9.8), 'Root')
    rig.bone('Head', (0, -0.6, 9.2), (0, -2.0, 8.8), 'Body')
    m = Meta(0.09)
    m.ball((0, 0, 9.4), 1, (1.9, 2.1, 1.3))
    m.ball((0, -1.5, 9.0), 1, (1.2, 1.2, 0.95))
    m.ball((0, 0.6, 10.3), 1, (1.2, 1.4, 0.7))
    legs = []
    for i in range(3):
        a = math.tau * i / 3 + math.pi / 2
        hip = Vector((1.3 * math.cos(a), 1.3 * math.sin(a), 8.8))
        knee = Vector((3.4 * math.cos(a), 3.4 * math.sin(a), 11.2))
        ankle = Vector((4.6 * math.cos(a), 4.6 * math.sin(a), 4.2))
        foot = Vector((5.0 * math.cos(a), 5.0 * math.sin(a), 0.15))
        n = 'Leg%d' % i
        rig.bone(n + '.Up', hip, knee, 'Body')
        rig.bone(n + '.Mid', knee, ankle, n + '.Up', True)
        rig.bone(n + '.Low', ankle, foot, n + '.Mid', True)
        rig.bone('ik.' + n, foot, foot + Vector((0, 0, -0.6)), 'Root', deform=False)
        m.path([hip, knee, ankle, foot], [0.55, 0.36, 0.3, 0.22])
        m.ball(knee, 0.55)
        m.ball(ankle, 0.42)
        for k in (-1, 0, 1):
            m.limb(foot, foot + Vector((0.9 * math.cos(a + k * 0.7), 0.9 * math.sin(a + k * 0.7),
                                        -0.12)), 0.24, 0.06)
        legs.append((n, a))
    for i in range(6):
        a = math.pi * (1.15 + 0.7 * i / 5)
        base = Vector((1.0 * math.cos(a), -1.6 + 0.3 * math.sin(a) * 0, 8.4))
        pts = [base + Vector((0.3 * math.cos(a) * f, -0.25 * f, -1.2 * f)) for f in range(5)]
        tentacle(rig, m, 'Feeler%d' % i, pts, 0.2, 0.04, 'Head', 5)
    rig.build()
    for n, _ in legs:
        rig.ik(n + '.Low', 'ik.' + n, 3)
    body = m.mesh('body', M.alien_skin('#2a2f2a', '#4a3a22', '#ff8a2a', 'hide', 0.18, 0.8, 4.0,
                                       0.5))
    rigid = []
    rnd = random.Random(21)
    for i in range(9):
        a = (i % 3 - 1) * 0.42 + rnd.uniform(-0.08, 0.08)
        b = (i // 3 - 1) * 0.36
        d = Vector((math.sin(a), -math.cos(a) * math.cos(b), math.sin(b)))
        rigid += eyeball(Vector((0, -1.5, 9.0)) + d * 1.02, rnd.uniform(0.17, 0.3), d, '#ff8a2a',
                         6.0, bone='Head', white='#140d08')

    def stride(t, P):
        for i, (n, a) in enumerate(legs):
            p = (t + i / 3) % 1.0
            if p < 0.67:
                y, z = (-0.5 + p / 0.67) * 2.6, 0.0
            else:
                u = (p - 0.67) / 0.33
                y, z = (0.5 - ease(u)) * 2.6, 1.6 * math.sin(math.pi * u)
            P.move('ik.' + n, 0, y, z)
        P.move('Body', 0.2 * wave(t, 0, 3), 0, -0.4 + 0.25 * math.cos(3 * math.tau * t))
        P.turn('Body', x=0.04 * wave(t, 0.1, 3), y=0.05 * wave(t, 0.3, 3))
        P.turn('Head', z=0.2 * wave(t))
        for i in range(6):
            sway(P, 'Feeler%d' % i, 5, t, 0.14, i * 0.17, 0.15, 'x', 3, 0.2, 0.3)

    def idle(t, P):
        P.move('Body', 0, 0, -0.3 + 0.2 * wave(t))
        P.turn('Head', z=0.35 * wave(t, 0.1), x=0.1 * wave(t, 0.3, 2))
        for i in range(6):
            sway(P, 'Feeler%d' % i, 5, t, 0.1, i * 0.17, 0.15, 'x', 1, 0.2, 0.5)

    def scan(t, P):
        d = pulse(t, 0.1, 0.35, 0.7, 0.95)
        P.move('Body', 0, -0.8 * d, -2.2 * d)
        P.turn('Body', x=0.3 * d)
        P.turn('Head', x=0.3 * d, z=0.6 * d * wave(t, 0, 2))
        for i in range(6):
            sway(P, 'Feeler%d' % i, 5, t, 0.2 + 0.2 * d, i * 0.17, 0.15, 'x', 2, 0.3, 0.5)

    rig.clip('Stride', 3.6, stride)
    rig.clip('Idle', 7.0, idle)
    rig.clip('Scan', 7.0, scan)
    return rig, finish(rig, [body], rigid, 'tripod-colossus'), DARK


MODELS = {
    'abyss-watcher': abyss_watcher,
    'void-stalker': void_stalker,
    'hive-crawler': hive_crawler,
    'star-jelly': star_jelly,
    'maw-worm': maw_worm,
    'sky-leviathan': sky_leviathan,
    'shadow-wraith': shadow_wraith,
    'bloom-titan': bloom_titan,
    'crystal-golem': crystal_golem,
    'glow-sprite': glow_sprite,
    'tripod-colossus': tripod_colossus,
}
ATLAS = {name: 2048 for name in MODELS}
