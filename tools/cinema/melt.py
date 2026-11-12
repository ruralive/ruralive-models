"""The Melting Ones: big-headed, wide-eyed creatures that drip, crack into facets and wear
folded paper. They stand on the cast's rig, so they can act: every emotion clip works."""
import math
import random

import bpy
from core import (Meta, Vector, activate, ico, join, new_object, place, pulse, shade, sphere,
                  tag, wave, lathe, box)
import human
import materials as M
from monsters import eyeball

TAU = math.tau
A = human.A

LOOKS = {
    'melting-one': dict(skin=('#2a7684', '#b06aa8', '#27407a'), paper=('#d977a8', '#2f6f73'),
                        cloth='collar', facets=True, eyes=(0.062, 0.078)),
    'melting-dancer': dict(skin=('#3a8a98', '#a87fb5', '#2f4a86'), paper=('#b8336f', '#2f8f8a'),
                           cloth='dancer', facets=True, eyes=(0.07, 0.07), sprouts=7),
    'melting-grasper': dict(skin=('#7f9fb0', '#b0a5c9', '#55678f'), paper=None, cloth=None,
                            facets=True, eyes=(0.06, 0.085), hands=2.1, droop=True),
    'melting-ember': dict(skin=('#2a1a1c', '#c9431c', '#120a0c'), paper=('#f08a1c', '#3a1014'),
                          cloth='collar', facets=True, eyes=(0.07, 0.074), glow='#ff6a1c',
                          iris='#ffb000', iris_glow=5.0),
    'melting-ghost': dict(skin=('#d9dbe6', '#c9b5e0', '#9aa2c9'), paper=('#eef0f6', '#b5b0d9'),
                          cloth='dancer', facets=False, eyes=(0.075, 0.075), iris='#9fe9ff',
                          iris_glow=6.0, sprouts=5, height=1.9),
    'melting-candy': dict(skin=('#f29ac0', '#ffd27a', '#b35a9a'), paper=('#7ad9c9', '#ffe08a'),
                          cloth='collar', facets=True, eyes=(0.08, 0.066), height=1.2,
                          belly=1.3),
}


def fan(centre, direction, up, radius, spread, pleats, mat_a, mat_b, depth=0.02, droop=0.0):
    """A pleated paper fan: a zigzag of flat panels around a point."""
    d, u = Vector(direction).normalized(), Vector(up).normalized()
    n = d.cross(u).normalized()
    verts = [Vector(centre)]
    for i in range(pleats + 1):
        a = -spread / 2 + spread * i / pleats
        r = radius * (0.85 + 0.15 * math.sin(i * 1.7))
        p = Vector(centre) + (d * math.cos(a) + u * math.sin(a)) * r + n * depth * (
            1 if i % 2 else -1) - Vector((0, 0, droop * r * (i / pleats)))
        verts.append(p)
    out = []
    for k, mat in ((0, mat_a), (1, mat_b)):
        faces = [(0, i, i + 1) for i in range(1, pleats + 1) if i % 2 == k]
        if faces:
            o = new_object('fan', verts, faces, mat, smooth=False)
            o.modifiers.new('s', 'SOLIDIFY').thickness = 0.004
            activate(o)
            bpy.ops.object.modifier_apply(modifier='s')
            out.append(shade(o, False))
    return out


def chunk(centre, radius, mat, seed):
    """A faceted shard, as if the skin had been cut from stone there."""
    rnd = random.Random(seed)
    o = ico(radius, (0, 0, 0), 1, (rnd.uniform(0.7, 1.2), rnd.uniform(0.7, 1.2),
                                   rnd.uniform(0.7, 1.2)), mat)
    for v in o.data.vertices:
        v.co *= rnd.uniform(0.75, 1.2)
    o.rotation_euler = (rnd.uniform(0, 3), rnd.uniform(0, 3), rnd.uniform(0, 3))
    activate(o)
    bpy.ops.object.transform_apply(rotation=True)
    return shade(place(o, centre), False)


def build(model_id):
    look = LOOKS[model_id]
    rnd = random.Random(sum(map(ord, model_id)))
    s = dict(name=model_id, height=look.get('height', 1.55), shoulders=0.72, hips=0.8,
             shoes='bare')
    j = human.joints(s)
    skin = M.melt_skin(*look['skin'], name='skin', glow=look.get('glow'))
    rig = human.build_rig(dict(s, more=True), j)
    belly = look.get('belly', 1.0)
    hc = Vector((0, -0.02, 1.78))
    hr = 0.235
    m = Meta(0.0085)
    # torso: narrow chest, pot belly
    m.ball((0, 0.01, 1.33), 1, (0.105, 0.075, 0.12))
    m.ball((0, -0.03, 1.1), 1, (0.125 * belly, 0.13 * belly, 0.15))
    m.ball((0, 0.01, 0.97), 1, (0.115, 0.09, 0.08))
    m.limb((0, 0.01, 1.42), (0, 0.0, 1.6), 0.034, 0.03)
    m.ball((0, -0.155 * belly, 1.08), 0.012, negative=True)
    for side, sx in (('L', 1), ('R', -1)):
        sh, el, wr = j['sh' + side], j['el' + side], j['wr' + side]
        m.ball(sh, 0.04)
        m.limb(sh, el, 0.03, 0.024)
        m.ball(el, 0.03)
        m.limb(el, wr, 0.024, 0.019)
        hip, kn, an = j['hip' + side], j['kn' + side], j['an' + side]
        m.limb(hip, kn, 0.055, 0.034)
        m.ball(kn, 0.04)
        m.limb(kn, an, 0.034, 0.024)
        m.ball(kn.lerp(an, 0.3) + Vector((0, 0.015, 0)), 1, (0.034, 0.04, 0.08))
        m.ball(an + Vector((0, -0.07, -0.05)), 1, (0.05, 0.115, 0.03))
        m.ball(an + Vector((0, 0.02, -0.04)), 1, (0.036, 0.045, 0.04))
        for i in range(5):
            m.ball(an + Vector(((i - 2) * 0.02 * sx, -0.185 + abs(i - 1.2) * 0.012, -0.063)),
                   0.017 - i * 0.0015)
        # drips from the arms
        for f in (0.35, 0.7):
            p = sh.lerp(el, f)
            ln = rnd.uniform(0.06, 0.16)
            m.limb(p, p + Vector((0, 0, -ln)), 0.014, 0.006)
            m.ball(p + Vector((0, 0, -ln)), 0.012)
        for f in (0.4, 0.85):
            p = el.lerp(wr, f)
            ln = rnd.uniform(0.05, 0.12)
            m.limb(p, p + Vector((0, 0, -ln)), 0.011, 0.005)
            m.ball(p + Vector((0, 0, -ln)), 0.01)
    for a in (0.5, 2.2, 4.0):
        p = Vector((0.11 * math.cos(a), 0.09 * math.sin(a), 0.95))
        ln = rnd.uniform(0.08, 0.2)
        m.limb(p, p + Vector((0, 0, -ln)), 0.014, 0.005)
        m.ball(p + Vector((0, 0, -ln)), 0.012)
    body = m.mesh('body', skin)
    for v in body.data.vertices:
        v.co.z = max(v.co.z, 0.004)
    # head: a big soft sphere with hollows for the eyes and an open mouth
    h = Meta(0.0075)
    h.ball(hc, 1, (hr, hr * 0.98, hr * 0.97))
    h.ball(hc + Vector((0, -0.05, -0.14)), 1, (0.11, 0.11, 0.1))
    e1, e2 = look['eyes']
    eye_l = hc + Vector((0.085, -hr * 0.8, 0.03))
    eye_r = hc + Vector((-0.085, -hr * 0.8, 0.045))
    for c, r in ((eye_l, e2), (eye_r, e1)):
        h.ball(c + Vector((0, 0.015, 0)), r * 1.12, negative=True)
        h.ball(c + Vector((0, 0.03, 0.0)), 1, (r * 1.5, r * 0.9, r * 1.5))
    h.ball(hc + Vector((0, -hr * 0.97, -0.055)), 1, (0.022, 0.03, 0.022))
    for sx in (1, -1):
        h.ball(hc + Vector((sx * 0.009, -hr * 1.08, -0.066)), 0.0065, negative=True)
    h.ball(hc + Vector((0, -hr * 0.93, -0.125)), 1, (0.042, 0.04, 0.03), negative=True)
    h.ball(hc + Vector((0, -hr * 0.86, -0.1)), 1, (0.05, 0.03, 0.012))
    h.ball(hc + Vector((0, -hr * 0.84, -0.152)), 1, (0.042, 0.03, 0.013))
    if look.get('droop'):
        h.limb(eye_l + Vector((0, 0.02, -e2)), eye_l + Vector((0.02, 0.0, -e2 * 3.2)), e2 * 0.7,
               e2 * 0.2)
    # sprouts: stalks that fork and end in beads, each letting go of a drop
    sprouts = look.get('sprouts', 9)
    for i in range(sprouts):
        a = TAU * i / sprouts + 0.3
        tilt = rnd.uniform(-0.2, 0.9)
        d = Vector((math.cos(a) * math.cos(tilt), 0.25 * math.sin(a * 2), math.sin(tilt) * 0.9
                    + 0.35 * abs(math.sin(a)))).normalized()
        if d.y < -0.3:
            d.y = 0.1
        base = hc + d * hr * 0.92
        ln = rnd.uniform(0.09, 0.2)
        tip = base + d * ln
        h.limb(base - d * 0.02, tip, 0.026, 0.012)
        if i % 3 == 0:
            h.ball(tip, rnd.uniform(0.028, 0.04))
        else:
            for k in (-1, 1):
                side = d.cross(Vector((0, 1, 0))).normalized() * k
                t2 = tip + (d * 0.5 + side).normalized() * rnd.uniform(0.05, 0.09)
                h.limb(tip, t2, 0.012, 0.009)
                h.ball(t2, 0.016)
                h.limb(t2, t2 + Vector((0, 0, -rnd.uniform(0.03, 0.07))), 0.008, 0.004)
    h.limb(hc + Vector((0.03, -0.1, -hr * 0.98)), hc + Vector((0.03, -0.1, -hr * 1.3)), 0.012,
           0.005)
    head = h.mesh('head', skin)
    hands = [human.hand_mesh(j, side, skin, look.get('hands', 1.25)) for side in 'LR']
    soft = join([body, head] + hands, 'body')
    rig.bind_auto(soft)
    rigid = []
    white = M.bloodshot('sclera')
    iris = look.get('iris', '#7f97a8')
    for c, r in ((eye_l, e2), (eye_r, e1)):
        ball = eyeball(c, r, (rnd.uniform(-0.25, 0.25), -1, rnd.uniform(-0.2, 0.25)), iris,
                       look.get('iris_glow', 0.25), bone='Head')
        ball[0].data.materials.clear()
        ball[0].data.materials.append(white)
        rigid += ball
    tooth = M.horn('#e9e2d0', 'tooth')
    for i in (-1, 0, 1):
        rigid.append(tag(box((0.012, 0.008, 0.014), hc + Vector((i * 0.016, -hr * 0.93, -0.108)),
                             material=tooth, bevel_width=0.002), 'Head'))
    rigid.append(tag(sphere(0.036, hc + Vector((0, -hr * 0.8, -0.128)), (1, 0.6, 0.75),
                            material=M.eye('#1a0d14', 'mouth')), 'Head'))
    if look.get('facets'):
        stone = M.rock(look['skin'][0], 'facet', 4.0, look['skin'][2], rough=0.6)
        for i in range(9):
            a, b = rnd.uniform(-0.2, 1.3), rnd.uniform(-0.5, 0.9)
            d = Vector((math.cos(b) * math.cos(a), -math.cos(b) * math.sin(a) * 0.9,
                        math.sin(b))).normalized()
            rigid.append(tag(chunk(hc + d * hr * 0.93, rnd.uniform(0.065, 0.1), stone, i),
                             'Head'))
        for i in range(8):
            z = 1.38 - i * 0.055
            rigid.append(tag(chunk((0.085 + 0.02 * math.sin(i), -0.045 - 0.02 * math.cos(i * 2),
                                    z), rnd.uniform(0.04, 0.065), stone, 20 + i),
                             'Spine2' if z > 1.27 else 'Spine1' if z > 1.13 else 'Spine'))
    if look.get('cloth'):
        pa = M.origami(look['paper'][0], 'paper_a', look['paper'][1])
        pb = M.origami(look['paper'][1], 'paper_b')
        neck = Vector((0, 0.0, 1.47))
        ruff = 14 if look['cloth'] == 'dancer' else 6
        for i in range(ruff):
            a = TAU * i / ruff
            d = Vector((math.cos(a), math.sin(a), 0.15))
            for o in fan(neck, d, Vector((-math.sin(a), math.cos(a), 0)),
                         0.24 if look['cloth'] == 'dancer' else 0.2, 0.9, 6, pa, pb, 0.022, 0.5):
                rigid.append(tag(o, 'Spine2'))
        hip = Vector((-0.1, -0.06, 1.02))
        count = 9 if look['cloth'] == 'dancer' else 3
        for i in range(count):
            a = math.pi * (0.9 + 0.9 * i / max(1, count - 1)) if look['cloth'] == 'dancer' \
                else math.pi * (1.05 + 0.2 * i)
            d = Vector((math.cos(a) * 0.45, math.sin(a) * 0.3 - 0.25, -1)).normalized()
            base = Vector((0.12 * math.cos(a), 0.1 * math.sin(a), 1.02)) if look['cloth'] == \
                'dancer' else hip
            for o in fan(base, d, Vector((math.cos(a + 1.5), math.sin(a + 1.5), 0.0)),
                         rnd.uniform(0.3, 0.5), 0.7, 7, pb if i % 2 else pa, pa if i % 2 else pb,
                         0.02):
                rigid.append(tag(o, 'Hips' if i % 2 else 'UpLeg.R'))
        if look['cloth'] == 'dancer':
            for i in range(5):
                a = math.pi * (0.2 + 0.15 * i)
                for o in fan((0, 0.07, 1.2), (math.cos(a) * 0.4, 0.9, -0.3 + 0.2 * i),
                             (math.sin(a), 0, 0.6), rnd.uniform(0.3, 0.45), 0.8, 8, pa, pb, 0.02):
                    rigid.append(tag(o, 'Spine1'))
    for p in rigid:
        p.vertex_groups.new(name=p['bone']).add(range(len(p.data.vertices)), 1.0, 'REPLACE')
    mesh = join([soft] + rigid, model_id)
    k = s['height'] / 1.75
    if k != 1.0:
        for o in (rig.obj, mesh):
            if o is rig.obj:
                o.scale = (k, k, k)
            activate(o)
            bpy.ops.object.transform_apply(scale=True)

    def more(rig, k, idle):
        def hands_over(t, P):
            up = pulse(t, 0.08, 0.3, 0.75, 0.95)
            idle(t, P)
            for side, sx in (('L', 1), ('R', -1)):
                P.turn('UpperArm.' + side, y=sx * (0.33 - 2.3 * up), x=-0.25 * up)
                P.turn('ForeArm.' + side, y=sx * -1.35 * up)
                P.turn('Hand.' + side, y=sx * -0.7 * up)
                human.curl(P, side, 0.25 + 0.2 * up * wave(t, 0.1 * sx, 4))
            P.turn('Head', x=-0.12 * up, y=0.14 * up * wave(t, 0, 2))
            P.turn('Jaw', x=0.2 * up)
            P.move('Hips', 0.03 * k * wave(t), 0, -0.02 * k)

        def melt(t, P):
            d = pulse(t, 0.05, 0.6, 0.72, 0.98)
            wob = wave(t, 0, 3)
            P.move('Hips', 0.02 * k * wob, 0.05 * d * k, -0.55 * d * k)
            P.turn('Hips', x=0.2 * d)
            P.turn('Spine', x=0.25 * d)
            P.turn('Spine1', x=0.3 * d)
            P.turn('Spine2', x=0.3 * d, y=0.1 * d * wob)
            P.turn('Neck', x=0.4 * d)
            P.turn('Head', x=0.35 * d, y=0.3 * d)
            P.scale('Head', 1 + 0.12 * d, 1 + 0.06 * d, 1 - 0.18 * d)
            P.scale('Spine1', 1 + 0.25 * d, 1 - 0.2 * d, 1 + 0.25 * d)
            for side, sx in (('L', 1), ('R', -1)):
                human.arm(P, side, fwd=0.15 * d, out=-0.1 * d, bend=0.1)
                P.scale('ForeArm.' + side, 1, 1 + 0.35 * d, 1)
                human.curl(P, side, 0.1)
                P.move('ik_foot.' + side, sx * 0.1 * d * k, 0.0, 0)
                P.turn('ik_foot.' + side, z=sx * 0.5 * d)

        def stagger(t, P):
            for side, ph, sx in (('L', 0.0, 1), ('R', 0.5, -1)):
                human.step(P, side, t + ph, k, 0.8, 0.34, 0.4, 0.08)
                sw = math.sin(TAU * (t + ph))
                human.arm(P, side, fwd=0.4 * sw, out=1.1 + 0.3 * sw, bend=0.4)
                human.curl(P, side, 0.0)
            P.move('Hips', 0.07 * k * wave(t), 0.05 * k, (-0.1 + 0.06 * math.cos(2 * TAU * t)) * k)
            P.turn('Hips', x=-0.2, y=0.2 * wave(t))
            P.turn('Spine2', x=-0.2, y=-0.15 * wave(t))
            P.turn('Head', x=-0.25, y=0.3 * wave(t, 0.1), z=0.2 * wave(t, 0.3))
            P.turn('Jaw', x=0.3)

        def wobble(t, P):
            idle(t, P)
            P.scale('Head', 1 + 0.05 * wave(t, 0, 2), 1, 1 - 0.05 * wave(t, 0, 2))
            P.turn('Head', y=0.25 * wave(t), z=0.2 * wave(t, 0.25))
            P.turn('Neck', y=0.12 * wave(t, 0.1))
        rig.clip('Wobble', 4.0, wobble)
        rig.clip('Hands Over Head', 5.0, hands_over)
        rig.clip('Melt', 7.0, melt)
        rig.clip('Stagger', 0.9, stagger)
    human.animate(rig, dict(s, more_clips=more), k)
    return rig, mesh, {'preview_frame': 30, 'preview_clip': 1, 'preview_angle': 20}


MODELS = {name: (lambda n=name: build(n)) for name in LOOKS}
ATLAS = {name: 2048 for name in LOOKS}
