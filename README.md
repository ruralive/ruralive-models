# Ruralive models

Free 3D models for the Realistic 3D Model node in Ruralive Set Film. The app downloads each file once to the viewer's browser the first time it is used.

These are copies from the sources below, packed into single `.glb` files at 1K texture resolution. We did not make them. [`CREDITS.md`](CREDITS.md) lists every model with its authors, licence and source, and [`models.json`](models.json) holds the same data for the app.

## Sources

| Source | Models | Licence |
|---|---|---|
| [Poly Haven](https://polyhaven.com/models) | Trees, plants, grass, rocks, ground cover, street rat | [CC0 1.0](https://polyhaven.com/license) |
| [Khronos glTF Sample Assets](https://github.com/KhronosGroup/glTF-Sample-Assets) | Barramundi Fish | CC0 1.0 |

Thanks to Poly Haven and its artists. CC0 does not require credit, but we give it anyway.

## Licence

Everything here is under [CC0 1.0](LICENSE), including the build script. Only models under CC0 are accepted, so nothing here requires credit.

CC0 gives no warranty and grants no trademark rights. If you use these models, check the original source for its current terms.

## Updating

Edit the lists in `tools/build_models.py` and push to `main`. The **Build models** workflow downloads the models again and commits the results.
