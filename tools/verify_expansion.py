"""Smoke-test all expansion GLBs with Blender's glTF importer."""
import json
import math
import struct
import sys
from pathlib import Path

import bpy


def pose(scene, frame):
    scene.frame_set(frame)
    matrices = {}
    for obj in scene.objects:
        matrices[obj.name] = tuple(v for row in obj.matrix_world for v in row)
        if obj.type == "ARMATURE":
            for bone in obj.pose.bones:
                matrices[obj.name + "/" + bone.name] = tuple(v for row in bone.matrix for v in row)
    return matrices


def verify(path, entry):
    data = path.read_bytes()
    assert struct.unpack_from("<4sII", data) == (b"glTF", 2, len(data)), path
    length, kind = struct.unpack_from("<I4s", data, 12)
    assert kind == b"JSON", path
    document = json.loads(data[20:20+length])
    assert len(data) == entry["bytes"] < 50_000_000, path
    assert all("uri" not in buffer for buffer in document["buffers"]), path
    assert document["images"] and all(
        "bufferView" in image and image["mimeType"] in ("image/png", "image/jpeg")
        for image in document["images"]
    ), path
    animation = document["animations"][0]
    assert animation["name"] == entry["animation"] and animation["channels"], path
    assert not set(document.get("extensionsUsed", [])) & {
        "EXT_meshopt_compression", "KHR_texture_basisu"
    }, path

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    scene = bpy.context.scene
    assert any(obj.type == "MESH" for obj in scene.objects), path
    assert bpy.data.actions and bpy.data.images, path
    assert all(image.packed_file for image in bpy.data.images), path
    armatures = [obj for obj in scene.objects if obj.type == "ARMATURE"]
    if any(tag in path.stem for tag in ("woman", "man-in", "caveman", "with-driver", "with-rider")):
        assert len(armatures) == 1 and len(armatures[0].data.bones) >= 10, path

    frames = [(int(action.frame_range[0]), int(action.frame_range[1])) for action in bpy.data.actions]
    first, last = min(a for a, _ in frames), max(b for _, b in frames)
    assert last > first, path
    start, middle, end = (pose(scene, frame) for frame in (first, first+(last-first)//4, last))
    assert any(
        not math.isclose(a, b, abs_tol=1e-4)
        for name in start for a, b in zip(start[name], middle[name])
    ), f"No animated transforms: {path}"
    assert all(
        math.isclose(a, b, abs_tol=2e-4)
        for name in start for a, b in zip(start[name], end[name])
    ), f"Loop endpoints differ: {path}"
    print("VERIFIED", path.name, entry["animation"], len(armatures))


directory = Path(sys.argv[-1]).resolve()
manifest = json.loads((directory / "manifest.json").read_text())
for model in manifest["models"]:
    verify(directory / model["file"], model)
