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
sys.path[:0] = [HERE]

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
        freckles=0.0, stubble=0.0, body_hair=0.35, grime=0.5, brow=0.45, age=0.35, hair='coils', hair_color='#120c0a',
        outfit=(('wool', '#7e3526'), ('wool', '#3b4632')),
        assets=dict(eyes='brown', eyebrows='eyebrow008', eyelashes='eyelashes02', hair='afro01',
                    clothes=['female_casualsuit01', 'shoes05'])),
    'tomas': dict(
        macro=dict(gender=1.0, age=0.654, muscle=0.55, weight=0.6, height=0.6, proportions=0.5,
                   african=0.0, asian=0.0, caucasian=1.0),
        skin='#cfa093', skin2='#b07a70', flush='#c0545a', lips='#9a4650', iris='#6b8090',
        freckles=0.15, stubble=0.75, body_hair=0.85, grime=0.7, brow=0.75, age=0.45, hair='short', hair_color='#5a4b40',
        outfit=(('linen', '#c4b38c'), ('wool', '#4a3626')),
        assets=dict(eyes='grey', eyebrows='eyebrow009', eyelashes='eyelashes01', hair='short02',
                    clothes=['male_casualsuit04', 'shoes02'])),
    'mei': dict(
        macro=dict(gender=0.0, age=0.433, muscle=0.45, weight=0.42, height=0.42, proportions=0.6,
                   african=0.0, asian=0.92, caucasian=0.08),
        skin='#e6bf9f', skin2='#d4a183', flush='#d07a6c', lips='#a35a58', iris='#2a1a12',
        freckles=0.05, stubble=0.0, body_hair=0.2, grime=0.4, brow=0.55, age=0.25, hair='long', hair_color='#0e0b0b',
        outfit=(('linen', '#d6cbb0'), ('wool', '#33455a')),
        assets=dict(eyes='brown', eyebrows='eyebrow012', eyelashes='eyelashes03', hair='long01',
                    clothes=['female_casualsuit01', 'shoes06'])),
    # A medieval beggar: old, thin, weathered and filthy; barefoot, in torn linen and wool; long
    # matted hair, a long beard and moustache; rotten and missing teeth; black under the nails.
    'beggar': dict(
        macro=dict(gender=1.0, age=0.82, muscle=0.38, weight=0.32, height=0.5, proportions=0.45,
                   african=0.0, asian=0.0, caucasian=1.0),
        skin='#b08575', skin2='#8e6255', flush='#a84848', lips='#84404a', iris='#5a4a30',
        freckles=0.25, stubble=0.6, body_hair=0.9, grime=1.5, brow=0.8, age=0.95, hair='long',
        hair_color='#4a4038', outfit=(('linen', '#8e826a'), ('wool', '#4a3f33')),
        keep_skin=True, rags=True, wear=1.0, beard=dict(length=0.19, grey=0.25),
        teeth=dict(missing=4, rot=0.8), nail_dirt=1.0,
        assets=dict(eyes='brownlight', eyebrows='eyebrow009', eyelashes='eyelashes01',
                    hair='long01', clothes=['male_casualsuit03'])),
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


MH = os.environ.get('MH_DATA', '/opt/chars/mh/data')   # MakeHuman CC0 system assets


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
        # Strands scatter light: a broad, dim sheen, not the hard white patch of a smooth cap.
        b.inputs['Roughness'].default_value = 0.75
        b.inputs['Specular IOR Level'].default_value = 0.08
        # The MakeHuman hair normal map turns parts of the cap edge-on to the rim light and they
        # flare white; strands read better without it.
        for link in list(nt.links):
            if link.to_node == b and link.to_socket.name == 'Normal':
                nt.links.remove(link)
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
    # World height, remapped round the waist: a colour ramp clamps its input to 0..1, so a raw height
    # of a metre or more would never reach the split.
    z = N(nt, 'SeparateXYZ', {'Vector': m.geometry.outputs['Position']}).outputs['Z']
    # Which garment: the MakeHuman suits are exactly two loose pieces, top and trousers, marked
    # per vertex by mark_outfit_parts (splitting by height let the trouser colour climb into the
    # hem of a shirt that hangs below the waist).
    upper = N(nt, 'Attribute', attribute_name='top').outputs['Fac']
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
    w = spec.get('wear', 0.0)
    if w:
        # Years of wear: sun-faded patches, grease and sweat stains, mud splashed up from the
        # ground, a few sewn-on patches of other cloth with coarse stitches.
        mm = m.math
        fade = m.ramp(m.noise(4, 3, 0.6), [(0.5, 0.0), (0.75, 1.0)])
        col = m.mix(col, m.mix(col, '#c8bca0', 0.5), mm('MULTIPLY', fade, 0.5 * w))
        stain = m.ramp(m.noise(9, 4, 0.65, 0.5), [(0.58, 0.0), (0.7, 1.0)])
        col = m.mix(col, m.mix(col, '#2a2016', 0.6), mm('MULTIPLY', stain, 0.6 * w))
        mud = mm('MULTIPLY', m.ramp(z, [(0.0, 1.0), (0.6, 0.0)]),
                 m.ramp(m.noise(30, 4, 0.6), [(0.35, 0.3), (0.65, 1.0)]))
        col = m.mix(col, '#3e3222', mm('MULTIPLY', mud, 0.8 * w))
        cell = m.voronoi(14, 'F1', out='Color')
        pick = N(nt, 'SeparateColor', {'Color': cell}).outputs[0]
        patch = m.ramp(pick, [(0.9, 0.0), (0.905, 1.0)])
        edge = m.ramp(m.voronoi(14, 'DISTANCE_TO_EDGE'), [(0.0, 1.0), (0.03, 0.0)])
        col = m.mix(col, m.ramp(N(nt, 'SeparateColor', {'Color': cell}).outputs[1],
                                [(0.0, '#5a4a3a'), (0.5, '#6a5a44'), (1.0, '#3e3a30')]),
                    mm('MULTIPLY', patch, w))
        stitch = mm('MULTIPLY', mm('MULTIPLY', patch, edge),
                    m.ramp(m.wave(900, 0.0, 0.0), [(0.4, 0.0), (0.6, 1.0)]))
        col = m.mix(col, '#c8b896', mm('MULTIPLY', stitch, 0.8))
        height = mm('ADD', height, mm('MULTIPLY', mm('ADD', patch, stitch), 0.3))
        rough = mm('ADD', rough, mm('MULTIPLY', mud, 0.1))
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


# ----------------------------------------------------------------------------- eyes
# The MakeHuman CC0 eye mesh is an eyeball plus a slightly larger cornea shell over it, both UV
# mapped onto one texture: the two eyeballs round the iris centres below, the shells onto a
# transparent corner (u > 0.85, v < 0.15). We keep the geometry and write our own materials.
IRIS_UV = ((0.7052, 0.6955), (0.2892, 0.2834))
IRIS_R = 0.112          # iris radius in UV units (about 5.9 mm on the eye)


def eye_material(spec):
    """Iris and sclera from the eye's UVs, baked later like the skin.
    Iris: radial stroma fibres, crypts, a lighter collarette round the pupil, a dark limbal ring.
    Sclera: ivory, a cool tint by the limbus, warmer and pinker towards the corners, fine red
    vessels that thicken and multiply away from the iris."""
    m = Mat('eye')
    nt = m.nt
    mm = m.math
    uv = N(nt, 'TexCoord').outputs['UV']
    (u0, v0), (u1, v1) = IRIS_UV
    sep_uv = N(nt, 'SeparateXYZ', {'Vector': uv})
    first = mm('GREATER_THAN', sep_uv.outputs['X'], 0.5)     # which eye this texel belongs to
    cu = mm('MULTIPLY_ADD', first, u0 - u1, u1)
    cv = mm('MULTIPLY_ADD', first, v0 - v1, v1)
    du = mm('SUBTRACT', sep_uv.outputs['X'], cu)
    dv = mm('SUBTRACT', sep_uv.outputs['Y'], cv)
    d = mm('SQRT', mm('ADD', mm('MULTIPLY', du, du), mm('MULTIPLY', dv, dv)))
    ang = mm('ARCTAN2', dv, du)
    r = mm('DIVIDE', d, IRIS_R)
    # Colour ramps clamp their input to 0..1: feed them r/3 (stops below are r/3 too).
    r3 = mm('DIVIDE', r, 3.0)
    # Polar coordinates without a seam: a circle of radius 8 for the angle, r for depth.
    ring = lambda k_: N(nt, 'CombineXYZ', {'X': mm('MULTIPLY', mm('COSINE', ang), k_),
                                          'Y': mm('MULTIPLY', mm('SINE', ang), k_),
                                          'Z': r}).outputs['Vector']
    iris_col = core.rgb(spec['iris'])
    light = tuple(min(1, c * 1.9 + 0.08) for c in iris_col)
    dark = tuple(c * 0.45 for c in iris_col)
    fibres = m.noise(9, 6, 0.65, 0.0, co=ring(8.0))
    crypts = m.ramp(m.voronoi(6, 'F1', co=ring(2.0)), [(0.0, 1.0), (0.22, 0.0)])
    iris = m.ramp(fibres, [(0.3, '#%02x%02x%02x' % tuple(int(255 * c) for c in dark)),
                           (0.55, spec['iris']),
                           (0.8, '#%02x%02x%02x' % tuple(int(255 * c) for c in light))])
    collarette = m.ramp(r3, [(0.1200, 0.0), (0.1500, 1.0), (0.2000, 0.0)])
    iris = m.mix(iris, '#%02x%02x%02x' % tuple(int(255 * c) for c in light),
                 mm('MULTIPLY', collarette, 0.45))
    iris = m.mix(iris, '#%02x%02x%02x' % tuple(int(255 * c) for c in dark),
                 mm('MULTIPLY', crypts, 0.5))
    limbal = m.ramp(r3, [(0.2667, 0.0), (0.3233, 1.0), (0.3500, 0.6), (0.3800, 0.0)])
    iris = m.mix(iris, '#1a1412', mm('MULTIPLY', limbal, 0.8))
    pupil = m.ramp(r3, [(0.1100, 1.0), (0.1233, 0.0)])
    iris = m.mix(iris, '#030303', pupil)
    # Sclera: never paper white.
    sclera = m.ramp(r3, [(0.3500, '#d6dade'), (0.4667, '#e9e2d8'), (0.7667, '#e8d2c8'), (1.0000, '#dcb8b0')])
    sclera = m.mix(sclera, '#e6ddd0', mm('MULTIPLY', m.noise(30, 3, 0.5), 0.3))
    vessels = m.ramp(m.noise(18, 4, 0.55, 2.2), [(0.488, 0.0), (0.5, 1.0), (0.512, 0.0)])
    fine = m.ramp(m.noise(45, 3, 0.5, 2.5), [(0.494, 0.0), (0.5, 1.0), (0.506, 0.0)])
    away = m.ramp(r3, [(0.4333, 0.0), (0.8667, 1.0)])
    vein = mm('MULTIPLY', mm('MAXIMUM', vessels, mm('MULTIPLY', fine, 0.6)), away)
    sclera = m.mix(sclera, '#a8302c', mm('MULTIPLY', vein, 0.55))
    on_iris = m.ramp(r3, [(0.3600, 1.0), (0.3867, 0.0)])
    col = m.mix(sclera, iris, on_iris)
    rough = mm('ADD', 0.12, mm('MULTIPLY', on_iris, -0.06))
    height = mm('ADD', mm('MULTIPLY', fibres, mm('MULTIPLY', on_iris, 0.4)),
                mm('MULTIPLY', vein, 0.15))
    m.set(color=col, rough=rough, height=height, bump=0.25, bump_distance=0.0004)
    return m.m


def cornea_material():
    """The clear, wet cornea and tear film: refracts the iris (index 1.376) and carries the
    catchlights that make an eye look alive."""
    m = bpy.data.materials.new('cornea')
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (1, 1, 1, 1)
    b.inputs['Roughness'].default_value = 0.0
    b.inputs['IOR'].default_value = 1.376
    b.inputs['Transmission Weight'].default_value = 1.0
    b.inputs['Specular IOR Level'].default_value = 0.7
    if hasattr(m, 'surface_render_method'):
        m.surface_render_method = 'BLENDED'
    m['bake'] = False
    return m


def split_eyes(obj, spec, model_id):
    """Give the eyeball our iris and sclera, move the cornea shell to its own object, and bulge it
    a little in front of the iris, as a real cornea stands proud of the eyeball."""
    import bmesh
    obj.data.materials.clear()
    obj.data.materials.append(eye_material(spec))
    obj.data.materials.append(cornea_material())
    uv = obj.data.uv_layers.active.data
    for poly in obj.data.polygons:
        us = [uv[i].uv for i in poly.loop_indices]
        poly.material_index = 1 if all(u.x > 0.85 and u.y < 0.15 for u in us) else 0
    activate(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    obj.active_material_index = 1
    bpy.ops.object.material_slot_select()
    bpy.ops.mesh.separate(type='SELECTED')
    bpy.ops.object.mode_set(mode='OBJECT')
    cornea = next(o for o in bpy.context.selected_objects if o != obj)
    cornea.name = model_id + '_cornea'
    for o, keep in ((obj, 0), (cornea, 1)):
        mats = list(o.data.materials)
        o.data.materials.clear()
        o.data.materials.append(mats[keep])
        for poly in o.data.polygons:
            poly.material_index = 0
    # Bulge: per eye, push the front cap of the shell outwards, most at the centre of the iris.
    ball = [v.co.copy() for v in obj.data.vertices]
    for sign in (1, -1):
        pts = [p for p in ball if p.x * sign > 0]
        c = sum(pts, Vector()) / len(pts)
        radius = sum((p - c).length for p in pts) / len(pts)
        for v in cornea.data.vertices:
            if v.co.x * sign <= 0:
                continue
            dirn = (v.co - c).normalized()
            front = -dirn.y
            cap = max(0.0, (front - 0.86) / 0.14)
            v.co += dirn * (radius * 0.04 * cap ** 0.8)
    return obj, cornea


# ----------------------------------------------------------------------------- rags, teeth, beard
def mark_outfit_parts(obj):
    """Point attribute 'top': 1 on the upper garment, 0 on the trousers. Each loose piece of the
    outfit is one garment; the piece whose middle is higher is the top."""
    me = obj.data
    parent = list(range(len(me.vertices)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for e in me.edges:
        a, b = find(e.vertices[0]), find(e.vertices[1])
        if a != b:
            parent[a] = b
    groups = {}
    for v in me.vertices:
        groups.setdefault(find(v.index), []).append(v.index)
    big = sorted(groups.values(), key=len, reverse=True)
    mid = {id(g): sum(me.vertices[i].co.z for i in g) / len(g) for g in big}
    # Torn rags break into many pieces: each piece joins the garment whose height it is nearer.
    top_z = max(mid[id(g)] for g in big[:2]) if len(big) > 1 else mid[id(big[0])]
    low_z = min(mid[id(g)] for g in big[:2]) if len(big) > 1 else top_z - 1.0
    values = [0.0] * len(me.vertices)
    for g in big:
        is_top = abs(mid[id(g)] - top_z) < abs(mid[id(g)] - low_z)
        for i in g:
            values[i] = 1.0 if is_top else 0.0
    attr = me.attributes.new('top', 'FLOAT', 'POINT')
    attr.data.foreach_set('value', values)


def tear_outfit(obj, j, seed=7):
    """Turn a garment into rags by removing cloth: ragged cuffs and trouser legs cut off at mid
    shin, worn-through holes at knees, elbows, seat and here and there, then a fraying pass that
    nibbles the new edges. Real geometry, so it works in any engine without alpha."""
    from mathutils import noise
    rnd = random.Random(seed)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    # Finer cloth first, so torn edges are ragged rather than square.
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    bm.faces.ensure_lookup_table()
    hip_z = j['hips'].z
    holes = []
    for sd in 'LR':
        holes.append((j['kn' + sd] + Vector((0, -0.05, 0.01)), 0.045))
        holes.append((j['el' + sd] + Vector((0, 0.03, 0)), 0.03))
    holes.append((j['hips'] + Vector((0.06, 0.1, -0.07)), 0.035))
    verts = [v.co.copy() for v in bm.verts]
    for _ in range(5):
        holes.append((rnd.choice(verts), rnd.uniform(0.012, 0.025)))
    kill = set()
    for f in bm.faces:
        c = f.calc_center_median()
        jag = noise.noise(c * 40.0) * 0.5 + noise.noise(c * 140.0) * 0.3 + noise.noise(c * 400.0) * 0.2
        # Trousers: cut at mid shin, ragged.
        if c.z < hip_z - 0.25:
            sd = 'L' if c.x > 0 else 'R'
            cut = j['kn' + sd].z * 0.5 + j['an' + sd].z * 0.5 + 0.03 * jag
            if c.z < cut:
                kill.add(f)
                continue
        # Sleeves: torn off a hand's width above the wrist.
        for sd in 'LR':
            el, wr = j['el' + sd], j['wr' + sd]
            ab = wr - el
            t = (c - el).dot(ab) / ab.length_squared
            r = (c - (el + ab * max(0.0, min(1.0, t)))).length
            if r < 0.09 and t > 0.55 + 0.12 * jag:
                kill.add(f)
        for centre, rad in holes:
            if (c - centre).length < rad * (1.0 + 0.45 * jag):
                kill.add(f)
    bmesh.ops.delete(bm, geom=list(kill), context='FACES')
    # Fray: nibble a third of the faces on the new open edges, twice.
    for _ in range(2):
        edge = [f for f in bm.faces if any(e.is_boundary for e in f.edges)]
        bmesh.ops.delete(bm, geom=[f for f in edge if rnd.random() < 0.3], context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(obj.data)
    bm.free()
    for mat in obj.data.materials:
        mat.use_backface_culling = False


def rot_teeth(obj, spec, seed=11):
    """Old, neglected teeth: a few missing, the rest yellow to brown, dark caries in the pits and
    between teeth, brown tartar at the gum line, inflamed gums. Per tooth decay goes in a
    'decay' attribute the material reads."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    islands, seen = [], set()
    for v in bm.verts:
        if v in seen:
            continue
        stack, isl = [v], []
        seen.add(v)
        while stack:
            x = stack.pop()
            isl.append(x)
            for e in x.link_edges:
                o = e.other_vert(x)
                if o not in seen:
                    seen.add(o)
                    stack.append(o)
        islands.append(isl)
    islands.sort(key=len, reverse=True)
    gums, teeth = islands[0], islands[1:]
    # Missing: mostly visible ones (front half), never all neighbours.
    front = sorted(teeth, key=lambda t: sum(v.co.y for v in t) / len(t))[:14]
    gone = rnd.sample(front, min(spec['teeth']['missing'], len(front)))
    bmesh.ops.delete(bm, geom=[v for t in gone for v in t], context='VERTS')
    bm.to_mesh(obj.data)
    bm.free()
    # Per-vertex decay: 0 gum, 0.2..1 for teeth.
    attr = obj.data.attributes.new('decay', 'FLOAT', 'POINT')
    gum_ids = None
    lookup = {}
    me = obj.data
    # Rebuild islands on the cleaned mesh (vertex indices changed).
    adj = {i: set() for i in range(len(me.vertices))}
    for e in me.edges:
        a, b = e.vertices
        adj[a].add(b)
        adj[b].add(a)
    seen, groups = set(), []
    for i in range(len(me.vertices)):
        if i in seen:
            continue
        stack, g = [i], []
        seen.add(i)
        while stack:
            x = stack.pop()
            g.append(x)
            for o in adj[x]:
                if o not in seen:
                    seen.add(o)
                    stack.append(o)
        groups.append(g)
    groups.sort(key=len, reverse=True)
    values = [0.0] * len(me.vertices)
    for g in groups[1:]:
        level = min(1.0, max(0.15, rnd.random() ** 0.7 * spec['teeth']['rot'] * 1.2))
        for i in g:
            values[i] = level
    attr.data.foreach_set('value', values)


def teeth_material():
    m = Mat('teeth')
    mm = m.math
    decay = N(m.nt, 'Attribute', attribute_name='decay').outputs['Fac']
    tooth = m.ramp(decay, [(0.0, '#b85a58'), (0.08, '#e2d6b8'), (0.5, '#c8b07a'),
                           (1.0, '#8a6a3a')])
    gum = mm('LESS_THAN', decay, 0.05)
    tooth = m.mix(tooth, m.ramp(m.noise(60, 3, 0.6), [(0.3, '#a0484a'), (0.7, '#c06a64')]), gum)
    # Caries: dark pits and patches, more on the worst teeth.
    pits = m.ramp(m.noise(220, 4, 0.65), [(0.62, 0.0), (0.7, 1.0)])
    caries = mm('MULTIPLY', pits, mm('MULTIPLY', decay, mm('SUBTRACT', 1.0, gum)))
    tooth = m.mix(tooth, '#2a1a10', mm('MULTIPLY', caries, 1.2, clamp=True))
    # Tartar: brown-yellow crust where tooth meets gum (low pointiness = the crease).
    crease = m.ramp(m.geometry.outputs['Pointiness'], [(0.42, 1.0), (0.5, 0.0)])
    tooth = m.mix(tooth, '#6a5030', mm('MULTIPLY', crease, mm('MULTIPLY', decay, 0.8)))
    rough = mm('ADD', 0.25, mm('MULTIPLY', decay, 0.45))
    m.set(color=tooth, rough=rough, height=mm('MULTIPLY', caries, -0.5), bump=0.2,
          bump_distance=0.0004)
    return m.m


def strand_texture(name, seed=3, size=(256, 1024), strands=70):
    """A hair-card texture drawn from code: tapered, slightly wavy strands of mixed tone on
    transparent ground (RGB tone, A coverage). Root at v=0, tips towards v=1."""
    rnd = np.random.default_rng(seed)
    w, h = size
    img = np.zeros((h, w, 4), np.float32)
    ys = np.arange(h)
    for _ in range(strands):
        x0 = rnd.uniform(4, w - 4)
        length = rnd.uniform(0.6, 1.0) * h
        amp, freq, ph = rnd.uniform(1, 6), rnd.uniform(1.5, 4), rnd.uniform(0, 6.3)
        tone = rnd.uniform(0.55, 1.0)
        width = rnd.uniform(1.2, 3.0)
        for y in ys[: int(length)]:
            t = y / length
            x = x0 + amp * np.sin(ph + freq * t * np.pi) + 8 * t * rnd.normal(0, 0.05)
            r = width * (1 - t) ** 0.6 + 0.4
            lo, hi = int(max(0, x - r - 1)), int(min(w, x + r + 2))
            for xi in range(lo, hi):
                cover = max(0.0, 1 - abs(xi - x) / r)
                if cover > img[h - 1 - y, xi, 3]:
                    img[h - 1 - y, xi] = (tone, tone * 0.97, tone * 0.94, cover)
    image = bpy.data.images.new(name, w, h, alpha=True)
    image.pixels.foreach_set(img.ravel())
    image.pack()
    return image


def grow_beard(body, j, spec, model_id):
    """A long beard and moustache from hair cards grown on the face: roots in the beard zone,
    strands that leave the skin along its normal and fall under gravity, longest at the chin,
    shortest on the cheeks; the moustache droops over the lip corners. Cards are pushed out of
    the body so they never sink into the chin, neck or chest."""
    cfg = spec['beard']
    rnd = random.Random(5)
    eye = (j['eyeL'] + j['eyeR']) / 2
    mouth = j['mouth']
    tree = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
    down = Vector((0, 0, -1))
    roots = []
    for v in body.data.vertices:
        p, n = v.co, v.normal
        mouth_hole = abs(p.x) < 0.027 and abs(p.z - mouth.z) < 0.012 and p.y < mouth.y + 0.01
        moustache = (mouth.z + 0.008 < p.z < mouth.z + 0.022 and abs(p.x) < 0.034 and
                     p.y < mouth.y + 0.004)
        zone = beard_zone(p, j, eye, 0.0)
        if moustache:
            roots.append((p.copy(), n.copy(), 'm'))
        elif zone > 0.3 and not mouth_hole:
            roots.append((p.copy(), n.copy(), 'b'))
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new('UVMap')
    segs = 7
    for p0, n, kind in roots:
        for copy in range(1 if kind == 'b' else 2):
            jitter = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * 0.002
            if kind == 'm':
                side = 1.0 if p0.x > 0 else -1.0
                d = (n * 0.4 + down * 0.6 + Vector((side * 0.45, 0, 0))).normalized()
                length = rnd.uniform(0.035, 0.055) * (1.0 if abs(p0.x) > 0.01 else 0.7)
                width, gravity = 0.006, 0.25
            else:
                chin = max(0.0, 1 - abs(p0.x) / 0.05) * (1.0 if p0.z < mouth.z - 0.015 else 0.4)
                length = cfg['length'] * (0.3 + 0.7 * chin) * rnd.uniform(0.75, 1.1)
                d = (n * 0.55 + down * 0.45).normalized()
                width, gravity = 0.009, 0.45
            pts = [p0 + n * 0.0015 + jitter]
            for i in range(segs):
                d = (d + down * gravity * (i + 1) / segs +
                     Vector((rnd.uniform(-0.08, 0.08), rnd.uniform(-0.05, 0.05), 0))).normalized()
                q = pts[-1] + d * (length / segs)
                hit = tree.find_nearest(q)
                if hit[0] is not None:
                    loc, nrm = hit[0], hit[1]
                    clear = 0.002 + 0.012 * min(1.0, (j['neck'].z - q.z) / 0.1) if q.z < j[
                        'neck'].z else 0.002
                    if (q - loc).dot(nrm) < clear:
                        q = loc + nrm * clear
                pts.append(q)
            u0 = rnd.choice((0.0, 0.25, 0.5, 0.75))
            ring = []
            for i, q in enumerate(pts):
                t = i / segs
                dirn = (pts[min(i + 1, segs)] - pts[max(i - 1, 0)]).normalized()
                sidev = dirn.cross(n).normalized() * (width * (1 - 0.55 * t) / 2)
                ring.append((bm.verts.new(q - sidev), bm.verts.new(q + sidev), t))
            for i in range(segs):
                a, b_, ta = ring[i]
                c_, d_, tb = ring[i + 1]
                f = bm.faces.new((a, b_, d_, c_))
                for loop, uvv in zip(f.loops, ((u0, ta), (u0 + 0.25, ta), (u0 + 0.25, tb),
                                               (u0, tb))):
                    loop[uv_layer].uv = uvv
    mesh = bpy.data.meshes.new(model_id + '_beard')
    bm.to_mesh(mesh)
    bm.free()
    obj = link(bpy.data.objects.new(model_id + '_beard', mesh))
    # Material: strand texture tinted to the hair colour, greying, cut-out alpha.
    m = bpy.data.materials.new('beard')
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    tex = N(nt, 'TexImage', image=strand_texture(model_id + '_beard_strands'))
    tint = core.rgb(spec['hair_color'])
    grey = cfg.get('grey', 0.0)
    tint = tuple(c * (1 - grey) + 0.58 * grey for c in tint)
    mul = N(nt, 'MixRGB', blend_type='MULTIPLY')
    mul.inputs['Fac'].default_value = 1.0
    nt.links.new(tex.outputs['Color'], mul.inputs['Color1'])
    mul.inputs['Color2'].default_value = (*[min(1.0, c * 1.25) for c in tint], 1)
    nt.links.new(mul.outputs['Color'], b.inputs['Base Color'])
    cut = N(nt, 'Math', operation='ROUND')
    nt.links.new(tex.outputs['Alpha'], cut.inputs[0])
    nt.links.new(cut.outputs[0], b.inputs['Alpha'])
    b.inputs['Roughness'].default_value = 0.72
    b.inputs['Specular IOR Level'].default_value = 0.1
    if hasattr(m, 'surface_render_method'):
        m.surface_render_method = 'DITHERED'
    m.use_backface_culling = False
    m['bake'] = False
    mesh.materials.append(m)
    return obj


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
    # Finger and toe tips with the direction of their last joint, for the nails.
    j['nails'] = []
    for side, s in (('L', 'l'), ('R', 'r')):
        sx = 1.0 if side == 'L' else -1.0
        for f in range(1, 6):
            tip, last = c('joint-%s-finger-%d-4' % (s, f)), c('joint-%s-finger-%d-3' % (s, f))
            j['nails'].append((tip, (tip - last).normalized(), Vector((sx, 0.0, 0.25)).normalized(),
                               0.0055 if f > 1 else 0.007))
        for f in range(1, 6):
            names = ['joint-%s-toe-%d-%d' % (s, f, k) for k in (4, 3, 2, 1)]
            have = [n for n in names if n in groups]
            if len(have) < 2:
                continue
            tip, last = c(have[0]), c(have[1])
            j['nails'].append((tip, (tip - last).normalized(), Vector((0.0, 0.0, 1.0)),
                               0.008 if f == 1 else 0.0045))
    for side, s in (('L', 'l'), ('R', 'r')):
        j['eye' + side] = c('helper-%s-eye' % s)
    # The lips sit just in front of the upper teeth (MakeHuman's mouth joint is up at the nose).
    # Measured on the renders: the lip parting sits about 11 mm under the upper-teeth helper.
    j['mouth'] = c('helper-upper-teeth') + Vector((0, 0, -0.011))
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
def beard_zone(p, j, eye, lips):
    """Where a few days of beard grows, with soft edges: moustache, chin, jaw, the lower cheeks
    rising to the sideburns, and under the jaw down the neck."""
    def fade(v, width):
        return max(0.0, min(1.0, v / width))
    mz = j['mouth'].z
    side = min(1.0, abs(p.x) / 0.055)
    # The cheek line climbs from the mouth corners to the sideburns in front of the ears.
    top = mz + 0.014 + 0.03 * side ** 1.5 + (0.035 if abs(p.x) > 0.062 else 0.0) * fade(
        abs(p.x) - 0.062, 0.006)
    under_top = fade(top - p.z, 0.012)
    above_neck = fade(p.z - (mz - 0.105), 0.03)
    front = fade(eye.y + 0.075 - p.y, 0.015)
    # Keep it off the lips and the strip just under the lower lip thinner.
    off_lips = 1.0 - min(1.0, lips * 1.6)
    soul = 1.0 - 0.5 * fade(0.012 - abs(p.z - (mz - 0.016)), 0.006) * fade(0.012 - abs(p.x), 0.006)
    return under_top * above_neck * front * off_lips * soul


def limb(p, a, b, reach):
    """(t along a->b, distance from the segment) or None when p is too far from it."""
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    r = (p - (a + ab * t)).length
    return (t, r) if r < reach else None


def body_hair(p, n, j, side):
    """How much fine body hair grows at p (normal n) on one side, 0..1. Hair grows on the outer
    forearm most, the upper arm less, the back of the hand and the first finger joints a little;
    on the front and outside of the shins and thighs, and the top of the big toe. Palms and soles
    never have any."""
    sx = 1.0 if side == 'L' else -1.0
    out_arm = Vector((sx, 0.0, 0.6)).normalized()
    out_leg = Vector((sx * 0.5, -1.0, 0.0)).normalized()
    sh, el, wr, d = j['sh' + side], j['el' + side], j['wr' + side], j['d' + side]
    best = 0.0
    for a, b, lo, hi, out, reach in ((sh, el, 0.35, 0.45, out_arm, 0.07),
                                     (el, wr, 0.75, 1.0, out_arm, 0.07),
                                     (j['hip' + side], j['kn' + side], 0.35, 0.55, out_leg, 0.11),
                                     (j['kn' + side], j['an' + side], 0.7, 0.95, out_leg, 0.08)):
        hit = limb(p, a, b, reach)
        if not hit:
            continue
        t, _ = hit
        dorsal = 0.35 + 0.65 * max(0.0, n.dot(out))
        along = lo + (hi - lo) * math.sin(math.pi * min(1.0, t * 1.15))
        best = max(best, along * dorsal)
    # Back of the hand and the first joints of the fingers: only on the back.
    hit = limb(p, wr, wr + d * 0.17, 0.05)
    if hit:
        t, _ = hit
        back = max(0.0, n.dot(out_arm))
        amount = 0.45 * max(0.0, 1 - abs(t - 0.3) / 0.3) + 0.35 * max(0.0, 1 - abs(t - 0.62) / 0.08)
        best = max(best, amount * back ** 1.5)
    # The top of the big toe and the foot just behind it.
    toe = j['toe' + side] + Vector((-sx * 0.015, -0.02, 0.01))
    best = max(best, 0.4 * max(0.0, 1 - (p - toe).length / 0.03) * max(0.0, n.z))
    return best


def nape_hair(p, j):
    """Fine hair at the back of the neck, under the hairline, thinning downwards."""
    neck, head = j['neck'], j['head']
    if p.y < neck.y + 0.01:
        return 0.0
    top, bottom = head.z + 0.01, neck.z - 0.02
    v = max(0.0, min(1.0, (p.z - bottom) / (top - bottom)))
    side = max(0.0, 1 - abs(p.x) / 0.06)
    return v ** 1.5 * side * min(1.0, (p.y - neck.y - 0.01) / 0.02)


def paint_nails(body, j):
    """Attribute 'nails': R the nail plate, G the free edge at the tip (where dirt collects).
    A nail sits on the back of the last joint: near the tip, on the side the dorsal direction
    points to."""
    attr = body.data.color_attributes.new('nails', 'FLOAT_COLOR', 'POINT')
    data = []
    for v in body.data.vertices:
        p, n = v.co, v.normal
        plate = edge = 0.0
        for tip, axis, dorsal, size in j['nails']:
            q = p - tip
            if q.length > size * 2.2:
                continue
            along = q.dot(axis)                      # 0 at the tip joint, negative towards the hand
            side_ = (q - axis * along).length
            if n.dot(dorsal) < 0.15 or along < -size * 1.9 or along > size * 0.9:
                continue
            width = max(0.0, 1 - side_ / (size * 1.25))
            plate = max(plate, width * min(1.0, (along + size * 1.9) / (size * 0.5)))
            edge = max(edge, width * max(0.0, min(1.0, (along + size * 0.15) / (size * 0.5))))
        data += [plate, edge, 0.0, 1.0]
    attr.data.foreach_set('color', data)


def paint_scalp(body, j, hair):
    """Mark the skin that lies under the hair, so the shader paints a scalp there: the colour of
    the hair, roots and a soft hairline. Where cards lift off the head, hair shows, not bare skin
    (the game-art way to hide the gap between the hair and the face)."""
    attr = body.data.attributes.new('scalp', 'FLOAT', 'POINT')
    if hair is None:
        return
    deps = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(hair, deps)
    to_hair = hair.matrix_world.inverted() @ body.matrix_world
    turn = to_hair.to_3x3()
    eye = (j['eyeL'] + j['eyeR']) / 2
    values = []
    for v in body.data.vertices:
        p = v.co
        if p.z < eye.z + 0.005 and not (p.y > eye.y + 0.07 and p.z > j['neck'].z + 0.03):
            values.append(0.0)
            continue
        origin, ray = to_hair @ p, (turn @ v.normal).normalized()
        hits = 0
        for wobble in (Vector((0, 0, 0)), Vector((0.3, 0, 0)), Vector((-0.3, 0, 0)),
                       Vector((0, 0, 0.3)), Vector((0, 0, -0.3))):
            hit = tree.ray_cast(origin + ray * 0.0005, (ray + wobble).normalized(), 0.05)
            hits += hit[0] is not None
        values.append(hits / 5.0)
    attr.data.foreach_set('value', values)


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
        stubble = spec['stubble'] * beard_zone(p, j, eye, lips) if spec['stubble'] else 0.0
        freckle_zone = 1.0 if (p.z > j['chest'].z - 0.05) else 0.25
        data += [flush, lips, stubble, freckle_zone]
    layer.data.foreach_set('color', data)
    # A second mask for the fine hair of the arms: thickest on the outer forearm, lighter on the
    # upper arm, a little on the back of the hand.
    hz = body.data.attributes.new('hairzone', 'FLOAT', 'POINT')
    values = []
    for v in body.data.vertices:
        values.append(max(spec.get('body_hair', 0.0) * max(body_hair(v.co, v.normal, j, sd)
                                                            for sd in 'LR'),
                          max(0.45, spec.get('body_hair', 0.0)) * nape_hair(v.co, j)))
    hz.data.foreach_set('value', values)


def lips_shape(m, j):
    """The lips drawn per pixel round the mouth, so the bake gives them a crisp outline in the UV
    texture: a cupid's bow on top, a fuller lower lip, a darker parting line and fine vertical creases.
    Returns (mask, parting line, creases)."""
    mouth = j['mouth']
    half_w, up_h, low_h, soft = 0.024, 0.0075, 0.0095, 0.0018
    pos = N(m.nt, 'SeparateXYZ', {'Vector': N(m.nt, 'TexCoord').outputs['Object']})
    x, y, z = pos.outputs['X'], pos.outputs['Y'], pos.outputs['Z']
    mm = m.math
    u = mm('DIVIDE', x, half_w)
    dz = mm('SUBTRACT', z, mouth.z)
    span = mm('SQRT', mm('MAXIMUM', mm('SUBTRACT', 1.0, mm('MULTIPLY', u, u)), 0.0))
    au = mm('ABSOLUTE', u)
    bump = lambda at, w: mm('EXPONENT', mm('MULTIPLY', -1.0, mm('POWER', mm('DIVIDE', mm(
        'SUBTRACT', au, at), w), 2.0)))
    # Upper edge: two peaks either side of a small dip in the middle (the cupid's bow).
    upper = mm('SUBTRACT', mm('MULTIPLY', mm('MULTIPLY', span, up_h),
                               mm('ADD', 1.0, mm('MULTIPLY', bump(0.2, 0.13), 0.22))),
               mm('MULTIPLY', bump(0.0, 0.09), 0.0016))
    lower = mm('MULTIPLY', mm('POWER', span, 0.7), -low_h)
    inside_up = mm('DIVIDE', mm('SUBTRACT', upper, dz), soft, clamp=True)
    inside_low = mm('DIVIDE', mm('SUBTRACT', dz, lower), soft, clamp=True)
    front = mm('DIVIDE', mm('SUBTRACT', mouth.y - 0.004, y), 0.003, clamp=True)
    mask = mm('MULTIPLY', mm('MULTIPLY', inside_up, inside_low), front)
    parting = mm('MULTIPLY', mm('EXPONENT', mm('MULTIPLY', -1.0, mm('POWER', mm(
        'DIVIDE', mm('ADD', dz, 0.0004), 0.0009), 2.0))), mask)
    stretch = N(m.nt, 'Mapping', {'Vector': N(m.nt, 'TexCoord').outputs['Object']})
    stretch.inputs['Scale'].default_value = (1.0, 1.0, 0.12)
    crease = m.ramp(m.voronoi(1400, 'DISTANCE_TO_EDGE', co=stretch.outputs['Vector']),
                    [(0.0, 1.0), (0.06, 0.0)])
    return mask, parting, mm('MULTIPLY', crease, mask)


def lip_surface(m, j, spec):
    """Height, colour and roughness of the lips alone (mixed in by the lip mask)."""
    mm = m.math
    mouth = j['mouth']
    pos = N(m.nt, 'SeparateXYZ', {'Vector': N(m.nt, 'TexCoord').outputs['Object']})
    dz = mm('ABSOLUTE', mm('SUBTRACT', pos.outputs['Z'], mouth.z))
    near = m.ramp(mm('DIVIDE', dz, 0.012), [(0.05, 1.0), (0.85, 0.15)])
    # Furrows: cell edges of a voronoi squashed hard in height, so they run vertically; a little
    # distortion lets them wander and branch. Two sizes: ~1.2 mm and ~0.5 mm apart.
    warp = N(m.nt, 'Mapping', {'Vector': m.co})
    warp.inputs['Scale'].default_value = (1.0, 1.0, 0.07)
    # Offset by a small noise (up to ~0.3 mm) so the furrows wander instead of running straight.
    jitter = N(m.nt, 'VectorMath', {0: m.noise(900, 2, 0.5, 0.0, color=True),
                                    1: (0.0003, 0.0003, 0.0)}, operation='MULTIPLY')
    wob_v = N(m.nt, 'VectorMath', {0: warp.outputs['Vector'], 1: jitter.outputs['Vector']},
              operation='ADD')
    big = m.ramp(m.voronoi(820, 'DISTANCE_TO_EDGE', co=wob_v.outputs['Vector']),
                 [(0.0, 1.0), (0.06, 0.0)])
    small = m.ramp(m.voronoi(2000, 'DISTANCE_TO_EDGE', co=warp.outputs['Vector']),
                   [(0.0, 1.0), (0.05, 0.0)])
    furrow = mm('MULTIPLY', mm('MAXIMUM', big, mm('MULTIPLY', small, 0.45)), near)
    swell = m.noise(140, 3, 0.5)
    height = mm('SUBTRACT', mm('MULTIPLY', swell, 0.04), mm('MULTIPLY', furrow, 0.8))
    # Dry patches: paler, rougher, a few lifted flakes.
    dry = m.ramp(m.noise(260, 3, 0.6), [(0.7, 0.0), (0.82, 1.0)])
    flake = m.ramp(m.voronoi(1800, 'DISTANCE_TO_EDGE'), [(0.0, 1.0), (0.05, 0.0)])
    height = mm('ADD', height, mm('MULTIPLY', mm('MULTIPLY', dry, flake), 0.05))
    col = m.mix(spec['lips'], m.mix(spec['lips'], spec['skin'], 0.35), mm('MULTIPLY', dry, 0.4))
    col = m.mix(col, m.mix(spec['lips'], '#2a1210', 0.4), mm('MULTIPLY', furrow, 0.5))
    # Blood shows more at the centre of each lip, less at the corners.
    centre = m.ramp(mm('ABSOLUTE', mm('DIVIDE', pos.outputs['X'], 0.024)), [(0.0, 1.0), (1.0, 0.0)])
    col = m.mix(col, m.mix(spec['lips'], '#b03a3a', 0.25), mm('MULTIPLY', centre, 0.25))
    rough = mm('ADD', 0.34, mm('ADD', mm('MULTIPLY', dry, 0.15), mm('MULTIPLY', furrow, 0.12)))
    return height, col, rough


def blob(m, centre, radius, squash=(1.0, 1.0, 1.0)):
    """1 at a point of the body, fading to 0 at radius (object space), optionally squashed."""
    rel = N(m.nt, 'VectorMath', {0: N(m.nt, 'TexCoord').outputs['Object'], 1: tuple(centre)},
            operation='SUBTRACT')
    sq = N(m.nt, 'VectorMath', {0: rel.outputs['Vector'], 1: squash}, operation='MULTIPLY')
    dist = N(m.nt, 'VectorMath', {0: sq.outputs['Vector']}, operation='LENGTH').outputs['Value']
    return m.math('SUBTRACT', 1.0, m.math('DIVIDE', dist, radius), clamp=True)


def rare_spots(m, scale, rate, size, seed):
    """Sparse round spots: a few voronoi cells chosen by their random colour. Returns (spot, pick)."""
    shift = N(m.nt, 'Mapping', {'Vector': m.co})
    shift.inputs['Location'].default_value = (seed * 1.7, seed * 3.1, seed * 0.9)
    cell = m.voronoi(scale, 'F1', out='Color', co=shift.outputs['Vector'])
    pick = N(m.nt, 'SeparateColor', {'Color': cell})
    spot = m.math('MULTIPLY', m.ramp(pick.outputs[0], [(1 - rate, 0.0), (1 - rate + 0.002, 1.0)]),
                  m.ramp(m.voronoi(scale, 'F1', co=shift.outputs['Vector']),
                         [(0.0, 1.0), (size, 0.0)]))
    return spot, pick


def skin_imperfections(m, spec, j, base, height, rough, flush, lips):
    """What makes skin look lived in: blemishes and the marks they leave, a scar or two, broken
    capillaries, blotchy redness, shadows under the eyes, open pores and oil on the T-zone,
    dry patches. Returns the new (base, height, rough)."""
    mm = m.math
    # Blotchy, uneven redness at a hand's scale.
    blotch = m.ramp(m.noise(9, 3, 0.55, 1.4), [(0.55, 0.0), (0.72, 1.0)])
    base = m.mix(base, spec['flush'], mm('MULTIPLY', blotch, 0.1))
    # Active blemishes: small raised red bumps with a paler head, mostly on the face and back.
    pim, _ = rare_spots(m, 55, 0.02, 0.09, 1)
    head = m.ramp(m.voronoi(55, 'F1'), [(0.0, 1.0), (0.025, 0.0)])
    base = m.mix(base, '#a8443a', mm('MULTIPLY', pim, 0.5))
    base = m.mix(base, '#d8b08a', mm('MULTIPLY', mm('MULTIPLY', pim, head), 0.35))
    height = mm('ADD', height, mm('MULTIPLY', pim, 0.6))
    # Old marks: flat, faded brown-red spots left behind.
    mark, pick = rare_spots(m, 70, 0.03, 0.08, 2)
    tone = m.ramp(pick.outputs[1], [(0.0, '#8a4a3a'), (1.0, '#6a3e2c')])
    base = m.mix(base, tone, mm('MULTIPLY', mark, 0.3))
    # Small healed scars: thin pale lines, a little sunken and shinier.
    long = N(m.nt, 'Mapping', {'Vector': m.co})
    long.inputs['Scale'].default_value = (1.0, 1.0, 5.0)
    long.inputs['Rotation'].default_value = (0.4, 0.2, 0.7)
    scar_line = m.ramp(m.voronoi(12, 'DISTANCE_TO_EDGE', co=long.outputs['Vector']),
                       [(0.0, 1.0), (0.012, 0.0)])
    scar_zone, _ = rare_spots(m, 6, 0.12, 0.6, 3)
    scar = mm('MULTIPLY', scar_line, mm('MINIMUM', mm('MULTIPLY', scar_zone, 3.0), 1.0))
    base = m.mix(base, '#e8c8b4', mm('MULTIPLY', scar, 0.35))
    height = mm('SUBTRACT', height, mm('MULTIPLY', scar, 0.5))
    rough = mm('SUBTRACT', rough, mm('MULTIPLY', scar, 0.15))
    # Broken capillaries: thin red threads where the cheeks and nose flush.
    cap = m.ramp(m.noise(120, 2, 0.5, 2.5), [(0.485, 0.0), (0.5, 1.0), (0.515, 0.0)])
    base = m.mix(base, '#b0302a', mm('MULTIPLY', mm('MULTIPLY', cap, flush), 0.22))
    # Open pores and a little oil down the nose and across the forehead.
    eye = (j['eyeL'] + j['eyeR']) / 2
    tzone = mm('MAXIMUM', blob(m, eye + Vector((0, -0.04, -0.03)), 0.03, (1.6, 1.0, 0.8)),
               blob(m, eye + Vector((0, -0.025, 0.05)), 0.05, (0.6, 1.0, 1.2)))
    big = m.ramp(m.voronoi(1500, 'F1'), [(0.0, 1.0), (0.14, 0.0)])
    height = mm('SUBTRACT', height, mm('MULTIPLY', mm('MULTIPLY', big, tzone), 0.2))
    rough = mm('SUBTRACT', rough, mm('MULTIPLY', tzone, 0.05))
    # Dry, slightly ashy patches here and there (elbows, knees, knuckles end up in some).
    dry = m.ramp(m.noise(4, 3, 0.6, 0.8), [(0.62, 0.0), (0.75, 1.0)])
    base = m.mix(base, m.mix(spec['skin'], '#e0d4cc', 0.3), mm('MULTIPLY', dry, 0.18))
    rough = mm('ADD', rough, mm('MULTIPLY', dry, 0.12))
    flake = m.ramp(m.voronoi(900, 'DISTANCE_TO_EDGE'), [(0.0, 1.0), (0.05, 0.0)])
    height = mm('ADD', height, mm('MULTIPLY', mm('MULTIPLY', flake, dry), 0.25))
    # Nose: the oiliest skin. Tiny blackheads (rare, very small, dark), more of the pale grey-yellow
    # sebaceous filaments, both only on the nose and the creases beside it.
    nose = any_of(m, blob(m, eye.lerp(j['mouth'], 0.55) + Vector((0, -0.045, 0.0)), 0.028,
                          (1.0, 0.8, 0.9)),
                  blob(m, eye.lerp(j['mouth'], 0.3) + Vector((0, -0.04, 0.0)), 0.02, (1.6, 1.0, 0.8)))
    black, _ = rare_spots(m, 1900, 0.07, 0.22, 5)
    filament, _ = rare_spots(m, 1600, 0.16, 0.28, 6)
    base = m.mix(base, '#2b2219', mm('MULTIPLY', mm('MULTIPLY', black, nose), 0.65))
    base = m.mix(base, '#cbbd9e', mm('MULTIPLY', mm('MULTIPLY', filament, nose), 0.3))
    height = mm('SUBTRACT', height, mm('MULTIPLY', mm('MULTIPLY', black, nose), 0.3))
    # Knuckles: concentric folds over the finger joints, a little darker and redder.
    knuckles = any_of(m, *[blob(m, j['wr' + sd] + j['d' + sd] * k_, 0.03)
                           for sd in 'LR' for k_ in (0.095, 0.135, 0.16)])
    folds = m.ramp(m.wave(900, 3.0, 2.0, 'RINGS', 'SPHERICAL'), [(0.0, 1.0), (0.18, 0.0)])
    base = m.mix(base, m.mix(spec['skin2'], spec['flush'], 0.4), mm('MULTIPLY', mm(
        'MULTIPLY', folds, knuckles), 0.35))
    height = mm('SUBTRACT', height, mm('MULTIPLY', mm('MULTIPLY', folds, knuckles), 0.6))
    # Bare feet: thick yellowish horn on the soles, paler rough calluses on the heel and the ball of
    # the foot, fine cracks at the heel.
    nz = N(m.nt, 'SeparateXYZ', {'Vector': m.geometry.outputs['Normal']}).outputs['Z']
    pz = N(m.nt, 'SeparateXYZ', {'Vector': m.geometry.outputs['Position']}).outputs['Z']
    sole = mm('MULTIPLY', m.ramp(nz, [(-0.75, 1.0), (-0.3, 0.0)]),
              m.ramp(pz, [(0.03, 1.0), (0.06, 0.0)]))
    heel = any_of(m, *[blob(m, j['an' + sd] + Vector((0, 0.03, -0.07)), 0.045) for sd in 'LR'])
    ball = any_of(m, *[blob(m, j['toe' + sd] + Vector((0, 0.015, -0.02)), 0.04) for sd in 'LR'])
    callus = mm('MINIMUM', mm('ADD', sole, mm('MULTIPLY', mm('ADD', heel, ball), 0.6)), 1.0)
    base = m.mix(base, m.mix(spec['skin'], '#e8d4a0', 0.35), mm('MULTIPLY', callus, 0.4))
    rough = mm('ADD', rough, mm('MULTIPLY', callus, 0.2))
    cracks = m.ramp(m.voronoi(160, 'DISTANCE_TO_EDGE'), [(0.0, 1.0), (0.04, 0.0)])
    crack = mm('MULTIPLY', cracks, heel)
    base = m.mix(base, '#5a3a2a', mm('MULTIPLY', crack, 0.4))
    height = mm('SUBTRACT', height, mm('MULTIPLY', crack, 0.6))
    # Grime: a working life before running water. Dirt settles in creases and cavities (pointiness
    # is correct while baking in Cycles), gathers on hands, feet and the neck, and lies in faint
    # smudges elsewhere. Kept off the lips.
    g = spec.get('grime', 0.0)
    if g:
        cavity = mm('SUBTRACT', 1.0, m.pointiness(0.46, 0.52))
        parts = any_of(m, *[blob(m, j['wr' + sd] + j['d' + sd] * 0.08, 0.11) for sd in 'LR'],
                       *[blob(m, j['an' + sd] + Vector((0, -0.03, -0.04)), 0.12) for sd in 'LR'],
                       blob(m, j['neck'], 0.08, (0.9, 0.9, 1.4)))
        smudge = m.ramp(m.noise(7, 4, 0.6, 1.0), [(0.55, 0.0), (0.8, 1.0)])
        dirt = mm('ADD', mm('MULTIPLY', cavity, mm('ADD', 0.25, mm('MULTIPLY', parts, 0.75))),
                  mm('MULTIPLY', smudge, mm('ADD', 0.12, mm('MULTIPLY', parts, 0.3))))
        if g > 1.0:
            # Filthy: smudges everywhere, heavier on the face and hands; bare feet caked in mud up
            # the shins.
            big = m.ramp(m.noise(5, 4, 0.65, 0.8), [(0.4, 0.0), (0.7, 1.0)])
            dirt = mm('ADD', dirt, mm('MULTIPLY', big, 0.35 * (g - 1.0) * 2))
            pz = N(m.nt, 'SeparateXYZ', {'Vector': m.geometry.outputs['Position']}).outputs['Z']
            mud = mm('MULTIPLY', m.ramp(pz, [(0.0, 1.0), (0.25, 0.0)]),
                     m.ramp(m.noise(25, 4, 0.6), [(0.25, 0.55), (0.6, 1.0)]))
            dirt = mm('ADD', dirt, mm('MULTIPLY', mud, 1.4))
        dirt = mm('MULTIPLY', mm('MULTIPLY', dirt, g), mm('SUBTRACT', 1.0, lips), clamp=True)
        base = m.mix(base, '#4a3a2a', mm('MULTIPLY', dirt, 0.45))
        rough = mm('ADD', rough, mm('MULTIPLY', dirt, 0.15))
    return base, height, rough


def luminance(hex_colour):
    r, g, b = core.rgb(hex_colour)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def any_of(m, *masks):
    out = masks[0]
    for k in masks[1:]:
        out = m.math('MAXIMUM', out, k)
    return out


def skin_chroma(m, spec, j, base, flush):
    """The colours under the skin. Skin is not one colour: melanin (brown) sits on top, blood in the
    dermis (red where it carries oxygen, blue-purple where it does not), carotene and the thick
    horny layer (yellow), and veins seen through fat and tissue (blue-green, never true blue).
    Each acts as an absorber, so each is a gentle multiply. On darker skin melanin hides most of
    them, so they are scaled by how light the skin is. Portrait painters split the face in three:
    a golden forehead, a red middle (cheeks, nose, ears), a cool blue-green-grey lower third."""
    mm = m.math
    k = 0.45 + 0.55 * min(1.0, luminance(spec['skin']) / 0.5)
    tint = lambda col, fac: m.mix(base, col, mm('MULTIPLY', fac, k), 'MULTIPLY')
    eye = (j['eyeL'] + j['eyeR']) / 2
    mouth = j['mouth']
    # Large, slow blotches of each chromophore, out of step with each other.
    for scale, col, amount in ((3.5, '#ffc4b4', 0.55), (2.2, '#fff0c0', 0.6), (2.8, '#e4eedc', 0.5)):
        bl = m.ramp(m.noise(scale, 3, 0.55, 0.5), [(0.4, 0.0), (0.7, 1.0)])
        base = tint(col, mm('MULTIPLY', bl, amount))
    # Fine chromatic grain: tiny red, yellow and blue shifts, cell by cell.
    for scale, col, amount in ((420, '#ffcfc8', 0.5), (510, '#fff2cc', 0.45), (380, '#dde6f2', 0.4)):
        grain = m.ramp(m.noise(scale, 2, 0.5), [(0.45, 0.0), (0.7, 1.0)])
        base = tint(col, mm('MULTIPLY', grain, amount))
    # The face in thirds.
    forehead = blob(m, eye + Vector((0, -0.01, 0.055)), 0.06, (0.75, 1.0, 1.3))
    lower = blob(m, mouth + Vector((0, -0.01, -0.02)), 0.06, (0.85, 1.0, 1.0))
    base = tint('#fff0d8', mm('MULTIPLY', forehead, 0.6))
    base = tint('#ffb2a6', mm('MULTIPLY', flush, 0.6))
    base = tint('#d6e2de', mm('MULTIPLY', lower, 0.6 + 0.5 * spec['stubble']))
    # Blood comes up where skin is thin over bone or pressed and used: knuckles, elbows, knees,
    # heels and toes, fingertips, the tip of the nose and the ears (already in the flush mask).
    joints = []
    for sd in 'LR':
        joints += [blob(m, j['el' + sd], 0.05), blob(m, j['kn' + sd] + Vector((0, -0.04, 0)), 0.06),
                   blob(m, j['an' + sd], 0.07), blob(m, j['tip' + sd], 0.06),
                   blob(m, j['wr' + sd] + j['d' + sd] * 0.12, 0.06)]
    red_parts = any_of(m, *joints)
    base = tint('#ffaa9c', mm('MULTIPLY', red_parts, 0.5))
    # Thick, yellow horn on palms, soles and heels.
    yellow_parts = any_of(m, *[blob(m, j['wr' + sd] + j['d' + sd] * 0.07, 0.05) for sd in 'LR'],
                          *[blob(m, j['an' + sd] + Vector((0, 0.01, -0.06)), 0.07) for sd in 'LR'])
    base = tint('#ffe2a0', mm('MULTIPLY', yellow_parts, 0.35))
    # Veins: blue-green threads, clear where the skin is thin (temples, eyelids, inner wrist and
    # forearm, back of the hand, the top of the chest and the feet), barely there elsewhere.
    vein_zone = any_of(
        m, *[blob(m, j['eye' + sd] + Vector((0.035 if sd == 'L' else -0.035, 0.01, 0.01)), 0.03)
             for sd in 'LR'],
        *[blob(m, j['eye' + sd], 0.018) for sd in 'LR'],
        *[blob(m, j['el' + sd].lerp(j['wr' + sd], 0.65), 0.09, (1.0, 1.0, 1.0)) for sd in 'LR'],
        *[blob(m, j['wr' + sd] + j['d' + sd] * 0.05, 0.05) for sd in 'LR'],
        blob(m, j['chest'] + Vector((0, -0.08, 0.06)), 0.12, (0.7, 1.0, 1.2)),
        *[blob(m, j['an' + sd] + Vector((0, -0.05, -0.02)), 0.06) for sd in 'LR'])
    pattern = N(m.nt, 'Mapping', {'Vector': m.co})
    pattern.inputs['Scale'].default_value = (1.0, 1.0, 0.45)
    vein = m.ramp(m.noise(16, 4, 0.55, 1.6, co=pattern.outputs['Vector']),
                  [(0.475, 0.0), (0.5, 1.0), (0.525, 0.0)])
    vein_amount = mm('MULTIPLY', vein, mm('ADD', 0.12, mm('MULTIPLY', vein_zone, 0.6)))
    base = tint('#a8bcc8', vein_amount)
    # Deoxygenated blood pools under the eyes: a violet-blue cast.
    under = any_of(m, *[blob(m, j['eye' + sd] + Vector((0, -0.006, -0.016)), 0.02, (0.8, 1.0, 1.6))
                        for sd in 'LR'])
    base = tint('#c8b0b8', mm('MULTIPLY', under, 0.75))
    # Painters' temperature rule: the planes that face out (cheekbones, brow, nose bridge,
    # knuckles) read warm and rosy; the hollows and creases read cool, green-grey, and their darks
    # stay saturated reddish brown rather than grey (black "kills" skin colour). Pointiness gives
    # convex vs concave while baking in Cycles.
    curve = m.geometry.outputs['Pointiness']
    convex = m.ramp(curve, [(0.5, 0.0), (0.56, 1.0)])
    concave = m.ramp(curve, [(0.44, 1.0), (0.5, 0.0)])
    base = tint('#fff0e6', mm('MULTIPLY', convex, 0.5))
    base = tint('#e0e8de', mm('MULTIPLY', concave, 0.7))
    base = tint('#e8c4b4', mm('MULTIPLY', concave, 0.25))
    # Green is red's complement: faint green patches stop the reds from going one flat pink.
    mute = m.ramp(m.noise(11, 3, 0.6, 0.7), [(0.55, 0.0), (0.75, 1.0)])
    base = tint('#eef4e6', mm('MULTIPLY', mute, mm('ADD', 0.15, mm('MULTIPLY', flush, 0.5))))
    return base


def ellipse(m, centre, ax, az):
    """Normalised elliptic distance in the face plane (x, z) from centre: 1 on the ellipse."""
    rel = N(m.nt, 'VectorMath', {0: N(m.nt, 'TexCoord').outputs['Object'], 1: tuple(centre)},
            operation='SUBTRACT')
    sq = N(m.nt, 'VectorMath', {0: rel.outputs['Vector'], 1: (1.0 / ax, 0.0, 1.0 / az)},
           operation='MULTIPLY')
    return N(m.nt, 'VectorMath', {0: sq.outputs['Vector']}, operation='LENGTH').outputs['Value']


def eye_area(m, spec, j, base, height, rough):
    """Round each eye: the wet red of the inner corner (caruncle and the fold where the lids meet
    the nose), an even, slightly darker lash line along both lid margins, and the soft fold of the
    upper lid."""
    mm = m.math
    pos = N(m.nt, 'SeparateXYZ', {'Vector': N(m.nt, 'TexCoord').outputs['Object']})
    for sd in 'LR':
        c = j['eye' + sd]
        inward = -1.0 if sd == 'L' else 1.0
        # Only the front of the face, not the skin behind the eyeball.
        front = mm('DIVIDE', mm('SUBTRACT', c.y - 0.004, pos.outputs['Y']), 0.004, clamp=True)
        # Inner corner: a small wet red-pink core and a softer pink spreading onto the nose.
        corner = c + Vector((inward * 0.0155, -0.007, -0.001))
        core = mm('MULTIPLY', blob(m, corner, 0.0055), front)
        spread = mm('MULTIPLY', blob(m, corner + Vector((inward * 0.003, 0, 0)), 0.013,
                                     (1.0, 1.0, 1.3)), front)
        base = m.mix(base, m.mix(spec['flush'], '#d06a64', 0.5), mm('MULTIPLY', spread, 0.3))
        base = m.mix(base, '#b84e4a', mm('MULTIPLY', core, 0.7))
        rough = mm('SUBTRACT', rough, mm('MULTIPLY', core, 0.3))
        # Lash line: an even band on both lid margins where the lashes root.
        d = ellipse(m, c + Vector((0, 0, 0.0005)), 0.0148, 0.0068)
        band = mm('MULTIPLY', mm('SUBTRACT', 1.0, mm('DIVIDE', mm('ABSOLUTE', mm('SUBTRACT', d, 1.0)),
                                                    0.2), clamp=True), front)
        base = m.mix(base, m.mix(spec['skin2'], '#3a2620', 0.55), mm('MULTIPLY', band, 0.45))
        # Tear line: the wet meniscus along the lower lid margin, thicker at the bottom: a pink,
        # mirror-smooth strip that catches a thin bright line of light.
        lower = mm('DIVIDE', mm('SUBTRACT', c.z - 0.001, pos.outputs['Z']), 0.002, clamp=True)
        tear_d = ellipse(m, c + Vector((0, 0, 0.0005)), 0.0142, 0.0062)
        tear = mm('MULTIPLY', mm('MULTIPLY', mm('SUBTRACT', 1.0, mm('DIVIDE', mm(
            'ABSOLUTE', mm('SUBTRACT', tear_d, 0.97)), 0.07), clamp=True), lower), front)
        base = m.mix(base, '#c8706c', mm('MULTIPLY', tear, 0.5))
        rough = mm('SUBTRACT', rough, mm('MULTIPLY', tear, 0.45))
        # Brow: hair-coloured skin and fine roots under the eyebrow cards, so the brow reads full
        # and dense (thicker on men; a medieval man never plucked).
        outer = -inward
        brow_c = c + Vector((outer * 0.004, -0.008, 0.018))
        brow_d = ellipse(m, brow_c, 0.023, 0.0055)
        tilt = mm('DIVIDE', mm('SUBTRACT', pos.outputs['X'], brow_c.x), 0.023 * outer)
        arch = mm('SUBTRACT', 1.0, mm('MULTIPLY', mm('MAXIMUM', tilt, 0.0), 0.5))
        brow = mm('MULTIPLY', mm('MULTIPLY', mm('SUBTRACT', 1.0, brow_d, clamp=True), arch), front)
        roots = m.ramp(m.voronoi(2200, 'F1'), [(0.0, 1.0), (0.4, 0.0)])
        bcol = m.mix(spec['hair_color'], spec['skin2'], 0.35)
        base = m.mix(base, bcol, mm('MULTIPLY', brow, 0.3 * spec.get('brow', 0.4)))
        base = m.mix(base, spec['hair_color'], mm('MULTIPLY', mm('MULTIPLY', brow, roots),
                                                  0.35 * spec.get('brow', 0.4)))
        # Upper-lid fold: a soft darker crease above the lid, sunken a little.
        dz = mm('SUBTRACT', pos.outputs['Z'], c.z + 0.002)
        upper = mm('DIVIDE', dz, 0.003, clamp=True)
        fold_d = ellipse(m, c + Vector((inward * -0.001, 0, 0.002)), 0.0175, 0.0115)
        fold = mm('MULTIPLY', mm('MULTIPLY', mm('SUBTRACT', 1.0, mm('DIVIDE', mm(
            'ABSOLUTE', mm('SUBTRACT', fold_d, 1.0)), 0.13), clamp=True), upper), front)
        base = m.mix(base, m.mix(spec['skin2'], '#5a3a40', 0.3), mm('MULTIPLY', fold, 0.35))
        height = mm('SUBTRACT', height, mm('MULTIPLY', fold, 0.7))
    return base, height, rough


def age_marks(m, spec, j, base, height, rough):
    """What a face gains from 30 on, measured on reference photos of a 37-year-old man:
    horizontal forehead lines, vertical lines between the brows, crow's feet at the outer eye
    corners, fine crepey lines under the eyes, the nasolabial fold from the nose wing to the
    mouth corner, greyer (less red) temples and sides of the neck, a few small red papules on the
    nose. Scaled by spec['age'] (0 young .. 1 old)."""
    age = spec.get('age', 0.0)
    if not age:
        return base, height, rough
    mm = m.math
    eye = (j['eyeL'] + j['eyeR']) / 2
    mouth = j['mouth']
    co = N(m.nt, 'TexCoord').outputs['Object']

    def lines(scale, distortion, direction, sharp):
        w = N(m.nt, 'TexWave', {'Vector': co, 'Scale': scale, 'Distortion': distortion,
                                'Detail': 2.0}, wave_type='BANDS', bands_direction=direction)
        return m.ramp(w.outputs['Fac'], [(0.0, 1.0), (sharp, 0.0)])
    # Forehead: 4-6 shallow horizontal lines across the middle of the forehead.
    fore = blob(m, eye + Vector((0, -0.03, 0.045)), 0.045, (0.75, 1.0, 1.6))
    f_lines = mm('MULTIPLY', lines(14, 3.0, 'Z', 0.08), fore)
    # Glabella: two short vertical lines between the brows.
    glab = blob(m, eye + Vector((0, -0.04, 0.016)), 0.012, (1.6, 1.0, 0.7))
    g_lines = mm('MULTIPLY', lines(55, 1.5, 'X', 0.06), glab)
    # Crow's feet: fine lines fanning out from the outer eye corners.
    crow = any_of(m, *[blob(m, j['eye' + sd] + Vector((0.028 if sd == 'L' else -0.028, -0.004, 0.0)),
                            0.016, (0.9, 1.0, 1.0)) for sd in 'LR'])
    c_lines = mm('MULTIPLY', lines(90, 6.0, 'Z', 0.07), crow)
    # Under the eyes: thin, crepey skin with fine lines.
    under = any_of(m, *[blob(m, j['eye' + sd] + Vector((0, -0.006, -0.02)), 0.018, (0.8, 1.0, 1.8))
                        for sd in 'LR'])
    u_lines = mm('MULTIPLY', lines(160, 4.0, 'Z', 0.1), under)
    # Nasolabial fold: a soft groove and shadow from each nose wing to the mouth corner.
    fold = None
    pos = N(m.nt, 'SeparateXYZ', {'Vector': co})
    for sd in 'LR':
        sx = 1.0 if sd == 'L' else -1.0
        a = Vector((sx * 0.02, 0, eye.z + (mouth.z - eye.z) * 0.62))
        b = Vector((sx * 0.033, 0, mouth.z - 0.006))
        ab = b - a
        tx = mm('DIVIDE', mm('ADD', mm('MULTIPLY', mm('SUBTRACT', pos.outputs['X'], a.x), ab.x),
                                    mm('MULTIPLY', mm('SUBTRACT', pos.outputs['Z'], a.z), ab.z)),
                ab.length_squared)
        t_ = mm('MINIMUM', mm('MAXIMUM', tx, 0.0), 1.0)
        dx = mm('SUBTRACT', pos.outputs['X'], mm('ADD', a.x, mm('MULTIPLY', t_, ab.x)))
        dz = mm('SUBTRACT', pos.outputs['Z'], mm('ADD', a.z, mm('MULTIPLY', t_, ab.z)))
        d = mm('SQRT', mm('ADD', mm('MULTIPLY', dx, dx), mm('MULTIPLY', dz, dz)))
        front = mm('DIVIDE', mm('SUBTRACT', eye.y - 0.01, pos.outputs['Y']), 0.01, clamp=True)
        g = mm('MULTIPLY', mm('SUBTRACT', 1.0, mm('DIVIDE', d, 0.004), clamp=True), front)
        fold = g if fold is None else mm('MAXIMUM', fold, g)
    wrink = mm('ADD', mm('ADD', mm('MULTIPLY', f_lines, 0.8), mm('MULTIPLY', g_lines, 0.7)),
               mm('ADD', mm('MULTIPLY', c_lines, 0.7), mm('MULTIPLY', u_lines, 0.5)))
    height = mm('SUBTRACT', height, mm('MULTIPLY', mm('ADD', wrink, mm('MULTIPLY', fold, 1.2)), age))
    base = m.mix(base, spec['skin2'], mm('MULTIPLY', mm('ADD', mm('MULTIPLY', wrink, 0.25),
                                                       mm('MULTIPLY', fold, 0.45)), age))
    # Temples and the sides of the neck read greyer and less red than the cheeks.
    grey = any_of(m, *[blob(m, j['eye' + sd] + Vector((0.05 if sd == 'L' else -0.05, 0.02, 0.0)),
                            0.03) for sd in 'LR'],
                  *[blob(m, j['neck'] + Vector((0.05 if sd == 'L' else -0.05, 0.0, 0.0)), 0.05)
                    for sd in 'LR'])
    base = m.mix(base, m.mix(base, '#a09490', 0.5), mm('MULTIPLY', grey, 0.35))
    # A few small red papules on the nose.
    nose = blob(m, eye.lerp(mouth, 0.55) + Vector((0, -0.045, 0.0)), 0.028, (1.0, 0.8, 0.9))
    pap, _ = rare_spots(m, 600, 0.04, 0.2, 9)
    base = m.mix(base, '#b84848', mm('MULTIPLY', mm('MULTIPLY', pap, nose), 0.55 * min(1.0, age * 2)))
    return base, height, rough


def porosity(m, j, lips):
    """0 (smooth: eyelids, under the eyes, lips) .. 1 (the nose): how open and deep the pores are.
    The body sits at 0.4; nose, inner cheeks, forehead and chin rise; temples, jaw sides and the
    neck fall a little."""
    mm = m.math
    eye = (j['eyeL'] + j['eyeR']) / 2
    mouth = j['mouth']
    nose = any_of(m, blob(m, eye.lerp(mouth, 0.55) + Vector((0, -0.045, 0.0)), 0.03, (1.0, 0.8, 0.9)),
                  blob(m, eye.lerp(mouth, 0.3) + Vector((0, -0.04, 0.0)), 0.022, (1.6, 1.0, 0.8)))
    malar = any_of(m, *[blob(m, j['eye' + sd] + Vector((0.006 if sd == 'L' else -0.006, -0.02, -0.035)),
                             0.03) for sd in 'LR'])
    forehead = blob(m, eye + Vector((0, -0.025, 0.05)), 0.05, (0.7, 1.0, 1.3))
    chin = blob(m, mouth + Vector((0, -0.012, -0.035)), 0.025)
    eyes = any_of(m, *[blob(m, j['eye' + sd] + Vector((0, -0.004, -0.004)), 0.024, (0.85, 1.0, 1.25))
                       for sd in 'LR'])
    temples = any_of(m, *[blob(m, j['eye' + sd] + Vector((0.045 if sd == 'L' else -0.045, 0.015, 0.01)),
                               0.03) for sd in 'LR'])
    neck = blob(m, j['neck'] + Vector((0, -0.03, 0.0)), 0.07, (0.9, 1.0, 1.3))
    p = mm('ADD', 0.4, mm('MULTIPLY', nose, 0.6))
    p = mm('ADD', p, mm('MULTIPLY', malar, 0.45))
    p = mm('ADD', p, mm('MULTIPLY', forehead, 0.35))
    p = mm('ADD', p, mm('MULTIPLY', chin, 0.3))
    p = mm('SUBTRACT', p, mm('MULTIPLY', eyes, 0.45))
    p = mm('SUBTRACT', p, mm('MULTIPLY', temples, 0.15))
    p = mm('SUBTRACT', p, mm('MULTIPLY', neck, 0.12))
    p = mm('MULTIPLY', p, mm('SUBTRACT', 1.0, lips), clamp=True)
    # A little random unevenness, so a zone is never perfectly uniform.
    wobble = m.math('MULTIPLY_ADD', m.noise(12, 2, 0.5), 0.3, 0.85)
    return mm('MULTIPLY', p, wobble, clamp=True)


def skin_material(spec, j):
    m = Mat('skin', scale=1.0)
    attr = N(m.nt, 'Attribute', attribute_name='masks')
    sep = N(m.nt, 'SeparateColor', {'Color': attr.outputs['Color']})
    flush, stubble = sep.outputs['Red'], sep.outputs['Blue']
    lips, parting, crease = lips_shape(m, j)
    zone = attr.outputs['Alpha']
    # Pores are not the same everywhere: the face has porous and smooth zones (see the
    # realistic-skin skill, "Porosity map"). Visible pores run ~200-300 per cm2 (0.6-0.7 mm apart,
    # openings 40-80 um, wider on the nose); the eyelids and under the eyes are almost poreless
    # with very fine crossing wrinkles; the lips have none.
    por = porosity(m, j, lips)
    smooth = m.math('SUBTRACT', 1.0, por)
    pore_cells = m.voronoi(1800, 'F1')
    pore_r = m.math('MULTIPLY_ADD', por, 0.07, 0.04)
    pores = m.math('MULTIPLY', m.math('SUBTRACT', 1.0, m.math('DIVIDE', pore_cells, pore_r),
                                      clamp=True), por)
    pores2 = m.ramp(m.voronoi(3800, 'F1'), [(0.0, 1.0), (0.1, 0.0)])
    lines = m.ramp(m.voronoi(1400, 'DISTANCE_TO_EDGE'), [(0.0, 1.0), (0.03, 0.0)])
    fine_lines = m.ramp(m.voronoi(2600, 'DISTANCE_TO_EDGE'), [(0.0, 1.0), (0.04, 0.0)])
    relief = m.noise(60, 4, 0.6)
    texture = m.math('ADD', m.math('MULTIPLY', pores, 0.6),
                     m.math('ADD', m.math('MULTIPLY', m.math('MULTIPLY', pores2, por), 0.18),
                            m.math('MULTIPLY', lines, m.math('MULTIPLY_ADD', por, 0.12, 0.06))))
    # Smooth thin skin: fine crossing lines instead of pores.
    texture = m.math('ADD', texture, m.math('MULTIPLY', m.math('MULTIPLY', fine_lines, smooth), 0.12))
    height = m.math('SUBTRACT', m.math('MULTIPLY', relief, m.math('MULTIPLY_ADD', por, 0.15, 0.12)),
                    texture)
    # Colour: melanin unevenness, blood beneath, veins, freckles and moles.
    base = m.ramp(m.noise(5, 5, 0.6), [(0.3, spec['skin2']), (0.7, spec['skin'])])
    base = m.mix(base, m.mix(spec['skin'], spec['skin2'], 0.5), m.math(
        'MULTIPLY', m.noise(30, 4, 0.6), 0.25))
    base = m.mix(base, spec['flush'], m.math('MULTIPLY', flush, 0.28))
    base = skin_chroma(m, spec, j, base, flush)
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
    # The lip colour is richer at the centre and fades a touch into the skin at the corners.
    base = m.mix(base, spec['lips'], m.math('MULTIPLY', lips, 0.88))
    base = m.mix(base, '#2a1210', m.math('MULTIPLY', parting, 0.45))
    base = m.mix(base, spec['skin2'], m.math('MULTIPLY', crease, 0.15))
    if spec['stubble']:
        # Several days of growth, uneven: denser on the chin and moustache, thin patches on the
        # cheeks, a grey-blue shadow of hair under the skin and short dark hairs on top.
        patch = m.ramp(m.noise(28, 3, 0.6, 0.6), [(0.35, 0.45), (0.65, 1.0)])
        grow = m.math('MULTIPLY', stubble, patch)
        base = m.mix(base, m.mix(spec['skin2'], '#4a5058', 0.5), m.math('MULTIPLY', grow, 0.42))
        hairs = m.ramp(m.voronoi(1800, 'F1'), [(0.0, 1.0), (0.4, 0.0)])
        fine = m.ramp(m.voronoi(3400, 'F1'), [(0.0, 1.0), (0.35, 0.0)])
        dots = m.math('MULTIPLY', grow, m.math('MAXIMUM', hairs, m.math('MULTIPLY', fine, 0.7)))
        base = m.mix(base, m.mix(spec['hair_color'], '#1a1410', 0.4), m.math('MULTIPLY', dots, 0.6))
        height = m.math('ADD', height, m.math('MULTIPLY', dots, 0.2))
    base = m.mix(base, spec['skin2'], m.math('MULTIPLY', pores, 0.2))
    rough = m.math('ADD', m.math('ADD', 0.56, m.math('MULTIPLY', pores, 0.1)),
                   m.math('MULTIPLY', lips, -0.18))
    height = m.math('SUBTRACT', height, m.math('ADD', m.math('MULTIPLY', crease, 0.15),
                                               m.math('MULTIPLY', parting, 0.5)))
    base, height, rough = skin_imperfections(m, spec, j, base, height, rough, flush, lips)
    base, height, rough = eye_area(m, spec, j, base, height, rough)
    base, height, rough = age_marks(m, spec, j, base, height, rough)
    # Scalp under the hair: hair-coloured skin, dense roots, a hairline broken up by noise.
    scalp = N(m.nt, 'Attribute', attribute_name='scalp').outputs['Fac']
    edge = m.ramp(m.noise(70, 3, 0.6), [(0.3, 0.0), (0.7, 1.0)])
    cover = m.math('MULTIPLY', m.ramp(scalp, [(0.15, 0.0), (0.75, 1.0)]),
                   m.math('ADD', 0.55, m.math('MULTIPLY', edge, 0.45)))
    roots = m.ramp(m.voronoi(2600, 'F1'), [(0.0, 1.0), (0.35, 0.0)])
    base = m.mix(base, m.mix(spec['hair_color'], spec['skin2'], 0.25), m.math('MULTIPLY', cover, 0.8))
    base = m.mix(base, m.mix(spec['hair_color'], '#000000', 0.3),
                 m.math('MULTIPLY', m.math('MULTIPLY', cover, roots), 0.6))
    rough = m.math('ADD', rough, m.math('MULTIPLY', cover, 0.2))
    # Nails: a smooth, pinker plate over the nail bed, a paler free edge; dirt packed under and
    # round the tip on a dirty character.
    nails = N(m.nt, 'SeparateColor', {'Color': N(m.nt, 'Attribute', attribute_name='nails',
                                                  attribute_type='GEOMETRY').outputs['Color']})
    plate, tip = nails.outputs['Red'], nails.outputs['Green']
    base = m.mix(base, m.mix(spec['skin'], '#f0c8bc', 0.5), m.math('MULTIPLY', plate, 0.6))
    base = m.mix(base, '#efe2d0', m.math('MULTIPLY', tip, 0.5))
    rough = m.math('SUBTRACT', rough, m.math('MULTIPLY', plate, 0.25))
    height = m.math('ADD', height, m.math('MULTIPLY', plate, 0.25))
    if spec.get('nail_dirt'):
        grime_n = m.ramp(m.noise(900, 3, 0.6), [(0.3, 0.55), (0.7, 1.0)])
        base = m.mix(base, '#2a1e14', m.math('MULTIPLY', m.math('MULTIPLY', tip, grime_n),
                                             0.9 * spec['nail_dirt']))
        base = m.mix(base, '#4a3a2a', m.math('MULTIPLY', plate, 0.25 * spec['nail_dirt']))
    if spec.get('body_hair'):
        # Fine arm hair: soft darker patches made of short strokes laid along the arm.
        zone = N(m.nt, 'Attribute', attribute_name='hairzone').outputs['Fac']
        streak = N(m.nt, 'Mapping', {'Vector': m.co})
        streak.inputs['Scale'].default_value = (0.25, 0.25, 1.0)
        strands = m.ramp(m.noise(900, 2, 0.5, 0.3, co=streak.outputs['Vector']),
                         [(0.58, 0.0), (0.68, 1.0)])
        patch = m.ramp(m.noise(18, 3, 0.6), [(0.3, 0.4), (0.7, 1.0)])
        fur = m.math('MULTIPLY', zone, patch)
        base = m.mix(base, m.mix(spec['skin2'], spec['hair_color'], 0.25),
                     m.math('MULTIPLY', fur, 0.18))
        base = m.mix(base, m.mix(spec['hair_color'], spec['skin2'], 0.35),
                     m.math('MULTIPLY', m.math('MULTIPLY', fur, strands), 0.35))
        height = m.math('ADD', height, m.math('MULTIPLY', m.math('MULTIPLY', fur, strands), 0.12))
    # Lips have their own surface (see the skill, "Lips (study)"): no pores and none of the skin's
    # crossing lines; vertical furrows perpendicular to the parting, closer and deeper near it and
    # fading at the vermilion border, branching here and there; smooth, wet ridges between them;
    # small drier patches, most on the lower lip.
    lip_h, lip_col, lip_rough = lip_surface(m, j, spec)
    keep = m.math('SUBTRACT', 1.0, lips)
    height = m.math('ADD', m.math('MULTIPLY', height, keep), m.math('MULTIPLY', lip_h, lips))
    base = m.mix(base, lip_col, lips)
    rough = m.math('ADD', m.math('MULTIPLY', rough, keep), m.math('MULTIPLY', lip_rough, lips))
    base = m.mix(base, '#2a1210', m.math('MULTIPLY', parting, 0.45))
    height = m.math('SUBTRACT', height, m.math('MULTIPLY', parting, 0.5))
    m.set(color=base, rough=rough, height=height, bump=0.36, bump_distance=0.0005)
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
    if cap.data.attributes.get('hairzone'):
        cap.data.attributes.remove(cap.data.attributes['hairzone'])
    if cap.data.attributes.get('scalp'):
        cap.data.attributes.remove(cap.data.attributes['scalp'])
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
    if dup.data.attributes.get('hairzone'):
        dup.data.attributes.remove(dup.data.attributes['hairzone'])
    if dup.data.attributes.get('scalp'):
        dup.data.attributes.remove(dup.data.attributes['scalp'])
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
    # The masks hide the helpers and the skin under the clothes: apply them. Torn clothes need the
    # skin under them, so a ragged character keeps it (only the helpers go).
    for mod in list(body.modifiers):
        if mod.type == 'MASK' and (mod.vertex_group == 'body' or not spec.get('keep_skin')):
            bpy.ops.object.modifier_apply(modifier=mod.name)
        else:
            body.modifiers.remove(mod)
    body.vertex_groups.clear()
    body.parent = None
    body.name = model_id
    shade(body)
    height = max(v.co.z for v in body.data.vertices)
    paint_masks(body, j, spec)
    paint_scalp(body, j, next((o for k, o, _ in assets if k == 'Hair'), None))
    paint_nails(body, j)
    body.data.materials.clear()
    body.data.materials.append(skin_material(spec, j))
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
        if kind == 'Teeth' and spec.get('teeth'):
            mat = teeth_material()
        frozen = freeze(obj, name, mat)
        if kind == 'Teeth' and spec.get('teeth'):
            rot_teeth(frozen, spec)
        if name.endswith('_outfit') and spec.get('rags'):
            tear_outfit(frozen, j)
        if name.endswith('_outfit'):
            mark_outfit_parts(frozen)
        if kind == 'Eyes':
            ball, cornea = split_eyes(frozen, spec, model_id)
            parts += [('Eyes', ball), ('Cornea', cornea)]
            continue
        parts.append((kind, frozen))
    if spec.get('beard'):
        parts.append(('Beard', grow_beard(body, j, spec, model_id)))
    arm = (j['elL'] - j['shL']).normalized()
    rest = math.acos(max(-1, min(1, arm.dot(Vector((0, 0, -1))))))
    human.REST_DOWN = rest - 0.06
    human.ARM_ORDER = 'YXZ'
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
                # Long sleeves must follow the forearm, so only a short-sleeved outfit drops it.
                drop = ('Hand', 'Index', 'Middle', 'Ring', 'Pinky', 'Thumb') + (
                    () if spec.get('rags') else ('ForeArm',))
                if group.name.split('.')[0].rstrip('0123456789') in drop:
                    obj.vertex_groups.remove(group)
            activate(obj)
            bpy.ops.object.vertex_group_normalize_all(lock_active=False)
            clothes.append(obj)
        else:
            rig.bind_rigid(obj, 'Jaw' if kind in ('Tongue',) else 'Head')
            rigid.append(obj)
    bpy.data.objects.remove(full)
    # Export the Root bone (it has no skin weights, so making it a deform bone changes nothing on
    # the mesh) so games get a root-motion track.
    rig.obj.data.bones['Root'].use_deform = True
    import game_clips
    s['manifest'] = []
    s['more_clips'] = lambda rig_, k_, idle_: s['manifest'].extend(game_clips.add_game_clips(rig_, k_))
    human.animate(rig, s, height / 1.75)
    rig.manifest = s['manifest']
    return rig, body, clothes, rigid


def bake_all(model_id, body, clothes, rigid=()):
    bake_atlas(body, 4096, name=model_id + '_skin', do_unwrap=False, ao_samples=16)
    # The eyes bake under their lids (the lids' occlusion is the shadow on the top of the eyeball);
    # the clear cornea is hidden meanwhile so it does not occlude the eyeball it covers.
    corneas = [o for o in rigid if o.name.endswith('_cornea')]
    for o in corneas:
        o.hide_render = True
    for o in rigid:
        if o.name.endswith('_eyes'):
            bake_atlas(o, 1024, name=model_id + '_eyes', do_unwrap=False, ao_samples=16)
    for o in corneas:
        o.hide_render = False
    for o in rigid:
        if o.name.endswith('_teeth') and any(m_.get('bake', True) for m_ in o.data.materials if m_):
            bake_atlas(o, 512, name=model_id + '_teeth', do_unwrap=False, ao_samples=8)
    for c in clothes:
        if c.name.endswith('_outfit') or c.name.endswith('_boots'):
            bake_atlas(c, 2048, name=model_id + '_outfit', do_unwrap=False, ao_samples=8)
    # Skin lets light in: only the renders here use it, the web player draws the baked colour.
    for mat in body.data.materials:
        b = mat.node_tree.nodes.get('Principled BSDF')
        if b:
            b.inputs['Subsurface Weight'].default_value = 0.35
            # Peach fuzz: the fine vellus hair all over the skin gives a soft, velvety rim glow.
            b.inputs['Sheen Weight'].default_value = 0.1
            b.inputs['Sheen Roughness'].default_value = 0.45
            b.inputs['Sheen Tint'].default_value = (1.0, 0.93, 0.86, 1.0)
            b.inputs['Subsurface Radius'].default_value = (1.0, 0.35, 0.18)
            b.inputs['Subsurface Scale'].default_value = 0.0035


def shoot(path, j_head, height, size=(900, 1100), portrait=False, samples=96, frame=1, rig=None,
          clip=2):
    scene = bpy.context.scene
    if rig is not None:
        ad = rig.obj.animation_data
        # A clip by name (or index): the portrait and full shots must not depend on clip order.
        action = next(a for a in rig.actions if a.name == clip) if isinstance(clip, str) else rig.actions[clip]
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
    # REAL_FAST=1: skip the bakes and the renders (a quick rig and animation check).
    fast = os.environ.get('REAL_FAST') == '1'
    for model_id in ids:
        rig, body, clothes, rigid = build(model_id)
        if not fast:
            bake_all(model_id, body, clothes, rigid)
        rig.obj.name = model_id + '-rig'
        core.export(os.path.join(out, 'real-' + model_id + '.glb'))
        import json
        with open(os.path.join(out, 'real-' + model_id + '.anim.json'), 'w') as fh:
            json.dump(dict(model='real-' + model_id + '.glb', fps=core.FPS, facing='-Y (Blender), +Z (glTF)',
                           root_bone='Root', clips=rig.manifest), fh, indent=1)
        if fast:
            print('BUILT', model_id, '(fast)', flush=True)
            continue
        eye = None
        for o in rigid:
            if o.name.endswith('_eyes'):
                eye = sum((v.co for v in o.data.vertices), Vector()) / len(o.data.vertices)
                break
        height = max(v.co.z for v in body.data.vertices)
        shoot(os.path.join(shots, model_id + '-portrait.jpg'), eye, height, (900, 1100), True,
              rig=rig, clip='Idle', frame=30)
        shoot(os.path.join(shots, model_id + '-full.jpg'), eye, height, (900, 1200), False,
              samples=64, rig=rig, clip='Walk in Place', frame=8)
        print('BUILT', model_id, flush=True)


if __name__ == '__main__':
    main(sys.argv[1:])
