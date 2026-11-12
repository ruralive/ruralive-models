"""Shared Blender (bpy) helpers for the cinema model set.

Every model is built from code: geometry, a procedural material per surface, one armature,
named animation clips. The procedural materials are baked into a single PBR atlas (base
colour, normal, occlusion/roughness/metallic, emission) so the exported GLB is self-contained.
"""
import math
import os
import random

import bpy  # noqa: I001 (bpy must load before bmesh)
import bmesh
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector, noise

TAU = math.tau
FPS = 24


# ----------------------------------------------------------------------------- scene
def reset(seed=1):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.render.fps = FPS
    scene.unit_settings.system = 'METRIC'
    random.seed(seed)
    np.random.seed(seed)
    return scene


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def activate(obj, others=()):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    for o in others:
        o.select_set(True)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    return obj


def new_object(name, verts, faces, material=None, smooth=True):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    mesh.update()
    obj = link(bpy.data.objects.new(name, mesh))
    if material:
        mesh.materials.append(material)
    if smooth:
        shade(obj)
    return obj


def shade(obj, smooth=True):
    obj.data.polygons.foreach_set('use_smooth', [smooth] * len(obj.data.polygons))
    obj.data.update()
    return obj


def from_bmesh(name, bm, material=None, smooth=True):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = link(bpy.data.objects.new(name, mesh))
    if material:
        mesh.materials.append(material)
    if smooth:
        shade(obj)
    return obj


def place(obj, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), apply=True):
    """Move, rotate (XYZ euler, radians) and scale an object; bakes it into the mesh."""
    if isinstance(scale, (int, float)):
        scale = (scale,) * 3
    m = Matrix.LocRotScale(Vector(loc), Euler(rot), Vector(scale))
    if apply:
        obj.data.transform(m)
        obj.data.update()
    else:
        obj.matrix_world = m @ obj.matrix_world
    return obj


def modifier(obj, kind, apply=True, **props):
    mod = obj.modifiers.new(kind.lower(), kind)
    for key, value in props.items():
        setattr(mod, key, value)
    if apply:
        activate(obj)
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def subdivide(obj, levels=2):
    return modifier(obj, 'SUBSURF', levels=levels, render_levels=levels)


def bevel(obj, width=0.01, segments=2, angle=math.radians(35)):
    return modifier(obj, 'BEVEL', width=width, segments=segments, limit_method='ANGLE',
                    angle_limit=angle, harden_normals=False)


def solidify(obj, thickness=0.01, offset=-1):
    return modifier(obj, 'SOLIDIFY', thickness=thickness, offset=offset)


def remesh(obj, voxel=0.02, smooth=True):
    modifier(obj, 'REMESH', mode='VOXEL', voxel_size=voxel, use_smooth_shade=smooth)
    return obj


def smooth(obj, factor=0.5, repeat=4):
    return modifier(obj, 'SMOOTH', factor=factor, iterations=repeat)


def decimate(obj, ratio=0.5):
    return modifier(obj, 'DECIMATE', ratio=ratio)


def join(objs, name=None):
    objs = [o for o in objs if o is not None]
    if len(objs) > 1:
        activate(objs[0], objs[1:])
        bpy.ops.object.join()
    if name:
        objs[0].name = name
        objs[0].data.name = name
    return objs[0]


def copy(obj, loc=None, rot=None, scale=None):
    dup = link(obj.copy())
    dup.data = obj.data.copy()
    if loc is not None or rot is not None or scale is not None:
        place(dup, loc or (0, 0, 0), rot or (0, 0, 0), scale or (1, 1, 1))
    return dup


def set_material(obj, material):
    obj.data.materials.clear()
    obj.data.materials.append(material)
    return obj


def tag(obj, bone):
    """Remember which bone a rigid part follows."""
    obj['bone'] = bone
    return obj


def displace(obj, fn):
    """Move each vertex with fn(co, normal) -> Vector offset."""
    mesh = obj.data
    for v in mesh.vertices:
        v.co += fn(v.co, v.normal)
    mesh.update()
    return obj


def fbm(p, scale=1.0, octaves=5, lacunarity=2.0, gain=0.5, offset=(0, 0, 0)):
    q = (Vector(p) + Vector(offset)) * scale
    total, amp = 0.0, 1.0
    for _ in range(octaves):
        total += amp * noise.noise(q)
        q *= lacunarity
        amp *= gain
    return total


def ridged(p, scale=1.0, octaves=5, offset=(0, 0, 0)):
    q = (Vector(p) + Vector(offset)) * scale
    total, amp = 0.0, 1.0
    for _ in range(octaves):
        total += amp * (1 - abs(noise.noise(q))) ** 2
        q *= 2.03
        amp *= 0.5
    return total


def roughen(obj, amount=0.02, scale=3.0, octaves=4, seed=0):
    off = (seed * 13.7, seed * 7.3, seed * 3.1)
    return displace(obj, lambda co, n: n * amount * fbm(co, scale, octaves, offset=off))


# ----------------------------------------------------------------------------- primitives
def box(size=(1, 1, 1), loc=(0, 0, 0), rot=(0, 0, 0), material=None, bevel_width=0.0, name='box',
        segments=2):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    obj = from_bmesh(name, bm, material, smooth=False)
    place(obj, scale=size)
    if bevel_width:
        bevel(obj, bevel_width, segments, math.radians(30))
        shade(obj)
        obj.data.set_sharp_from_angle(angle=math.radians(40)) if hasattr(
            obj.data, 'set_sharp_from_angle') else None
    return place(obj, loc, rot)


def cylinder(radius=0.5, depth=1.0, loc=(0, 0, 0), rot=(0, 0, 0), material=None, segments=32,
             radius2=None, bevel_width=0.0, name='cyl', cap=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=segments, radius1=radius,
                          radius2=radius if radius2 is None else radius2, depth=depth)
    obj = from_bmesh(name, bm, material)
    if bevel_width:
        bevel(obj, bevel_width, 2, math.radians(40))
    sharp(obj)
    return place(obj, loc, rot)


def sharp(obj, angle=40):
    if hasattr(obj.data, 'set_sharp_from_angle'):
        obj.data.set_sharp_from_angle(angle=math.radians(angle))
    return obj


def sphere(radius=0.5, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0), material=None, segments=32,
           rings=16, name='sphere'):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    return place(from_bmesh(name, bm, material), loc, rot, scale)


def ico(radius=0.5, loc=(0, 0, 0), subdivisions=3, scale=(1, 1, 1), material=None, name='ico'):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdivisions, radius=radius)
    return place(from_bmesh(name, bm, material), loc, (0, 0, 0), scale)


def torus(major=0.5, minor=0.1, loc=(0, 0, 0), rot=(0, 0, 0), material=None, segments=48,
          ring=16, name='torus', scale=(1, 1, 1)):
    verts, faces = [], []
    for i in range(segments):
        a = TAU * i / segments
        for j in range(ring):
            b = TAU * j / ring
            r = major + minor * math.cos(b)
            verts.append((r * math.cos(a), r * math.sin(a), minor * math.sin(b)))
    for i in range(segments):
        for j in range(ring):
            a, b = i * ring + j, i * ring + (j + 1) % ring
            c, d = ((i + 1) % segments) * ring + (j + 1) % ring, ((i + 1) % segments) * ring + j
            faces.append((a, d, c, b))
    return place(new_object(name, verts, faces, material), loc, rot, scale)


def lathe(profile, segments=48, loc=(0, 0, 0), rot=(0, 0, 0), material=None, name='lathe',
          cap=True, scale=(1, 1, 1)):
    """Spin a (radius, height) profile around Z."""
    verts, faces = [], []
    n = len(profile)
    for i in range(segments):
        a = TAU * i / segments
        for r, z in profile:
            verts.append((r * math.cos(a), r * math.sin(a), z))
    for i in range(segments):
        for j in range(n - 1):
            a, b = i * n + j, ((i + 1) % segments) * n + j
            faces.append((a, b, b + 1, a + 1))
    if cap:
        for j, flip in ((0, True), (n - 1, False)):
            if profile[j][0] > 1e-6:
                ring = [i * n + j for i in range(segments)]
                faces.append(ring if flip else ring[::-1])
    obj = new_object(name, verts, faces, material)
    fix_normals(obj)
    sharp(obj)
    return place(obj, loc, rot, scale)


def fix_normals(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    return obj


def tube(points, radius=0.05, segments=12, material=None, name='tube', cap=True, smooth_path=0,
         cyclic=False):
    """Sweep a circle along a path. radius can be a number, a list or fn(t)."""
    pts = [Vector(p) for p in points]
    for _ in range(smooth_path):
        new = [pts[0]] if not cyclic else []
        count = len(pts) - (0 if cyclic else 1)
        for i in range(count):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            new += [a.lerp(b, 0.25), a.lerp(b, 0.75)]
        if not cyclic:
            new.append(pts[-1])
        pts = new
    n = len(pts)
    verts, faces = [], []
    up = Vector((0, 0, 1))
    prev_side = None
    for i, p in enumerate(pts):
        if cyclic:
            tangent = pts[(i + 1) % n] - pts[i - 1]
        else:
            tangent = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        tangent.normalize()
        side = tangent.cross(up)
        if side.length < 1e-4:
            side = prev_side.copy() if prev_side else Vector((1, 0, 0))
        side.normalize()
        if prev_side and side.dot(prev_side) < 0:
            side = -side
        prev_side = side
        other = side.cross(tangent).normalized()
        t = i / max(1, n - 1)
        r = radius(t) if callable(radius) else radius[i] if isinstance(radius, (list, tuple)) \
            else radius
        for j in range(segments):
            a = TAU * j / segments
            verts.append(p + (side * math.cos(a) + other * math.sin(a)) * r)
    rows = n if cyclic else n - 1
    for i in range(rows):
        for j in range(segments):
            a, b = i * segments + j, i * segments + (j + 1) % segments
            c, d = ((i + 1) % n) * segments + (j + 1) % segments, ((i + 1) % n) * segments + j
            faces.append((a, b, c, d))
    if cap and not cyclic:
        faces.append(list(range(segments))[::-1])
        faces.append([(n - 1) * segments + j for j in range(segments)])
    obj = new_object(name, verts, faces, material)
    fix_normals(obj)
    return obj


def grid(size=(1, 1), cuts=(32, 32), fn=None, material=None, name='grid', loc=(0, 0, 0)):
    """A flat grid in XY; fn(x, y) -> height."""
    nx, ny = cuts
    verts, faces = [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x, y = (i / nx - .5) * size[0], (j / ny - .5) * size[1]
            verts.append((x, y, fn(x, y) if fn else 0.0))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    return place(new_object(name, verts, faces, material), loc)


def prism(outline, depth=1.0, material=None, name='prism', loc=(0, 0, 0), rot=(0, 0, 0),
          bevel_width=0.0):
    """Extrude a 2D outline drawn in XZ along Y (centred)."""
    n = len(outline)
    verts = [(x, -depth / 2, z) for x, z in outline] + [(x, depth / 2, z) for x, z in outline]
    faces = [list(range(n)), list(range(2 * n - 1, n - 1, -1))]
    faces += [(i, i + n, (i + 1) % n + n, (i + 1) % n) for i in range(n)]
    obj = new_object(name, verts, faces, material, smooth=False)
    fix_normals(obj)
    if bevel_width:
        bevel(obj, bevel_width, 2, math.radians(25))
        shade(obj)
        sharp(obj)
    return place(obj, loc, rot)


class Meta:
    """Soft organic volumes: blended balls, ellipsoids and capsules turned into one mesh."""

    def __init__(self, resolution=0.03, threshold=0.6):
        self.data = bpy.data.metaballs.new('meta')
        self.data.resolution = resolution
        self.data.render_resolution = resolution
        self.data.threshold = threshold

    K = 1 / math.sqrt(1 - (0.6 / 2.0) ** (1 / 3))

    def ball(self, co, radius, scale=(1, 1, 1), rot=(0, 0, 0), negative=False):
        """An ellipsoid whose surface has semi-axes radius * scale."""
        e = self.data.elements.new(type='ELLIPSOID')
        e.co = co
        e.radius = self.K
        e.size_x, e.size_y, e.size_z = (max(1e-4, radius * s) for s in scale)
        e.rotation = Euler(rot).to_quaternion()
        e.use_negative = negative
        e.stiffness = 2.0
        return self

    def limb(self, a, b, r1, r2=None, negative=False, steps=None):
        """A tapered capsule, made of overlapping balls."""
        a, b = Vector(a), Vector(b)
        r2 = r1 if r2 is None else r2
        length = (b - a).length
        steps = steps or max(2, int(length / (min(r1, r2) * 0.7)) + 1)
        for i in range(steps + 1):
            t = i / steps
            e = self.data.elements.new(type='BALL')
            e.co = a.lerp(b, t)
            e.radius = (r1 + (r2 - r1) * t) * self.K * 0.93
            e.use_negative = negative
            e.stiffness = 2.0
        return self

    def path(self, points, radii):
        for i in range(len(points) - 1):
            self.limb(points[i], points[i + 1], radii[i], radii[i + 1])
        return self

    def mesh(self, name='body', material=None, mirror=False):
        holder = link(bpy.data.objects.new('meta', self.data))
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        mesh = bpy.data.meshes.new_from_object(holder.evaluated_get(dg))
        bpy.data.objects.remove(holder)
        obj = link(bpy.data.objects.new(name, mesh))
        if material:
            mesh.materials.append(material)
        return shade(obj)


# ----------------------------------------------------------------------------- materials
def N(nt, kind, ins=None, **props):
    node = nt.nodes.new('ShaderNode' + kind)
    for key, value in props.items():
        setattr(node, key, value)
    for key, value in (ins or {}).items():
        sock = node.inputs[key]
        if isinstance(value, bpy.types.NodeSocket):
            nt.links.new(value, sock)
        else:
            try:
                sock.default_value = value
            except (TypeError, ValueError):
                sock.default_value = (*value, 1.0) if len(value) == 3 else value
    return node


def rgb(hex_or_tuple):
    if isinstance(hex_or_tuple, str):
        h = hex_or_tuple.lstrip('#')
        c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
    if isinstance(hex_or_tuple, (int, float)):
        return (float(hex_or_tuple),) * 3
    return tuple(hex_or_tuple)[:3]


def ramp(nt, fac, stops, interpolation='LINEAR'):
    node = nt.nodes.new('ShaderNodeValToRGB')
    cr = node.color_ramp
    cr.interpolation = interpolation
    while len(cr.elements) < len(stops):
        cr.elements.new(0.5)
    for el, (pos, col) in zip(cr.elements, stops):
        el.position = pos
        c = rgb(col) if not isinstance(col, (int, float)) else (col, col, col)
        el.color = (*c, 1)
    nt.links.new(fac, node.inputs['Fac'])
    return node.outputs['Color']


def mix(nt, a, b, fac, mode='MIX'):
    node = N(nt, 'MixRGB', blend_type=mode)
    for key, value in (('Fac', fac), ('Color1', a), ('Color2', b)):
        sock = node.inputs[key]
        if isinstance(value, bpy.types.NodeSocket):
            nt.links.new(value, sock)
        elif key == 'Fac':
            sock.default_value = value
        else:
            sock.default_value = (*rgb(value), 1)
    return node.outputs['Color']


def math_node(nt, op, a, b=None, c=None, clamp=False):
    node = N(nt, 'Math', operation=op, use_clamp=clamp)
    for i, value in enumerate((a, b, c)):
        if value is None:
            continue
        if isinstance(value, bpy.types.NodeSocket):
            nt.links.new(value, node.inputs[i])
        else:
            node.inputs[i].default_value = value
    return node.outputs[0]


class Mat:
    """A procedural Principled material written with a few helpers."""

    def __init__(self, name, scale=1.0, bake=True, coords='Object'):
        self.m = bpy.data.materials.new(name)
        self.m.use_nodes = True
        self.nt = self.m.node_tree
        self.bsdf = self.nt.nodes['Principled BSDF']
        self.m['bake'] = bake
        tc = N(self.nt, 'TexCoord')
        mapping = N(self.nt, 'Mapping', {'Vector': tc.outputs[coords], 'Scale': (scale,) * 3})
        self.co = mapping.outputs['Vector']
        self.mapping = mapping
        self.geometry = N(self.nt, 'NewGeometry')

    def stretch(self, x=1, y=1, z=1):
        m = N(self.nt, 'Mapping', {'Vector': self.co, 'Scale': (x, y, z)})
        return m.outputs['Vector']

    def noise(self, scale=5.0, detail=6.0, rough=0.55, distortion=0.0, co=None, color=False):
        n = N(self.nt, 'TexNoise', {'Vector': co or self.co, 'Scale': scale, 'Detail': detail,
                                    'Roughness': rough, 'Distortion': distortion})
        return n.outputs['Color' if color else 'Fac']

    def voronoi(self, scale=5.0, feature='F1', out='Distance', co=None, randomness=1.0,
                distance='EUCLIDEAN'):
        n = N(self.nt, 'TexVoronoi', {'Vector': co or self.co, 'Scale': scale,
                                      'Randomness': randomness}, feature=feature,
              distance=distance)
        return n.outputs[out]

    def wave(self, scale=5.0, distortion=2.0, detail=3.0, kind='BANDS', direction='X', co=None,
             detail_scale=1.0):
        n = N(self.nt, 'TexWave', {'Vector': co or self.co, 'Scale': scale,
                                   'Distortion': distortion, 'Detail': detail,
                                   'Detail Scale': detail_scale}, wave_type=kind)
        if kind == 'BANDS':
            n.bands_direction = direction
        else:
            n.rings_direction = direction
        return n.outputs['Fac']

    def brick(self, scale=4.0, mortar=0.02, width=0.5, height=0.25, co=None, offset=0.5):
        n = N(self.nt, 'TexBrick', {'Vector': co or self.co, 'Scale': scale,
                                    'Mortar Size': mortar, 'Brick Width': width,
                                    'Row Height': height, 'Color1': (1, 1, 1, 1),
                                    'Color2': (0.6, 0.6, 0.6, 1), 'Mortar': (0, 0, 0, 1)},
              offset=offset)
        return n.outputs['Color'], n.outputs['Fac']

    def ramp(self, fac, stops, interpolation='LINEAR'):
        return ramp(self.nt, fac, stops, interpolation)

    def mix(self, a, b, fac, mode='MIX'):
        return mix(self.nt, a, b, fac, mode)

    def math(self, op, a, b=None, c=None, clamp=False):
        return math_node(self.nt, op, a, b, c, clamp)

    def pointiness(self, lo=0.45, hi=0.55):
        """Edge mask from curvature (only correct while baking in Cycles)."""
        return self.ramp(self.geometry.outputs['Pointiness'], [(lo, 0.0), (hi, 1.0)])

    def up(self, lo=0.3, hi=0.8):
        """1 where the surface faces up (snow, dust, moss)."""
        sep = N(self.nt, 'SeparateXYZ', {'Vector': self.geometry.outputs['Normal']})
        return self.ramp(sep.outputs['Z'], [(lo, 0.0), (hi, 1.0)])

    def axis(self, axis='Z'):
        return N(self.nt, 'SeparateXYZ', {'Vector': self.co}).outputs[axis]

    def set(self, color=None, rough=None, metal=None, height=None, bump=0.3, emission=None,
            emission_strength=1.0, alpha=None, bump_distance=0.01, transmission=None, ior=None,
            coat=None):
        b = self.bsdf
        for key, value in (('Base Color', color), ('Roughness', rough), ('Metallic', metal),
                           ('Alpha', alpha), ('Transmission Weight', transmission),
                           ('IOR', ior), ('Coat Weight', coat)):
            if value is None:
                continue
            if isinstance(value, bpy.types.NodeSocket):
                self.nt.links.new(value, b.inputs[key])
            elif key == 'Base Color':
                b.inputs[key].default_value = (*rgb(value), 1)
            else:
                b.inputs[key].default_value = value
        if height is not None:
            node = N(self.nt, 'Bump', {'Height': height, 'Strength': bump,
                                       'Distance': bump_distance})
            self.nt.links.new(node.outputs['Normal'], b.inputs['Normal'])
        if emission is not None:
            if isinstance(emission, bpy.types.NodeSocket):
                self.nt.links.new(emission, b.inputs['Emission Color'])
            else:
                b.inputs['Emission Color'].default_value = (*rgb(emission), 1)
            b.inputs['Emission Strength'].default_value = emission_strength
            self.m['emissive'] = True
        if alpha is not None or transmission is not None:
            self.m['bake'] = False
            if hasattr(self.m, 'surface_render_method'):
                self.m.surface_render_method = 'BLENDED'
        return self.m


# ----------------------------------------------------------------------------- baking
def _source(nt, bsdf, key):
    sock = bsdf.inputs[key]
    if sock.is_linked:
        return sock.links[0].from_socket
    node = nt.nodes.new('ShaderNodeRGB')
    v = sock.default_value
    node.outputs[0].default_value = (v, v, v, 1) if isinstance(v, float) else tuple(v)
    return node.outputs[0]


def unwrap(obj, margin=0.004, angle=66):
    activate(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin,
                             area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj


def bake_atlas(obj, size=2048, ao_samples=12, name=None, do_unwrap=True):
    """Bake every bakeable procedural material of obj into one PBR texture set."""
    scene = bpy.context.scene
    name = name or obj.name
    mesh = obj.data
    keep = [m for m in mesh.materials if m and not m.get('bake', True)]
    baked = [m for m in mesh.materials if m and m.get('bake', True)]
    if not baked:
        return obj
    emissive = any(m.get('emissive') for m in baked)
    if do_unwrap:
        unwrap(obj)
    activate(obj)
    images = {}

    def target(kind, res, colour=False):
        img = bpy.data.images.new(name + '_' + kind, res, res, alpha=False,
                                  float_buffer=False, is_data=not colour)
        images[kind] = img
        for m in baked:
            node = m.node_tree.nodes.get('bake_target') or m.node_tree.nodes.new(
                'ShaderNodeTexImage')
            node.name = 'bake_target'
            node.image = img
            m.node_tree.nodes.active = node
        return img

    scene.render.bake.margin = max(4, size // 128)
    scene.render.bake.use_clear = True
    scene.cycles.samples = 1
    scene.cycles.use_denoising = False
    target('normal', size)
    bpy.ops.object.bake(type='NORMAL')
    scene.cycles.samples = ao_samples
    target('ao', size // 2)
    bpy.ops.object.bake(type='AO')
    scene.cycles.samples = 1
    passes = [('color', 'Base Color', True), ('rough', 'Roughness', False),
              ('metal', 'Metallic', False)] + ([('emit', 'Emission Color', True)] if emissive
                                               else [])
    state = []
    for m in baked:
        nt = m.node_tree
        out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
        bsdf = nt.nodes['Principled BSDF']
        em = nt.nodes.new('ShaderNodeEmission')
        state.append((m, nt, out, bsdf, em))
    for kind, key, colour in passes:
        target(kind, size, colour)
        for m, nt, out, bsdf, em in state:
            src = _source(nt, bsdf, key)
            if kind == 'emit':
                strength = bsdf.inputs['Emission Strength'].default_value if m.get(
                    'emissive') else 0.0
                em.inputs['Strength'].default_value = min(1.0, strength)
            else:
                em.inputs['Strength'].default_value = 1.0
            nt.links.new(src, em.inputs['Color'])
            nt.links.new(em.outputs[0], out.inputs['Surface'])
        bpy.ops.object.bake(type='EMIT')

    def pixels(kind):
        img = images[kind]
        arr = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
        img.pixels.foreach_get(arr)
        return arr.reshape(img.size[1], img.size[0], 4)

    ao = pixels('ao')[..., 0]
    ao = np.kron(ao, np.ones((2, 2), dtype=np.float32))
    ao = np.clip(0.25 + 0.75 * ao, 0, 1)
    orm = np.ones((size, size, 4), dtype=np.float32)
    orm[..., 0] = ao
    orm[..., 1] = pixels('rough')[..., 0]
    orm[..., 2] = pixels('metal')[..., 0]
    orm_img = bpy.data.images.new(name + '_orm', size, size, alpha=False, is_data=True)
    orm_img.pixels.foreach_set(orm.ravel())
    strength = max([m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
                    .default_value for m in baked if m.get('emissive')] or [0.0])
    final = bpy.data.materials.new(name)
    final.use_nodes = True
    nt = final.node_tree
    b = nt.nodes['Principled BSDF']
    col = N(nt, 'TexImage', image=images['color'])
    nt.links.new(col.outputs['Color'], b.inputs['Base Color'])
    o = N(nt, 'TexImage', image=orm_img)
    sep = N(nt, 'SeparateColor', {'Color': o.outputs['Color']})
    nt.links.new(sep.outputs['Green'], b.inputs['Roughness'])
    nt.links.new(sep.outputs['Blue'], b.inputs['Metallic'])
    nrm = N(nt, 'TexImage', image=images['normal'])
    nmap = N(nt, 'NormalMap', {'Color': nrm.outputs['Color']})
    nt.links.new(nmap.outputs['Normal'], b.inputs['Normal'])
    group = bpy.data.node_groups.get('glTF Material Output') or bpy.data.node_groups.new(
        'glTF Material Output', 'ShaderNodeTree')
    if not group.interface.items_tree:
        group.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    gn = nt.nodes.new('ShaderNodeGroup')
    gn.node_tree = group
    nt.links.new(sep.outputs['Red'], gn.inputs['Occlusion'])
    if emissive:
        e = N(nt, 'TexImage', image=images['emit'])
        nt.links.new(e.outputs['Color'], b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value = max(1.0, strength)
    for img in (images['color'], images['normal'], orm_img) + (
            (images['emit'],) if emissive else ()):
        img.pack()
    slots = {m.name: i for i, m in enumerate(mesh.materials) if m}
    order = [final] + keep
    remap = {slots[m.name]: (0 if m in baked else 1 + keep.index(m))
             for m in baked + keep}
    indices = np.empty(len(mesh.polygons), dtype=np.int32)
    mesh.polygons.foreach_get('material_index', indices)
    lut = np.zeros(max(remap) + 1, dtype=np.int32)
    for old, new in remap.items():
        lut[old] = new
    mesh.materials.clear()
    for m in order:
        mesh.materials.append(m)
    mesh.polygons.foreach_set('material_index', lut[np.clip(indices, 0, len(lut) - 1)])
    mesh.update()
    for m in baked:
        bpy.data.materials.remove(m)
    for kind in ('ao', 'rough', 'metal'):
        bpy.data.images.remove(images[kind])
    return obj


# ----------------------------------------------------------------------------- rigging
class Rig:
    def __init__(self, name='Armature'):
        self.arm = bpy.data.armatures.new(name)
        self.obj = link(bpy.data.objects.new(name, self.arm))
        self.obj.show_in_front = True
        self.specs = []
        self.actions = []

    def bone(self, name, head, tail, parent=None, connect=False, deform=True, roll=0.0):
        self.specs.append((name, Vector(head), Vector(tail), parent, connect, deform, roll))
        return name

    def chain(self, prefix, points, parent=None, deform=True):
        names = []
        for i in range(len(points) - 1):
            name = '%s.%02d' % (prefix, i + 1) if len(points) > 2 else prefix
            self.bone(name, points[i], points[i + 1], parent, connect=i > 0, deform=deform)
            parent = name
            names.append(name)
        return names

    def build(self):
        activate(self.obj)
        bpy.ops.object.mode_set(mode='EDIT')
        eb = self.arm.edit_bones
        for name, head, tail, parent, connect, deform, roll in self.specs:
            b = eb.new(name)
            b.head, b.tail = head, tail
            if (tail - head).length < 1e-4:
                b.tail = head + Vector((0, 0, 0.05))
            b.roll = roll
            b.use_deform = deform
            if parent:
                b.parent = eb[parent]
                b.use_connect = connect and (eb[parent].tail - head).length < 1e-4
        bpy.ops.object.mode_set(mode='OBJECT')
        for pb in self.obj.pose.bones:
            pb.rotation_mode = 'QUATERNION'
        return self

    def ik(self, bone, target, chain=2, pole=None, pole_angle=0.0):
        c = self.obj.pose.bones[bone].constraints.new('IK')
        c.target = self.obj
        c.subtarget = target
        c.chain_count = chain
        if pole:
            c.pole_target = self.obj
            c.pole_subtarget = pole
            c.pole_angle = pole_angle
        return c

    def copy_rotation(self, bone, target, influence=1.0):
        c = self.obj.pose.bones[bone].constraints.new('COPY_ROTATION')
        c.target = self.obj
        c.subtarget = target
        c.influence = influence
        return c

    # ---- binding
    def bind_auto(self, obj):
        activate(self.obj, [obj])
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        return obj

    def bind_rigid(self, obj, bone=None):
        """Every vertex follows one bone (falls back to the object's 'bone' tag)."""
        bone = bone or obj.get('bone') or self.specs[0][0]
        obj.vertex_groups.clear()
        g = obj.vertex_groups.new(name=bone)
        g.add(range(len(obj.data.vertices)), 1.0, 'REPLACE')
        obj.parent = self.obj
        mod = obj.modifiers.new('Armature', 'ARMATURE')
        mod.object = self.obj
        return obj

    def bind_parts(self, parts, name='mesh'):
        """Join rigid parts into one skinned mesh; each keeps the bone it was tagged with."""
        default = self.specs[0][0]
        deform = {s[0] for s in self.specs if s[5]}
        for obj in parts:
            if obj.get('weighted'):
                continue
            bone = obj.get('bone') or default
            if bone not in deform:
                raise ValueError('part %s follows unknown bone %s' % (obj.name, bone))
            obj.vertex_groups.clear()
            g = obj.vertex_groups.new(name=bone)
            g.add(range(len(obj.data.vertices)), 1.0, 'REPLACE')
        obj = join(parts, name)
        obj.parent = self.obj
        mod = obj.modifiers.new('Armature', 'ARMATURE')
        mod.object = self.obj
        return obj

    def weight_chain(self, obj, names, axis=2):
        """Blend an object between the bones of a chain by how far along the chain each vertex is."""
        joints = [self._spec(n)[1] for n in names] + [self._spec(names[-1])[2]]
        groups = [obj.vertex_groups.get(n) or obj.vertex_groups.new(name=n) for n in names]
        for v in obj.data.vertices:
            best, k, f = 1e18, 0, 0.0
            for i in range(len(names)):
                a, b = joints[i], joints[i + 1]
                ab = b - a
                t = min(1.0, max(0.0, (v.co - a).dot(ab) / max(ab.length_squared, 1e-12)))
                d = (v.co - (a + ab * t)).length_squared
                if d < best:
                    best, k, f = d, i, t
            # the joint itself is shared half and half, so the bend is smooth
            if f > 0.5 and k < len(names) - 1:
                groups[k].add([v.index], 1.5 - f, 'REPLACE')
                groups[k + 1].add([v.index], f - 0.5, 'REPLACE')
            elif f <= 0.5 and k > 0:
                groups[k].add([v.index], 0.5 + f, 'REPLACE')
                groups[k - 1].add([v.index], 0.5 - f, 'REPLACE')
            else:
                groups[k].add([v.index], 1.0, 'REPLACE')
        obj['weighted'] = True
        return obj

    def _spec(self, name):
        return next(s for s in self.specs if s[0] == name)

    def transfer_weights(self, source, target):
        """Give target the weights of the nearest surface of source."""
        for g in source.vertex_groups:
            if g.name not in target.vertex_groups:
                target.vertex_groups.new(name=g.name)
        mod = target.modifiers.new('transfer', 'DATA_TRANSFER')
        mod.object = source
        mod.use_vert_data = True
        mod.data_types_verts = {'VGROUP_WEIGHTS'}
        mod.vert_mapping = 'POLYINTERP_NEAREST'
        activate(target)
        bpy.ops.object.modifier_apply(modifier=mod.name)
        target.parent = self.obj
        arm = target.modifiers.new('Armature', 'ARMATURE')
        arm.object = self.obj
        return target

    # ---- animation
    def clip(self, name, seconds, pose_fn, loop=True):
        """pose_fn(t, P) with t in 0..1; P.rot(bone, x, y, z), P.loc(bone, x, y, z), P.scale()."""
        ao = self.obj
        ad = ao.animation_data or ao.animation_data_create()
        action = bpy.data.actions.new(name)
        ad.action = action
        frames = max(2, round(seconds * FPS))
        pose = Pose(ao)
        for f in range(frames + 1):
            t = f / frames
            pose.begin()
            pose_fn(t if not loop or f < frames else 0.0, pose)
            pose.key(f + 1)
        action.frame_range = (1, frames + 1)
        action.use_frame_range = True
        for pb in ao.pose.bones:
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.location = (0, 0, 0)
            pb.scale = (1, 1, 1)
        self.actions.append(action)
        return action

    def finish(self):
        """Stash every clip so the exporter writes all of them, first clip first."""
        ad = self.obj.animation_data
        if not ad:
            return
        slot = ad.action_slot if hasattr(ad, 'action_slot') else None
        ad.action = None
        for action in self.actions:
            track = ad.nla_tracks.new()
            track.name = action.name
            strip = track.strips.new(action.name, 1, action)
            if slot is not None and hasattr(strip, 'action_slot') and action.slots:
                strip.action_slot = action.slots[0]
            track.mute = True


class Pose:
    def __init__(self, obj):
        self.obj = obj
        self.bones = obj.pose.bones
        self.touched = {}

    def begin(self):
        for name in self.touched:
            pb = self.bones[name]
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.location = (0, 0, 0)
            pb.scale = (1, 1, 1)

    def rot(self, bone, x=0.0, y=0.0, z=0.0, add=True):
        """Local euler rotation in radians (X pitch, Y twist along the bone, Z side)."""
        if bone not in self.bones:
            return
        q = Euler((x, y, z), 'XYZ').to_quaternion()
        pb = self.bones[bone]
        pb.rotation_quaternion = pb.rotation_quaternion @ q if add and bone in self.touched \
            and 'r' in self.touched[bone] else q
        self.touched.setdefault(bone, set()).add('r')

    def loc(self, bone, x=0.0, y=0.0, z=0.0):
        if bone not in self.bones:
            return
        self.bones[bone].location = (x, y, z)
        self.touched.setdefault(bone, set()).add('l')

    def _rest(self, bone):
        return self.obj.data.bones[bone].matrix_local.to_3x3()

    def turn(self, bone, x=0.0, y=0.0, z=0.0):
        """Rotate in armature axes (X to the model's left, Y back, Z up), radians."""
        if bone not in self.bones:
            return
        rest = self._rest(bone).to_quaternion()
        world = Euler((x, y, z), 'XYZ').to_quaternion()
        q = rest.inverted() @ world @ rest
        pb = self.bones[bone]
        pb.rotation_quaternion = pb.rotation_quaternion @ q if bone in self.touched \
            and 'r' in self.touched[bone] else q
        self.touched.setdefault(bone, set()).add('r')

    def move(self, bone, x=0.0, y=0.0, z=0.0):
        """Translate in armature axes."""
        if bone not in self.bones:
            return
        b = self.obj.data.bones[bone]
        rest = b.matrix_local.to_3x3()
        self.bones[bone].location = rest.inverted() @ Vector((x, y, z))
        self.touched.setdefault(bone, set()).add('l')

    def scale(self, bone, x=1.0, y=None, z=None):
        if bone not in self.bones:
            return
        self.bones[bone].scale = (x, x if y is None else y, x if z is None else z)
        self.touched.setdefault(bone, set()).add('s')

    def key(self, frame):
        for name, kinds in self.touched.items():
            pb = self.bones[name]
            if 'r' in kinds:
                pb.keyframe_insert('rotation_quaternion', frame=frame)
            if 'l' in kinds:
                pb.keyframe_insert('location', frame=frame)
            if 's' in kinds:
                pb.keyframe_insert('scale', frame=frame)


def ease(t):
    return t * t * (3 - 2 * t)


def pulse(t, a, b, c=None, d=None):
    """0 → 1 between a and b, hold, 1 → 0 between c and d (all eased)."""
    if c is None:
        return ease(min(1, max(0, (t - a) / (b - a))))
    if t < c:
        return ease(min(1, max(0, (t - a) / (b - a))))
    return 1 - ease(min(1, max(0, (t - c) / (d - c))))


def wave(t, phase=0.0, harmonics=1):
    return math.sin(TAU * (t * harmonics + phase))


# ----------------------------------------------------------------------------- output
def export(path, objects=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if objects:
        bpy.ops.object.select_all(action='DESELECT')
        for o in objects:
            o.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=bool(objects),
        export_image_format='WEBP', export_image_quality=80, export_yup=True,
        export_apply=False, export_animations=True, export_animation_mode='ACTIONS',
        export_force_sampling=True, export_def_bones=True, export_skins=True,
        export_optimize_animation_size=True, export_anim_slide_to_zero=True,
        export_tangents=False, export_cameras=False, export_lights=False,
        export_extras=False, export_morph=False)
    return path


def preview(path, objects, size=720, samples=40, angle=35, elevation=14, frame=None,
            dark=False, fill=0.82):
    """A lit studio render of the finished model, to check it by eye."""
    scene = bpy.context.scene
    if frame is not None:
        scene.frame_set(frame)
    bpy.context.view_layer.update()
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objects:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        stride = max(1, len(me.vertices) // 4000)
        for i in range(0, len(me.vertices), stride):
            v = me.vertices[i]
            w = ev.matrix_world @ v.co
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
        ev.to_mesh_clear()
    centre = (lo + hi) / 2
    radius = max((hi - lo).length / 2, 1e-3)
    world = bpy.data.worlds.new('preview')
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes['Background']
    sky = nt.nodes.new('ShaderNodeTexSky')
    try:
        sky.sky_type = 'MULTIPLE_SCATTERING'
    except TypeError:
        sky.sky_type = 'HOSEK_WILKIE'
    if hasattr(sky, 'sun_elevation'):
        sky.sun_elevation = math.radians(38)
        sky.sun_rotation = math.radians(angle + 215)
    nt.links.new(sky.outputs[0], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 0.02 if dark else 0.11
    scene.world = world
    floor = grid((radius * 40, radius * 40), (1, 1), name='preview_floor')
    floor.location = (centre.x, centre.y, lo.z - radius * 0.002)
    fm = Mat('preview_floor')
    fm.set(color=(0.02, 0.02, 0.025) if dark else (0.32, 0.32, 0.33), rough=0.7)
    floor.data.materials.append(fm.m)
    cam_data = bpy.data.cameras.new('preview')
    cam_data.lens = 70
    cam = link(bpy.data.objects.new('preview', cam_data))
    half = math.atan(cam_data.sensor_width / 2 / cam_data.lens)
    dist = radius / math.sin(half) / fill * 0.86
    a, e = math.radians(angle), math.radians(elevation)
    cam.location = centre + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e),
                                    math.sin(e))) * dist
    cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = cam
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = 'AgX' if 'AgX' in [
        i.identifier for i in type(scene.view_settings).bl_rna.properties[
            'view_transform'].enum_items] else 'Filmic'
    scene.render.filepath = path
    scene.render.image_settings.file_format = 'JPEG'
    scene.render.image_settings.quality = 88
    bpy.ops.render.render(write_still=True)
    for o in (floor, cam):
        bpy.data.objects.remove(o)
    return path
