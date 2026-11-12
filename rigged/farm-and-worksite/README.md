# Farm and worksite

28 original stylized models under the [Ruralive Models Licence](../../LICENSE). Meshes, textures, rigs where applicable, and animation clips are embedded in each GLB. See the [manifest](manifest.json) for the full file and clip list.

- **Construction:** tower crane, dump truck, forklift, road roller, bulldozer and wheel loader. Actions include hook lowering, bed tipping, fork lifting, rolling and bucket dumping.
- **Farm and storage:** tractor, farmyard barn with opening doors, cow, pig, sheep, goat, hen, duck, goose, two crates and a coin-filled treasure chest.
- **Characters:** six people with different body shapes and outfits, including two construction workers, plus a humanoid fox, rabbit, bear and pig. Each has a skeletal rig and seven clips: Walk in Place, Run in Place, Idle, Wave, Dance, Jump and Squat.
- **Farm animals:** three clips per animal: Walk in Place, Forage and Idle. These use animated body parts.

Rebuild with Python, NumPy and Pillow, then verify using Blender 4.3 or compatible.

```sh
python tools/build_farm_and_worksite.py
blender -b --python-exit-code 1 -P tools/verify_farm_and_worksite.py -- rigged/farm-and-worksite
```
