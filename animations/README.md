# Rigged Ruralive models

The files in [rigged/](../rigged/) embed their model, materials and any original textures, skeleton and animation clips in each GLB. The first clip is the default loop. Clip names and source animation counts are in [manifest.json](../rigged/manifest.json).

| Models | Default motion and rig |
| --- | --- |
| Astronaut | Idle, with additional in-place Walk and Dance clips on a weighted humanoid rig |
| Four posed spacesuits | Subtle Idle adapted around each suit's rest pose, with a weighted humanoid rig |
| Barramundi and street rat | Procedural Swim and Tail Flick on weighted chains |
| Quaternius quadrupeds | Original rig and named clips, with Idle first and in-place Walk and Gallop |
| Grass, foliage and live trees | Wind on a weighted chain with the base anchored |
| Ingenuity | Rotor Hover with counter-rotating rotor joints |
| Perseverance | Survey Rock on the assembly root, with the source rover rig, clips and six separately driven wheels |
| Other spacecraft | Orbital Turn on a rigid rig, with any source clips retained |
| Rocks, terrain and static props | Tumble or Prop Reveal on a rigid rig |

Clips are sampled and close at the loop seam. The models use glTF's Y-up convention with the rest bounds centered horizontally and the base on the ground. The Walk clip is in place and can slide if the movement speed does not match its stride. The spacesuit rigs are weighted for their supplied poses and the included motion. Some posed suits have built-in backpacks or props, which can deform under larger gestures.

The humanoid Idle, Walk and Dance were adapted from the [Quaternius Universal Animation Library Standard](https://opengameart.org/content/universal-animation-library), CC0 1.0. The source archive SHA-256 is `18ff1a7215f4852b320203e8aaf02a1578b5c8eef9027fbaedfcedc7b85a3ac2`. The compact rotation samples in this directory are from the Godot Standard GLB. To regenerate them, pass that GLB via `--extract-source` to the build script. Procedural clips and rigging code are CC0 1.0. Original model credits and NASA usage conditions are documented in [CREDITS.md](../CREDITS.md) and the repository [README](../README.md).

## Rebuild and test

Run from the repository root with Node.js, Python with NumPy, SciPy and Pillow, and Blender 4.3 or later. The Blender test runs on decoded GLBs so it also works in distributions that ship Blender without its Draco import library.

```sh
npm ci --prefix animations
python -m pip install numpy scipy Pillow
node animations/decode.mjs /tmp/ruralive-decoded
python animations/prepare-nature.py /tmp/ruralive-nature-source /tmp/ruralive-decoded
python animations/build.py /tmp/ruralive-decoded /tmp/ruralive-rigged
blender -b --python-exit-code 1 --python animations/test_blender.py -- /tmp/ruralive-rigged
node animations/pack.mjs /tmp/ruralive-rigged
```

The Blender check imports every model and checks every added clip for visible vertex motion, finite geometry, and loop closure. The packer uses Draco for larger files and validates the final GLBs. The original motion clips remain available, including non-looping clips.

## Nature assets and NASA adjustments

[nature.json](nature.json) credits the four Poly Haven trees and 12 CC0 Quaternius animals from the [Animated Animal Pack](https://poly.pizza/bundle/Animated-Animal-Pack-ILAPXeUYiS). The tree builder keeps one variant, reduces the branch and trunk geometry, and keeps whole textured foliage islands. It needs the large upstream tree files during a rebuild. The checksum-pinned, CC0 animal originals are included as compressed build inputs because the upstream CDN can block unattended builds. The resulting rigged GLBs are considerably smaller.

The Z2 suit uses a cleaned version of the source colour atlas. James Webb starts with its gold mirror array in view, with revised mirror and sunshield finishes. These are Setfilm presentation changes to the NASA originals.

### Driving the Perseverance wheels

The GLB has six wheel meshes, each entirely weighted to its own bone: `wheel.FL`, `wheel.FR`, `wheel.ML`, `wheel.MR`, `wheel.RL` and `wheel.RR`. Positive local Y is the axle on all six. Each bone includes `extras.wheelName`, `extras.radius` (in original model units), and `extras.axle`. Read `userData.wheelName` in Three.js because the loader may sanitize periods in node names. Multiply the radius by the model's applied scale when converting world-space travel distance into a rotation angle. There are no drive channels on the wheels.
