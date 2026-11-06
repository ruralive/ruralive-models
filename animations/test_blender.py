"""Import every output and sample every new loop with Blender's evaluated geometry."""
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

directory = Path(sys.argv[sys.argv.index('--') + 1])
report = []
for entry in json.loads((directory / 'manifest.json').read_text()):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str((directory / (entry['id'] + '.glb')).resolve()))
    scene = bpy.context.scene
    assert any(obj.type == 'ARMATURE' for obj in scene.objects), entry['id']
    meshes = [obj for obj in scene.objects if obj.type == 'MESH' and not obj.hide_render]
    assert meshes, entry['id']
    animated = [obj.animation_data for obj in scene.objects if obj.animation_data]
    for data in animated:
        data.action = None
        for track in data.nla_tracks:
            track.mute = True

    def sample(frame):
        scene.frame_set(int(frame), subframe=float(frame % 1))
        deps = bpy.context.evaluated_depsgraph_get()
        positions = []
        for obj in meshes:
            mesh = obj.evaluated_get(deps)
            vertices = np.empty(len(mesh.data.vertices) * 3, dtype=np.float32)
            mesh.data.vertices.foreach_get('co', vertices)
            matrix = np.asarray(mesh.matrix_world)
            xyz = vertices.reshape(-1, 3)[::max(1, len(vertices) // 12_000)]
            positions.append(xyz @ matrix[:3, :3].T + matrix[:3, 3])
        joined = np.concatenate(positions)
        assert np.isfinite(joined).all(), entry['id']
        return joined

    rest = sample(1)
    extent = np.ptp(rest, axis=0).max()
    assert extent > 0, entry['id']
    if entry.get('wheels'):
        wheel_meshes = [scene.objects[name + '.mesh'] for name in entry['wheels']]
        armature = next(obj for obj in scene.objects if obj.type == 'ARMATURE' and
                        all(name in obj.pose.bones for name in entry['wheels']))
        def wheel_geometry():
            bpy.context.view_layer.update()
            deps = bpy.context.evaluated_depsgraph_get()
            return [np.array([tuple(v.co) for v in mesh.evaluated_get(deps).data.vertices])
                    for mesh in wheel_meshes]
        original = wheel_geometry()
        for index, name in enumerate(entry['wheels']):
            bone = armature.pose.bones[name]
            axis = armature.matrix_world.to_3x3() @ bone.bone.matrix_local.to_3x3() @ Vector((0, 1, 0))
            assert abs(axis.normalized().x) > .9999, (name, axis)
            bone.rotation_mode = 'XYZ'
            bone.rotation_euler.y = .53
            moved = [np.max(np.abs(a - b)) for a, b in zip(original, wheel_geometry())]
            assert moved[index] > .01 and all(d < 1e-6 for i, d in enumerate(moved) if i != index), (name, moved)
            bone.rotation_euler.y = 0
        print('PASS all six wheels rotate independently around their axles', flush=True)
    results = []
    for name in entry['clips']:
        selected = [t for data in animated for t in data.nla_tracks if t.name == name]
        assert selected, (entry['id'], name)
        for track in selected:
            track.mute = False
        start = min(t.strips[0].frame_start for t in selected)
        end = max(t.strips[-1].frame_end for t in selected)
        first = sample(start)
        last = sample(end - .0001)
        middle = [sample(start + (end - start) * fraction) for fraction in (.17, .37, .63, .83)]
        gap = float(np.max(np.abs(last - first)) / extent)
        movement = float(max(np.max(np.abs(p - first)) for p in middle) / extent)
        assert gap < .003, (entry['id'], name, 'loop seam', gap)
        assert .00005 < movement < 3, (entry['id'], name, 'motion', movement)
        for track in selected:
            track.mute = True
        results.append(dict(name=name, seam=round(gap, 7), motion=round(movement, 7)))
        print('PASS', entry['id'], name, gap, movement, flush=True)
    report.append(dict(id=entry['id'], clips=results))
(directory / 'blender-test.json').write_text(json.dumps(report, indent=2) + '\n')
