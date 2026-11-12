# Animated model expansion

37 original, stylized 3D assets for general scenes, under the [Ruralive Models Licence](../../LICENSE). The [manifest](manifest.json) lists each file, its default animation and its size.

| Category | Models |
| --- | --- |
| Vehicles | City hatchback, utility pickup, open car with driver, bicycle, motorcycle, motorcycle with rider |
| People | Two women, two men, cavewoman, caveman |
| Animals and insects | Chestnut horse, wild rabbit, crested dinosaur, housefly, mosquito, butterfly |
| Plants | Cactus, sunflower, young palm |
| Space | Venus, Saturn, Sun, variable star, black hole |
| Environments | Sand dunes, rocky river, snowy mountains, limestone cave, erupting volcano, giant breaking wave |
| Props | Steel spoon, gears, chemical reaction bench, snare drum, acoustic guitar |

Each GLB embeds meshes, UVs, normals, procedural JPEG textures and a named two-second animation. The characters walk in place or sit in their vehicle. Character geometry uses an armature with one joint influence per vertex. Vehicles, animals, insects, vegetation, effects and props use animated component transforms. Space and natural phenomena are stylized illustrations.

The Blender verification imports every GLB, checks embedded images, inspects character armatures and samples animated transforms to verify movement and matching loop endpoints.

Build from the repository root with Python, NumPy and Pillow. Verify with Blender 4.3 or compatible.

```sh
python tools/build_expansion.py
blender -b -P tools/verify_expansion.py -- rigged/expansion
```
