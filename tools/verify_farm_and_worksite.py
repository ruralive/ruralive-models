"""Check each clip's sampled motion and import the model in Blender."""
import json
import math
import struct
import sys
from pathlib import Path

import bpy


def verify(path, entry):
    data = path.read_bytes()
    assert struct.unpack_from("<4sII", data) == (b"glTF", 2, len(data)), path
    json_size, json_tag = struct.unpack_from("<I4s", data, 12)
    assert json_tag == b"JSON", path
    gltf = json.loads(data[20:20+json_size])
    binary = 28+json_size
    assert len(data) == entry["bytes"] and len(data) < 2_000_000, path
    assert len(gltf["buffers"]) == 1 and "uri" not in gltf["buffers"][0], path
    assert gltf["images"] and all("bufferView" in image for image in gltf["images"]), path
    assert [animation["name"] for animation in gltf["animations"]] == entry["animations"], path

    def samples(index):
        a = gltf["accessors"][index]
        v = gltf["bufferViews"][a["bufferView"]]
        count = {"SCALAR":1,"VEC3":3,"VEC4":4}[a["type"]]
        assert a["componentType"] == 5126
        offset = binary+v.get("byteOffset",0)+a.get("byteOffset",0)
        return [struct.unpack_from("<"+"f"*count,data,offset+i*count*4) for i in range(a["count"])]

    for animation in gltf["animations"]:
        channels = animation["channels"]
        assert channels and len({(c["target"]["node"], c["target"]["path"]) for c in channels}) == len(channels)
        moved = False
        for channel in channels:
            sampler = animation["samplers"][channel["sampler"]]
            times, values = samples(sampler["input"]), samples(sampler["output"])
            assert len(values) == len(times) and times[0] == (0.0,)
            assert all(a < b for a,b in zip(times,times[1:]))
            assert all(math.isfinite(x) for row in values for x in row)
            first, last = values[0], values[-1]
            if channel["target"]["path"] == "rotation":
                assert all(abs(sum(x*x for x in row)-1)<1e-5 for row in values)
                assert abs(sum(a*b for a,b in zip(first,last))) > .99999
                moved |= any(abs(sum(a*b for a,b in zip(first,row))) < .999 for row in values)
            else:
                assert all(math.isclose(a,b,abs_tol=1e-5) for a,b in zip(first,last))
                moved |= any(not math.isclose(a,b,abs_tol=1e-3) for row in values for a,b in zip(first,row))
        assert moved, (path,animation["name"])

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    assert any(obj.type == "MESH" for obj in bpy.context.scene.objects), path
    assert bpy.data.images and all(image.packed_file for image in bpy.data.images), path
    tracks = [track.name for obj in bpy.context.scene.objects if obj.animation_data
              for track in obj.animation_data.nla_tracks]
    assert all(name in tracks for name in entry["animations"]), (path,tracks)
    arms = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    assert bool(arms) == entry["armature"], path
    if arms:
        assert len(arms) == 1 and len(arms[0].data.bones) >= 11, path
    print("VERIFIED",path.name,len(entry["animations"]))


directory=Path(sys.argv[-1]).resolve()
for entry in json.loads((directory/"manifest.json").read_text())["models"]:
    verify(directory/entry["file"],entry)
