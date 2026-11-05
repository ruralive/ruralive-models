# Ruralive models

Free 3D models for the Realistic 3D Model node in Ruralive Set Film. The app downloads each file once to the viewer's browser the first time it is used.

These are copies from the sources below, packed into single `.glb` files at 1K texture resolution. We did not make them. [`CREDITS.md`](CREDITS.md) lists every model with its authors, licence and source, and [`models.json`](models.json) holds the same data for the app.

## Rigged versions

The [rigged/](rigged/) folder contains self-contained animated GLBs. See [the animation guide](animations/README.md) for the rig types, clips and tests.

## Sources

| Source | Models | Licence |
|---|---|---|
| [Poly Haven](https://polyhaven.com/models) | Trees, plants, grass, rocks, ground cover, street rat | [CC0 1.0](https://polyhaven.com/license) |
| [NASA 3D Resources](https://github.com/nasa/NASA-3D-Resources) | Astronaut, spacesuits, rovers, spacecraft, telescopes, Mission Control | No copyright, under [NASA's media usage guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/) |
| [Khronos glTF Sample Assets](https://github.com/KhronosGroup/glTF-Sample-Assets) | Barramundi Fish | CC0 1.0 |

Thanks to Poly Haven and its artists. CC0 does not require credit, but we give it anyway.

## Licence

The Poly Haven and Khronos models and the build script are under [CC0 1.0](LICENSE). Only CC0 models are accepted from those sources, so they require no credit.

**NASA models are not under that licence.** NASA describes them as free and without copyright, and they come with its own conditions: use must not suggest that NASA endorses a product or film, and NASA's names, logos and insignia, some of which may appear on the models, have their own rules. Read [NASA's guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/) before commercial use.

These files come with no warranty and grant no trademark rights. If you use these models, check the original source for its current terms.

## Updating

Edit the lists in `tools/build_models.py` and push to `main`. The **Build models** workflow downloads the models again and commits the results.
