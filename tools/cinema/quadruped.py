"""A parametric four-legged animal: anatomy from a spec, IK legs and real gaits."""
import math

from core import Meta, Rig, Vector, ease, join, lathe, sphere, tag, tube, wave, place
import materials as M

LEGS = ('FL', 'FR', 'HL', 'HR')


def layout(s):
    h, L, r = s['height'], s['length'], s['barrel']
    zs = h - r
    fw, hw = s.get('front_width', 0.55) * r, s.get('hind_width', 0.6) * r
    hoof = s.get('hoof', 0.04)
    p = {'zs': zs}
    knee = s.get('knee', 0.5)
    hock = s.get('hock', 0.42)
    for side, sx in (('L', 1), ('R', -1)):
        top = zs - 0.25 * r
        p['F' + side] = [Vector((sx * fw, -L / 2, top)),
                         Vector((sx * fw, -L / 2 - 0.035 * h, hoof + (top - hoof) * knee)),
                         Vector((sx * fw, -L / 2 + 0.01 * h, hoof)),
                         Vector((sx * fw, -L / 2 - s.get('toe', 0.07) * h, 0.012))]
        top = zs - 0.05 * r
        p['H' + side] = [Vector((sx * hw, L / 2, top)),
                         Vector((sx * hw, L / 2 + 0.11 * h, hoof + (top - hoof) * hock)),
                         Vector((sx * hw, L / 2 + 0.035 * h, hoof)),
                         Vector((sx * hw, L / 2 - (s.get('toe', 0.07) - 0.03) * h, 0.012))]
    a = math.radians(s.get('neck_angle', 45))
    n0 = Vector((0, -L / 2 - 0.1 * r, zs + 0.35 * r))
    n1 = n0 + Vector((0, -math.cos(a), math.sin(a))) * s['neck']
    b = math.radians(s.get('head_angle', 35))
    hd = Vector((0, -math.cos(b), -math.sin(b)))
    p.update(n0=n0, n1=n1, hd=hd, snout=n1 + hd * s['head'])
    t = math.radians(s.get('tail_angle', -60))
    p['t0'] = Vector((0, L / 2 + 0.75 * s.get('rump', r), zs + 0.35 * r))
    p['td'] = Vector((0, math.cos(t), math.sin(t)))
    return p


def build(s):
    p = layout(s)
    h, L, r = s['height'], s['length'], s['barrel']
    zs = p['zs']
    rig = Rig(s.get('name', 'Animal'))
    b = rig.bone
    b('Root', (0, 0, 0), (0, 0.3 * h, 0), deform=False)
    spine = [Vector((0, L / 2 * (1 - 2 * f), zs + 0.25 * r)) for f in (0, 0.33, 0.66, 1.0)]
    b('Hips', spine[0] + Vector((0, 0.3 * r, 0)), spine[0], 'Root')
    b('Spine.01', spine[0], spine[1], 'Hips', True)
    b('Spine.02', spine[1], spine[2], 'Spine.01', True)
    b('Chest', spine[2], spine[3] + Vector((0, -0.1 * r, 0)), 'Spine.02', True)
    nmid = p['n0'].lerp(p['n1'], 0.5)
    b('Neck.01', p['n0'], nmid, 'Chest')
    b('Neck.02', nmid, p['n1'], 'Neck.01', True)
    b('Head', p['n1'], p['snout'], 'Neck.02', True)
    b('Jaw', p['n1'] + p['hd'] * s['head'] * 0.25 + Vector((0, 0, -0.3 * s['skull'])),
      p['snout'] + Vector((0, 0, -0.5 * s.get('muzzle', s['skull'] * 0.6))), 'Head')
    el, er = s.get('ear', 0.1), s['skull']
    for side, sx in (('L', 1), ('R', -1)):
        e0 = p['n1'] + Vector((sx * er * 0.75, 0.02, er * 0.75))
        out = s.get('ear_out', 0.5)
        b('Ear.' + side, e0, e0 + Vector((sx * out, 0.15, 1 - out * 0.6)).normalized() * el,
          'Head')
        for pre, parent in (('F', 'Chest'), ('H', 'Hips')):
            q = p[pre + side]
            leg = pre + side[0]
            b(leg + '.Upper', q[0], q[1], parent)
            b(leg + '.Lower', q[1], q[2], leg + '.Upper', True)
            b(leg + '.Foot', q[2], q[3], leg + '.Lower', True)
            b('ik.' + leg, q[2], q[3], 'Root', deform=False)
    tl = s.get('tail', 0.3)
    tp = [p['t0'] + p['td'] * tl * f + Vector((0, 0, -tl * s.get('tail_droop', 0.3) * f * f))
          for f in (0, 0.25, 0.5, 0.75, 1.0)]
    rig.chain('Tail', tp, 'Hips')
    rig.build()
    for leg in LEGS:
        rig.ik(leg + '.Lower', 'ik.' + leg, 2)
        rig.copy_rotation(leg + '.Foot', 'ik.' + leg)

    coat = s.get('coat') or M.fur(s.get('color', '#8a6241'), s.get('belly_color'), 'coat',
                                  s.get('fur_scale', 1.0), s.get('spots'),
                                  s.get('spot_scale', 3.0))
    res = s.get('res', max(0.006, h / 110))
    m = Meta(res)
    cr, br, rr = s.get('chest', r), s.get('belly', r), s.get('rump', r)
    wd = s.get('width', 0.8)
    m.ball((0, -L / 2 + 0.1 * r, zs), 1, (cr * wd, cr * 1.05, cr))
    m.ball((0, 0, zs - 0.06 * r), 1, (br * wd * 1.05, L * 0.42, br))
    m.ball((0, L / 2 - 0.05 * r, zs + 0.04 * r), 1, (rr * wd, rr * 1.05, rr * 0.98))
    if s.get('withers'):
        m.ball((0, -L / 2 + 0.25 * r, zs + cr * 0.75), 1, (cr * 0.3, cr * 0.6, cr * s['withers']))
    n0r, n1r = s.get('neck_r0', 0.6 * r), s.get('neck_r1', 0.4 * r)
    m.limb(p['n0'] + Vector((0, 0.3 * r, -0.25 * r)), p['n1'], n0r, n1r)
    sk = s['skull']
    m.ball(p['n1'] + p['hd'] * sk * 0.35, 1, (sk * 0.82, sk, sk * 0.9))
    mz = s.get('muzzle', sk * 0.6)
    m.limb(p['n1'] + p['hd'] * sk * 0.8, p['snout'] - p['hd'] * mz * 0.8, sk * 0.72, mz)
    m.ball(p['snout'] - p['hd'] * mz * 0.75, 1, (mz * 1.02, mz, mz * 0.95))
    if s.get('cheeks'):
        for sx in (1, -1):
            m.ball(p['n1'] + p['hd'] * sk * 0.5 + Vector((sx * sk * 0.55, 0, -sk * 0.35)),
                   sk * s['cheeks'])
    for sx in (1, -1):
        m.ball(p['n1'] + p['hd'] * sk * 0.72 + Vector((sx * sk * 0.72, 0, sk * 0.3)),
               sk * 0.2, negative=True)
    up, lo, fr = s.get('leg_upper', 0.3 * r), s.get('leg_knee', 0.13 * r), s.get('leg_lower',
                                                                                 0.1 * r)
    for side, sx in (('L', 1), ('R', -1)):
        f, hq = p['F' + side], p['H' + side]
        m.limb(f[0] + Vector((0, 0, 0.25 * r)), f[1], up * 1.15, lo * 1.2)
        m.ball(f[1], lo * 1.3)
        m.limb(f[1], f[2], lo * 1.05, fr)
        m.ball(hq[0] + Vector((-sx * 0.05 * r, -0.28 * r, -0.25 * r)), 1,
               (up * 1.15, up * 1.9, up * 2.1))
        m.limb(hq[0] + Vector((0, -0.2 * r, -0.4 * r)), hq[1], up * 1.2, lo * 1.15)
        m.ball(hq[1], lo * 1.2)
        m.limb(hq[1], hq[2], lo * 1.05, fr)
        if s.get('paws'):
            for q in (f, hq):
                m.ball(q[2].lerp(q[3], 0.6) + Vector((0, 0, 0.3 * fr)), 1,
                       (fr * 1.5, fr * 2.4, fr * 1.1))
        e0 = p['n1'] + Vector((sx * er * 0.75, 0.02, er * 0.75))
        out = s.get('ear_out', 0.5)
        ed = Vector((sx * out, 0.15, 1 - out * 0.6)).normalized()
        ew = s.get('ear_r', 0.03)
        if s.get('ear_style') == 'round':
            m.ball(e0 + ed * el * 0.6, 1, (ew, ew * 0.45, ew))
        elif s.get('ear_style') == 'flop':
            m.limb(e0, e0 + Vector((sx * el * 0.8, -0.2 * el, -el * 0.6)), ew, ew * 0.5)
        else:
            m.limb(e0 - ed * el * 0.2, e0 + ed * el, ew, ew * 0.25)
    style = s.get('tail_style', 'thin')
    tr = s.get('tail_r', 0.12 * r)
    fine = [p['t0'] + p['td'] * tl * f + Vector((0, 0, -tl * s.get('tail_droop', 0.3) * f * f))
            for f in [i / 10 for i in range(11)]]
    prof = {'thin': lambda f: tr * (1 - 0.6 * f), 'stub': lambda f: tr * (1 - 0.4 * f),
            'bushy': lambda f: tr * (0.55 + 1.6 * math.sin(math.pi * min(1, f * 1.08)) ** 0.8),
            'tuft': lambda f: tr * (0.7 - 0.4 * f + (1.6 * (f - 0.72) / 0.28 if f > 0.72 else 0)),
            'hair': lambda f: tr * (0.6 + 1.5 * math.sin(math.pi * (0.15 + 0.7 * f)))}[style]
    m.path([fine[0] - p['td'] * 0.5 * r] + fine, [tr] + [prof(i / 10) for i in range(11)])
    if s.get('udder'):
        m.ball((0, L * 0.28, zs - br * 0.95), s['udder'])
    if s.get('dewlap'):
        m.ball(p['n0'] + Vector((0, -0.2 * r, -0.75 * r)), 1, (cr * 0.25, cr * 0.6, cr * 0.5))
    if s.get('hump'):
        m.ball((0, -L * 0.3, zs + cr * 0.9), 1, (cr * 0.4, cr * 0.5, cr * s['hump']))
    if s.get('crest'):
        m.ball(p['n1'] + Vector((0, 0.5 * sk, sk * 1.2)), 1, (sk * 0.12, sk * 1.3, sk * 0.9),
               (-0.5, 0, 0))
    body = m.mesh('body', coat)
    soft = [body]
    if s.get('wool'):
        w = Meta(res * 1.3)
        import random
        rnd = random.Random(7)
        for _ in range(170):
            a, y = rnd.uniform(0, math.tau), rnd.uniform(-L / 2 - 0.15 * r, L / 2 + 0.3 * r)
            rad = r * (1.0 + 0.12 * rnd.random())
            c = Vector((rad * wd * math.cos(a), y, zs + rad * math.sin(a)))
            if c.z > zs - r * 0.75:
                w.ball(c, r * rnd.uniform(0.22, 0.32))
        w.limb(p['n0'], p['n0'].lerp(p['n1'], 0.7), n0r * 1.25, n1r * 1.25)
        soft.append(w.mesh('wool', M.wool(s['wool'])))
    if s.get('mane'):
        mm = Meta(res)
        for i in range(12):
            f = i / 11
            c = p['n0'].lerp(p['n1'], 0.1 + 0.95 * f) + Vector((0, 0.3 * n1r, 0.9 * (
                n0r + (n1r - n0r) * f)))
            mm.limb(c, c + Vector((s.get('mane_side', 0.5) * n1r * 1.5, 0.3 * n1r,
                                   -s.get('mane_len', 1.2) * n1r)), n1r * 0.42, n1r * 0.12)
        mm.limb(p['n1'] + Vector((0, 0, sk * 0.8)), p['n1'] + p['hd'] * sk * 0.9 + Vector(
            (0, 0, sk * 0.55)), sk * 0.3, sk * 0.1)
        soft.append(mm.mesh('mane', M.fur(s['mane'], name='mane', scale=1.5, rough=0.5)))
    if style == 'hair' and s.get('mane'):
        pass
    hoofs = Meta(res * 0.8)
    hc = s.get('hoof', 0.04)
    for side in 'LR':
        for q in (p['F' + side], p['H' + side]):
            if s.get('paws'):
                for i in (-1, 0, 1):
                    hoofs.ball(q[3] + Vector((i * fr * 0.8, -fr * 0.3, 0.004)), fr * 0.38)
            else:
                hoofs.ball(q[2].lerp(q[3], 0.45) + Vector((0, 0, -hc * 0.45)), 1,
                           (fr * 1.45, fr * 1.9, hc * 0.75))
    hm = hoofs.mesh('hoofs', M.horn(s.get('hoof_color', '#2a231d'), 'hoof'))
    for v in hm.data.vertices:
        v.co.z = max(v.co.z, 0.002)
    soft.append(hm)
    body = join(soft, 'body')
    rig.bind_auto(body)
    rigid = []
    eye = M.eye('#120c08', 'eye')
    for sx in (1, -1):
        rigid.append(tag(sphere(sk * 0.17, p['n1'] + p['hd'] * sk * 0.72 + Vector(
            (sx * sk * 0.6, 0, sk * 0.3)), material=eye, segments=16, rings=10), 'Head'))
        ns = p['snout'] + Vector((sx * mz * 0.35, 0.0, mz * 0.25)) - p['hd'] * mz * 0.02
        rigid.append(tag(sphere(mz * 0.16, ns, (1, 0.5, 0.7), material=M.eye('#0b0707',
                                                                           'nostril'),
                                segments=10, rings=6), 'Head'))
    if s.get('nose'):
        rigid.append(tag(sphere(mz * 0.42, p['snout'] + Vector((0, 0, mz * 0.3)), (1.2, 0.7, 0.8),
                                material=M.leather(s['nose'], 'nose', 0.3)), 'Head'))
    if s.get('horns'):
        kind, length, col = s['horns']
        hmat = M.horn(col, 'horn')
        for sx in (1, -1):
            base = p['n1'] + Vector((sx * sk * 0.45, 0.25 * sk, sk * 0.85))
            if kind == 'curve':
                pts = [base + Vector((sx * length * (0.5 * f + 0.25 * math.sin(f * 2.4)),
                                      -length * 0.35 * f * f, length * 0.75 * math.sin(f * 1.7)))
                       for f in [i / 7 for i in range(8)]]
            elif kind == 'back':
                pts = [base + Vector((sx * length * 0.2 * f, length * 0.8 * f,
                                      length * 0.6 * math.sin(f * 2.2)))
                       for f in [i / 7 for i in range(8)]]
            elif kind == 'spiral':
                pts = [base + Vector((sx * length * (0.25 + 0.2 * f) * (1 - math.cos(f * 5)),
                                      length * 0.3 * math.sin(f * 5) + 0.1 * length * f,
                                      -length * 0.25 * f + 0.2 * length * math.sin(f * 2.5)))
                       for f in [i / 12 for i in range(13)]]
            else:  # antlers
                pts = [base + Vector((sx * length * 0.45 * f, length * 0.25 * f * f,
                                      length * f)) for f in [i / 6 for i in range(7)]]
                for f, ln in ((0.3, 0.4), (0.55, 0.38), (0.8, 0.3)):
                    o = base + Vector((sx * length * 0.45 * f, length * 0.25 * f * f,
                                       length * f))
                    tine = [o, o + Vector((sx * 0.1 * length, -ln * length * 0.9,
                                           ln * length * 0.5)),
                            o + Vector((sx * 0.12 * length, -ln * length, ln * length))]
                    rigid.append(tag(tube(tine, lambda t: sk * 0.09 * (1 - 0.8 * t), 8, hmat,
                                          smooth_path=1), 'Head'))
            rigid.append(tag(tube(pts, lambda t: sk * s.get('horn_r', 0.16) * (1 - 0.85 * t), 10,
                                  hmat, smooth_path=1), 'Head'))
    if s.get('snout_disc'):
        rigid.append(tag(lathe([(0, 0), (mz * 0.95, 0), (mz * 1.0, 0.012), (mz * 0.9, 0.03)], 24,
                               p['snout'] + p['hd'] * 0.005, (math.pi / 2 + 0.3, 0, 0),
                               M.skin('#d99a93', 'snout')), 'Head'))
    for extra in s.get('extras', lambda p, rig: [])(p, rig) if callable(s.get('extras')) else []:
        rigid.append(extra)
    for part in rigid:
        part.vertex_groups.new(name=part['bone']).add(range(len(part.data.vertices)), 1.0,
                                                      'REPLACE')
    mesh = join([body] + rigid, s.get('name', 'animal'))
    animate(rig, s)
    return rig, mesh


GAITS = {
    'walk': dict(phase={'HL': 0.0, 'FL': 0.25, 'HR': 0.5, 'FR': 0.75}, stance=0.64, stride=0.5,
                 lift=0.1, seconds=1.25, bob=0.012, pitch=0.01, flex=0.0),
    'trot': dict(phase={'FL': 0.0, 'HR': 0.0, 'FR': 0.5, 'HL': 0.5}, stance=0.45, stride=0.7,
                 lift=0.17, seconds=0.72, bob=0.03, pitch=0.012, flex=0.0),
    'gallop': dict(phase={'HL': 0.0, 'HR': 0.12, 'FL': 0.5, 'FR': 0.62}, stance=0.28,
                   stride=1.15, lift=0.24, seconds=0.56, bob=0.05, pitch=0.09, flex=0.16),
    'hop': dict(phase={'HL': 0.0, 'HR': 0.02, 'FL': 0.5, 'FR': 0.52}, stance=0.3, stride=0.9,
                lift=0.3, seconds=0.6, bob=0.12, pitch=0.2, flex=0.25),
}


def animate(rig, s):
    h = s['height']
    amp = s.get('gait_scale', 1.0)

    def tail(t, P, energy=1.0, lift=0.0):
        for i in range(1, 5):
            P.turn('Tail.%02d' % i, z=0.2 * energy * wave(t, -0.12 * i),
                   x=lift + 0.05 * energy * wave(t, 0.2 - 0.1 * i, 2))

    def ears(t, P, energy=1.0):
        flick = max(0, math.sin(math.tau * (t * 3 + 0.1))) ** 6
        P.turn('Ear.L', x=0.35 * flick * energy, z=0.1 * wave(t, 0.3))
        P.turn('Ear.R', x=0.3 * max(0, math.sin(math.tau * (t * 2 + 0.55))) ** 6 * energy,
               z=-0.1 * wave(t, 0.5))

    def gait(name):
        g = GAITS[name]

        def fn(t, P):
            for leg in LEGS:
                ph = (t + g['phase'][leg]) % 1.0
                st = g['stance']
                if ph < st:
                    u = ph / st
                    y, z, pitch = (-0.5 + u) * g['stride'], 0.0, 0.5 * max(0, (u - 0.8) * 5)
                    z = 0.04 * max(0, (u - 0.8) * 5)
                else:
                    u = (ph - st) / (1 - st)
                    y = (0.5 - ease(u)) * g['stride']
                    z = g['lift'] * math.sin(math.pi * u) ** 1.1
                    pitch = 0.9 * math.sin(math.pi * min(1, u * 1.4)) * (
                        1.0 if leg[0] == 'F' else 0.6) + 0.5 * (1 - u) ** 3
                sx = 1 if leg[1] == 'L' else -1
                P.move('ik.' + leg, 0, y * h * amp, z * h * amp)
                P.turn('ik.' + leg, x=pitch)
            beat = 2 if name in ('walk', 'trot') else 1
            bob = g['bob'] * h * math.cos(math.tau * (t * beat + 0.1))
            P.move('Hips', 0, 0, -0.02 * h - bob)
            pitch = g['pitch'] * math.sin(math.tau * (t * beat + 0.2))
            P.turn('Hips', x=pitch + (0.03 * wave(t, 0.1) if name == 'walk' else 0),
                   z=0.05 * wave(t) if name == 'walk' else 0, y=0.03 * wave(t, 0.1))
            flex = g['flex'] * math.sin(math.tau * (t + 0.15))
            for bone in ('Spine.01', 'Spine.02', 'Chest'):
                P.turn(bone, x=-flex * 0.6 - pitch * 0.4, z=-0.03 * wave(t) if name == 'walk'
                       else 0)
            nod = 0.07 * math.sin(math.tau * (t * beat + 0.45)) * (1 + 2 * g['flex'])
            P.turn('Neck.01', x=nod + flex * 0.5)
            P.turn('Neck.02', x=nod * 0.6)
            P.turn('Head', x=-nod * 1.3)
            tail(t, P, 1.0 + 3 * g['flex'], lift=0.5 * g['flex'] * 2 + (0.15 if name != 'walk'
                                                                        else 0))
            ears(t, P, 0.5)
        return fn

    def idle(t, P):
        breath = wave(t, 0, 2)
        P.scale('Spine.02', 1 + 0.018 * breath, 1, 1 + 0.018 * breath)
        P.scale('Chest', 1 + 0.012 * breath, 1, 1 + 0.012 * breath)
        P.move('Hips', 0.006 * h * wave(t), 0, -0.01 * h)
        look = 0.3 * math.sin(math.tau * t) * (0.5 + 0.5 * math.cos(math.tau * 2 * t))
        P.turn('Neck.01', z=look * 0.5, x=0.03 * breath)
        P.turn('Neck.02', z=look * 0.5)
        P.turn('Head', z=look * 0.6, x=0.04 * wave(t, 0.3))
        tail(t, P, 1.3)
        ears(t, P, 1.0)

    def forage(t, P):
        down = 0.5 + 0.5 * math.sin(math.tau * (t - 0.25))
        d = ease(min(1, down * 1.6))
        reach = s.get('forage', 1.0)
        chew = math.sin(math.tau * t * 9)
        P.move('Hips', 0, -0.02 * h * d, -0.015 * h * d)
        P.turn('Chest', x=0.12 * d * reach)
        P.turn('Neck.01', x=0.75 * d * reach, z=0.1 * d * wave(t, 0, 3))
        P.turn('Neck.02', x=0.6 * d * reach)
        P.turn('Head', x=0.25 * d * reach + 0.04 * chew * d)
        P.turn('Jaw', x=0.12 * max(0, chew) * d)
        P.move('ik.FL', 0, -0.06 * h * d, 0)
        P.move('ik.FR', 0, 0.05 * h * d, 0)
        tail(t, P, 1.0)
        ears(t, P, 0.8)

    clips = s.get('clips', ['walk', 'trot', 'gallop', 'idle', 'forage'])
    names = {'walk': 'Walk in Place', 'trot': 'Trot', 'gallop': 'Gallop', 'hop': 'Hop',
             'idle': 'Idle', 'forage': 'Forage'}
    for c in clips:
        if c == 'idle':
            rig.clip('Idle', 5.0, idle)
        elif c == 'forage':
            rig.clip('Forage', 4.5, forage)
        else:
            rig.clip(names[c], GAITS[c]['seconds'] * s.get('tempo', 1.0), gait(c))
    rig.finish()
