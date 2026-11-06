# Vael and Mira story assets

Original, stylized models for *The Echo of Vael* and *The Margin of Mira*. The
models are dedicated to the public domain under CC0-1.0. Each GLB contains the
mesh, UVs, JPEG textures and its named animation clips. They use Y up and contain
no external media or compression extensions. Characters have skinned skeletons.
Vehicles, rooms, props and the cat use rigid animated part hierarchies.

| Collection | Models |
| --- | --- |
| Vael cast | Lyra, Teo, child Teo, Ismael, Captain Tanaka-Bell, Aru |
| Vael sets | Ring city, transit car, apartment, cradle room, clinic, mission control |
| Vael hardware | Meridian Hymn, visor, Severance Lance, signal probe |
| Mira cast | Mira, the director as an adult and child, Producer Vale, Lumen, studio cat |
| Mira sets | Open studio, edit bay, commuter train, night shuttle |
| Mira props | Stylus and page, laptop, phone, pen jar, light table, archive panel stack, Severance Cut console, paper memory-fish |
| Shared | Kite core, lantern, dandelion |

The manifest lists the default clip and all available clips per model. The
human rigs include in-place walk and run, idle, wave, dance, jump and squat.
Move characters and vehicles through the scene with Setfilm position controls.
The clip endpoints match, including one-shot-style loops such as the laptop
closing and reopening and the lance firing and resetting.

Rebuild from the repository root with `python tools/build_story_models.py`.
The generator reuses the existing expansion, motion-prop and character
builders. Validate the embedded textures and every clip in Blender with
`blender -b -t 2 --python-exit-code 1 -P tools/verify_farm_and_worksite.py -- rigged/story-worlds`.
