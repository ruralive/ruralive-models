#!/usr/bin/env python3
"""Build separate rigged GLBs from decoded Ruralive assets."""
import argparse
import json
import math
import struct
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation, Slerp
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parent.parent
IDENTITY = np.eye(4)
HUMANS = {'astronaut', 'gemini-spacesuit', 'mercury-spacesuit', 'mark-3-spacesuit', 'z2-spacesuit'}
RIG_NAMES = ('hips', 'spine.001', 'neck', 'head', 'upper_arm', 'forearm', 'hand', 'thigh', 'shin', 'foot')


class Asset:
    def __init__(self, path):
        raw = path.read_bytes()
        size, = struct.unpack_from('<I', raw, 12)
        self.doc = json.loads(raw[20:20 + size])
        self.bin = bytearray(raw[28 + size:])
        self.nodes = self.doc['nodes']

    def read(self, index):
        a = self.doc['accessors'][index]
        v = self.doc['bufferViews'][a['bufferView']]
        dtype = np.dtype({5126: '<f4', 5121: 'u1', 5123: '<u2', 5125: '<u4'}[a['componentType']])
        width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
        return np.ndarray((a['count'], width), dtype=dtype, buffer=self.bin,
                          offset=v.get('byteOffset', 0) + a.get('byteOffset', 0),
                          strides=(v.get('byteStride', width * dtype.itemsize), dtype.itemsize)).copy()

    def repair_geometry(self):
        # Gemini includes non-finite normals on a small set of vertices.
        for mesh in self.doc['meshes']:
            for primitive in mesh['primitives']:
                attrs = primitive['attributes']
                if 'WEIGHTS_0' in attrs:
                    weights = self.read(attrs['WEIGHTS_0'])
                    if weights.dtype.kind == 'f':
                        sums = weights.sum(axis=1, keepdims=True)
                        if not np.allclose(sums, 1):
                            weights = weights / np.where(sums > 0, sums, 1)
                            weights[sums[:, 0] == 0, 0] = 1
                            self.overwrite_floats(attrs['WEIGHTS_0'], weights)
                if 'NORMAL' not in attrs:
                    continue
                i = attrs['NORMAL']
                normals = self.read(i)
                valid = np.isfinite(normals).all(axis=1)
                if valid.all():
                    continue
                pos = self.read(attrs['POSITION'])
                _, nearest = cKDTree(pos[valid]).query(pos[~valid])
                normals[~valid] = normals[valid][nearest]
                self.overwrite_floats(i, normals)

    def overwrite_floats(self, index, values):
        a = self.doc['accessors'][index]
        view = self.doc['bufferViews'][a['bufferView']]
        offset = view.get('byteOffset', 0) + a.get('byteOffset', 0)
        destination = np.ndarray(values.shape, dtype='<f4', buffer=self.bin,
                                 offset=offset, strides=(view.get('byteStride', values.shape[1] * 4), 4))
        destination[:] = values

    def add(self, values, kind, target=None, bounds=False):
        values = np.asarray(values)
        self.bin.extend(b'\0' * (-len(self.bin) % 4))
        view = dict(buffer=0, byteOffset=len(self.bin), byteLength=values.nbytes)
        if target:
            view['target'] = target
        views = self.doc['bufferViews']
        views.append(view)
        self.bin.extend(values.tobytes())
        accessor = dict(bufferView=len(views) - 1, componentType=5121 if values.dtype == np.uint8 else 5126,
                        count=len(values), type=kind)
        if bounds:
            accessor.update(min=np.atleast_1d(values.min(axis=0)).tolist(), max=np.atleast_1d(values.max(axis=0)).tolist())
        accessors = self.doc['accessors']
        accessors.append(accessor)
        return len(accessors) - 1

    def write(self, path):
        self.doc['buffers'][0]['byteLength'] = len(self.bin)
        self.bin.extend(b'\0' * (-len(self.bin) % 4))
        data = json.dumps(self.doc, separators=(',', ':'), allow_nan=False).encode()
        data += b' ' * (-len(data) % 4)
        with path.open('wb') as f:
            f.write(struct.pack('<4sIII4s', b'glTF', 2, 28 + len(data) + len(self.bin), len(data), b'JSON'))
            f.write(data)
            f.write(struct.pack('<I4s', len(self.bin), b'BIN\0'))
            f.write(self.bin)


def local(node):
    if 'matrix' in node:
        return np.array(node['matrix']).reshape(4, 4).T
    transform = IDENTITY.copy()
    transform[:3, :3] = Rotation.from_quat(node.get('rotation', [0, 0, 0, 1])).as_matrix() * node.get('scale', [1, 1, 1])
    transform[:3, 3] = node.get('translation', [0, 0, 0])
    return transform


def scene_matrices(asset):
    world, parents = {}, {}

    def visit(i, parent, transform):
        world[i] = transform @ local(asset.nodes[i])
        parents[i] = parent
        for child in asset.nodes[i].get('children', []):
            visit(child, i, world[i])

    for scene in asset.doc['scenes']:
        for i in scene['nodes']:
            visit(i, None, IDENTITY)
    return world, parents


def points(matrix, vertices):
    return vertices @ matrix[:3, :3].T + matrix[:3, 3]


def bounds(asset, world):
    low, high = [], []
    for i, matrix in world.items():
        node = asset.nodes[i]
        if 'mesh' not in node:
            continue
        for p in asset.doc['meshes'][node['mesh']]['primitives']:
            pos = points(matrix, asset.read(p['attributes']['POSITION']))
            low.append(pos.min(axis=0))
            high.append(pos.max(axis=0))
    return np.min(low, axis=0), np.max(high, axis=0)


def add_node(asset, name, position, parent=None):
    index = len(asset.nodes)
    asset.nodes.append(dict(name=name, translation=np.asarray(position).tolist()))
    if parent is not None:
        asset.nodes[parent].setdefault('children', []).append(index)
    return index


def clip(asset, name, times, tracks):
    time_accessor = asset.add(np.asarray(times, dtype='<f4'), 'SCALAR', bounds=True)
    channels, samplers = [], []
    for node, path, values in tracks:
        values = np.asarray(values, dtype='<f4')
        assert np.isfinite(values).all() and len(values) == len(times)
        assert np.allclose(values[0], values[-1], atol=1e-6) or (
            path == 'rotation' and np.allclose(values[0], -values[-1], atol=1e-6))
        output = asset.add(values, 'VEC4' if path == 'rotation' else 'VEC3')
        channels.append(dict(sampler=len(samplers), target=dict(node=node, path=path)))
        samplers.append(dict(input=time_accessor, output=output, interpolation='LINEAR'))
    asset.doc.setdefault('animations', []).append(dict(name=name, channels=channels, samplers=samplers))


def rotation(axis, angles):
    return Rotation.from_rotvec(np.asarray(angles)[:, None] * np.asarray(axis)[None, :]).as_quat()


def wave(phase, offset=0):
    return np.sin(phase + offset) - math.sin(offset)


def humanoid_layout(model, lo, hi):
    """Joint landmarks in upright, normalized glTF world coordinates."""
    width, height, depth = hi - lo
    cx, _, cz = (hi + lo) / 2
    # Shoulder, elbow and wrist positions adapt to the model's baked pose.
    poses = {
        'astronaut': ((.18, .75, .04), (.32, .75, .08), (.44, .74, .10)),
        'gemini-spacesuit': ((.23, .80, .00), (.36, .62, .12), (.43, .49, .26)),
        'mercury-spacesuit': ((.22, .80, .00), (.34, .62, .07), (.42, .48, .21)),
        'mark-3-spacesuit': ((.29, .72, .03), (.39, .62, .24), (.44, .51, .38)),
        'z2-spacesuit': ((.31, .77, .06), (.38, .66, .28), (.31, .55, .42)),
    }
    front = -1 if model == 'mark-3-spacesuit' else 1

    def pt(x, y, z):
        return np.array([cx + x * width, lo[1] + y * height, cz + front * z * depth])

    layout = {
        'hips': (None, pt(0, .49, -.05), pt(0, .60, -.05)),
        'spine.001': ('hips', pt(0, .60, -.05), pt(0, .80, -.05)),
        'neck': ('spine.001', pt(0, .80, -.05), pt(0, .86, .03)),
        'head': ('neck', pt(0, .86, .03), pt(0, .98, .08)),
    }
    for side, sign in [('L', front), ('R', -front)]:
        shoulder, elbow, wrist = [pt(sign * x, y, z) for x, y, z in poses[model]]
        fingertips = wrist + .24 * (wrist - elbow)
        leg_x = .14 if model == 'astronaut' else .15
        hip = pt(sign * leg_x, .48, -.04)
        knee = pt(sign * leg_x * 1.13, .26, .01)
        ankle = pt(sign * leg_x * 1.20, .065, -.03)
        for bone, parent, start, end in [
            ('upper_arm', 'spine.001', shoulder, elbow),
            ('forearm', 'upper_arm.' + side, elbow, wrist),
            ('hand', 'forearm.' + side, wrist, fingertips),
            ('thigh', 'hips', hip, knee),
            ('shin', 'thigh.' + side, knee, ankle),
            ('foot', 'shin.' + side, ankle, pt(sign * leg_x * 1.20, .035, .38)),
        ]:
            layout[bone + '.' + side] = parent, start, end
    return layout


def human_weights(pos, layout, lo, hi, model):
    distances = []
    for name, (_, start, end) in layout.items():
        direction = end - start
        u = np.clip((pos - start) @ direction / (direction @ direction), 0, 1)
        distance = np.linalg.norm(pos - start - u[:, None] * direction, axis=1)
        if name == 'spine.001':
            distance *= .82
        # Keep backpack geometry together on the torso.
        if model in {'astronaut', 'mark-3-spacesuit', 'z2-spacesuit'} and name.startswith(('upper_arm', 'forearm', 'hand')):
            front = -1 if model == 'mark-3-spacesuit' else 1
            behind = (pos[:, 2] - (lo[2] + hi[2]) / 2) * front < -(hi[2] - lo[2]) * .19
            distance[behind] += (hi[1] - lo[1]) * .15
        distances.append(distance)
    matrix = np.column_stack(distances)
    order = np.argsort(matrix, axis=1)[:, :4]
    nearest = np.take_along_axis(matrix, order, axis=1)
    weights = np.exp(-(nearest - nearest[:, :1]) / ((hi[1] - lo[1]) * .026))
    return order, weights / weights.sum(axis=1, keepdims=True)


def chain_weights(u, count):
    u = np.clip(u, 0, 1) * (count - 1)
    low = np.floor(u).astype(int)
    ids = np.column_stack([low, np.minimum(low + 1, count - 1), low * 0, low * 0])
    fraction = u - low
    return ids, np.column_stack([1 - fraction, fraction, fraction * 0, fraction * 0])


def skin_mesh(asset, index, world_matrix, joints, bind_positions, weight_for, split=False):
    doc = asset.doc
    mesh_index = asset.nodes[index]['mesh']
    import copy
    mesh = copy.deepcopy(doc['meshes'][mesh_index])
    for primitive in mesh['primitives']:
        attrs = primitive['attributes']
        pos = points(world_matrix, asset.read(attrs['POSITION']))
        ids, weights = weight_for(pos, asset.nodes[index])
        assert np.isfinite(weights).all() and np.allclose(weights.sum(axis=1), 1)
        assert ids.min() >= 0 and ids.max() < len(joints)
        attrs['JOINTS_0'] = asset.add(ids.astype('u1'), 'VEC4', target=34962)
        attrs['WEIGHTS_0'] = asset.add(weights.astype('<f4'), 'VEC4', target=34962)
    doc['meshes'].append(mesh)
    if split:
        asset.nodes[index].pop('mesh')
        index = add_node(asset, asset.nodes[index].get('name', 'Part') + ' mesh', [0, 0, 0], index)
    asset.nodes[index]['mesh'] = len(doc['meshes']) - 1
    matrices = []
    for bind in bind_positions:
        inv_bind = np.linalg.inv(bind) @ world_matrix
        assert np.allclose(bind @ inv_bind, world_matrix)
        matrices.append(inv_bind.T.ravel())
    skins = doc.setdefault('skins', [])
    skins.append(dict(joints=joints, skeleton=joints[0],
                      inverseBindMatrices=asset.add(np.asarray(matrices, dtype='<f4'), 'MAT4')))
    asset.nodes[index]['skin'] = len(skins) - 1


def rigid_weights(pos, node):
    ids = np.zeros((len(pos), 4), dtype='u1')
    weights = ids.astype(float)
    weights[:, 0] = 1
    return ids, weights


def source_rotations(source, wanted, samples=41):
    world, parents = scene_matrices(source)
    result = {}
    for animation in source.doc['animations']:
        if animation.get('name') not in wanted:
            continue
        tracks = []
        duration = max(source.read(s['input'])[-1, 0] for s in animation['samplers'])
        times = np.linspace(0, duration, samples)
        for channel in animation['channels']:
            target = channel['target']
            i = target['node']
            name = source.nodes[i].get('name', '').removeprefix('DEF-')
            if target['path'] != 'rotation' or name.split('.')[0] not in RIG_NAMES and name != 'spine.001':
                continue
            sampler = animation['samplers'][channel['sampler']]
            if sampler.get('interpolation', 'LINEAR') != 'LINEAR':
                raise ValueError('Expected LINEAR source rotations')
            keys = source.read(sampler['input'])[:, 0]
            values = Rotation.from_quat(source.read(sampler['output']))
            posed = (Slerp(keys, values)(np.clip(times, keys[0], keys[-1]))
                     if len(keys) > 1 else Rotation.from_quat(np.repeat(values.as_quat(), samples, axis=0)))
            parent = Rotation.from_matrix(world[parents[i]][:3, :3])
            rest = Rotation.from_quat(source.nodes[i].get('rotation', [0, 0, 0, 1]))
            delta = parent * posed * rest.inv() * parent.inv()
            tracks.append((name, delta.as_quat().round(6).tolist()))
        result[animation['name']] = dict(seconds=round(float(duration), 6), tracks=dict(tracks))
    assert set(result) == set(wanted)
    return result


def build(path, entry, output, motions):
    asset = Asset(path)
    doc = asset.doc
    asset.repair_geometry()
    name = entry['id']
    world, parents = scene_matrices(asset)
    lo, hi = bounds(asset, world)
    center = (lo + hi) / 2
    height = hi[1] - lo[1]
    extent = max(hi - lo)
    originals = len(doc.get('animations', []))
    rest_root = center.copy()
    rest_root[1] = lo[1]
    root = add_node(asset, 'Ruralive_Root', rest_root)
    for scene in doc['scenes']:
        # Keep original world transforms while adding a pivot at the base.
        offset = add_node(asset, 'Ruralive_Original_Offset', -rest_root)
        asset.nodes[offset]['children'] = scene['nodes']
        asset.nodes[root].setdefault('children', []).append(offset)
        scene['nodes'] = [root]
    joints, binds, parts = [root], [rest_root], {}
    times = np.linspace(0, 1, 49)
    phase = times * math.tau

    def joint(key, pos, parent, parent_pos):
        index = add_node(asset, 'Ruralive_' + key, pos - parent_pos, parent)
        parts[key] = index, pos
        return index

    weight_for = rigid_weights
    rig = 'rigid root'
    if name in HUMANS:
        rig = 'weighted humanoid'
        layout = humanoid_layout(name, lo, hi)
        for key, (parent, pos, _) in layout.items():
            p, pp = parts[parent] if parent else (root, rest_root)
            joints.append(joint(key, pos, p, pp))
            binds.append(pos)
        joints, binds = joints[1:], binds[1:]
        def weight_for(pos, node):
            return human_weights(pos, layout, lo, hi, name)
        correction = Rotation.from_euler('y', 180 if name == 'mark-3-spacesuit' else 0, degrees=True)
        for motion in ("Idle_Loop", "Walk_Loop", "Dance_Loop"):
            data = motions[motion]
            if name != 'astronaut' and motion != 'Idle_Loop':
                continue
            tracks = []
            for key, values in data['tracks'].items():
                if key not in parts:
                    continue
                change = correction * Rotation.from_quat(values) * correction.inv()
                if name != 'astronaut':
                    # Adapt a small gesture around the suit's existing rest pose.
                    change = Rotation.from_rotvec((change * change[0].inv()).as_rotvec() * .48)
                elif key.startswith(('upper_arm', 'forearm', 'hand')):
                    change = Rotation.from_rotvec(change.as_rotvec() * .8)
                quats = change.as_quat()
                quats[-1] = quats[0] * (-1 if np.dot(quats[-2], quats[0]) < 0 else 1)
                tracks.append((parts[key][0], 'rotation', quats))
            clip(asset, motion.removesuffix('_Loop'), np.linspace(0, data['seconds'], len(values)), tracks)

    elif name in {'barramundi_fish', 'street_rat'} or (
        entry['category'] in {'plants', 'grass', 'trees'} and name not in {'moss_01', 'dead_tree_trunk', 'tree_stump_01'}
    ):
        animal = entry['category'] == 'animals'
        rig = 'weighted body and tail' if animal else 'weighted wind chain'
        axis = 2 if animal else 1
        start = center.copy() if animal else rest_root.copy()
        end = start.copy()
        if animal:
            start[axis] = hi[axis] - (hi[axis] - lo[axis]) * (.57 if name == 'street_rat' else .40)
            end[axis] = lo[axis]
            if name == 'street_rat':
                start[1] = lo[1] + .26 * height
                end[1] = lo[1] + .07 * height
        else:
            end[axis] = hi[axis]
        p, pp = root, rest_root
        chain = []
        for k, pos in enumerate(np.linspace(start, end, 4)):
            p = joint(('BodyTail' if animal else 'Wind') + str(k + 1), pos, p, pp)
            chain.append(p)
            joints.append(p)
            binds.append(pos)
            pp = pos

        def weight_for(pos, node):
            if name == 'potted_plant_01' and any(x in node.get('name', '') for x in ('pot', 'pebble')) and not any(
                x in node.get('name', '') for x in ('stem', 'leaves')
            ):
                return rigid_weights(pos, node)
            u = (pos[:, axis] - start[axis]) / (end[axis] - start[axis])
            ids, weights = chain_weights(u, len(joints))
            return ids, weights

        tracks = []
        for k, node in enumerate(chain):
            angle = (.09 + .07 * k) if animal else (.024 + .008 * k)
            if name == 'street_rat' and k == 0:
                angle = .024
            tracks.append((node, 'rotation', rotation([0, 1, 0] if animal else [.8, 0, .6],
                                                       angle * wave(phase, -k * .65))))
        label = 'Swim' if name == 'barramundi_fish' else 'Tail_Flick' if animal else 'Wind'
        clip(asset, label, times * (1.4 if name == 'barramundi_fish' else 2.6 if animal else 4), tracks)

    if rig == 'rigid root':
        tracks = []
        if name == 'ingenuity-helicopter':
            rig = 'rigid root and rotor joints'
            for sign, label in [(1, 'rotors_01'), (-1, 'rotors_02')]:
                i = next(i for i, node in enumerate(asset.nodes) if node.get('name') == label)
                # The source nodes are oriented sideways locally. Rotate around world up in parent space.
                parent_rot = world[parents[i]][:3, :3]
                axis = np.linalg.solve(parent_rot, [0, 1, 0])
                axis /= np.linalg.norm(axis)
                base = Rotation.from_quat(asset.nodes[i].get('rotation', [0, 0, 0, 1]))
                tracks.append((i, 'rotation', (Rotation.from_quat(rotation(axis, sign * phase * 3)) * base).as_quat()))
                parts[label] = i, None
            tracks.append((root, 'translation', np.column_stack([times * 0, .16 * extent * (1 - np.cos(phase)) / 2, times * 0])))
            clip(asset, 'Rotor_Hover', times * 2, tracks)
        elif name == 'perseverance-rover':
            rig = 'original rover skin and rigid assembly root'
            clip(asset, 'Survey_Rock', times * 4, [(root, 'rotation', rotation([0, 0, 1], .045 * np.sin(phase)))])
        elif entry['category'] == 'space' and name != 'mission-control':
            clip(asset, 'Orbital_Turn', times * 8, [(root, 'rotation', rotation([0, 1, 0], phase))])
        elif name in {'boulder_01', 'moon_rock_01', 'moon_rock_02', 'namaqualand_boulder_02', 'rock_moss_set_01'}:
            clip(asset, 'Tumble', times * 6, [(root, 'rotation', rotation([.6, 0, .8], phase)),
                                             (root, 'translation', np.column_stack([times * 0, .18 * extent * (1 - np.cos(phase)), times * 0]))])
        else:
            clip(asset, 'Prop_Reveal', times * 5, [(root, 'rotation', rotation([0, 1, 0], .15 * np.sin(phase)))])

    bind_matrices = []
    for pos in binds:
        bind = IDENTITY.copy()
        bind[:3, 3] = pos
        bind_matrices.append(bind)
    for i, matrix in world.items():
        if 'mesh' not in asset.nodes[i] or 'skin' in asset.nodes[i]:
            continue
        if originals or name == 'ingenuity-helicopter':
            # Preserve any source object-level animation, by skinning its new child to the original node.
            skin_mesh(asset, i, matrix, [i], [matrix], rigid_weights, split=True)
        else:
            skin_mesh(asset, i, matrix, joints, bind_matrices, weight_for)
    asset.nodes[root]['translation'] = [0, 0, 0]
    animations = doc['animations']
    added = animations[originals:]
    doc['animations'] = added + animations[:originals]
    mesh_ids = sorted({node['mesh'] for node in asset.nodes if 'mesh' in node})
    mesh_map = {old: new for new, old in enumerate(mesh_ids)}
    doc['meshes'] = [doc['meshes'][i] for i in mesh_ids]
    for node in asset.nodes:
        if 'mesh' in node:
            node['mesh'] = mesh_map[node['mesh']]
    assert doc.get('skins')
    destination = output / (name + '.glb')
    asset.write(destination)
    return dict(id=name, rig=rig, original_clips=originals, skins=len(doc['skins']),
                clips=[a['name'] for a in added])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('decoded', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--extract-source', type=Path, help='rebuild the compact CC0 source motion data')
    args = parser.parse_args()
    motions_path = Path(__file__).with_name('humanoid-motion.json')
    if args.extract_source:
        motions = source_rotations(Asset(args.extract_source), {'Idle_Loop', 'Walk_Loop', 'Dance_Loop'})
        motions_path.write_text(json.dumps(motions, separators=(',', ':')) + '\n')
        return
    args.output.mkdir(parents=True, exist_ok=True)
    motions = json.loads(motions_path.read_text())
    records = []
    for entry in json.loads((ROOT / 'models.json').read_text()):
        record = build(args.decoded / Path(entry['file']).name, entry, args.output, motions)
        records.append(record)
        print(record['id'], record['rig'], ', '.join(record['clips']), flush=True)
    (args.output / 'manifest.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
