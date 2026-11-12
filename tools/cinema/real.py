"""Realistic people from the MPFB 2 (MakeHuman) CC0 body, finished here.

MPFB gives the body shape. Everything else is made in this file: the skin is a procedural shader
(pores, fine lines, mottling, freckles, moles, veins, flushed areas, lips, stubble) baked to
textures; eyes, brows, lashes, hair grown as strands and turned into hair cards; clothes fitted
over the body; and the cast rig with its full clip library.

Run: python3 tools/cinema/real.py OUT_DIR SHOTS_DIR [id ...]
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, '/tmp/chars']

import bpy  # noqa: E402
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

import core  # noqa: E402
from core import Mat, N, activate, bake_atlas, join, link, new_object, rgb, shade  # noqa: E402
import human  # noqa: E402
import materials as M  # noqa: E402

CAST = {
    'amara': dict(
        macro=dict(gender=0.0, age=0.523, muscle=0.58, weight=0.5, height=0.55, proportions=0.6,
                   african=0.85, asian=0.05, caucasian=0.1),
        skin='#7a4a32', skin2='#5e3524', flush='#8a3a2e', lips='#4e2420', iris='#3a2414',
        freckles=0.0, stubble=0.0, hair='coils', hair_color='#120c0a',
        outfit=(('wool', '#7e3526'), ('wool', '#3b4632')),
        assets=dict(eyes='brown', eyebrows='eyebrow008', eyelashes='eyelashes02', hair='afro01',
                    clothes=['female_casualsuit01', 'shoes05'])),
    'tomas': dict(
        macro=dict(gender=1.0, age=0.654, muscle=0.55, weight=0.6, height=0.6, proportions=0.5,
                   african=0.0, asian=0.0, caucasian=1.0),
        skin='#d7a487', skin2='#c08066', flush='#c4584a', lips='#9c4f4a', iris='#6b8090',
        freckles=0.15, stubble=0.75, hair='short', hair_color='#5a4b40',
        outfit=(('linen', '#c4b38c'), ('wool', '#4a3626')),
        assets=dict(eyes='grey', eyebrows='eyebrow001', eyelashes='eyelashes01', hair='short02',
                    clothes=['male_casualsuit04', 'shoes02'])),
    'mei': dict(
        macro=dict(gender=0.0, age=0.433, muscle=0.45, weight=0.42, height=0.42, proportions=0.6,
                   african=0.0, asian=0.92, caucasian=0.08),
        skin='#e6bf9f', skin2='#d4a183', flush='#d07a6c', lips='#a35a58', iris='#2a1a12',
        freckles=0.05, stubble=0.0, hair='long', hair_color='#0e0b0b',
        outfit=(('linen', '#d6cbb0'), ('wool', '#33455a')),
        assets=dict(eyes='brown', eyebrows='eyebrow004', eyelashes='eyelashes03', hair='long01',
                    clothes=['female_casualsuit01', 'shoes06'])),
}


# ----------------------------------------------------------------------------- body
def mpfb_body(spec):
    from mpfb_env import enable_mpfb
    enable_mpfb()
    from bl_ext.user_default.mpfb.services.humanservice import HumanService
    from bl_ext.user_default.mpfb.services.targetservice import TargetService
    from bl_ext.user_default.mpfb.entities.objectproperties import HumanObjectProperties
    body = HumanService.create_human()
    for key, value in spec['macro'].items():
        HumanObjectProperties.set_value(key, value, entity_reference=body)
    TargetService.reapply_macro_details(body)
    return body, HumanService


MH = '/opt/chars/mh/data'


def mhmat(path):
    out = {}
    for line in open(path, encoding='utf-8', errors='ignore'):
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and not parts[0].startswith('#'):
            out[parts[0]] = parts[1]
    return out


def mh_material(mhmat_path, name):
    """A plain glTF-friendly material from a MakeHuman .mhmat: colour, normal, cut-out alpha."""
    info = mhmat(mhmat_path)
    folder = os.path.dirname(mhmat_path)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = 0.6
    tex = info.get('diffuseTexture')
    if tex and os.path.exists(os.path.join(folder, tex)):
        node = N(nt, 'TexImage', image=bpy.data.images.load(os.path.join(folder, tex)))
        nt.links.new(node.outputs['Color'], b.inputs['Base Color'])
        if info.get('transparent', '').lower() == 'true' or 'alphaToCoverage' in info or \
                any(k in name for k in ('hair', 'eyebrow', 'eyelash')):
            cut = N(nt, 'Math', operation='ROUND')
            nt.links.new(node.outputs['Alpha'], cut.inputs[0])
            nt.links.new(cut.outputs[0], b.inputs['Alpha'])
            if hasattr(m, 'surface_render_method'):
                m.surface_render_method = 'DITHERED'
    elif 'diffuseColor' in info:
        b.inputs['Base Color'].default_value = (*[float(x) for x in info['diffuseColor'].split()[:3]], 1)
    nrm = info.get('normalmapTexture')
    if nrm and os.path.exists(os.path.join(folder, nrm)):
        image = bpy.data.images.load(os.path.join(folder, nrm))
        image.colorspace_settings.name = 'Non-Color'
        node = N(nt, 'TexImage', image=image)
        nm = N(nt, 'NormalMap', {'Color': node.outputs['Color']})
        nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    if 'hair' in name:
        b.inputs['Roughness'].default_value = 0.42
    if 'eye' in name and 'brow' not in name and 'lash' not in name:
        b.inputs['Roughness'].default_value = 0.05
    m['bake'] = False
    return m


def fabric_layer(m, kind, color):
    """A fabric's colour, height and roughness, built inside material m."""
    c = core.rgb(color)
    dark = tuple(x * 0.78 for x in c)
    light = tuple(min(1.0, x * 1.2 + 0.03) for x in c)
    var = m.noise(4, 4, 0.6)
    if kind == 'denim':
        twill = m.noise(1100, 2, 0.5, co=m.stretch(1, 1, 0.2))
        col = m.ramp(var, [(0.2, dark), (0.55, c), (0.85, light)])
        col = m.mix(col, tuple(min(1.0, x * 1.9) for x in c), m.math('MULTIPLY', twill, 0.22))
        return col, twill, 0.8
    if kind == 'rib':
        ribs = m.wave(900, 0.0, 0, direction='X')
        return m.ramp(var, [(0.2, dark), (0.8, c)]), ribs, 0.85
    if kind == 'heather':
        fleck = m.noise(1400, 2, 0.6)
        col = m.ramp(fleck, [(0.35, dark), (0.65, light)])
        return m.mix(col, c, m.math('MULTIPLY', var, 0.3)), fleck, 0.9
    if kind == 'linen':
        # Hand-spun linen: uneven slubs along the threads, a loose plain weave, sun-faded patches.
        slub = m.noise(130, 3, 0.7, co=m.stretch(1, 1, 0.08))
        weave = m.math('MAXIMUM', m.wave(520, 1.5, 1, direction='X'), m.wave(520, 1.5, 1, direction='Z'))
        col = m.ramp(var, [(0.15, dark), (0.6, c), (0.9, light)])
        col = m.mix(col, light, m.math('MULTIPLY', m.ramp(slub, [(0.6, 0.0), (0.8, 1.0)]), 0.5))
        col = m.mix(col, '#6a5a44', m.math('MULTIPLY', m.ramp(m.noise(2.5, 5, 0.7), [(0.6, 0.0), (0.85, 1.0)]), 0.25))
        return col, m.math('ADD', m.math('MULTIPLY', weave, 0.6), m.math('MULTIPLY', slub, 0.4)), 0.92
    if kind == 'wool':
        # Fulled wool: a soft felted surface, carded fibres of mixed tones, worn darker in places.
        fibres = m.noise(260, 4, 0.75, 1.5)
        felt = m.noise(40, 5, 0.65)
        col = m.ramp(fibres, [(0.3, dark), (0.55, c), (0.75, light)])
        col = m.mix(col, dark, m.math('MULTIPLY', m.ramp(m.noise(3, 5, 0.7), [(0.55, 0.0), (0.85, 1.0)]), 0.45))
        return col, m.math('ADD', m.math('MULTIPLY', felt, 0.6), m.math('MULTIPLY', fibres, 0.4)), 0.97
    weave = m.noise(900, 2, 0.5)
    return m.ramp(var, [(0.2, dark), (0.8, c)]), weave, 0.75


def outfit_material(spec, mhmat_path, waist):
    """Today's fabrics, top and bottom, over the folds and seams of the original garment."""
    m = Mat('outfit')
    nt = m.nt
    top_col, top_h, top_r = fabric_layer(m, *spec['outfit'][0])
    bot_col, bot_h, bot_r = fabric_layer(m, *spec['outfit'][1])
    z = N(nt, 'SeparateXYZ', {'Vector': N(nt, 'TexCoord').outputs['Object']}).outputs['Z']
    upper = m.ramp(z, [(waist - 0.012, 0.0), (waist + 0.012, 1.0)])
    col = m.mix(bot_col, top_col, upper)
    height = m.mix(bot_h, top_h, upper)
    rough = m.mix(bot_r, top_r, upper)
    info = mhmat(mhmat_path)
    folder = os.path.dirname(mhmat_path)
    ao = info.get('aomapTexture')
    if ao and os.path.exists(os.path.join(folder, ao)):
        img = bpy.data.images.load(os.path.join(folder, ao))
        img.colorspace_settings.name = 'Non-Color'
        shade_ = N(nt, 'TexImage', image=img).outputs['Color']
        col = m.mix(col, shade_, 0.85, 'MULTIPLY')
    m.set(color=col, rough=rough, height=height, bump=0.35, bump_distance=0.0015)
    nrm = info.get('normalmapTexture')
    if nrm and os.path.exists(os.path.join(folder, nrm)):
        img = bpy.data.images.load(os.path.join(folder, nrm))
        img.colorspace_settings.name = 'Non-Color'
        nm = N(nt, 'NormalMap', {'Color': N(nt, 'TexImage', image=img).outputs['Color']})
        bump = next(n for n in nt.nodes if n.type == 'BUMP')
        nt.links.new(nm.outputs['Normal'], bump.inputs['Normal'])
    return m.m


def add_assets(body, service, spec):
    """Fit the CC0 MakeHuman assets to this body, as MPFB does, and return them as plain meshes."""
    a = spec['assets']
    wanted = [('Eyes', MH + '/eyes/high-poly/high-poly.mhclo', MH + '/eyes/materials/%s.mhmat' % a['eyes']),
              ('Eyebrows', MH + '/eyebrows/%s/%s.mhclo' % (a['eyebrows'], a['eyebrows']), None),
              ('Eyelashes', MH + '/eyelashes/%s/%s.mhclo' % (a['eyelashes'], a['eyelashes']), None),
              ('Teeth', MH + '/teeth/teeth_base/teeth_base.mhclo', None),
              ('Tongue', MH + '/tongue/tongue01/tongue01.mhclo', None),
              ('Hair', MH + '/hair/%s/%s.mhclo' % (a['hair'], a['hair']), None)]
    wanted += [('Clothes', MH + '/clothes/%s/%s.mhclo' % (c, c), None) for c in a['clothes']]
    out = []
    for kind, path, material in wanted:
        before = set(bpy.data.objects)
        service.add_mhclo_asset(path, body, asset_type=kind, subdiv_levels=0)
        made = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
        if not made:
            print('ASSET MISSING', path)
            continue
        obj = made[0]
        mat_path = material or os.path.splitext(path)[0] + '.mhmat'
        if not os.path.exists(mat_path):
            mat_path = None
        out.append((kind, obj, mat_path))
    return out


def freeze(obj, name, material):
    """Apply an asset's modifiers and give it a plain material."""
    dg = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    plain = link(bpy.data.objects.new(name, mesh))
    plain.matrix_world = obj.matrix_world.copy()
    bpy.data.objects.remove(obj)
    activate(plain)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    plain.data.materials.clear()
    if material:
        plain.data.materials.append(material)
    return plain


def groups_of(obj):
    names = {g.index: g.name for g in obj.vertex_groups}
    out = {}
    for v in obj.data.vertices:
        for g in v.groups:
            if g.weight > 0.5:
                out.setdefault(names[g.group], []).append(v.index)
    return out


def centre(obj, idx):
    return sum((obj.data.vertices[i].co for i in idx), Vector()) / max(1, len(idx))


def joints_from(body, groups):
    c = lambda name: centre(body, groups[name])
    top = max(v.co.z for v in body.data.vertices if v.index in set(groups['body']))
    j = {'hips': c('joint-pelvis'), 'spine1': c('joint-spine-3'), 'chest': c('joint-spine-2'),
         'neck': c('joint-neck'), 'head': c('joint-head'), 'top': Vector((0, c('joint-head').y, top))}
    # MakeHuman numbers the spine from the top: spine-1 is the upper chest.
    j['spine1'], j['chest'] = c('joint-spine-3'), c('joint-spine-1')
    for side, s in (('L', 'l'), ('R', 'r')):
        j['clav' + side] = c('joint-%s-clavicle' % s)
        j['sh' + side] = c('joint-%s-shoulder' % s)
        j['el' + side] = c('joint-%s-elbow' % s)
        j['wr' + side] = c('joint-%s-hand' % s)
        j['d' + side] = (j['wr' + side] - j['sh' + side]).normalized()
        j['hip' + side] = c('joint-%s-upper-leg' % s)
        j['kn' + side] = c('joint-%s-knee' % s)
        j['an' + side] = c('joint-%s-ankle' % s)
        j['toe' + side] = c('joint-%s-foot-2' % s)
        j['tip' + side] = j['toe' + side] + Vector((0, -0.07, -0.01))
    for side, s in (('L', 'l'), ('R', 'r')):
        j['eye' + side] = c('helper-%s-eye' % s)
    # The lips sit just in front of the upper teeth (MakeHuman's mouth joint is up at the nose).
    j['mouth'] = c('helper-upper-teeth') + Vector((0, 0, -0.004))
    return j


def keep_only(body, keep):
    """Delete every vertex outside the given set."""
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context='VERTS')
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()


# ----------------------------------------------------------------------------- skin
def paint_masks(body, j, spec):
    """Vertex colours the skin shader reads: R flush, G lips, B stubble, A freckle zone."""
    eye = (j['eyeL'] + j['eyeR']) / 2
    mouth = j['mouth'] + Vector((0, -0.02, 0.0))
    nose = eye.lerp(mouth, 0.5) + Vector((0, -0.035, 0))
    layer = body.data.color_attributes.new('masks', 'FLOAT_COLOR', 'POINT')
    data = []
    for v in body.data.vertices:
        p = v.co
        face_front = max(0.0, min(1.0, (eye.y + 0.045 - p.y) / 0.03))
        cheek = max(0.0, 1 - min((p - (j['eyeL'] + Vector((0.012, -0.005, -0.04)))).length,
                                 (p - (j['eyeR'] + Vector((-0.012, -0.005, -0.04)))).length) / 0.035)
        nose_flush = max(0.0, 1 - (p - nose).length / 0.025)
        ear = max(0.0, 1 - min(abs(abs(p.x) - 0.075), 0.04) / 0.02) * max(
            0.0, 1 - abs(p.z - eye.z + 0.01) / 0.035) * (1 if p.y > eye.y + 0.06 else 0)
        knuckle = 0.0
        for side in 'LR':
            knuckle = max(knuckle, max(0.0, 1 - (p - (j['wr' + side] + j['d' + side] * 0.1)).length
                                       / 0.06))
        flush = min(1.0, (0.8 * cheek + 0.3 * nose_flush + 0.5 * ear) * face_front +
                    0.4 * knuckle + 0.5 * ear)
        lips = max(0.0, 1 - (Vector((p.x * 0.85, 0, (p.z - j['mouth'].z) * 2.1))).length / 0.02) * (
            1.0 if p.y < j['mouth'].y - 0.004 else 0.0)
        lips = min(1.0, lips * 2.5) * 0.85
        jaw = (p.z < mouth.z + 0.012 and p.z > mouth.z - 0.075 and p.y < eye.y + 0.075 and
               (p - mouth).length < 0.095)
        upper_lip = (abs(p.z - mouth.z - 0.016) < 0.012 and abs(p.x) < 0.03 and face_front > 0.3)
        stubble = spec['stubble'] if ((jaw or upper_lip) and lips < 0.3) else 0.0
        freckle_zone = 1.0 if (p.z > j['chest'].z - 0.05) else 0.25
        data += [flush, lips, stubble, freckle_zone]
    layer.data.foreach_set('color', data)


def skin_material(spec):
    m = Mat('skin', scale=1.0)
    attr = N(m.nt, 'Attribute', attribute_name='masks')
    sep = N(m.nt, 'SeparateColor', {'Color': attr.outputs['Color']})
    flush, lips, stubble = sep.outputs['Red'], sep.outputs['Green'], sep.outputs['Blue']
    zone = attr.outputs['Alpha']
    # Pores two sizes, cell lines, and the larger soft relief of flesh.
    pores = m.ramp(m.voronoi(2200, 'F1'), [(0.0, 1.0), (0.1, 0.0)])
    pores2 = m.ramp(m.voronoi(5200, 'F1'), [(0.0, 1.0), (0.12, 0.0)])
    lines = m.ramp(m.voronoi(650, 'DISTANCE_TO_EDGE'), [(0.0, 1.0), (0.035, 0.0)])
    relief = m.noise(60, 4, 0.6)
    height = m.math('SUBTRACT', m.math('MULTIPLY', relief, 0.25),
                    m.math('ADD', m.math('MULTIPLY', pores, 0.55),
                           m.math('ADD', m.math('MULTIPLY', pores2, 0.25),
                                  m.math('MULTIPLY', lines, 0.2))))
    # Colour: melanin unevenness, blood beneath, veins, freckles and moles.
    base = m.ramp(m.noise(5, 5, 0.6), [(0.3, spec['skin2']), (0.7, spec['skin'])])
    base = m.mix(base, m.mix(spec['skin'], spec['skin2'], 0.5), m.math(
        'MULTIPLY', m.noise(30, 4, 0.6), 0.25))
    base = m.mix(base, spec['flush'], m.math('MULTIPLY', flush, 0.28))
    veins = m.ramp(m.noise(14, 3, 0.5, 1.2), [(0.47, 0.0), (0.5, 1.0), (0.53, 0.0)])
    base = m.mix(base, '#5a6a8a', m.math('MULTIPLY', veins, 0.06))
    if spec['freckles']:
        fr = m.voronoi(260, 'F1', out='Color')
        fr_mask = m.math('MULTIPLY', m.ramp(N(m.nt, 'SeparateColor', {'Color': fr}).outputs[0],
                                            [(1 - 0.18 * spec['freckles'], 0.0),
                                             (1 - 0.17 * spec['freckles'], 1.0)]),
                         m.ramp(m.voronoi(260, 'F1'), [(0.0, 1.0), (0.22, 0.0)]))
        base = m.mix(base, spec['skin2'], m.math('MULTIPLY', m.math('MULTIPLY', fr_mask, zone),
                                                 0.45))
    mole_cell = N(m.nt, 'SeparateColor', {'Color': m.voronoi(22, 'F1', out='Color')}).outputs[0]
    mole = m.math('MULTIPLY', m.ramp(mole_cell, [(0.985, 0.0), (0.987, 1.0)]),
                  m.ramp(m.voronoi(22, 'F1'), [(0.0, 1.0), (0.05, 0.0)]))
    base = m.mix(base, '#3a2218', m.math('MULTIPLY', mole, 0.7))
    # Small moles and freckles everywhere, in two sizes and several browns.
    for scale, rate, size, amount in ((90, 0.035, 0.07, 0.55), (300, 0.06, 0.12, 0.35)):
        cell = m.voronoi(scale, 'F1', out='Color')
        pick = N(m.nt, 'SeparateColor', {'Color': cell})
        spot = m.math('MULTIPLY', m.ramp(pick.outputs[0], [(1 - rate, 0.0), (1 - rate + 0.002, 1.0)]),
                      m.ramp(m.voronoi(scale, 'F1'), [(0.0, 1.0), (size, 0.0)]))
        tone = m.ramp(pick.outputs[1], [(0.0, '#4a2a1c'), (1.0, '#8a5a3c')])
        base = m.mix(base, tone, m.math('MULTIPLY', spot, amount))
    base = m.mix(base, spec['lips'], lips)
    if spec['stubble']:
        hairs = m.ramp(m.voronoi(3200, 'F1'), [(0.0, 1.0), (0.3, 0.0)])
        dots = m.math('MULTIPLY', stubble, m.math('ADD', 0.35, m.math('MULTIPLY', hairs, 0.65)))
        base = m.mix(base, '#2a2420', m.math('MULTIPLY', dots, 0.55))
    base = m.mix(base, spec['skin2'], m.math('MULTIPLY', pores, 0.3))
    rough = m.math('ADD', m.math('ADD', 0.5, m.math('MULTIPLY', pores, 0.12)),
                   m.math('MULTIPLY', lips, -0.15))
    m.set(color=base, rough=rough, height=height, bump=0.55, bump_distance=0.0007)
    return m.m


# ----------------------------------------------------------------------------- eyes, brows, lashes
def eyes(j, spec):
    parts = []
    white = Mat('sclera')
    white.set(color='#ece4dc', rough=0.12)
    white.m['bake'] = False
    iris = Mat('iris')
    iris.set(color=spec['iris'], rough=0.3)
    iris.m['bake'] = False
    pupil = Mat('pupil')
    pupil.set(color='#030303', rough=0.2)
    pupil.m['bake'] = False
    cornea = Mat('cornea')
    cornea.set(color='#ffffff', rough=0.02, alpha=0.12)
    for side in 'LR':
        c = j['eye' + side]
        r = 0.0118
        parts.append(core.sphere(r, c, material=white.m, segments=32, rings=20))
        f = Vector((0, -1, 0))
        rot = f.to_track_quat('Z', 'Y').to_euler()
        for mat, a, lift in ((iris.m, 0.55, 1.004), (pupil.m, 0.24, 1.008)):
            prof = [(r * lift * math.sin(a * i / 6), r * lift * math.cos(a * i / 6))
                    for i in range(6, -1, -1)]
            parts.append(core.lathe(prof, 32, c, rot, mat, cap=False))
        parts.append(core.sphere(r * 1.03, c, material=cornea.m, segments=32, rings=20))
    for p in parts:
        p['bone'] = 'Head'
    return parts


def strip_texture(name, kind, size=(256, 1024), seed=1):
    """A hair strip: many thin strands with gaps, alpha in the A channel."""
    rnd = np.random.default_rng(seed)
    w, h = size
    img = np.zeros((h, w, 4), np.float32)
    y = np.linspace(0, 1, h)[:, None]
    strands = 46 if kind == 'hair' else 18
    for _ in range(strands):
        x0 = rnd.uniform(0.04, 0.96) * w
        wobble = rnd.uniform(-6, 6) * np.sin(y * rnd.uniform(2, 7) + rnd.uniform(0, 6))
        width = rnd.uniform(3.0, 6.0)
        length = rnd.uniform(0.7, 1.0)
        tone = rnd.uniform(0.75, 1.15)
        xs = np.arange(w)[None, :]
        cover = np.clip(1 - np.abs(xs - (x0 + wobble)) / width, 0, 1)
        cover *= (y < length) * np.clip((length - y) / 0.12, 0, 1)
        img[..., 3] = np.maximum(img[..., 3], cover)
        img[..., :3] = np.maximum(img[..., :3], cover[..., None] * tone)
    img[..., :3] = np.clip(img[..., :3], 0, 1.2) / 1.2
    image = bpy.data.images.new(name, w, h, alpha=True)
    image.pixels.foreach_set(img[::-1].ravel())
    image.pack()
    return image


def card_material(name, color, kind, seed=1):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    tex = N(nt, 'TexImage', image=strip_texture(name + '_tex', kind, seed=seed))
    tint = N(nt, 'MixRGB', {'Fac': 1.0, 'Color1': (*rgb(color), 1)}, blend_type='MULTIPLY')
    nt.links.new(tex.outputs['Color'], tint.inputs['Color2'])
    nt.links.new(tint.outputs['Color'], b.inputs['Base Color'])
    cut = N(nt, 'Math', operation='ROUND')
    nt.links.new(tex.outputs['Alpha'], cut.inputs[0])
    nt.links.new(cut.outputs[0], b.inputs['Alpha'])
    b.inputs['Roughness'].default_value = 0.38
    b.inputs['Specular IOR Level'].default_value = 0.6
    if hasattr(m, 'surface_render_method'):
        m.surface_render_method = 'DITHERED'
    m['bake'] = False
    return m


def ribbon(points, widths, normals, mat, name='card'):
    """A flat strip along a polyline, facing along the given normals."""
    verts, faces, uvs = [], [], []
    n = len(points)
    for i, p in enumerate(points):
        t = (points[min(i + 1, n - 1)] - points[max(i - 1, 0)]).normalized()
        side = t.cross(normals[i]).normalized() * widths[i]
        verts += [p - side, p + side]
        uvs += [(0, 1 - i / (n - 1)), (1, 1 - i / (n - 1))]
    for i in range(n - 1):
        faces.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
    obj = new_object(name, verts, faces, mat, smooth=True)
    uv = obj.data.uv_layers.new(name='UVMap')
    for poly in obj.data.polygons:
        for li in poly.loop_indices:
            uv.data[li].uv = uvs[obj.data.loops[li].vertex_index]
    return obj


def brows_and_lashes(j, spec, bvh):
    parts = []
    brow_mat = card_material('brows', spec['hair_color'], 'brow', 3)
    lash_mat = card_material('lashes', '#0b0908', 'brow', 4)
    rnd = random.Random(5)
    for side, sx in (('L', 1), ('R', -1)):
        e = j['eye' + side]
        for k in range(70):
            u = rnd.random()
            x = e.x + sx * (-0.016 + 0.036 * u)
            z = e.z + 0.018 + 0.0055 * math.sin(math.pi * min(1, u * 1.2)) - 0.004 * u + rnd.uniform(-0.003, 0.003) * (1.2 - u)
            start = Vector((x, e.y - 0.03, z))
            hit = bvh.ray_cast(start, Vector((0, 1, 0)), 0.08)
            if not hit[0]:
                continue
            root = hit[0] + hit[1] * 0.0008
            d = Vector((sx * (0.6 + 0.4 * u), 0, 0.35 - 0.6 * u)).normalized()
            pts = [root + d * 0.0032 * t + hit[1] * 0.0008 * t for t in range(4)]
            parts.append(ribbon(pts, [0.0011 * (1.2 - 0.25 * t) for t in range(4)],
                                [hit[1]] * 4, brow_mat, 'brow'))
        for k in range(14):
            a = math.pi * (0.15 + 0.7 * k / 13)
            root = e + Vector((sx * -math.cos(a) * 0.011, -0.0105, math.sin(a) * 0.0042 + 0.0035))
            d = Vector((sx * -math.cos(a) * 0.25, -0.75, 0.6)).normalized()
            pts = [root + d * 0.0028 * t + Vector((0, 0, 0.0006 * t * t)) for t in range(3)]
            parts.append(ribbon(pts, [0.0009, 0.0008, 0.0005], [Vector((0, -0.3, 1)).normalized()]
                                * 3, lash_mat, 'lash'))
    for p in parts:
        p['bone'] = 'Head'
    return parts


# ----------------------------------------------------------------------------- hair
def surface(bvh, p):
    near, normal, _, _ = bvh.find_nearest(p)
    return near, normal


def grow_hair(body, j, spec, bvh, scalp):
    """Strands grown from the scalp and combed along it, then made into cards.

    Like hair in games, the cards sit on a hair-coloured cap so no skin shows between them.
    """
    rnd = random.Random(sum(map(ord, spec['hair'])))
    style = spec['hair']
    eye = (j['eyeL'] + j['eyeR']) / 2
    mat = card_material('hair', spec['hair_color'], 'hair', 7)
    volume = {'coils': 0.016, 'short': 0.004, 'long': 0.005}[style]
    roots = [body.data.vertices[i].co.copy() for i in scalp]
    rnd.shuffle(roots)
    count = {'coils': 2200, 'short': 2000, 'long': 1600}[style]
    cards = []
    for co in roots[:count]:
        root, nrm = surface(bvh, co)
        if style == 'long':
            length, segs = rnd.uniform(0.3, 0.4), 18
        elif style == 'short':
            length, segs = rnd.uniform(0.06, 0.1), 7
        else:
            length, segs = rnd.uniform(0.025, 0.045), 7
        # Combed away from a side parting, towards the back and down.
        side = 1 if co.x > 0.02 else -1
        comb = Vector((side * 0.8, 0.5, -0.6)) if style != 'long' else Vector((side * 0.3, 0.45, -1))
        if style == 'short':
            comb = Vector((side * 0.55, 0.65, -0.35)) if co.y < eye.y + 0.06 else Vector((side * 0.2, 0.3, -1))
        p = root + nrm * (0.002 + volume)
        pts = [p.copy()]
        phase = rnd.uniform(0, 6.28)
        step = length / segs
        for i in range(segs):
            t = (i + 1) / segs
            near, n = surface(bvh, p)
            on_head = (p - eye).length < 0.17 and p.z > eye.z - 0.09
            if on_head:
                d = comb - n * comb.dot(n)
            else:
                d = Vector((comb.x * 0.15, comb.y * 0.2, -1))
            if style == 'coils':
                d = d.normalized() + Vector((math.cos(phase + i * 2.1), math.sin(phase + i * 2.1),
                                             math.cos(phase * 1.3 + i * 1.7))) * 0.9
            p = p + d.normalized() * step
            near, n = surface(bvh, p)
            gap = 0.002 + volume + (0.004 if style == 'long' else 0.002) * t
            if (p - near).dot(n) < gap:
                p = near + n * gap
            pts.append(p.copy())
        width = {'coils': 0.006, 'short': 0.0055, 'long': 0.006}[style]
        widths = [width * (1.0 - 0.6 * (i / segs) ** 2) for i in range(segs + 1)]
        normals = [surface(bvh, q)[1] for q in pts]
        cards.append(ribbon(pts, widths, normals, mat, 'hair'))
    # The cap: the scalp, lifted, in the hair colour, with the strands' grain.
    cap = body.copy()
    cap.data = body.data.copy()
    link(cap)
    keep_only(cap, set(scalp))
    for v in cap.data.vertices:
        v.co += v.normal * (0.0012 + volume * 0.85)
    cap.data.update()
    cap_m = Mat('hair_cap')
    streak = cap_m.noise(900, 2, 0.6, co=cap_m.stretch(1, 0.08, 1))
    cap_m.set(color=cap_m.ramp(streak, [(0.3, core.rgb(spec['hair_color'])), (0.7, tuple(
        min(1.0, c * 1.6) for c in core.rgb(spec['hair_color'])))]), rough=0.55, height=streak,
              bump=0.2, bump_distance=0.001)
    cap_mat = cap_m.m
    cap.data.materials.clear()
    cap.data.materials.append(cap_mat)
    cap.vertex_groups.clear()
    for mod in list(cap.modifiers):
        cap.modifiers.remove(mod)
    if cap.data.color_attributes.get('masks'):
        cap.data.color_attributes.remove(cap.data.color_attributes['masks'])
    cap['bone'] = 'Head'
    hair = join(cards, 'hair')
    hair['bone'] = 'Head'
    return [hair], cap


def scalp_vertices(body, j):
    eye = (j['eyeL'] + j['eyeR']) / 2
    head_c = eye + Vector((0, 0.07, 0.035))
    out = []
    for v in body.data.vertices:
        p = v.co
        if (p - head_c).length > 0.15 or p.z < eye.z - 0.075:
            continue
        forehead = p.y < eye.y + 0.05 and p.z < eye.z + 0.075
        temple = abs(p.x) > 0.062 and p.z < eye.z + 0.035
        if forehead or temple:
            continue
        if p.z < eye.z + 0.02 and p.y < head_c.y + 0.02:
            continue
        out.append(v.index)
    return out


# ----------------------------------------------------------------------------- clothes
def fabric(kind, color):
    if kind == 'jeans':
        return M.denim(color, 'bottom')
    if kind in ('chinos', 'trousers'):
        return M.cloth(color, 'bottom', 520, 0.78, 0.2)
    if kind == 'tank':
        return M.cloth(color, 'top', 700, 0.85, 0.25)
    return M.cloth(color, 'top', 600, 0.88, 0.25)


def garment(body, j, kind, color, region):
    """A copy of the body faces in a region, pushed out from the skin, as a fitted garment."""
    keep = set(i for i, v in enumerate(body.data.vertices) if region(v))
    dup = body.copy()
    dup.data = body.data.copy()
    link(dup)
    keep_only(dup, keep)
    # Cloth does not follow every curve of the body: smooth the copy before pushing it out.
    core.modifier(dup, 'SMOOTH', factor=0.8, iterations=40 if kind == 'shoes' else 14)
    loose = {'tank': 0.005, 'tee': 0.009, 'jeans': 0.006, 'chinos': 0.01, 'trousers': 0.011,
             'shoes': 0.012}[kind]
    bottom = min((v.co.z for v in dup.data.vertices), default=0.0)
    top = max((v.co.z for v in dup.data.vertices), default=0.0)
    for v in dup.data.vertices:
        extra = 0.0
        if kind in ('tee', 'tank'):
            extra = 0.008 * max(0.0, 1 - (v.co.z - bottom) / 0.18)
        if kind in ('chinos', 'trousers'):
            extra = 0.01 * max(0.0, 1 - (v.co.z - bottom) / 0.35)
        v.co += v.normal * (loose + extra)
        if kind == 'shoes':
            v.co.z = max(v.co.z, 0.0)
    dup.data.update()
    core.solidify(dup, 0.0025, -1)
    dup.data.materials.clear()
    dup.data.materials.append(fabric(kind, color) if kind != 'shoes' else M.leather(
        color, 'shoes', 0.45))
    if dup.data.color_attributes.get('masks'):
        dup.data.color_attributes.remove(dup.data.color_attributes['masks'])
    return dup


def dominant_bones(body):
    names = {g.index: g.name for g in body.vertex_groups}
    out = []
    for v in body.data.vertices:
        best = max(v.groups, key=lambda g: g.weight, default=None)
        out.append(names[best.group] if best else '')
    return out


def regions(j, spec, bones):
    """Garment regions by the bone that moves each vertex most, as a game pipeline would."""
    waist = j['hips'].z + 0.075
    torso = {'Spine', 'Spine1', 'Spine2', 'Shoulder.L', 'Shoulder.R', 'Hips'}
    legs = {'Hips', 'UpLeg.L', 'UpLeg.R', 'Leg.L', 'Leg.R'}
    feet = {'Foot.L', 'Foot.R', 'Toe.L', 'Toe.R'}
    kind = spec['top'][0]

    def along_upper_arm(v, side):
        sh, el = j['sh' + side], j['el' + side]
        axis = el - sh
        return (v.co - sh).dot(axis) / axis.length_squared

    def top(v):
        bone = bones[v.index]
        if v.co.z < waist - (0.03 if kind == 'tee' else 0.0):
            return False
        if v.co.y < j['chest'].y - 0.04 and v.co.z > j['neck'].z - (0.08 if kind == 'tank' else 0.05):
            return False
        if bone in torso:
            if kind == 'tank' and bone.startswith('Shoulder'):
                return v.co.z < j['shL'].z - 0.02 and abs(v.co.x) < abs(j['shL'].x) - 0.05
            return v.co.z < j['neck'].z - 0.015
        if kind == 'tee' and bone.startswith('UpperArm'):
            return along_upper_arm(v, bone[-1]) < 0.42
        return False

    def bottom(v):
        return bones[v.index] in legs and v.co.z < waist + 0.01 and v.co.z > j['anL'].z + 0.02

    def shoes(v):
        return bones[v.index] in feet or (bones[v.index] in legs and v.co.z < j['anL'].z + 0.035)

    return top, bottom, shoes


# ----------------------------------------------------------------------------- build
def build(model_id):
    spec = CAST[model_id]
    core.reset(sum(map(ord, model_id)))
    body, service = mpfb_body(spec)
    assets = add_assets(body, service, spec)
    activate(body)
    if body.data.shape_keys:
        bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
    groups = groups_of(body)
    j = joints_from(body, groups)
    # A whole-body copy, without the helpers but with the skin under the clothes, gives the
    # clothes their weights: the visible body has lost exactly the skin they would copy from.
    full = body.copy()
    full.data = body.data.copy()
    link(full)
    activate(full)
    for mod in list(full.modifiers):
        if mod.type == 'MASK' and mod.vertex_group == 'body':
            bpy.ops.object.modifier_apply(modifier=mod.name)
        else:
            full.modifiers.remove(mod)
    full.vertex_groups.clear()
    full.parent = None
    activate(body)
    # The masks hide the helpers and the skin under the clothes: apply them.
    for mod in list(body.modifiers):
        if mod.type == 'MASK':
            bpy.ops.object.modifier_apply(modifier=mod.name)
        else:
            body.modifiers.remove(mod)
    body.vertex_groups.clear()
    body.parent = None
    body.name = model_id
    shade(body)
    height = max(v.co.z for v in body.data.vertices)
    paint_masks(body, j, spec)
    body.data.materials.clear()
    body.data.materials.append(skin_material(spec))
    parts = []
    for kind, obj, mat_path in assets:
        name = '%s_%s' % (model_id, kind.lower())
        if kind == 'Clothes' and 'suit' in os.path.basename(mat_path or ''):
            mat = outfit_material(spec, mat_path, j['hips'].z + 0.07)
            name = model_id + '_outfit'
        elif kind == 'Clothes' and 'shoes' in os.path.basename(mat_path or ''):
            mat = M.leather('#3e2a1c', 'boots', 0.62)
            name = model_id + '_boots'
        else:
            mat = mh_material(mat_path, kind.lower()) if mat_path else None
        parts.append((kind, freeze(obj, name, mat)))
    arm = (j['elL'] - j['shL']).normalized()
    rest = math.acos(max(-1, min(1, arm.dot(Vector((0, 0, -1))))))
    human.REST_DOWN = rest - 0.06
    s = dict(name=model_id, height=height)
    rig = human.build_rig(s, j)
    rig.bind_auto(full)
    rig.transfer_weights(full, body)
    clothes, rigid = [], []
    for kind, obj in parts:
        obj.vertex_groups.clear()
        if kind in ('Clothes', 'Hair') and not (kind == 'Hair' and spec['hair'] != 'long'):
            rig.transfer_weights(full, obj)
            # Cloth near the hands must not follow them: only the body moves clothes and hair.
            for group in list(obj.vertex_groups):
                if group.name.split('.')[0].rstrip('0123456789') in (
                        'Hand', 'ForeArm', 'Index', 'Middle', 'Ring', 'Pinky', 'Thumb'):
                    obj.vertex_groups.remove(group)
            activate(obj)
            bpy.ops.object.vertex_group_normalize_all(lock_active=False)
            clothes.append(obj)
        else:
            rig.bind_rigid(obj, 'Jaw' if kind in ('Tongue',) else 'Head')
            rigid.append(obj)
    bpy.data.objects.remove(full)
    human.animate(rig, s, height / 1.75)
    return rig, body, clothes, rigid


def bake_all(model_id, body, clothes):
    bake_atlas(body, 4096, name=model_id + '_skin', do_unwrap=False, ao_samples=16)
    for c in clothes:
        if c.name.endswith('_outfit') or c.name.endswith('_boots'):
            bake_atlas(c, 2048, name=model_id + '_outfit', do_unwrap=False, ao_samples=8)
    # Skin lets light in: only the renders here use it, the web player draws the baked colour.
    for mat in body.data.materials:
        b = mat.node_tree.nodes.get('Principled BSDF')
        if b:
            b.inputs['Subsurface Weight'].default_value = 0.35
            b.inputs['Subsurface Radius'].default_value = (1.0, 0.35, 0.18)
            b.inputs['Subsurface Scale'].default_value = 0.0035


def shoot(path, j_head, height, size=(900, 1100), portrait=False, samples=96, frame=1, rig=None,
          clip=2):
    scene = bpy.context.scene
    if rig is not None:
        ad = rig.obj.animation_data
        action = rig.actions[clip]
        ad.action = action
        if hasattr(ad, 'action_slot') and action.slots:
            ad.action_slot = action.slots[0]
    scene.frame_set(frame)
    world = bpy.data.worlds.new('studio')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.05, 0.055, 0.06, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0
    scene.world = world
    for name, loc, energy, size_, colour in (('key', (-1.4, -2.0, 2.3), 160, 1.6, (1, 0.95, 0.88)),
                                             ('fill', (1.8, -1.6, 1.4), 35, 2.5, (0.85, 0.9, 1)),
                                             ('rim', (0.6, 2.2, 2.2), 220, 1.0, (1, 0.97, 0.92))):
        if bpy.data.objects.get(name):
            continue
        light = bpy.data.lights.new(name, 'AREA')
        light.energy, light.size, light.color = energy, size_, colour
        o = link(bpy.data.objects.new(name, light))
        o.location = loc
        o.rotation_euler = (Vector((0, 0, 1.2)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if not bpy.data.objects.get('floor'):
        floor = core.grid((20, 20), (1, 1), name='floor')
        fm = Mat('floor_mat')
        fm.set(color='#2a2b2e', rough=0.6)
        floor.data.materials.append(fm.m)
    cam_data = bpy.data.cameras.new('cam')
    cam = link(bpy.data.objects.new('cam', cam_data))
    if portrait:
        cam_data.lens = 85
        target = j_head + Vector((0, 0, -0.03))
        cam.location = target + Vector((0.18, -0.95, 0.03))
    else:
        cam_data.lens = 50
        target = Vector((0, 0, height * 0.52))
        cam.location = target + Vector((0.9, -3.3, 0.15))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = cam
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.render.image_settings.file_format = 'JPEG'
    scene.render.image_settings.quality = 90
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)


def main(argv):
    out, shots = argv[0], argv[1]
    ids = argv[2:] or list(CAST)
    os.makedirs(out, exist_ok=True)
    os.makedirs(shots, exist_ok=True)
    for model_id in ids:
        rig, body, clothes, rigid = build(model_id)
        bake_all(model_id, body, clothes)
        rig.obj.name = model_id + '-rig'
        core.export(os.path.join(out, 'real-' + model_id + '.glb'))
        eye = None
        for o in rigid:
            if o.name.endswith('_eyes'):
                eye = sum((v.co for v in o.data.vertices), Vector()) / len(o.data.vertices)
                break
        height = max(v.co.z for v in body.data.vertices)
        shoot(os.path.join(shots, model_id + '-portrait.jpg'), eye, height, (900, 1100), True,
              rig=rig, clip=2, frame=30)
        shoot(os.path.join(shots, model_id + '-full.jpg'), eye, height, (900, 1200), False,
              samples=64, rig=rig, clip=0, frame=8)
        print('BUILT', model_id, flush=True)


if __name__ == '__main__':
    main(sys.argv[1:])
