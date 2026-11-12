# Cinema set

Original models for telling a story on screen: a cast that can act, creatures nobody has
met, and the places and props they need. Every file here is generated from code in
[`tools/cinema`](../tools/cinema) with Blender's Python module, so nothing is downloaded and
nothing is scanned.

Each `.glb` is self-contained:

- one skinned mesh on one armature, so copies, crowds and clips work the same for every model
- a baked PBR texture set (base colour, normal, occlusion/roughness/metallic and, where the
  model glows, emission), stored as WebP
- Draco-compressed geometry
- several named animation clips; the first one is the default

[`manifest.json`](manifest.json) lists every file with its size, triangle count, deforming
bones and clips with their length in seconds.

## What is in it

| Group | Models | Clips |
|---|---|---|
| Cast | 25 people and humanoid animals, built on one rig with fingers, jaw and IK legs | Walk, Run, Idle, Wave, Dance, Jump, Squat, Talk, Clap, Cheer, Look Around, Point, Sit, Look Up, Float, and the emotions: Sad, Cry, Surprise, Love, Terror, Angry, Laugh, Embrace, Kneel, Shiver |
| Astronauts and suits | seven original suits | everything the cast has, plus Float, Moonwalk, Reach and Tumble |
| Animals | horses, cattle, deer, dogs, a cat, a rabbit, a rat, a fish, farm animals and a crested dinosaur | Walk, Trot, Gallop or Hop, Idle, Forage, Swim |
| Creatures | Abyss Watcher, Void Stalker, Hive Crawler, Star Jelly, Maw Worm, Sky Leviathan, Shadow Wraith, Bloom Titan, Crystal Golem, Glow Sprite, Tripod Colossus | each has its own, such as Hover, Stare, Lash, Loom, Screech, Rise, Roar, Bloom, Awaken, Giggle |
| The Melting Ones | six big-headed, wide-eyed creatures that drip, crack into facets and wear folded paper | every cast clip, plus Wobble, Hands Over Head, Melt and Stagger |
| The Shard family | a head of broken plates with a cross eye and a red tongue, as a floating head, a walker and a serpent | Hover, Lick, Shatter, Chomp, Laugh, Strut, Swim |
| Spacecraft | rocket, spaceplane, rover, scout drone, two landers, two probes, two telescopes, an orbital station and a control room | Liftoff, Engines, Glide, Open Bay, Drive, Survey, Rotor Hover, Touchdown, Signal Sweep, Orbital Turn, Scan the Sky |
| Nature | eight trees, eight plants, three grasses, eight rocks and three ground pieces | Wind, Gust, Turntable, Tumble |

Where a model shares its name with one in [`rigged/`](../rigged), it is the cinema version of
that model, and Set Film switches between the two with the model's Style setting. The spacecraft
and nature files keep the file names Set Film already used, but every design is original.

These are stylised film models, not photographic scans: they are meant to read clearly, light
well and move with feeling.

## Building

```sh
pip install bpy numpy pillow
npm ci --prefix animations
python3 tools/cinema/build.py --list                # every id
python3 tools/cinema/build.py cinema-astronaut      # one model, into cinema/
python3 tools/cinema/build.py --module monsters --preview /tmp/shots
node tools/cinema/pack.mjs                          # Draco, validation, manifest.json
```

`core.py` holds the shared helpers (soft volumes, procedural materials, atlas baking, rigging,
clips, export), `materials.py` the surfaces, and each other file one family of models.

## Licence

The [Ruralive Models Licence](../LICENSE), like everything else in this repository.
