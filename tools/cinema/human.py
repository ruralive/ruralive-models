"""Parametric clothed people and humanoid animals with a full-body rig and a clip library."""
import math

from core import (Meta, Rig, Vector, activate, bake_atlas, cylinder, ease, join, lathe, pulse,
                  set_material, sphere, tag, torus, tube, wave, place, bpy)
import materials as M

A = math.radians(22)  # arms rest in an A-pose
FINGERS = (('Index', -0.027, 0.070), ('Middle', -0.009, 0.079), ('Ring', 0.009, 0.073),
           ('Pinky', 0.026, 0.056))


def joints(s):
    """Rest joint positions of the canonical 1.75 m body, widened by the spec."""
    sw, hw = s.get('shoulders', 1.0), s.get('hips', 1.0)
    j = {'hips': Vector((0, 0, 1.0)), 'spine1': Vector((0, 0.005, 1.13)),
         'chest': Vector((0, 0.01, 1.27)), 'neck': Vector((0, 0.008, 1.475)),
         'head': Vector((0, -0.002, 1.56)), 'top': Vector((0, -0.002, 1.76))}
    for side, sx in (('L', 1), ('R', -1)):
        d = Vector((sx * math.sin(A), 0, -math.cos(A)))
        sh = Vector((sx * 0.172 * sw, 0.008, 1.425))
        j['clav' + side] = Vector((sx * 0.03, 0.0, 1.44))
        j['sh' + side] = sh
        j['el' + side] = sh + d * 0.29
        j['wr' + side] = sh + d * 0.55
        j['d' + side] = d
        j['hip' + side] = Vector((sx * 0.095 * hw, 0, 0.94))
        j['kn' + side] = Vector((sx * 0.10 * hw, -0.012, 0.50))
        j['an' + side] = Vector((sx * 0.10 * hw, 0.012, 0.085))
        j['toe' + side] = Vector((sx * 0.105 * hw, -0.105, 0.025))
        j['tip' + side] = Vector((sx * 0.105 * hw, -0.175, 0.02))
    return j


def build_rig(s, j):
    rig = Rig(s.get('name', 'Character'))
    b = rig.bone
    b('Root', (0, 0, 0), (0, 0.25, 0), deform=False)
    b('Hips', j['hips'], j['hips'] + Vector((0, 0, 0.09)), 'Root')
    b('Spine', j['hips'] + Vector((0, 0, 0.09)), j['spine1'], 'Hips', True)
    b('Spine1', j['spine1'], j['chest'], 'Spine', True)
    b('Spine2', j['chest'], j['neck'], 'Spine1', True)
    b('Neck', j['neck'], j['head'], 'Spine2', True)
    b('Head', j['head'], j['top'], 'Neck', True)
    b('Jaw', j['head'] + Vector((0, -0.02, 0.02)), j['head'] + Vector((0, -0.09, -0.01)), 'Head')
    for side in 'LR':
        sx = 1 if side == 'L' else -1
        d = j['d' + side]
        fwd = Vector((0, -1, 0))
        b('Shoulder.' + side, j['clav' + side], j['sh' + side], 'Spine2')
        b('UpperArm.' + side, j['sh' + side], j['el' + side], 'Shoulder.' + side, True)
        b('ForeArm.' + side, j['el' + side], j['wr' + side], 'UpperArm.' + side, True)
        b('Hand.' + side, j['wr' + side], j['wr' + side] + d * 0.085, 'ForeArm.' + side, True)
        k = j['wr' + side] + d * 0.09
        for name, off, length in FINGERS:
            base = k + fwd * -off * -1 if False else k + Vector((0, off, 0))
            p = [base + d * (length * f) for f in (0, 0.45, 0.75, 1.0)]
            parent = 'Hand.' + side
            for i in range(3):
                bn = '%s%d.%s' % (name, i + 1, side)
                b(bn, p[i], p[i + 1], parent, i > 0)
                parent = bn
        t0 = j['wr' + side] + d * 0.025 + Vector((0, -0.028, 0))
        td = (d * 0.55 + Vector((0, -0.8, 0))).normalized()
        p = [t0 + td * f for f in (0, 0.032, 0.058, 0.08)]
        parent = 'Hand.' + side
        for i in range(3):
            bn = 'Thumb%d.%s' % (i + 1, side)
            b(bn, p[i], p[i + 1], parent, i > 0)
            parent = bn
        b('UpLeg.' + side, j['hip' + side], j['kn' + side], 'Hips')
        b('Leg.' + side, j['kn' + side], j['an' + side], 'UpLeg.' + side, True)
        b('Foot.' + side, j['an' + side], j['toe' + side], 'Leg.' + side, True)
        b('Toe.' + side, j['toe' + side], j['tip' + side], 'Foot.' + side, True)
        b('ik_foot.' + side, j['an' + side], j['toe' + side], 'Root', deform=False)
        if s.get('species'):
            ez = 1.74
            b('Ear.' + side, (sx * 0.05, 0.0, ez), (sx * 0.07, 0.0, ez + s.get('ear', 0.1)),
              'Head')
    if s.get('species') or s.get('tail'):
        tail = s.get('tail_len', 0.4)
        pts = [Vector((0, 0.09 + tail * f, 0.98 - 0.25 * tail * f * f + 0.2 * tail * f))
               for f in (0, 0.25, 0.5, 0.75, 1.0)]
        rig.chain('Tail', pts, 'Hips')
    if s.get('hair') in ('long', 'ponytail'):
        rig.chain('Hair', [(0, 0.085, 1.6), (0, 0.105, 1.5), (0, 0.11, 1.38)], 'Head')
    if s.get('skirt'):
        for side in 'LR':
            sx = 1 if side == 'L' else -1
            b('Skirt.' + side, (sx * 0.1, 0.0, 0.95), (sx * 0.16, 0.0, s.get('hem', 0.55)),
              'Hips')
    rig.build()
    for side in 'LR':
        rig.ik('Leg.' + side, 'ik_foot.' + side, 2)
        rig.copy_rotation('Foot.' + side, 'ik_foot.' + side)
    return rig


# ----------------------------------------------------------------------------- geometry
def head_mesh(s, mats):
    sp = s.get('species')
    m = Meta(0.0065)
    hs = s.get('head_width', 1.0)
    m.ball((0, 0.008, 1.668), 1, (0.077 * hs, 0.094, 0.092))
    m.ball((0, -0.022, 1.602), 1, (0.064 * hs, 0.07, 0.076))
    m.limb((0, 0.012, 1.46), (0, 0.004, 1.575), 0.052 * s.get('neck', 1.0), 0.05)
    if not sp:
        jaw = s.get('jaw', 1.0)
        m.ball((0, -0.06, 1.552), 1, (0.03 * jaw, 0.026, 0.024))
        for sx in (1, -1):
            m.ball((sx * 0.04 * hs, -0.052, 1.612), 0.027)
            m.ball((sx * 0.04 * jaw, -0.03, 1.565), 0.026)
            m.ball((sx * 0.03, -0.084, 1.664), 1, (0.027, 0.013, 0.010))
            m.ball((sx * 0.0115, -0.101, 1.607), 0.0095)
            m.ball((sx * 0.079 * hs, 0.004, 1.632), 1, (0.009, 0.018, 0.029), (0, 0, sx * 0.3))
            m.ball((sx * 0.031, -0.089, 1.646), 0.0165, negative=True)
        m.limb((0, -0.094, 1.648), (0, -0.108, 1.618), 0.010, 0.013)
        m.ball((0, -0.112, 1.613), 0.0145)
        m.ball((0, -0.092, 1.583), 1, (0.024, 0.012, 0.007))
        m.ball((0, -0.09, 1.572), 1, (0.021, 0.012, 0.008))
    else:
        snout = {'fox': (0.085, 0.024, 0.02), 'rabbit': (0.045, 0.03, 0.028),
                 'bear': (0.06, 0.042, 0.036), 'pig': (0.06, 0.04, 0.036)}[sp]
        m.limb((0, -0.07, 1.615), (0, -0.07 - snout[0], 1.6), snout[1] * 1.25, snout[2])
        for sx in (1, -1):
            m.ball((sx * 0.045, -0.05, 1.615), 0.034)
            m.ball((sx * 0.033, -0.086, 1.652), 0.014, negative=True)
            e = s.get('ear', 0.1)
            if sp == 'rabbit':
                m.limb((sx * 0.04, 0.0, 1.74), (sx * 0.055, 0.01, 1.74 + e), 0.02, 0.014)
            elif sp == 'bear':
                m.ball((sx * 0.065, 0.0, 1.755), 1, (0.03, 0.016, 0.03))
            elif sp == 'pig':
                m.limb((sx * 0.055, -0.01, 1.74), (sx * 0.095, -0.05, 1.745), 0.026, 0.008)
            else:
                m.limb((sx * 0.05, 0.0, 1.735), (sx * 0.068, 0.0, 1.74 + e), 0.03, 0.006)
        if sp == 'pig':
            m.ball((0, -0.138, 1.6), 1, (0.034, 0.012, 0.028))
    head = m.mesh('head', mats['fur'] if sp else mats['skin'])
    parts = []
    iris = M.eye(s.get('eyes', '#4a3320'), 'iris')
    white = M.eye('#e9e4dc', 'sclera')
    pupil = M.eye('#050505', 'pupil')
    ex, ez, ey = (0.033, 1.652, -0.074) if sp else (0.031, 1.646, -0.077)
    for sx in (1, -1):
        parts.append(sphere(0.0128, (sx * ex, ey, ez), material=M.eye('#0b0806', 'eyeball')
                            if sp else white, segments=20, rings=12))
        if not sp:
            parts.append(sphere(0.0066, (sx * ex, ey - 0.0108, ez), (1, 0.42, 1), material=iris,
                                segments=16, rings=8))
            parts.append(sphere(0.003, (sx * ex, ey - 0.0128, ez), (1, 0.5, 1), material=pupil,
                                segments=12, rings=6))
            parts.append(tube([(sx * 0.013, -0.097, 1.6655), (sx * 0.03, -0.0975, 1.67),
                               (sx * 0.049, -0.088, 1.667)], lambda t: 0.0042 - 0.002 * t, 8,
                              mats['hair'], 'brow', smooth_path=1))
    if sp:
        nose = {'fox': (0, -0.158, 1.607), 'rabbit': (0, -0.118, 1.607),
                'bear': (0, -0.135, 1.612), 'pig': None}[sp]
        if nose:
            parts.append(sphere(0.012, nose, (1.2, 0.8, 0.8), material=M.leather('#1b1412',
                                                                               'nose', 0.3)))
        else:
            for sx in (1, -1):
                parts.append(sphere(0.006, (sx * 0.012, -0.151, 1.6), (1, 0.4, 1.3),
                                    material=M.eye('#3a1d1d', 'nostril')))
    else:
        lips = Meta(0.004)
        lips.ball((0, -0.0985, 1.5835), 1, (0.02, 0.008, 0.0055))
        lips.ball((0, -0.0965, 1.5735), 1, (0.017, 0.008, 0.0065))
        parts.append(lips.mesh('lips', mats['lips']))
    for p in parts:
        tag(p, 'Head')
    return head, parts


def hair_parts(s, mats):
    style = s.get('hair', 'short')
    if style == 'bald' or s.get('species'):
        return []
    m = Meta(0.007)
    hs = s.get('head_width', 1.0)
    m.ball((0, 0.02, 1.688), 1, (0.083 * hs, 0.099, 0.086))
    m.ball((0, 0.05, 1.65), 1, (0.079 * hs, 0.066, 0.075))
    for sx in (1, -1):
        m.ball((sx * 0.066 * hs, 0.01, 1.668), 1, (0.02, 0.06, 0.05))
    if style == 'long':
        m.limb((0, 0.07, 1.62), (0, 0.105, 1.4), 0.075, 0.06)
        for sx in (1, -1):
            m.limb((sx * 0.07, 0.03, 1.63), (sx * 0.085, 0.05, 1.42), 0.035, 0.028)
    elif style == 'ponytail':
        m.ball((0, 0.105, 1.66), 0.03)
        m.limb((0, 0.115, 1.64), (0, 0.13, 1.4), 0.03, 0.014)
    elif style == 'bun':
        m.ball((0, 0.07, 1.775), 0.042)
    elif style == 'curly':
        import random
        r = random.Random(3)
        for _ in range(70):
            a, e = r.uniform(0, math.tau), r.uniform(-0.1, 1.5)
            p = (0.088 * hs * math.cos(a) * math.cos(e), 0.02 + 0.1 * math.sin(a) * math.cos(e),
                 1.675 + 0.095 * math.sin(e))
            if p[1] > -0.06 or p[2] > 1.72:
                m.ball(p, r.uniform(0.02, 0.03))
    elif style == 'wild':
        import random
        r = random.Random(5)
        for _ in range(26):
            a = r.uniform(0.3, math.pi - 0.3)
            b0 = Vector((0.075 * math.cos(a), 0.03 + r.uniform(0, 0.06), 1.69))
            m.limb(b0, b0 + Vector((0.1 * math.cos(a), r.uniform(0.02, 0.1),
                                    -r.uniform(0.1, 0.32))), 0.028, 0.008)
    if style in ('short', 'bun', 'ponytail') and s.get('fringe', True):
        m.ball((0, -0.062, 1.722), 1, (0.062 * hs, 0.022, 0.022))
    hair = m.mesh('hair', mats['hair'])
    out = [tag(hair, 'Head')]
    if s.get('beard'):
        b = Meta(0.006)
        b.ball((0, -0.062, 1.548), 1, (0.04, 0.03, 0.03))
        for sx in (1, -1):
            b.ball((sx * 0.045, -0.035, 1.572), 1, (0.024, 0.032, 0.035))
            b.ball((sx * 0.017, -0.097, 1.592), 1, (0.017, 0.007, 0.005))
        if s['beard'] == 'long':
            b.limb((0, -0.07, 1.53), (0, -0.075, 1.44), 0.04, 0.018)
        out.append(tag(b.mesh('beard', mats['hair']), 'Jaw' if s['beard'] != 'long' else 'Head'))
    return out


def hand_mesh(j, side, mat, scale=1.0):
    d = j['d' + side]
    sx = 1 if side == 'L' else -1
    w = j['wr' + side]
    m = Meta(0.0042)
    m.ball(w + d * 0.05, 1, (0.0135 * scale, 0.04 * scale, 0.046), (0, -sx * A, 0))
    m.limb(w - d * 0.03, w + d * 0.01, 0.027, 0.026)
    k = w + d * 0.09
    for _, off, length in FINGERS:
        base = k + Vector((0, off, 0))
        m.limb(base - d * 0.012, base + d * length, 0.0092 * scale, 0.0072 * scale)
    t0 = w + d * 0.025 + Vector((0, -0.028, 0))
    td = (d * 0.55 + Vector((0, -0.8, 0))).normalized()
    m.limb(t0 - td * 0.01, t0 + td * 0.08, 0.0115 * scale, 0.0085 * scale)
    return m.mesh('hand' + side, mat)


def body_shells(s, j, mats):
    """Skin and garments as separate overlapping shells, which reads as real layers."""
    g, belly = s.get('girth', 1.0), s.get('belly', 1.0)
    sw, hw = s.get('shoulders', 1.0), s.get('hips', 1.0)
    bust = s.get('bust', 0.0)
    top, bottom = s.get('top', 'shirt'), s.get('bottom', 'trousers')
    shells = []
    res = 0.011

    def torso(m, grow=0.0, low=0.93):
        m.ball((0, 0.014, 1.32), 1, (0.142 * sw + grow, 0.092 * g + grow, 0.125))
        m.limb((-0.1 * sw, 0.012, 1.425), (0.1 * sw, 0.012, 1.425), 0.04 + grow)
        m.ball((0, 0.006, 1.15), 1, (0.122 * (sw + hw) / 2 * (0.55 + 0.45 * g) + grow,
                                     0.085 * g * belly + grow, 0.13))
        if belly > 1.05:
            m.ball((0, -0.035 * belly, 1.1), 1, (0.115 * g, 0.085 * g * belly + grow, 0.11))
        m.ball((0, 0.014, low + 0.06), 1, (0.142 * hw + grow, 0.098 * g + grow, 0.1))
        for sx in (1, -1):
            m.ball((sx * 0.15 * sw, 0.01, 1.405), 0.042 * (0.7 + 0.3 * g) + grow)
            if bust:
                m.ball((sx * 0.066, -0.07 * g, 1.31), 0.056 * bust + grow * 0.5)

    def arms(m, grow=0.0, to=1.0, start=0.0):
        for side in 'LR':
            sh, el, wr = j['sh' + side], j['el' + side], j['wr' + side]
            a = 0.3 + 0.7 * g
            if start < 0.5:
                end = el if to >= 0.5 else sh.lerp(el, to * 2)
                m.limb(sh.lerp(el, start * 2), end, 0.045 * a + grow, 0.037 * a + grow)
            if to > 0.5:
                m.limb(el.lerp(wr, max(0, start - 0.5) * 2), el.lerp(wr, (to - 0.5) * 2),
                       0.037 * a + grow, 0.027 * a + grow)

    def legs(m, grow=0.0, to=1.0, start=0.0):
        for side in 'LR':
            hip, kn, an = j['hip' + side], j['kn' + side], j['an' + side]
            a = 0.35 + 0.65 * g
            if start < 0.5:
                end = kn if to >= 0.5 else hip.lerp(kn, to * 2)
                m.limb(hip.lerp(kn, start * 2), end, 0.076 * a + grow, 0.052 * a + grow)
            if to > 0.5:
                m.limb(kn.lerp(an, max(0, start - 0.5) * 2), kn.lerp(an, (to - 0.5) * 2),
                       0.05 * a + grow, 0.035 * a + grow)
                if grow < 0.006:
                    calf = kn.lerp(an, 0.3) + Vector((0, 0.018, 0))
                    m.ball(calf, 1, (0.044 * a, 0.05 * a, 0.1))

    skin = mats['fur'] if s.get('species') else mats['skin']
    if s.get('eva'):
        m = Meta(res)
        torso(m, 0.05, 0.9)
        arms(m, 0.034, 1.0)
        legs(m, 0.036, 1.0)
        m.ball((0, 0.01, 1.47), 1, (0.1, 0.1, 0.05))
        suit = m.mesh('suit', mats['top'])
        b = Meta(0.009)
        for side in 'LR':
            an = j['an' + side]
            b.ball(an + Vector((0, -0.055, -0.035)), 1, (0.065, 0.13, 0.05))
            b.ball(an + Vector((0, 0.03, -0.03)), 1, (0.058, 0.06, 0.055))
            b.limb(an + Vector((0, 0.005, 0.0)), an + Vector((0, 0.0, 0.2)), 0.07, 0.075)
        boots = b.mesh('boots', mats['shoes'])
        for v in boots.data.vertices:
            v.co.z = max(v.co.z, 0.004)
        return [suit, boots]
    # --- skin under the clothes, only where it shows
    sleeves = {'tshirt': 0.3, 'vest': 0.0, 'dress': s.get('sleeves', 0.0), 'fur': 0.0,
               'tank': 0.0}.get(top, 0.97)
    leg_cover = {'shorts': 0.38, 'skirt': 0.0, 'fur': 0.0, 'none': 0.0}.get(bottom, 0.97)
    if top == 'dress':
        leg_cover = 0.0
    m = Meta(res)
    used = False
    if sleeves < 0.9:
        arms(m, 0.0, 1.0, max(0.0, sleeves - 0.08))
        used = True
    if leg_cover < 0.9:
        legs(m, 0.0, 1.0, max(0.0, leg_cover - 0.08))
        used = True
    if top in ('fur', 'tank', 'vest') or s.get('open_chest'):
        torso(m)
        used = True
    if used:
        shells.append(m.mesh('skin_body', skin))
    # --- top
    m = Meta(res)
    if top == 'fur':
        m.ball((0, 0.01, 1.2), 1, (0.17 * sw, 0.125 * g, 0.2))
        m.ball((0.09 * sw, 0.01, 1.38), 1, (0.11, 0.115 * g, 0.1), (0, 0.5, 0))
        m.ball((0, 0.012, 1.0), 1, (0.175 * hw, 0.13 * g, 0.14))
        if s.get('skirt'):
            m.limb((0, 0.01, 0.95), (0, 0.01, s.get('hem', 0.6)), 0.19 * hw, 0.2 * hw)
    else:
        grow = {'jacket': 0.018, 'suit': 0.014, 'coat': 0.02, 'hivis': 0.012}.get(top, 0.007)
        torso(m, grow, 0.9 if top in ('jacket', 'coat', 'suit') else 0.95)
        if sleeves > 0:
            arms(m, grow, sleeves)
        if top == 'dress':
            hem = s.get('hem', 0.55)
            steps = 7
            for i in range(steps + 1):
                t = i / steps
                z = 1.02 + (hem - 1.02) * t
                r = 0.16 * hw + (s.get('flare', 0.1)) * t
                m.ball((0, 0.01, z), 1, (r, r * 0.8, 0.07))
        if top == 'coat':
            for i in range(5):
                z = 0.95 - i * 0.09
                m.ball((0, 0.012, z), 1, (0.17 * hw + 0.02, 0.125 * g + 0.02, 0.07))
    shells.append(m.mesh('top', mats['top']))
    if s.get('vest'):
        m = Meta(res)
        torso(m, 0.034, 0.99)
        shells.append(m.mesh('vest', mats['vest']))
    # --- bottom
    if top != 'dress' and bottom not in ('fur', 'none'):
        m = Meta(res)
        m.ball((0, 0.014, 0.975), 1, (0.146 * hw + 0.006, 0.1 * g + 0.006, 0.105))
        if bottom == 'skirt':
            hem = s.get('hem', 0.55)
            for i in range(7):
                t = i / 6
                r = 0.165 * hw + 0.07 * t
                m.ball((0, 0.01, 1.0 + (hem - 1.0) * t), 1, (r, r * 0.8, 0.06))
        else:
            legs(m, 0.01, leg_cover)
        shells.append(m.mesh('bottom', mats['bottom']))
    # --- feet
    shoes = s.get('shoes', 'shoes')
    m = Meta(0.008)
    for side in 'LR':
        an = j['an' + side]
        if shoes == 'bare':
            m.limb(an + Vector((0, 0.0, 0.0)), an + Vector((0, 0.0, 0.05)), 0.036, 0.036)
            m.ball(an + Vector((0, -0.055, -0.05)), 1, (0.04, 0.095, 0.03))
            m.ball(an + Vector((0, 0.02, -0.045)), 1, (0.034, 0.04, 0.035))
            for i in range(5):
                m.ball(an + Vector(((i - 2) * 0.016, -0.155 + abs(i - 1.5) * 0.008, -0.066)),
                       0.0115)
        else:
            boots = shoes == 'boots'
            m.ball(an + Vector((0, -0.06, -0.042)), 1, (0.047, 0.11, 0.04))
            m.ball(an + Vector((0, -0.125, -0.05)), 1, (0.045, 0.05, 0.033))
            m.ball(an + Vector((0, 0.025, -0.035)), 1, (0.04, 0.045, 0.05))
            m.limb(an + Vector((0, 0.005, -0.01)), an + Vector((0, 0.0, 0.2 if boots else 0.05)),
                   0.05 if boots else 0.044, 0.056 if boots else 0.044)
    feet = m.mesh('feet', skin if shoes == 'bare' else mats['shoes'])
    # flat soles
    for v in feet.data.vertices:
        if v.co.z < 0.004:
            v.co.z = 0.004
    shells.append(feet)
    return shells


def accessories(s, j, mats):
    parts = []
    g, hw = s.get('girth', 1.0), s.get('hips', 1.0)
    if s.get('belt'):
        parts.append(tag(torus(0.5, 0.014, (0, 0.014, 1.04), material=mats['belt'],
                               scale=(0.3 * hw, 0.215 * g * s.get('belly', 1.0), 1.6)), 'Hips'))
        parts.append(tag(__import__('core').box((0.045, 0.012, 0.04), (0, -0.096 * g * s.get(
            'belly', 1.0), 1.04), material=M.brass('buckle'), bevel_width=0.003), 'Hips'))
    if s.get('helmet'):
        shell = lathe([(0.0, 0.118), (0.05, 0.112), (0.09, 0.085), (0.108, 0.04), (0.112, 0.0),
                       (0.135, -0.008), (0.135, -0.014), (0.105, -0.012), (0.1, 0.035),
                       (0.085, 0.078), (0.0, 0.108)], 40, (0, 0.012, 1.7),
                      material=M.paint(s['helmet'], 'helmet', 0.3, 0.3, 0.25), cap=False,
                      scale=(0.86, 1.0, 1.0))
        parts.append(tag(shell, 'Head'))
        parts.append(tag(__import__('core').box((0.12, 0.07, 0.012), (0, -0.14, 1.692),
                                                (0.15, 0, 0), M.paint(s['helmet'], 'peak', 0.3,
                                                                      0.3, 0.2), 0.004), 'Head'))
    if s.get('visor'):
        parts.append(tag(lathe([(0.086, -0.022), (0.09, 0.0), (0.086, 0.022)], 40,
                               (0, -0.005, 1.648), material=M.emissive(s['visor'], 'visor', 2.5,
                                                                       '#0a0d12'), cap=False,
                               scale=(1, 1.12, 1)), 'Head'))
    if s.get('glasses'):
        frame = M.plastic('#15171a', 'glasses', 0.3)
        for sx in (1, -1):
            parts.append(tag(torus(0.019, 0.0022, (sx * 0.031, -0.094, 1.646), (math.pi / 2, 0, 0),
                                   frame, 24, 8), 'Head'))
            parts.append(tag(tube([(sx * 0.05, -0.092, 1.648), (sx * 0.078, -0.02, 1.65)],
                                  0.002, 6, frame), 'Head'))
        parts.append(tag(tube([(-0.012, -0.096, 1.65), (0.012, -0.096, 1.65)], 0.002, 6, frame),
                         'Head'))
    if s.get('scarf'):
        parts.append(tag(torus(0.07, 0.03, (0, 0.005, 1.49), material=M.cloth(
            s['scarf'], 'scarf', 180), scale=(1, 1, 0.9)), 'Neck'))
    if s.get('collar'):
        parts.append(tag(torus(0.056, 0.009, (0, 0.006, 1.488), (0.16, 0, 0), mats['top'],
                               scale=(1, 1.05, 2.2)), 'Spine2'))
    if s.get('buttons'):
        for i in range(5):
            parts.append(tag(sphere(0.0075, (0, -0.097 * g + 0.012 * abs(i - 1.5) * 0.9,
                                             1.38 - i * 0.075), (1, 0.4, 1),
                                    material=M.plastic('#d8d2c4', 'button', 0.35), segments=12,
                                    rings=6), 'Spine1' if i > 1 else 'Spine2'))
    if s.get('club'):
        d = j['dR']
        w = j['wrR'] + d * 0.06
        c = lathe([(0.0, 0.0), (0.014, 0.0), (0.017, 0.2), (0.03, 0.42), (0.045, 0.62),
                   (0.04, 0.7), (0.0, 0.72)], 20, material=M.wood('#5b3d26', 'club', 0, 0.75))
        __import__('core').roughen(c, 0.006, 22)
        place(c, w + Vector((0.0, 0.12, 0.0)), (math.pi / 2, 0, 0))
        parts.append(tag(c, 'Hand.R'))
    if s.get('necklace'):
        for i in range(11):
            a = math.pi * (0.1 + 0.8 * i / 10)
            parts.append(tag(sphere(0.008 if i % 2 else 0.011, (0.085 * math.cos(a), -0.075 -
                                                              0.03 * math.sin(a),
                                                              1.44 - 0.075 * math.sin(a)),
                                    material=M.horn('#e8dfc8', 'bead'), segments=10, rings=6),
                             'Spine2'))
    if s.get('clipboard'):
        d = j['dL']
        w = j['wrL'] + d * 0.08
        parts.append(tag(__import__('core').box((0.012, 0.2, 0.28), w + Vector((0.02, -0.04, 0.03)),
                                                material=M.paper('#e9e4d6', 'clipboard'),
                                                bevel_width=0.003), 'Hand.L'))
    return parts


def eva_parts(s, j, mats):
    """Helmet with a mirrored visor, life-support pack, chest unit and joint rings."""
    import core
    parts = []
    hard = M.paint(s.get('hard_color', '#e9e9e6'), 'hard', 0.35, 0.25, 0.3)
    dark = M.plastic('#1a1c20', 'dark', 0.45)
    metal = M.metal('#a9b0b6', 'ring', 0.3, 0.6)
    helmet = sphere(0.165, (0, -0.005, 1.66), (1, 1.04, 1.0), material=hard, segments=48,
                    rings=28)
    parts.append(tag(helmet, 'Head'))
    visor = sphere(0.15, (0, -0.045, 1.665), (0.93, 0.92, 0.86), material=M.chrome(
        'visor', s.get('visor_color', '#f2b545'), 0.06), segments=48, rings=28)
    parts.append(tag(visor, 'Head'))
    parts.append(tag(torus(0.118, 0.022, (0, 0.004, 1.5), material=metal, scale=(1, 1, 1.1)),
                     'Neck'))
    for sx in (1, -1):
        parts.append(tag(core.cylinder(0.03, 0.03, (sx * 0.165, 0.0, 1.66), (0, math.pi / 2, 0),
                                       dark, 20, bevel_width=0.004), 'Head'))
        parts.append(tag(core.box((0.018, 0.035, 0.022), (sx * 0.13, -0.11, 1.78),
                                  material=M.emissive('#fff3d6', 'lamp', 5.0),
                                  bevel_width=0.004), 'Head'))
    pack = core.box((0.36, 0.17, 0.52), (0, 0.2, 1.3), material=hard, bevel_width=0.03, segments=3)
    parts.append(tag(pack, 'Spine2'))
    parts.append(tag(core.box((0.26, 0.03, 0.2), (0, 0.29, 1.36), material=dark,
                              bevel_width=0.008), 'Spine2'))
    for sx in (1, -1):
        parts.append(tag(core.cylinder(0.035, 0.42, (sx * 0.12, 0.3, 1.3), material=metal,
                                       segments=20, bevel_width=0.008), 'Spine2'))
        parts.append(tag(tube([(sx * 0.12, 0.28, 1.5), (sx * 0.16, 0.14, 1.55),
                               (sx * 0.12, 0.02, 1.52)], 0.014, 10, dark, smooth_path=2),
                         'Spine2'))
    chest = core.box((0.2, 0.06, 0.15), (0, -0.17, 1.3), material=hard, bevel_width=0.012)
    parts.append(tag(chest, 'Spine2'))
    for i, col in enumerate(('#ff5a3c', '#3cff9a', '#3cb4ff', '#ffd23c')):
        parts.append(tag(core.box((0.022, 0.012, 0.022), (-0.06 + i * 0.04, -0.203, 1.33),
                                  material=M.emissive(col, 'led%d' % i, 3.0),
                                  bevel_width=0.003), 'Spine2'))
    parts.append(tag(core.box((0.1, 0.012, 0.04), (0, -0.203, 1.27),
                              material=M.screen(s.get('accent', '#3fb6ff'), 'display', 60),
                              bevel_width=0.003), 'Spine2'))
    accent = M.paint(s.get('accent', '#d9472b'), 'accent', 0.4, 0.2, 0.2)
    for side in 'LR':
        sx = 1 if side == 'L' else -1
        d = j['d' + side]
        rot = (0, -sx * A, 0)
        for pos, bone, r in ((j['el' + side], 'ForeArm.' + side, 0.078),
                             (j['wr' + side] - d * 0.03, 'ForeArm.' + side, 0.062),
                             (j['sh' + side] + d * 0.09, 'UpperArm.' + side, 0.092)):
            parts.append(tag(place(torus(r, 0.012, material=metal if r < 0.07 else accent,
                                         segments=32, ring=10), pos, rot), bone))
        for pos, bone, r in ((j['kn' + side], 'Leg.' + side, 0.092),
                             (j['an' + side] + Vector((0, 0, 0.2)), 'Leg.' + side, 0.08),
                             (j['hip' + side].lerp(j['kn' + side], 0.35), 'UpLeg.' + side,
                              0.112)):
            parts.append(tag(torus(r, 0.013, pos, material=metal if r < 0.1 else accent,
                                   segments=32, ring=10), bone))
    return parts


def tail_mesh(s, mats):
    sp = s.get('species')
    n = s.get('tail_len', 0.4)
    m = Meta(0.009)
    pts = [Vector((0, 0.09 + n * f, 0.98 - 0.25 * n * f * f + 0.2 * n * f))
           for f in [i / 8 for i in range(9)]]
    fat = {'fox': [0.03, 0.045, 0.06, 0.072, 0.078, 0.075, 0.062, 0.042, 0.016],
           'rabbit': [0.04, 0.05, 0.055, 0.055, 0.05, 0.045, 0.04, 0.03, 0.02],
           'bear': [0.035, 0.04, 0.042, 0.04, 0.036, 0.03, 0.026, 0.02, 0.014],
           'pig': [0.014] * 9}.get(sp, [0.02] * 9)
    if sp == 'pig':
        pts = [Vector((0.025 * math.sin(f * 9), 0.1 + 0.11 * f, 0.99 + 0.025 * math.cos(f * 9)))
               for f in [i / 8 for i in range(9)]]
    m.path(pts, fat)
    return m.mesh('tail', mats['fur'])


def build(s):
    """Returns (rig, mesh) for one character spec."""
    j = joints(s)
    tone = s.get('skin', '#c98f6b')
    sp = s.get('species')
    hair_c = s.get('hair_color', '#2a1c14')
    mats = {
        'skin': M.skin(tone),
        'lips': M.skin(s.get('lips', '#a8584f'), 'lips'),
        'hair': M.fur(hair_c, name='hair', scale=1.4, rough=0.5),
        'fur': M.fur(s.get('fur', '#b5651d'), s.get('fur2'), 'fur', 1.0) if sp else None,
        'top': s.get('top_mat') or M.cloth(s.get('top_color', '#b8b2a6'), 'top'),
        'bottom': s.get('bottom_mat') or M.denim(s.get('bottom_color', '#2f456f'), 'bottom'),
        'shoes': s.get('shoes_mat') or M.leather(s.get('shoe_color', '#2a1d16'), 'shoes'),
        'belt': M.leather('#2b1a12', 'belt', 0.45),
        'vest': s.get('vest_mat'),
    }
    rig = build_rig(s, j)
    eva = s.get('eva')
    head, head_parts = (None, []) if eva else head_mesh(s, mats)
    shells = body_shells(s, j, mats)
    hand_mat = s.get('glove_mat') or (mats['fur'] if sp else mats['skin'])
    hands = [hand_mesh(j, side, hand_mat, 1.45 if eva else 1.15 if sp else 1.0)
             for side in 'LR']
    soft = shells + hands + ([head] if head else [])
    if sp:
        soft.append(tail_mesh(s, mats))
    body = join(soft, 'body')
    rig.bind_auto(body)
    if len(body.vertex_groups) < 10:
        raise RuntimeError('automatic weights failed for ' + s.get('name', '?'))
    rigid = head_parts + ([] if eva else hair_parts(s, mats)) + accessories(s, j, mats) + (
        eva_parts(s, j, mats) if eva else [])
    for p in rigid:
        bone = p.get('bone')
        p.vertex_groups.new(name=bone).add(range(len(p.data.vertices)), 1.0, 'REPLACE')
    mesh = join([body] + rigid, s.get('name', 'character'))
    k = s.get('height', 1.75) / 1.75
    hk = s.get('head', 1.0)
    if hk != 1.0:
        # children: a larger head on the same skeleton
        for pb in ('Head',):
            rig.obj.data.bones[pb]['head_scale'] = hk
    if k != 1.0:
        rig.obj.scale = (k, k, k)
        activate(rig.obj)
        bpy.ops.object.transform_apply(scale=True)
        activate(mesh)
        bpy.ops.object.transform_apply(scale=True)
    animate(rig, s, k)
    return rig, mesh


# ----------------------------------------------------------------------------- animation
def curl(P, side, amount, thumb=None):
    sx = 1 if side == 'L' else -1
    for name, _, _ in FINGERS:
        for i in (1, 2, 3):
            P.turn('%s%d.%s' % (name, i, side), y=sx * amount * (0.8 if i == 1 else 1.0))
    t = amount * 0.5 if thumb is None else thumb
    for i in (2, 3):
        P.turn('Thumb%d.%s' % (i, side), y=sx * t * 0.6, x=t * 0.4)


def arm(P, side, fwd=0.0, out=0.0, bend=0.0, twist=0.0, down=0.33):
    """fwd: swing forward; out: lift sideways from hanging; bend: elbow."""
    sx = 1 if side == 'L' else -1
    P.turn('UpperArm.' + side, x=-fwd, y=sx * (down - out), z=sx * twist)
    P.turn('ForeArm.' + side, x=-bend)


def step(P, side, phase, k, stride, lift, stance=0.6, width=0.012):
    """Foot path of a walk or run played on the spot."""
    p = phase % 1.0
    if p < stance:
        u = p / stance
        y = (-0.5 + u) * stride
        z = 0.0
        pitch = -0.28 * max(0, 1 - u * 5) + 0.45 * max(0, (u - 0.75) * 4)
        z += 0.05 * max(0, (u - 0.75) * 4)
    else:
        u = (p - stance) / (1 - stance)
        y = (0.5 - ease(u)) * stride
        z = lift * math.sin(math.pi * u) ** 1.2 + 0.05 * (1 - u) ** 2
        pitch = 0.45 * (1 - u) ** 2 * (1 - u) - 0.28 * max(0, u - 0.6) * 2.5 + 0.5 * math.sin(
            math.pi * u) * (lift > 0.15)
    sx = 1 if side == 'L' else -1
    P.move('ik_foot.' + side, sx * width * k, y * k, z * k)
    P.turn('ik_foot.' + side, x=pitch)


def animate(rig, s, k):
    sp = s.get('species')
    heavy = min(1.4, max(0.8, s.get('girth', 1.0)))

    def extras(t, P, energy=1.0):
        if sp:
            for i in range(1, 5):
                P.turn('Tail.%02d' % i, z=0.22 * energy * wave(t, -i * 0.12),
                       x=0.06 * wave(t, 0.25 - i * 0.1, 2))
            for side, sx in (('L', 1), ('R', -1)):
                P.turn('Ear.' + side, x=0.08 * energy * wave(t, 0.1, 2), y=sx * 0.06 * wave(t))
        for i in (1, 2):
            P.turn('Hair.%02d' % i, x=0.08 * energy * wave(t, 0.15 - i * 0.1, 2))
        for side, sx in (('L', 1), ('R', -1)):
            P.turn('Skirt.' + side, x=0.0)

    def walk(t, P):
        for side, ph, sx in (('L', 0.0, 1), ('R', 0.5, -1)):
            step(P, side, t + ph, k, 0.62, 0.1)
            swing = math.sin(math.tau * (t + ph + 0.3))
            arm(P, side, fwd=-0.42 * swing, bend=0.28 - 0.16 * swing)
            curl(P, side, 0.35)
            P.turn('Skirt.' + side, x=0.25 * math.sin(math.tau * (t + ph + 0.8)))
        P.move('Hips', 0.018 * heavy * k * wave(t, 0.1), 0, (-0.014 - 0.016 * math.cos(
            2 * math.tau * (t + 0.02))) * k)
        P.turn('Hips', y=0.05 * wave(t, 0.1), z=0.11 * wave(t, 0.05))
        P.turn('Spine1', z=-0.1 * wave(t, 0.05), x=0.03)
        P.turn('Spine2', z=-0.1 * wave(t, 0.05), y=-0.03 * wave(t, 0.1))
        P.turn('Neck', z=0.08 * wave(t, 0.05))
        P.turn('Head', x=0.02 * wave(t, 0, 2))
        extras(t, P)

    def run(t, P):
        for side, ph, sx in (('L', 0.0, 1), ('R', 0.5, -1)):
            step(P, side, t + ph, k, 0.95, 0.3, 0.36)
            swing = math.sin(math.tau * (t + ph + 0.32))
            arm(P, side, fwd=-0.85 * swing, bend=1.45 - 0.2 * swing, out=0.08)
            curl(P, side, 1.0)
            P.turn('Skirt.' + side, x=0.5 * math.sin(math.tau * (t + ph + 0.8)))
        P.move('Hips', 0.012 * k * wave(t, 0.1), -0.02 * k,
               (-0.06 + 0.045 * math.cos(2 * math.tau * (t + 0.1))) * k)
        P.turn('Hips', x=0.12, z=0.16 * wave(t, 0.05))
        P.turn('Spine1', x=0.1, z=-0.16 * wave(t, 0.05))
        P.turn('Spine2', x=0.08, z=-0.14 * wave(t, 0.05))
        P.turn('Neck', x=-0.12, z=0.1 * wave(t, 0.05))
        extras(t, P, 2.0)

    def idle(t, P):
        breath = wave(t, 0, 2)
        sway = wave(t)
        P.move('Hips', 0.012 * k * sway, 0, -0.012 * k)
        P.turn('Hips', y=0.02 * sway)
        P.turn('Spine1', x=0.012 * breath, y=-0.012 * sway)
        P.turn('Spine2', x=0.018 * breath)
        P.scale('Spine2', 1 + 0.012 * breath, 1, 1 + 0.02 * breath)
        P.turn('Neck', z=0.06 * wave(t, 0.2), x=-0.01 * breath)
        P.turn('Head', z=0.08 * wave(t, 0.25), x=0.02 * wave(t, 0.4))
        for side, sx in (('L', 1), ('R', -1)):
            P.turn('Shoulder.' + side, y=-sx * 0.02 * breath)
            arm(P, side, fwd=0.03 * wave(t, 0.1 * sx), bend=0.14 + 0.03 * breath)
            curl(P, side, 0.45 + 0.05 * breath)
            P.move('ik_foot.' + side, sx * 0.03 * k, 0, 0)
        extras(t, P, 0.5)

    def wave_clip(t, P):
        up = pulse(t, 0.05, 0.25, 0.75, 0.95)
        idle(t, P)
        P.turn('UpperArm.R', x=0, y=-0.33 + up * 2.25, z=0)
        P.turn('ForeArm.R', y=up * (0.5 + 0.45 * math.sin(math.tau * t * 4)), x=-up * 0.3)
        P.turn('Hand.R', y=up * 0.25 * math.sin(math.tau * t * 4 + 0.6))
        curl(P, 'R', 0.45 * (1 - up) + 0.05)
        P.turn('Head', z=-0.12 * up, y=0.06 * up)
        P.turn('Spine2', y=0.05 * up)

    def dance(t, P):
        beat = wave(t, 0, 2)
        half = wave(t)
        P.move('Hips', 0.06 * k * half, 0, (-0.09 + 0.05 * abs(beat)) * k)
        P.turn('Hips', z=0.2 * half, y=0.1 * half)
        P.turn('Spine1', z=-0.15 * half, y=-0.08 * half)
        P.turn('Spine2', z=-0.2 * half, x=0.05 * beat)
        P.turn('Neck', z=0.1 * half)
        P.turn('Head', x=0.1 * beat, z=0.1 * half)
        for side, sx, ph in (('L', 1, 0.0), ('R', -1, 0.5)):
            lift = max(0, math.sin(math.tau * (t + ph)))
            arm(P, side, fwd=0.5 + 0.5 * lift, out=0.5 + 0.9 * lift, bend=1.3 - 0.6 * lift)
            P.turn('Hand.' + side, x=0.3 * beat)
            curl(P, side, 0.5)
            P.move('ik_foot.' + side, sx * (0.07 + 0.05 * lift) * k, -0.04 * lift * k,
                   0.07 * lift * k)
            P.turn('ik_foot.' + side, x=0.35 * lift, z=sx * 0.25)
            P.turn('Skirt.' + side, y=sx * 0.2 * lift)
        extras(t, P, 2.0)

    def jump(t, P):
        crouch = pulse(t, 0.0, 0.26, 0.3, 0.4) + 0.75 * pulse(t, 0.66, 0.74, 0.8, 1.0)
        u = min(1, max(0, (t - 0.36) / 0.32))
        air = 4 * u * (1 - u)
        P.move('Hips', 0, 0.06 * crouch * k, (-0.3 * crouch + 0.42 * air) * k)
        P.turn('Hips', x=0.35 * crouch)
        P.turn('Spine1', x=0.25 * crouch - 0.1 * air)
        P.turn('Spine2', x=0.15 * crouch - 0.08 * air)
        P.turn('Neck', x=-0.3 * crouch)
        for side, sx in (('L', 1), ('R', -1)):
            arm(P, side, fwd=-0.9 * crouch + 2.4 * air, bend=0.5 * crouch + 0.2, out=0.1 * air)
            curl(P, side, 0.6)
            P.move('ik_foot.' + side, sx * 0.03 * k, 0.05 * air * k,
                   0.42 * air * k * (0.55 + 0.45 * air))
            P.turn('ik_foot.' + side, x=0.6 * air)
        extras(t, P, 1.5)

    def squat(t, P):
        d = pulse(t, 0.05, 0.4, 0.55, 0.95)
        P.move('Hips', 0, 0.15 * d * k, -0.4 * d * k)
        P.turn('Hips', x=0.5 * d)
        P.turn('Spine1', x=0.12 * d)
        P.turn('Neck', x=-0.4 * d)
        for side, sx in (('L', 1), ('R', -1)):
            arm(P, side, fwd=1.25 * d, bend=0.15 + 0.1 * d, out=0.05)
            curl(P, side, 0.4)
            P.move('ik_foot.' + side, sx * 0.07 * k, 0, 0)
            P.turn('ik_foot.' + side, z=sx * 0.2)
        extras(t, P, 0.5)

    def talk(t, P):
        idle(t, P)
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

    def clap(t, P):
        idle(t, P)
        c = 0.5 + 0.5 * math.cos(math.tau * t * 4)
        for side, sx in (('L', 1), ('R', -1)):
            arm(P, side, fwd=0.95, bend=1.35, out=-0.12 + 0.2 * c)
            P.turn('ForeArm.' + side, z=-sx * (0.55 - 0.3 * c))
            curl(P, side, 0.08)
        P.turn('Head', x=0.05 * c)

    def cheer(t, P):
        b = abs(wave(t, 0, 1))
        P.move('Hips', 0, 0, (-0.05 + 0.07 * b) * k)
        P.turn('Spine2', x=-0.12 * b)
        P.turn('Head', x=-0.2 * b)
        P.turn('Jaw', x=0.25 * b)
        for side, sx in (('L', 1), ('R', -1)):
            P.turn('UpperArm.' + side, y=sx * (0.33 - 2.5 - 0.25 * b), x=-0.2)
            P.turn('ForeArm.' + side, x=-0.3 + 0.25 * b)
            curl(P, side, 1.1)
            P.move('ik_foot.' + side, sx * 0.05 * k, 0, 0.05 * max(0, b - 0.6) * k)
        extras(t, P, 2.0)

    def look(t, P):
        idle(t, P)
        yaw = 0.75 * math.sin(math.tau * t) * (0.6 + 0.4 * math.cos(math.tau * t * 2))
        P.turn('Head', z=yaw * 0.6, x=0.08 * math.sin(math.tau * t * 2))
        P.turn('Neck', z=yaw * 0.3)
        P.turn('Spine2', z=yaw * 0.15)

    def point(t, P):
        up = pulse(t, 0.08, 0.3, 0.72, 0.94)
        idle(t, P)
        arm(P, 'R', fwd=1.45 * up, bend=0.14 * (1 - up), out=0.1 * up)
        curl(P, 'R', 0.45 + 0.9 * up)
        for i in (1, 2, 3):
            P.turn('Index%d.R' % i, y=0.0)
        P.turn('Spine2', z=0.12 * up)
        P.turn('Head', z=0.1 * up)

    def sit(t, P):
        breath = wave(t, 0, 2)
        P.move('Hips', 0, 0.2 * k, -0.47 * k)
        P.turn('Hips', x=-0.1)
        P.turn('Spine1', x=0.08 + 0.012 * breath)
        P.turn('Spine2', x=0.05 + 0.015 * breath)
        P.turn('Head', z=0.1 * wave(t, 0.2), x=0.03 * wave(t, 0.4))
        for side, sx in (('L', 1), ('R', -1)):
            arm(P, side, fwd=0.55, bend=0.95, out=0.02)
            curl(P, side, 0.4)
            P.move('ik_foot.' + side, sx * 0.02 * k, -0.24 * k, 0)
        extras(t, P, 0.4)

    def drift(t, P):
        slow = wave(t)
        P.move('Hips', 0.03 * k * wave(t, 0.2), 0.02 * k * wave(t, 0.4, 2), 0.05 * k * slow)
        P.turn('Hips', x=0.12 + 0.08 * wave(t, 0.1), y=0.1 * wave(t, 0.3), z=0.15 * slow)
        P.turn('Spine1', x=0.06 * wave(t, 0.2))
        P.turn('Spine2', x=0.05 * wave(t, 0.35), z=-0.08 * slow)
        P.turn('Head', x=0.1 * wave(t, 0.5), z=0.15 * wave(t, 0.15))
        for side, sx, ph in (('L', 1, 0.0), ('R', -1, 0.37)):
            arm(P, side, fwd=0.45 + 0.2 * wave(t, ph), out=0.55 + 0.2 * wave(t, ph + 0.2),
                bend=0.7 + 0.25 * wave(t, ph + 0.4))
            P.turn('Hand.' + side, x=0.2 * wave(t, ph + 0.1))
            curl(P, side, 0.35 + 0.1 * wave(t, ph))
            P.move('ik_foot.' + side, sx * 0.06 * k, (0.1 + 0.1 * wave(t, ph + 0.5)) * k,
                   (0.16 + 0.07 * wave(t, ph + 0.25)) * k)
            P.turn('ik_foot.' + side, x=0.5 + 0.15 * wave(t, ph))

    def moonwalk(t, P):
        u = (t * 2) % 1.0
        hop = 4 * u * (1 - u)
        lead = 'L' if t < 0.5 else 'R'
        P.move('Hips', 0, -0.03 * k, (-0.07 + 0.3 * hop) * k)
        P.turn('Hips', x=0.2)
        P.turn('Spine1', x=0.12)
        P.turn('Neck', x=-0.15)
        for side, sx in (('L', 1), ('R', -1)):
            front = side == lead
            P.move('ik_foot.' + side, sx * 0.03 * k, (-0.16 if front else 0.2) * hop * k,
                   (0.3 * hop * (0.75 if front else 1.0)) * k)
            P.turn('ik_foot.' + side, x=0.5 * hop * (0.3 if front else 1.0))
            arm(P, side, fwd=(0.5 if not front else -0.2) * hop + 0.15, out=0.3 + 0.2 * hop,
                bend=0.6)
            curl(P, side, 0.4)

    def reach(t, P):
        up = pulse(t, 0.1, 0.45, 0.6, 0.95)
        drift(t, P)
        P.turn('UpperArm.R', x=-1.5 * up, y=-(0.33 - 0.55) * (1 - up) - 0.25 * up)
        P.turn('ForeArm.R', x=-0.7 * (1 - up) - 0.08)
        P.turn('Hand.R', x=-0.2 * up)
        curl(P, 'R', 0.35 * (1 - up) + 0.04)
        P.turn('Head', x=-0.2 * up, z=0.1 * up)
        P.turn('Spine2', x=-0.1 * up, z=0.15 * up)

    def tumble(t, P):
        drift(t, P)
        P.rot('Root', 0, 0, 0)
        P.turn('Hips', x=math.tau * t, y=0.2 * wave(t), z=0.3 * wave(t, 0.25))

    def look_up(t, P):
        up = pulse(t, 0.1, 0.4, 0.65, 0.95)
        idle(t, P)
        P.turn('Head', x=-0.5 * up)
        P.turn('Neck', x=-0.25 * up)
        P.turn('Spine2', x=-0.14 * up)
        for side in 'LR':
            arm(P, side, fwd=-0.1 * up, out=0.12 * up, bend=0.15)

    def hands_to(P, side, where, amount=1.0):
        sx = 1 if side == 'L' else -1
        fwd, bend, out, inward = {'face': (1.25, 2.25, -0.05, 0.35), 'heart': (0.62, 2.05, -0.2, 0.75),
                                  'shield': (1.7, 1.5, 0.25, 0.3), 'head': (2.3, 2.1, 0.5, 0.2),
                                  'hips': (-0.25, 1.35, 0.55, -0.6)}[where]
        arm(P, side, fwd=fwd * amount, bend=bend * amount, out=out * amount)
        P.turn('ForeArm.' + side, z=-sx * inward * amount)

    def sad(t, P):
        breath = wave(t, 0, 2)
        sigh = pulse(t, 0.55, 0.68, 0.72, 0.9)
        P.move('Hips', 0.008 * k * wave(t), 0.01 * k, -0.03 * k)
        P.turn('Hips', x=0.04)
        P.turn('Spine1', x=0.16 + 0.02 * breath + 0.05 * sigh)
        P.turn('Spine2', x=0.2 + 0.03 * breath + 0.06 * sigh)
        P.turn('Neck', x=0.3 - 0.08 * sigh)
        P.turn('Head', x=0.28, z=0.12 * wave(t, 0.2), y=0.06)
        for side, sx in (('L', 1), ('R', -1)):
            P.turn('Shoulder.' + side, y=sx * 0.12, x=0.1)
            arm(P, side, fwd=0.1 + 0.02 * breath, bend=0.1, down=0.36)
            curl(P, side, 0.5)
            P.move('ik_foot.' + side, sx * 0.01 * k, 0, 0)
        extras(t, P, 0.2)

    def cry(t, P):
        sob = max(0, math.sin(math.tau * t * 6)) ** 2 * (0.5 + 0.5 * math.sin(math.tau * t))
        sad(t, P)
        for side in 'LR':
            hands_to(P, side, 'face')
            curl(P, side, 0.3)
        P.turn('Spine2', x=0.3 + 0.07 * sob)
        P.turn('Shoulder.L', y=0.1 + 0.12 * sob)
        P.turn('Shoulder.R', y=-0.1 - 0.12 * sob)
        P.turn('Head', x=0.3 + 0.05 * sob)

    def surprise(t, P):
        hit = pulse(t, 0.12, 0.2, 0.62, 0.9)
        snap = max(0.0, 1 - abs(t - 0.2) * 9)
        idle(t, P)
        P.move('Hips', 0, 0.07 * hit * k, (-0.02 + 0.03 * snap) * k)
        P.turn('Spine1', x=-0.1 * hit)
        P.turn('Spine2', x=-0.14 * hit)
        P.turn('Head', x=-0.16 * hit)
        P.turn('Jaw', x=0.3 * hit)
        for side, sx in (('L', 1), ('R', -1)):
            arm(P, side, fwd=0.5 * hit, out=0.55 * hit, bend=1.5 * hit + 0.15)
            P.turn('Shoulder.' + side, y=-sx * 0.2 * hit)
            curl(P, side, 0.45 * (1 - hit))
        P.move('ik_foot.R', -0.02 * k, 0.16 * hit * k, 0.06 * snap * k)

    def love(t, P):
        sway = wave(t)
        breath = wave(t, 0, 2)
        P.move('Hips', 0.025 * k * sway, 0, -0.012 * k)
        P.turn('Hips', y=0.05 * sway)
        P.turn('Spine2', x=-0.05 + 0.03 * breath, y=-0.05 * sway)
        P.turn('Head', y=0.22 * sway, x=-0.08, z=0.1 * wave(t, 0.2))
        for side, sx in (('L', 1), ('R', -1)):
            hands_to(P, side, 'heart')
            curl(P, side, 0.2)
            P.turn('Shoulder.' + side, y=-sx * 0.08 * (1 + breath))
            P.move('ik_foot.' + side, sx * 0.01 * k, 0, 0)
        extras(t, P, 0.8)

    def terror(t, P):
        shake = math.sin(math.tau * t * 14) * 0.5 + math.sin(math.tau * t * 23) * 0.5
        glance = pulse(t, 0.3, 0.42, 0.55, 0.7)
        P.move('Hips', 0.004 * k * shake, 0.09 * k, -0.2 * k)
        P.turn('Hips', x=0.3, z=-0.25 * glance)
        P.turn('Spine1', x=0.2 + 0.01 * shake)
        P.turn('Spine2', x=0.18, z=-0.2 * glance)
        P.turn('Neck', x=-0.2, z=-0.35 * glance)
        P.turn('Head', x=-0.15 + 0.02 * shake, z=-0.5 * glance)
        P.turn('Jaw', x=0.25)
        for side, sx in (('L', 1), ('R', -1)):
            hands_to(P, side, 'shield', 1 - 0.25 * glance * (side == 'L'))
            P.turn('Hand.' + side, x=-0.6 + 0.05 * shake)
            curl(P, side, 0.1)
            P.move('ik_foot.' + side, sx * 0.06 * k, (0.0 if side == 'L' else 0.14) * k, 0)
        extras(t, P, 3.0)

    def angry(t, P):
        stomp = max(0, math.sin(math.tau * t * 2)) ** 3
        P.move('Hips', 0, -0.03 * k, (-0.05 - 0.03 * stomp) * k)
        P.turn('Hips', x=0.12)
        P.turn('Spine2', x=0.14, z=0.1 * wave(t))
        P.turn('Neck', x=-0.1)
        P.turn('Head', x=0.12, z=0.15 * wave(t, 0.1, 2))
        P.turn('Jaw', x=0.2 * stomp)
        arm(P, 'R', fwd=1.5 + 0.3 * stomp, bend=1.7 - 0.9 * stomp, out=0.25)
        arm(P, 'L', fwd=-0.2, bend=1.1, out=0.2)
        for side, sx in (('L', 1), ('R', -1)):
            curl(P, side, 1.3, 1.0)
            P.move('ik_foot.' + side, sx * 0.07 * k, 0, 0)
        P.move('ik_foot.R', -0.07 * k, -0.1 * k, 0.12 * (1 - stomp) * max(
            0, math.sin(math.tau * (t * 2 + 0.75))) * k)
        extras(t, P, 2.5)

    def laugh(t, P):
        ha = max(0, math.sin(math.tau * t * 5)) ** 2 * (0.6 + 0.4 * math.sin(math.tau * t))
        back = 0.5 + 0.5 * math.sin(math.tau * (t - 0.25))
        P.move('Hips', 0, 0, (-0.02 - 0.015 * ha) * k)
        P.turn('Spine1', x=-0.1 * back + 0.25 * (1 - back) + 0.04 * ha)
        P.turn('Spine2', x=-0.12 * back + 0.2 * (1 - back) + 0.05 * ha)
        P.turn('Head', x=-0.35 * back + 0.1 * (1 - back))
        P.turn('Jaw', x=0.3 + 0.1 * ha)
        hands_to(P, 'L', 'hips', 0.4 + 0.6 * (1 - back))
        arm(P, 'R', fwd=0.4 + 0.5 * (1 - back), bend=1.3, out=0.1)
        P.turn('ForeArm.R', z=0.6)
        for side, sx in (('L', 1), ('R', -1)):
            P.turn('Shoulder.' + side, y=-sx * 0.15 * ha)
            curl(P, side, 0.6)
            P.move('ik_foot.' + side, sx * 0.04 * k, 0, 0)
        extras(t, P, 2.0)

    def embrace(t, P):
        open_ = pulse(t, 0.05, 0.3, 0.45, 0.7)
        close = pulse(t, 0.45, 0.7, 0.85, 0.98)
        idle(t, P)
        P.turn('Spine2', x=-0.1 * open_ + 0.12 * close)
        P.turn('Head', x=-0.12 * open_ + 0.15 * close, y=0.15 * close)
        for side, sx in (('L', 1), ('R', -1)):
            arm(P, side, fwd=0.7 * open_ + 0.6 * close, out=1.15 * open_ * (1 - close),
                bend=0.35 * open_ + 1.5 * close)
            P.turn('ForeArm.' + side, z=-sx * 0.8 * close)
            curl(P, side, 0.15 + 0.3 * close)
        P.move('Hips', 0, -0.04 * close * k, -0.012 * k)

    def kneel(t, P):
        down = pulse(t, 0.05, 0.3, 0.75, 0.98)
        plea = pulse(t, 0.3, 0.5, 0.65, 0.8)
        P.move('Hips', 0, -0.12 * down * k, -0.5 * down * k)
        P.turn('Hips', x=-0.05 * down)
        P.turn('Spine2', x=-0.2 * plea + 0.15 * down * (1 - plea))
        P.turn('Head', x=-0.5 * plea + 0.25 * down * (1 - plea))
        for side, sx in (('L', 1), ('R', -1)):
            P.move('ik_foot.' + side, sx * 0.04 * k, 0.3 * down * k, 0.03 * down * k)
            P.turn('ik_foot.' + side, x=1.35 * down)
            arm(P, side, fwd=0.9 * plea, out=0.55 * plea, bend=0.5 * plea + 0.12)
            P.turn('Hand.' + side, y=sx * 1.2 * plea)
            curl(P, side, 0.45 * (1 - plea) + 0.05)
        extras(t, P, 0.5)

    def shiver(t, P):
        shake = math.sin(math.tau * t * 16)
        P.move('Hips', 0.003 * k * shake, 0, -0.04 * k)
        P.turn('Spine1', x=0.14)
        P.turn('Spine2', x=0.16 + 0.01 * shake)
        P.turn('Head', x=0.15, z=0.02 * shake)
        for side, sx in (('L', 1), ('R', -1)):
            arm(P, side, fwd=0.55, bend=2.0, out=-0.25)
            P.turn('ForeArm.' + side, z=-sx * 1.1)
            P.turn('Shoulder.' + side, y=-sx * (0.25 + 0.03 * shake))
            curl(P, side, 0.8)
            P.move('ik_foot.' + side, -sx * 0.02 * k, 0, 0)

    def float_any(t, P):
        drift(t, P)

    if s.get('eva'):
        rig.clip('Float', 8.0, drift)
        rig.clip('Moonwalk', 2.4, moonwalk)
        rig.clip('Reach', 6.0, reach)
        rig.clip('Tumble', 10.0, tumble)
    rig.clip('Walk in Place', 1.05 * heavy ** 0.5, walk)
    rig.clip('Run in Place', 0.68, run)
    rig.clip('Idle', 4.0, idle)
    rig.clip('Wave', 2.8, wave_clip)
    rig.clip('Dance', 1.9, dance)
    rig.clip('Jump', 1.6, jump)
    rig.clip('Squat', 2.6, squat)
    rig.clip('Talk', 4.0, talk)
    rig.clip('Clap', 2.0, clap)
    rig.clip('Cheer', 1.2, cheer)
    rig.clip('Look Around', 5.0, look)
    rig.clip('Point', 3.0, point)
    rig.clip('Sit', 4.0, sit)
    rig.clip('Look Up', 5.0, look_up)
    rig.clip('Sad', 6.0, sad)
    rig.clip('Cry', 4.0, cry)
    rig.clip('Surprise', 3.0, surprise)
    rig.clip('Love', 4.0, love)
    rig.clip('Terror', 4.0, terror)
    rig.clip('Angry', 2.0, angry)
    rig.clip('Laugh', 3.0, laugh)
    rig.clip('Embrace', 5.0, embrace)
    rig.clip('Kneel', 6.0, kneel)
    rig.clip('Shiver', 2.0, shiver)
    if not s.get('eva'):
        rig.clip('Float', 8.0, float_any)
    rig.finish()
