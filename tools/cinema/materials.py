"""Procedural PBR surfaces. Each returns a Blender material that core.bake_atlas can bake."""
from core import Mat, rgb


def _shade(c, k):
    return tuple(min(1.0, x * k) for x in rgb(c))


def skin(tone='#c98f6b', name='skin'):
    m = Mat(name)
    mottle = m.noise(9, 5, 0.6)
    fine = m.noise(160, 2, 0.5)
    pores = m.voronoi(520, out='Distance')
    col = m.ramp(mottle, [(0.3, _shade(tone, 0.86)), (0.55, tone), (0.8, _shade(tone, 1.08))])
    red = m.noise(3.5, 3, 0.5)
    col = m.mix(col, (rgb(tone)[0] * 1.05, rgb(tone)[1] * 0.74, rgb(tone)[2] * 0.7),
                m.ramp(red, [(0.5, 0.0), (0.8, 0.35)]))
    height = m.math('ADD', m.math('MULTIPLY', pores, 0.5), m.math('MULTIPLY', fine, 0.5))
    rough = m.ramp(mottle, [(0.2, 0.42), (0.8, 0.58)])
    return m.set(color=col, rough=rough, height=height, bump=0.12, bump_distance=0.002)


def cloth(color='#3b5b8c', name='cloth', weave=420, rough=0.86, wear=0.25, pattern=None,
          color2=None, pattern_scale=12):
    m = Mat(name)
    threads = m.math('MAXIMUM', m.noise(weave * 2.2, 2, 0.5, co=m.stretch(1, 1, 0.12)),
                     m.noise(weave * 2.2, 2, 0.5, co=m.stretch(0.12, 0.12, 1)))
    var = m.noise(4, 5, 0.6)
    col = m.ramp(var, [(0.25, _shade(color, 0.78)), (0.6, color), (0.9, _shade(color, 1.1))])
    if pattern == 'stripes':
        s = m.wave(pattern_scale, 0.0, 0, direction='Z')
        col = m.mix(col, color2 or _shade(color, 0.5), m.ramp(s, [(0.48, 0.0), (0.52, 1.0)]))
    elif pattern == 'check':
        a = m.ramp(m.wave(pattern_scale, 0, 0, direction='X'), [(0.48, 0.0), (0.52, 0.5)])
        b = m.ramp(m.wave(pattern_scale, 0, 0, direction='Z'), [(0.48, 0.0), (0.52, 0.5)])
        col = m.mix(col, color2 or _shade(color, 0.45), m.math('ADD', a, b))
    col = m.mix(col, _shade(color, 1.25), m.math('MULTIPLY', m.pointiness(0.5, 0.58), wear))
    folds = m.noise(7, 3, 0.5, 0.6)
    height = m.math('ADD', m.math('MULTIPLY', threads, 0.25), m.math('MULTIPLY', folds, 0.75))
    return m.set(color=col, rough=rough, height=height, bump=0.35, bump_distance=0.004)


def denim(color='#2f456f', name='denim'):
    m = Mat(name)
    twill = m.noise(900, 2, 0.5, co=m.stretch(1, 1, 0.2))
    var = m.noise(5, 6, 0.65)
    col = m.ramp(var, [(0.2, _shade(color, 0.7)), (0.55, color), (0.85, _shade(color, 1.25))])
    col = m.mix(col, _shade(color, 1.9), m.math('MULTIPLY', twill, 0.22))
    col = m.mix(col, _shade(color, 2.1), m.math('MULTIPLY', m.pointiness(0.5, 0.57), 0.5))
    return m.set(color=col, rough=0.82, height=twill, bump=0.3, bump_distance=0.002)


def leather(color='#4a2f20', name='leather', rough=0.5):
    m = Mat(name)
    cells = m.voronoi(260, 'DISTANCE_TO_EDGE')
    crease = m.ramp(cells, [(0.0, 0.0), (0.12, 1.0)])
    var = m.noise(6, 5, 0.6)
    col = m.ramp(var, [(0.25, _shade(color, 0.7)), (0.6, color), (0.9, _shade(color, 1.2))])
    col = m.mix(col, _shade(color, 1.6), m.math('MULTIPLY', m.pointiness(0.5, 0.57), 0.6))
    r = m.ramp(var, [(0.2, rough * 0.8), (0.8, rough * 1.25)])
    return m.set(color=col, rough=r, height=crease, bump=0.25, bump_distance=0.002)


def fur(color='#8a6241', color2=None, name='fur', scale=1.0, spots=None, spot_scale=3.0,
        rough=0.78):
    """Short coat: streaked strands, tonal variation and optional patches."""
    m = Mat(name)
    strands = m.noise(600 * scale, 3, 0.7, co=m.stretch(1, 1, 0.08))
    clumps = m.noise(40 * scale, 4, 0.6, co=m.stretch(1, 1, 0.3))
    var = m.noise(2.2, 5, 0.6)
    col = m.ramp(var, [(0.25, _shade(color, 0.72)), (0.55, color), (0.85, _shade(color, 1.18))])
    col = m.mix(col, _shade(color, 0.55), m.math('MULTIPLY', m.ramp(strands, [(0.35, 1.0),
                                                                              (0.6, 0.0)]), 0.5))
    if spots:
        patch = m.noise(spot_scale, 2, 0.4, 0.4)
        mask = m.ramp(patch, [(0.48, 0.0), (0.53, 1.0)])
        scol = m.ramp(var, [(0.25, _shade(spots, 0.8)), (0.8, spots)])
        col = m.mix(col, scol, mask)
    if color2:
        belly = m.ramp(m.geometry.outputs['Normal'], [(0.0, 1.0), (0.5, 0.0)])
        sep = m.up(-0.9, -0.2)
        col = m.mix(color2, col, sep)
    height = m.math('ADD', m.math('MULTIPLY', strands, 0.6), m.math('MULTIPLY', clumps, 0.4))
    return m.set(color=col, rough=rough, height=height, bump=0.5, bump_distance=0.004)


def wool(color='#e6dfd0', name='wool'):
    m = Mat(name)
    curls = m.voronoi(140, 'F1')
    lumps = m.noise(18, 4, 0.6)
    var = m.noise(3, 4, 0.6)
    col = m.ramp(var, [(0.2, _shade(color, 0.75)), (0.8, color)])
    col = m.mix(col, _shade(color, 0.6), m.ramp(curls, [(0.0, 0.6), (0.3, 0.0)]))
    height = m.math('ADD', m.math('MULTIPLY', curls, 0.6), m.math('MULTIPLY', lumps, 0.6))
    return m.set(color=col, rough=0.95, height=height, bump=0.9, bump_distance=0.01)


def feathers(color='#b9b4aa', color2=None, name='feathers', scale=1.0):
    m = Mat(name)
    rows = m.voronoi(90 * scale, 'F1', co=m.stretch(1, 0.45, 1))
    barbs = m.wave(900 * scale, 1.5, 2, direction='DIAGONAL')
    var = m.noise(5, 4, 0.6)
    col = m.ramp(var, [(0.2, _shade(color, 0.75)), (0.6, color), (0.9, _shade(color, 1.15))])
    if color2:
        col = m.mix(col, color2, m.ramp(m.noise(2.5, 2, 0.5), [(0.45, 0.0), (0.6, 1.0)]))
    col = m.mix(col, _shade(color, 0.5), m.ramp(rows, [(0.0, 0.55), (0.25, 0.0)]))
    height = m.math('ADD', m.math('MULTIPLY', rows, 0.8), m.math('MULTIPLY', barbs, 0.2))
    return m.set(color=col, rough=0.62, height=height, bump=0.6, bump_distance=0.004)


def scales(color='#5c7f3e', color2='#a3703a', name='scales', scale=1.0):
    m = Mat(name)
    cells = m.voronoi(70 * scale, 'DISTANCE_TO_EDGE')
    cid = m.voronoi(70 * scale, 'F1', out='Color')
    big = m.noise(1.6, 4, 0.6, 0.5)
    col = m.ramp(big, [(0.3, color), (0.7, color2)])
    col = m.mix(col, cid, 0.08, 'OVERLAY')
    col = m.mix(_shade(color, 0.35), col, m.ramp(cells, [(0.0, 0.0), (0.12, 1.0)]))
    rough = m.ramp(cells, [(0.0, 0.8), (0.2, 0.45)])
    return m.set(color=col, rough=rough, height=m.ramp(cells, [(0.0, 0.0), (0.25, 1.0)]),
                 bump=0.7, bump_distance=0.006)


def horn(color='#d9cdb4', name='horn'):
    m = Mat(name)
    rings = m.wave(60, 3.0, 2, direction='Z')
    col = m.ramp(rings, [(0.2, _shade(color, 0.6)), (0.8, color)])
    return m.set(color=col, rough=0.42, height=rings, bump=0.2)


def eye(iris='#4a3320', name='eye'):
    m = Mat(name, coords='Generated')
    return m.set(color=iris, rough=0.08)


def metal(color='#8c9aa3', name='metal', rough=0.35, scratches=0.5, rust=0.0, metal=1.0):
    m = Mat(name)
    scr = m.noise(180, 3, 0.6, co=m.stretch(1, 14, 1))
    scr2 = m.noise(140, 3, 0.6, co=m.stretch(12, 1, 1))
    grime = m.noise(3.5, 6, 0.65)
    col = m.ramp(grime, [(0.25, _shade(color, 0.72)), (0.6, color), (0.9, _shade(color, 1.1))])
    r = m.math('ADD', m.ramp(grime, [(0.2, rough * 0.7), (0.9, rough * 1.5)]),
               m.math('MULTIPLY', m.math('MAXIMUM', scr, scr2), 0.12 * scratches))
    met = metal
    if rust:
        mask = m.ramp(m.math('ADD', m.noise(5, 7, 0.7), m.math('MULTIPLY', m.pointiness(0.5, 0.6),
                                                               0.2)),
                      [(1.02 - rust, 0.0), (1.12 - rust, 1.0)])
        rc = m.ramp(m.noise(40, 5, 0.7), [(0.3, '#3d1c0e'), (0.6, '#7a3c18'), (0.8, '#a55a26')])
        col = m.mix(col, rc, mask)
        r = m.mix(r, 0.9, mask)
        met = m.math('SUBTRACT', metal, mask, clamp=True)
    height = m.math('MULTIPLY', m.math('MAXIMUM', scr, scr2), scratches)
    return m.set(color=col, rough=r, metal=met, height=height, bump=0.06, bump_distance=0.001)


def paint(color='#b6282c', name='paint', rough=0.22, wear=0.35, dirt=0.3, metal=0.0):
    """Painted metal with chipped edges and dust in the hollows."""
    m = Mat(name)
    grime = m.noise(3, 6, 0.65)
    chips = m.math('MULTIPLY', m.pointiness(0.56, 0.68),
                   m.ramp(m.noise(55, 4, 0.7), [(0.5, 0.0), (0.65, 1.0)]))
    chips = m.math('MULTIPLY', chips, wear * 2.2, clamp=True)
    col = m.ramp(grime, [(0.2, _shade(color, 0.8)), (0.7, color)])
    hollow = m.ramp(m.geometry.outputs['Pointiness'], [(0.4, 1.0), (0.5, 0.0)])
    dust = m.math('MULTIPLY', m.math('ADD', hollow, m.ramp(grime, [(0.55, 0.0), (0.9, 0.5)])),
                  dirt, clamp=True)
    col = m.mix(col, '#4a4034', dust)
    col = m.mix(col, '#8d9499', chips)
    r = m.mix(m.ramp(grime, [(0.2, rough), (0.9, rough + 0.2)]), 0.8, dust)
    r = m.mix(r, 0.4, chips)
    met = m.math('MAXIMUM', chips, metal)
    return m.set(color=col, rough=r, metal=met, height=m.math('SUBTRACT', 1.0, chips), bump=0.08,
                 bump_distance=0.001)


def chrome(name='chrome', color='#e3e6e8', rough=0.08):
    m = Mat(name)
    smudge = m.noise(8, 5, 0.6)
    return m.set(color=color, rough=m.ramp(smudge, [(0.3, rough), (0.9, rough + 0.14)]),
                 metal=1.0)


def gold(name='gold', rough=0.18):
    return metal('#ffc35a', name, rough, 0.3)


def brass(name='brass', rough=0.28):
    return metal('#c9a04a', name, rough, 0.5)


def rubber(name='rubber', color='#131416', tread=0.0):
    m = Mat(name)
    grain = m.noise(220, 3, 0.6)
    dust = m.noise(4, 5, 0.6)
    col = m.ramp(dust, [(0.3, color), (0.9, _shade(color, 2.4))])
    height = grain
    if tread:
        height = m.math('ADD', m.math('MULTIPLY', m.wave(tread, 0.0, 0, direction='DIAGONAL'), 1.0),
                        m.math('MULTIPLY', grain, 0.1))
    return m.set(color=col, rough=0.88, height=height, bump=0.5 if tread else 0.15,
                 bump_distance=0.004)


def plastic(color='#22262b', name='plastic', rough=0.4):
    m = Mat(name)
    grain = m.noise(380, 2, 0.5)
    smudge = m.noise(6, 4, 0.6)
    col = m.ramp(smudge, [(0.2, _shade(color, 0.85)), (0.8, color)])
    return m.set(color=col, rough=m.ramp(smudge, [(0.2, rough * 0.8), (0.9, rough * 1.3)]),
                 height=grain, bump=0.05, bump_distance=0.001)


def glass(name='glass', color='#9fc4cf', alpha=0.28, rough=0.04):
    m = Mat(name)
    return m.set(color=color, rough=rough, alpha=alpha, metal=0.0)


def wood(color='#8a5a34', name='wood', planks=0.0, rough=0.6, grain=1.0, axis='Z', age=0.3):
    m = Mat(name)
    st = {'Z': (9, 9, 1), 'X': (1, 9, 9), 'Y': (9, 1, 9)}[axis]
    co = m.stretch(*st)
    rings = m.wave(3.2 * grain, 6.0, 3, kind='RINGS', direction=axis, co=co, detail_scale=1.4)
    fibre = m.noise(60 * grain, 4, 0.7, co=co)
    var = m.noise(2.5, 4, 0.6)
    col = m.ramp(rings, [(0.0, _shade(color, 0.62)), (0.5, color), (1.0, _shade(color, 1.22))])
    col = m.mix(col, _shade(color, 0.5), m.math('MULTIPLY', m.ramp(fibre, [(0.4, 0.8), (0.6, 0.0)]),
                                                0.45))
    col = m.mix(col, '#7b766c', m.math('MULTIPLY', m.ramp(var, [(0.4, 0.0), (0.9, 1.0)]), age))
    height = m.math('ADD', m.math('MULTIPLY', rings, 0.3), m.math('MULTIPLY', fibre, 0.7))
    if planks:
        across = {'Z': ('X', 'Y'), 'X': ('Y', 'Z'), 'Y': ('X', 'Z')}[axis]
        u = m.math('DIVIDE', m.math('ADD', m.axis(across[0]), m.axis(across[1])), planks)
        frac = m.math('FRACT', u)
        gap = m.ramp(frac, [(0.0, 1.0), (0.035, 0.0), (0.965, 0.0), (1.0, 1.0)])
        tone = m.noise(0.31, 0, 0.5, co=__import__('core').N(
            m.nt, 'CombineXYZ', {'X': m.math('FLOOR', u), 'Y': 0.0, 'Z': 0.0}).outputs[0])
        col = m.mix(col, _shade(color, 0.72), m.ramp(tone, [(0.35, 0.0), (0.65, 0.6)]))
        col = m.mix(col, '#1c120c', gap)
        height = m.math('SUBTRACT', height, m.math('MULTIPLY', gap, 3.0))
    r = m.ramp(fibre, [(0.2, rough * 0.85), (0.9, rough * 1.2)])
    return m.set(color=col, rough=r, height=height, bump=0.35, bump_distance=0.004)


def bark(color='#4d3a2a', name='bark', scale=1.0):
    m = Mat(name)
    co = m.stretch(1, 1, 0.22)
    ridges = m.voronoi(26 * scale, 'DISTANCE_TO_EDGE', co=co)
    plates = m.ramp(ridges, [(0.0, 0.0), (0.18, 1.0)])
    fine = m.noise(120 * scale, 5, 0.7, co=co)
    var = m.noise(3, 5, 0.6)
    col = m.ramp(var, [(0.2, _shade(color, 0.7)), (0.6, color), (0.9, _shade(color, 1.3))])
    col = m.mix(_shade(color, 0.3), col, plates)
    moss = m.math('MULTIPLY', m.ramp(m.noise(4, 5, 0.7), [(0.55, 0.0), (0.75, 1.0)]), 0.5)
    col = m.mix(col, '#5d6b2c', moss)
    height = m.math('ADD', plates, m.math('MULTIPLY', fine, 0.35))
    return m.set(color=col, rough=0.9, height=height, bump=0.9, bump_distance=0.02)


def leaf(color='#3f7a2f', name='leaf', color2=None):
    m = Mat(name)
    var = m.noise(5, 4, 0.6)
    veins = m.voronoi(160, 'DISTANCE_TO_EDGE')
    col = m.ramp(var, [(0.2, _shade(color, 0.6)), (0.55, color),
                       (0.9, color2 or _shade(color, 1.45))])
    col = m.mix(col, _shade(color, 1.5), m.ramp(veins, [(0.0, 0.5), (0.06, 0.0)]))
    return m.set(color=col, rough=m.ramp(var, [(0.2, 0.35), (0.8, 0.6)]),
                 height=m.ramp(veins, [(0.0, 0.0), (0.1, 1.0)]), bump=0.3, bump_distance=0.002)


def petal(color='#f0b429', name='petal', color2=None):
    m = Mat(name)
    streak = m.noise(90, 3, 0.6, co=m.stretch(6, 6, 0.4))
    var = m.noise(6, 3, 0.5)
    col = m.ramp(var, [(0.2, color2 or _shade(color, 0.8)), (0.7, color)])
    col = m.mix(col, _shade(color, 0.7), m.math('MULTIPLY', streak, 0.3))
    return m.set(color=col, rough=0.55, height=streak, bump=0.15, bump_distance=0.002)


def rock(color='#77706a', name='rock', scale=1.0, color2=None, strata=0.0, moss=0.0, snow=0.0,
         rough=0.88):
    m = Mat(name)
    big = m.noise(1.4 * scale, 8, 0.65, 0.3)
    cracks = m.voronoi(5 * scale, 'DISTANCE_TO_EDGE')
    crack = m.ramp(cracks, [(0.0, 1.0), (0.05, 0.0)])
    grain = m.noise(90 * scale, 6, 0.75)
    col = m.ramp(big, [(0.25, _shade(color, 0.6)), (0.5, color),
                       (0.8, color2 or _shade(color, 1.3))])
    col = m.mix(col, _shade(color, 1.35), m.math('MULTIPLY', m.ramp(grain, [(0.5, 0.0),
                                                                           (0.8, 1.0)]), 0.4))
    if strata:
        bands = m.wave(strata, 2.5, 4, direction='Z', detail_scale=2.0)
        col = m.mix(col, _shade(color2 or color, 0.7), m.math('MULTIPLY', bands, 0.5))
    col = m.mix(col, _shade(color, 0.25), crack)
    r = rough
    if moss:
        mask = m.math('MULTIPLY', m.up(0.2, 0.75), m.ramp(m.noise(3 * scale, 6, 0.7),
                                                          [(0.62 - moss * 0.35, 0.0),
                                                           (0.72 - moss * 0.35, 1.0)]))
        mc = m.ramp(m.noise(60, 4, 0.7), [(0.3, '#2c3d17'), (0.7, '#5f7a2a')])
        col = m.mix(col, mc, mask)
    if snow:
        mask = m.math('MULTIPLY', m.up(0.35, 0.7), m.ramp(big, [(0.7 - snow * 0.6, 0.0),
                                                                (0.85 - snow * 0.6, 1.0)]))
        col = m.mix(col, '#eef3f7', mask)
        r = m.mix(rough, 0.55, mask)
    height = m.math('SUBTRACT', m.math('ADD', m.math('MULTIPLY', big, 0.6),
                                       m.math('MULTIPLY', grain, 0.25)), crack)
    return m.set(color=col, rough=r, height=height, bump=0.8, bump_distance=0.03 / scale)


def sand(color='#d3b27a', name='sand', ripples=18.0, wet=0.0):
    m = Mat(name)
    grain = m.noise(700, 2, 0.8)
    rip = m.wave(ripples, 3.0, 2, direction='X', detail_scale=0.6)
    var = m.noise(1.5, 5, 0.6)
    col = m.ramp(var, [(0.2, _shade(color, 0.8)), (0.8, _shade(color, 1.1))])
    col = m.mix(col, _shade(color, 0.72), m.math('MULTIPLY', grain, 0.3))
    height = m.math('ADD', m.math('MULTIPLY', rip, 0.8), m.math('MULTIPLY', grain, 0.2))
    return m.set(color=col, rough=0.92 - wet * 0.5, height=height, bump=0.5, bump_distance=0.01)


def soil(color='#5a4330', name='soil', grass=0.0, grass_color='#4c7a2b'):
    m = Mat(name)
    lumps = m.noise(14, 7, 0.75)
    pebbles = m.voronoi(60, 'F1')
    var = m.noise(1.8, 5, 0.6)
    col = m.ramp(var, [(0.2, _shade(color, 0.6)), (0.8, _shade(color, 1.2))])
    col = m.mix(col, '#8a8378', m.ramp(pebbles, [(0.0, 0.7), (0.12, 0.0)]))
    height = m.math('ADD', lumps, m.ramp(pebbles, [(0.0, 0.6), (0.2, 0.0)]))
    rough = 0.95
    if grass:
        blades = m.noise(260, 3, 0.8, co=m.stretch(1, 1, 0.15))
        mask = m.math('MULTIPLY', m.up(0.5, 0.85), m.ramp(m.noise(2.2, 5, 0.6),
                                                          [(0.6 - grass * 0.45, 0.0),
                                                           (0.75 - grass * 0.45, 1.0)]))
        gc = m.ramp(blades, [(0.2, _shade(grass_color, 0.45)), (0.6, grass_color),
                             (0.9, _shade(grass_color, 1.5))])
        col = m.mix(col, gc, mask)
        height = m.mix(height, m.math('ADD', blades, 0.6), mask)
    return m.set(color=col, rough=rough, height=height, bump=0.7, bump_distance=0.02)


def snow(name='snow', color='#eef3f8'):
    m = Mat(name)
    drift = m.noise(3, 5, 0.6)
    sparkle = m.voronoi(900, 'F1')
    col = m.ramp(drift, [(0.2, '#cfdcea'), (0.8, color)])
    return m.set(color=col, rough=m.ramp(sparkle, [(0.0, 0.25), (0.08, 0.6)]),
                 height=m.math('ADD', drift, m.math('MULTIPLY', m.noise(60, 4, 0.6), 0.15)),
                 bump=0.4, bump_distance=0.02)


def concrete(color='#8d8c88', name='concrete', panels=0.0):
    m = Mat(name)
    stains = m.noise(2.2, 7, 0.7, 0.4)
    pits = m.voronoi(240, 'F1')
    grain = m.noise(300, 3, 0.7)
    col = m.ramp(stains, [(0.2, _shade(color, 0.6)), (0.55, color), (0.9, _shade(color, 1.15))])
    streak = m.noise(8, 4, 0.7, co=m.stretch(6, 6, 0.25))
    col = m.mix(col, _shade(color, 0.5), m.math('MULTIPLY', m.ramp(streak, [(0.55, 0.0),
                                                                           (0.8, 1.0)]), 0.5))
    height = m.math('SUBTRACT', grain, m.ramp(pits, [(0.0, 1.0), (0.06, 0.0)]))
    if panels:
        _, gap = m.brick(1 / panels, 0.008, 1.0, 0.5)
        col = m.mix(col, _shade(color, 0.35), gap)
        height = m.math('SUBTRACT', height, m.math('MULTIPLY', gap, 2.0))
    return m.set(color=col, rough=0.9, height=height, bump=0.3, bump_distance=0.004)


def bricks(color='#8c4a34', name='bricks', scale=4.5, mortar='#b9b2a4'):
    m = Mat(name)
    wall = m.math('ADD', m.axis('X'), m.axis('Y'))
    comb = __import__('core').N(m.nt, 'CombineXYZ', {'X': wall, 'Y': m.axis('Z'), 'Z': 0.0})
    bc, gap = m.brick(scale, 0.022, 0.5, 0.22, co=comb.outputs[0])
    var = m.noise(3, 6, 0.7)
    grain = m.noise(180, 4, 0.7)
    col = m.ramp(var, [(0.2, _shade(color, 0.7)), (0.6, color), (0.9, _shade(color, 1.2))])
    col = m.mix(col, _shade(color, 0.6), m.math('SUBTRACT', 1.0, bc))
    col = m.mix(col, mortar, gap)
    height = m.math('SUBTRACT', m.math('MULTIPLY', grain, 0.3), m.math('MULTIPLY', gap, 1.5))
    return m.set(color=col, rough=0.9, height=height, bump=0.8, bump_distance=0.008)


def stonework(color='#8f887c', name='stonework', scale=3.0, mortar='#5d574d'):
    m = Mat(name)
    edge = m.voronoi(scale, 'DISTANCE_TO_EDGE')
    cid = m.voronoi(scale, 'F1', out='Color')
    gap = m.ramp(edge, [(0.0, 1.0), (0.05, 0.0)])
    grain = m.noise(110, 6, 0.75)
    col = m.ramp(grain, [(0.2, _shade(color, 0.7)), (0.8, _shade(color, 1.15))])
    col = m.mix(col, cid, 0.12, 'OVERLAY')
    col = m.mix(col, mortar, gap)
    moss = m.math('MULTIPLY', m.ramp(m.noise(3, 5, 0.7), [(0.6, 0.0), (0.8, 0.7)]), gap)
    col = m.mix(col, '#4c5c22', moss)
    height = m.math('ADD', m.ramp(edge, [(0.0, 0.0), (0.12, 1.0)]),
                    m.math('MULTIPLY', grain, 0.25))
    return m.set(color=col, rough=0.9, height=height, bump=1.0, bump_distance=0.02)


def plaster(color='#e4dccb', name='plaster', dirt=0.35):
    m = Mat(name)
    trowel = m.noise(22, 5, 0.6, 0.6)
    stain = m.noise(1.6, 6, 0.7, co=m.stretch(3, 3, 0.5))
    col = m.ramp(stain, [(0.25, _shade(color, 1 - dirt * 0.7)), (0.7, color)])
    return m.set(color=col, rough=0.88, height=trowel, bump=0.25, bump_distance=0.004)


def roof_tiles(color='#a1492d', name='roof'):
    m = Mat(name)
    rows = m.wave(22, 0.0, 0, direction='Z')
    cols = m.wave(30, 0.0, 0, direction='X')
    var = m.noise(4, 6, 0.7)
    col = m.ramp(var, [(0.2, _shade(color, 0.6)), (0.6, color), (0.9, _shade(color, 1.25))])
    col = m.mix(col, _shade(color, 0.45), m.ramp(rows, [(0.0, 0.8), (0.2, 0.0)]))
    lichen = m.ramp(m.noise(9, 5, 0.7), [(0.66, 0.0), (0.75, 0.8)])
    col = m.mix(col, '#9aa27c', lichen)
    height = m.math('ADD', rows, m.math('MULTIPLY', cols, 0.5))
    return m.set(color=col, rough=0.82, height=height, bump=0.8, bump_distance=0.015)


def water(name='water', color='#1d5e7a', alpha=0.82, rough=0.06):
    m = Mat(name)
    return m.set(color=color, rough=rough, alpha=alpha)


def emissive(color='#ffd27a', name='glow', strength=4.0, base=None):
    m = Mat(name)
    return m.set(color=base or color, rough=0.4, emission=color, emission_strength=strength)


def lava(name='lava'):
    m = Mat(name)
    crust = m.voronoi(5, 'DISTANCE_TO_EDGE')
    flow = m.noise(3, 6, 0.7, 1.2)
    hot = m.math('MULTIPLY', m.ramp(crust, [(0.0, 1.0), (0.18, 0.0)]),
                 m.ramp(flow, [(0.3, 0.3), (0.7, 1.0)]))
    col = m.ramp(crust, [(0.0, '#2a0d06'), (0.3, '#17110f')])
    glow = m.ramp(hot, [(0.0, '#000000'), (0.3, '#c21d02'), (0.7, '#ff7a12'), (1.0, '#ffe08a')])
    return m.set(color=col, rough=0.85, height=m.ramp(crust, [(0.0, 0.0), (0.2, 1.0)]),
                 bump=1.0, bump_distance=0.03, emission=glow, emission_strength=6.0)


def screen(color='#3fb6ff', name='screen', lines=160, strength=2.5):
    m = Mat(name)
    scan = m.wave(lines, 0.0, 0, direction='Z')
    blocks, _ = m.brick(14, 0.06, 0.5, 0.2)
    panel = m.ramp(m.noise(7, 2, 0.4), [(0.4, 0.15), (0.7, 1.0)])
    glow = m.mix('#000000', color, m.math('MULTIPLY', m.math('MULTIPLY', panel, blocks),
                                          m.ramp(scan, [(0.0, 0.7), (1.0, 1.0)])))
    return m.set(color='#05070a', rough=0.15, emission=glow, emission_strength=strength)


def paper(color='#ece5d3', name='paper'):
    m = Mat(name)
    fibre = m.noise(260, 4, 0.7)
    var = m.noise(4, 4, 0.6)
    col = m.ramp(var, [(0.2, _shade(color, 0.86)), (0.8, color)])
    return m.set(color=col, rough=0.9, height=fibre, bump=0.1, bump_distance=0.001)


def planet(stops, name='planet', scale=2.0, bands=0.0, distortion=1.0, rough=0.85, bump=0.4,
           craters=0.0):
    m = Mat(name)
    base = m.noise(scale, 9, 0.65, distortion)
    fac = base
    if bands:
        warp = m.noise(1.5, 5, 0.6, 0.5, color=True)
        mapping = __import__('core').N(m.nt, 'Mapping', {'Vector': m.mix(m.co, warp, 0.06),
                                                        'Scale': (0.02, 0.02, 1)})
        fac = m.math('ADD', m.math('MULTIPLY', m.wave(bands, 1.2, 4, direction='Z',
                                                      co=mapping.outputs[0]), 0.75),
                     m.math('MULTIPLY', base, 0.3))
    col = m.ramp(fac, stops)
    height = base
    if craters:
        rim = m.voronoi(craters, 'F1')
        height = m.math('ADD', base, m.ramp(rim, [(0.0, -1.0), (0.3, 0.3), (0.42, 0.0)]))
        col = m.mix(col, '#000000', m.ramp(rim, [(0.0, 0.25), (0.3, 0.0)]))
    return m.set(color=col, rough=rough, height=height, bump=bump, bump_distance=0.05)


# ----------------------------------------------------------------------------- otherworldly
def alien_skin(color='#1b2a3a', color2='#3a1b4a', glow='#35ffd0', name='alien', scale=1.0,
               veins=1.0, strength=4.0, rough=0.35):
    """Wet, cell-patterned hide whose seams carry light."""
    m = Mat(name)
    edge = m.voronoi(9 * scale, 'DISTANCE_TO_EDGE')
    cid = m.voronoi(9 * scale, 'F1', out='Color')
    big = m.noise(1.3 * scale, 6, 0.6, 0.8)
    col = m.ramp(big, [(0.3, color), (0.55, color2), (0.8, _shade(color, 1.6))])
    col = m.mix(col, cid, 0.12, 'OVERLAY')
    col = m.mix(_shade(color, 0.3), col, m.ramp(edge, [(0.0, 0.0), (0.1, 1.0)]))
    pulse = m.ramp(m.noise(2.2 * scale, 4, 0.6), [(0.42, 0.0), (0.62, 1.0)])
    light = m.math('MULTIPLY', m.ramp(edge, [(0.0, 1.0), (0.035, 0.0)]), pulse)
    light = m.math('MULTIPLY', light, veins, clamp=True)
    em = m.mix('#000000', glow, light)
    r = m.ramp(edge, [(0.0, rough + 0.3), (0.2, rough)])
    return m.set(color=col, rough=r, height=m.ramp(edge, [(0.0, 0.0), (0.2, 1.0)]), bump=0.8,
                 bump_distance=0.03 / scale, emission=em, emission_strength=strength)


def chitin(color='#141018', color2='#2a4a5a', glow=None, name='chitin', scale=1.0):
    m = Mat(name)
    ridges = m.wave(14 * scale, 4.0, 3, direction='Y', detail_scale=1.5)
    pits = m.voronoi(70 * scale, 'F1')
    sheen = m.noise(2.5 * scale, 5, 0.6, 1.5)
    col = m.ramp(sheen, [(0.3, color), (0.6, color2), (0.85, _shade(color2, 1.8))])
    col = m.mix(col, _shade(color, 0.4), m.ramp(ridges, [(0.0, 0.7), (0.3, 0.0)]))
    height = m.math('SUBTRACT', ridges, m.ramp(pits, [(0.0, 0.5), (0.08, 0.0)]))
    kw = {}
    if glow:
        spots = m.ramp(m.voronoi(16 * scale, 'F1'), [(0.0, 1.0), (0.12, 0.0)])
        kw = dict(emission=m.mix('#000000', glow, m.math('MULTIPLY', spots, m.ramp(
            sheen, [(0.45, 0.0), (0.6, 1.0)]))), emission_strength=5.0)
    return m.set(color=col, rough=m.ramp(sheen, [(0.2, 0.18), (0.9, 0.4)]), metal=0.35,
                 height=height, bump=0.5, bump_distance=0.02 / scale, **kw)


def biolum(color='#0a1622', glow='#4dffe1', name='biolum', scale=1.0, strength=6.0, density=14,
           stripes=False):
    m = Mat(name)
    var = m.noise(3 * scale, 5, 0.6)
    col = m.ramp(var, [(0.2, _shade(color, 0.6)), (0.8, _shade(color, 1.8))])
    if stripes:
        light = m.ramp(m.wave(density * scale, 3.0, 2, direction='Z'), [(0.85, 0.0), (0.97, 1.0)])
    else:
        light = m.ramp(m.voronoi(density * scale, 'F1'), [(0.0, 1.0), (0.14, 0.0)])
    light = m.math('MULTIPLY', light, m.ramp(var, [(0.35, 0.2), (0.7, 1.0)]))
    return m.set(color=col, rough=0.3, height=var, bump=0.3, bump_distance=0.02,
                 emission=m.mix('#000000', glow, light), emission_strength=strength)


def crystal(color='#7a4dff', glow='#c9a6ff', name='crystal', strength=3.0):
    m = Mat(name)
    facets = m.voronoi(6, 'F1', out='Color')
    inner = m.noise(4, 4, 0.6, 1.0)
    col = m.mix(color, facets, 0.25, 'OVERLAY')
    em = m.mix(_shade(color, 0.25), glow, m.ramp(inner, [(0.35, 0.0), (0.75, 1.0)]))
    return m.set(color=col, rough=0.12, metal=0.1, emission=em, emission_strength=strength)


def void_skin(glow='#9fb4ff', name='void', scale=1.0, strength=5.0):
    """Blacker than its shadow, with a slow nebula and pinprick stars inside."""
    m = Mat(name)
    stars = m.ramp(m.voronoi(120 * scale, 'F1'), [(0.0, 1.0), (0.05, 0.0)])
    neb = m.ramp(m.noise(1.6 * scale, 7, 0.7, 2.0), [(0.5, 0.0), (0.8, 0.5)])
    em = m.mix(m.mix('#000000', '#5a2a9a', neb), glow, stars)
    return m.set(color='#030305', rough=0.55, emission=em, emission_strength=strength)


def flesh(color='#8a2f3a', name='flesh', glow=None):
    m = Mat(name)
    veins = m.voronoi(22, 'DISTANCE_TO_EDGE')
    var = m.noise(5, 5, 0.6, 0.8)
    col = m.ramp(var, [(0.2, _shade(color, 0.55)), (0.6, color), (0.9, _shade(color, 1.5))])
    col = m.mix(col, '#2a0a14', m.ramp(veins, [(0.0, 0.8), (0.05, 0.0)]))
    kw = dict(emission=m.mix('#000000', glow, m.ramp(veins, [(0.0, 1.0), (0.03, 0.0)])),
              emission_strength=3.0) if glow else {}
    return m.set(color=col, rough=m.ramp(var, [(0.2, 0.15), (0.9, 0.4)]),
                 height=m.ramp(veins, [(0.0, 0.0), (0.1, 1.0)]), bump=0.5, bump_distance=0.02,
                 **kw)


def cap(color='#d9477a', color2='#ffd9a6', glow=None, name='cap'):
    """A mushroom or coral surface: dots on a soft gradient, gills of light."""
    m = Mat(name)
    dots = m.ramp(m.voronoi(11, 'F1'), [(0.0, 1.0), (0.22, 0.0)])
    var = m.noise(2, 4, 0.6)
    col = m.ramp(var, [(0.2, _shade(color, 0.7)), (0.8, color)])
    col = m.mix(col, color2, dots)
    kw = dict(emission=m.mix('#000000', glow, dots), emission_strength=4.0) if glow else {}
    return m.set(color=col, rough=0.45, height=dots, bump=0.4, bump_distance=0.03, **kw)


# ----------------------------------------------------------------------------- spacecraft
def foil(color='#e2a93b', name='foil', rough=0.28):
    """Crinkled insulation blanket."""
    m = Mat(name)
    crease = m.voronoi(38, 'DISTANCE_TO_EDGE')
    fold = m.noise(14, 4, 0.7, 1.5)
    col = m.ramp(fold, [(0.25, _shade(color, 0.6)), (0.6, color), (0.9, _shade(color, 1.35))])
    height = m.math('ADD', m.ramp(crease, [(0.0, 0.0), (0.2, 1.0)]), fold)
    return m.set(color=col, rough=m.ramp(fold, [(0.2, rough), (0.9, rough + 0.2)]), metal=1.0,
                 height=height, bump=0.9, bump_distance=0.02)


def solar(name='solar', color='#122a5c', scale=7.0):
    """Photovoltaic cells: a blue grid with bright busbars."""
    m = Mat(name)
    comb = __import__('core').N(m.nt, 'CombineXYZ', {'X': m.math('ADD', m.axis('X'), m.axis('Y')),
                                                    'Y': m.axis('Z'), 'Z': 0.0})
    cell, gap = m.brick(scale, 0.03, 0.5, 0.5, co=comb.outputs[0], offset=0.0)
    var = m.noise(30, 2, 0.5)
    col = m.ramp(var, [(0.3, _shade(color, 0.7)), (0.8, _shade(color, 1.5))])
    col = m.mix(col, '#c9ced6', gap)
    return m.set(color=col, rough=m.mix(0.18, 0.4, gap), metal=m.mix(0.6, 1.0, gap),
                 height=m.math('SUBTRACT', 1.0, gap), bump=0.15, bump_distance=0.005)


def hull(color='#e8e7e2', name='hull', panels=0.6, wear=0.3):
    """Painted spacecraft skin with panel lines and rivets."""
    m = Mat(name)
    comb = __import__('core').N(m.nt, 'CombineXYZ', {'X': m.math('ADD', m.axis('X'), m.axis('Y')),
                                                    'Y': m.axis('Z'), 'Z': 0.0})
    tone, gap = m.brick(1 / panels, 0.012, 0.5, 0.5, co=comb.outputs[0])
    grime = m.noise(2.5, 6, 0.65)
    streak = m.noise(9, 4, 0.7, co=m.stretch(5, 5, 0.3))
    col = m.ramp(grime, [(0.2, _shade(color, 0.82)), (0.7, color)])
    col = m.mix(col, _shade(color, 0.9), m.math('SUBTRACT', 1.0, tone))
    col = m.mix(col, _shade(color, 0.55), m.math('MULTIPLY', m.ramp(streak, [(0.55, 0.0),
                                                                           (0.85, 1.0)]), wear))
    col = m.mix(col, _shade(color, 0.3), gap)
    return m.set(color=col, rough=m.ramp(grime, [(0.2, 0.3), (0.9, 0.55)]), metal=0.15,
                 height=m.math('SUBTRACT', 1.0, gap), bump=0.25, bump_distance=0.006)


# ----------------------------------------------------------------------------- melting ones
def melt_skin(color='#3f8f9a', blush='#b889b5', deep='#34508a', name='melt', glow=None,
              rough=0.3):
    """Wet, marbled skin: one colour bleeding into two others."""
    m = Mat(name)
    marble = m.noise(2.6, 7, 0.62, 2.2)
    blotch = m.noise(5.5, 4, 0.6, 0.8)
    veins = m.voronoi(26, 'DISTANCE_TO_EDGE')
    col = m.ramp(marble, [(0.28, deep), (0.48, color), (0.7, _shade(color, 1.25))])
    col = m.mix(col, blush, m.ramp(blotch, [(0.55, 0.0), (0.78, 0.75)]))
    col = m.mix(col, deep, m.math('MULTIPLY', m.ramp(veins, [(0.0, 0.5), (0.04, 0.0)]),
                                  m.ramp(marble, [(0.4, 0.0), (0.7, 1.0)])))
    pores = m.voronoi(420, 'F1')
    kw = {}
    if glow:
        kw = dict(emission=m.mix('#000000', glow, m.ramp(veins, [(0.0, 1.0), (0.03, 0.0)])),
                  emission_strength=5.0)
    return m.set(color=col, rough=m.ramp(blotch, [(0.2, rough * 0.6), (0.9, rough * 1.4)]),
                 height=m.math('ADD', m.math('MULTIPLY', pores, 0.3), m.ramp(
                     veins, [(0.0, 0.0), (0.08, 1.0)])), bump=0.25, bump_distance=0.004, **kw)


def bloodshot(name='bloodshot', white='#e9dcd6', vein='#b23a3a'):
    m = Mat(name)
    veins = m.voronoi(34, 'DISTANCE_TO_EDGE', co=m.stretch(1, 1, 1))
    web = m.math('MULTIPLY', m.ramp(veins, [(0.0, 1.0), (0.02, 0.0)]),
                 m.ramp(m.noise(9, 3, 0.6), [(0.4, 0.0), (0.75, 1.0)]))
    col = m.mix(m.ramp(m.noise(6, 3, 0.5), [(0.3, '#e6c9c4'), (0.8, white)]), vein, web)
    return m.set(color=col, rough=0.07)


def origami(color='#d977a8', name='origami', color2=None):
    """Stiff folded paper with a faint grain and a second colour bleeding in."""
    m = Mat(name)
    grain = m.noise(180, 3, 0.7)
    wash = m.noise(3.0, 5, 0.6, 1.0)
    col = m.ramp(wash, [(0.3, _shade(color, 0.72)), (0.6, color),
                        (0.85, color2 or _shade(color, 1.2))])
    return m.set(color=col, rough=0.55, height=grain, bump=0.12, bump_distance=0.002)
