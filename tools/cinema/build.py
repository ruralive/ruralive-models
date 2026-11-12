"""Build cinema models: python3 tools/cinema/build.py [--preview DIR] [--out DIR] id ...

Every id is built in a clean Blender scene, baked to one PBR atlas and written to OUT/id.glb
with a small OUT/.meta/id.json for the manifest. Run with `--list` to print every id.
"""
import importlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402

MODULES = ['people', 'creatures', 'monsters', 'nature', 'worlds', 'vehicles', 'machines', 'props', 'places',
           'story', 'studio']


def registry():
    found = {}
    for name in MODULES:
        try:
            module = importlib.import_module(name)
        except ModuleNotFoundError as error:
            if error.name != name:
                raise
            continue
        for model_id, fn in module.MODELS.items():
            found[model_id] = (name, fn, getattr(module, 'ATLAS', {}).get(model_id, 2048))
    return found


def main(argv):
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out, shots, ids = os.path.join(root, 'cinema'), None, []
    args = list(argv)
    while args:
        a = args.pop(0)
        if a == '--out':
            out = args.pop(0)
        elif a == '--preview':
            shots = args.pop(0)
        elif a == '--list':
            print('\n'.join(registry()))
            return
        elif a == '--module':
            wanted = args.pop(0)
            ids += [i for i, v in registry().items() if v[0] == wanted]
        else:
            ids.append(a)
    reg = registry()
    for model_id in ids:
        started = time.time()
        module, fn, atlas = reg[model_id]
        core.reset(sum(map(ord, model_id)))
        result = fn()
        rig, mesh = result[0], result[1]
        opts = result[2] if len(result) > 2 else {}
        tris = sum(len(p.vertices) - 2 for p in mesh.data.polygons)
        core.bake_atlas(mesh, opts.get('atlas', atlas), name=model_id)
        if rig:
            rig.obj.name = model_id
        path = core.export(os.path.join(out, model_id + '.glb'))
        meta = {'id': model_id, 'set': module, 'triangles': tris,
                'bones': len([b for b in rig.obj.data.bones if b.use_deform]) if rig else 0,
                'animations': [a.name for a in rig.actions] if rig else [],
                'seconds': {a.name: round((a.frame_range[1] - a.frame_range[0]) / core.FPS, 3)
                            for a in rig.actions} if rig else {}}
        os.makedirs(os.path.join(out, '.meta'), exist_ok=True)
        with open(os.path.join(out, '.meta', model_id + '.json'), 'w') as handle:
            json.dump(meta, handle)
        if shots:
            os.makedirs(shots, exist_ok=True)
            if rig and rig.actions:
                ad = rig.obj.animation_data
                action = rig.actions[opts.get('preview_clip', 0)]
                ad.action = action
                if hasattr(ad, 'action_slot') and action.slots:
                    ad.action_slot = action.slots[0]
            core.preview(os.path.join(shots, model_id + '.jpg'), [mesh], size=560, samples=20,
                         frame=opts.get('preview_frame', 9), angle=opts.get('preview_angle', 32),
                         elevation=opts.get('preview_elevation', 12),
                         dark=opts.get('preview_dark', False))
        print('BUILT %s %.1fs %d tris %d bytes' % (model_id, time.time() - started, tris,
                                                   os.path.getsize(path)), flush=True)


if __name__ == '__main__':
    main(sys.argv[1:])
