---
name: realistic-skin
description: Build, tune or review realistic human skin for the cinema characters (tools/cinema/real.py): the colour science of skin (melanin, oxy/deoxy blood, carotene, veins), face colour zones, pores, moles and freckles, blemishes, scars, dirt, lips, beard stubble, arm hair, subsurface, baking to the UV texture and checking the renders. Use whenever a character's skin, lips, face hair or skin colour is made or changed, or when a render "looks like plastic / too clean / one flat colour".
---

# Realistic skin

Everything here is procedural and ours: no photo textures from the internet (licence rule of
ruralive-models: only models made by the user, Claude or ChatGPT; MPFB/MakeHuman CC0 assets are
the only outside pieces, and only for body shape, eyes, hair cards and garment meshes).
The skin is a Blender node tree built in `skin_material(spec, j)` and baked by `bake_all` to a
4096 atlas on the MPFB body UVs (colour, roughness, normal), so the glTF carries it.

## 1. What colour skin really is

Skin is translucent layers, each absorbing part of the light. Never paint it as one colour plus
noise. Think of four absorbers mixed in different amounts at every point:

| Chromophore | Where | Colour it adds | How it varies |
|---|---|---|---|
| Melanin (epidermis) | everywhere, more on sun-exposed parts | brown; hides everything under it | the skin tone itself; freckles, moles, sun spots |
| Oxygenated blood (dermis capillaries) | cheeks, nose, ears, lips, knuckles, elbows, knees, fingertips, toes | red-pink | flush, exercise, cold, emotion; blotchy |
| Deoxygenated blood (veins, pooled) | under the eyes, temples, eyelids, inner wrist, back of hands, chest, feet | violet-blue | thin skin over veins |
| Veins seen through fat | inner arms, hands, chest, temples, feet | **blue-green / teal-grey** (never pure blue: the skin scatters blue back, so veins look cool only next to warm skin) | branching threads, soft edges |
| Carotene + thick horny layer | palms, soles, heels, forehead, nose bridge | yellow-golden | thick skin, diet |
| Hair under the skin (shaved/stubble areas) | lower face in men, armpits, legs | grey-blue-green | the "beard shadow" |

Rules that follow:
- **Each absorber is a gentle MULTIPLY** with a near-white tint (`#ffb2a6` red, `#ffe9b8` yellow,
  `#a8bcc8` vein, `#d4c4dc` violet, `#d6e2de` cool green-grey). Multiplying keeps the light/dark
  structure of the skin and behaves like Beer-Lambert absorption. MIX toward a saturated colour
  makes paint-like blotches.
- **Melanin masks the rest.** Scale all chromophore tints by `k = 0.45 + 0.55*min(1, L/0.5)`, where
  L is the luminance of the skin tone: pale skin shows reds and veins strongly; deep skin keeps its
  warm undertones but much less visible veins and flush.
- **Three scales at once**: large slow blotches of each chromophore *out of step with each other*
  (noise 2-4), mid-scale mottling (noise 30), and fine chromatic grain cell by cell (noise ~400,
  a separate one each for red, yellow and blue). The fine grain is what stops the "plastic" look
  at portrait distance.
- **The face in thirds** (portrait painters' rule): forehead golden/yellow, middle third (cheeks,
  nose, ears) red, lower third (upper lip, chin, jaw) cool blue-green-grey — stronger on men
  because of the beard under the skin. Ears and nose tip are the reddest; eyelids and the
  hollows under the eyes are violet.

## 2. Layer order in the shader

Order matters; later layers sit on top. In `skin_material`:

1. **Relief / height**: pores at two scales (voronoi F1 2200 and 5200), fine cell lines
   (voronoi distance-to-edge 650), soft flesh relief (noise 60).
2. **Base tone**: noise ramp between `skin2` (shadow tone) and `skin` (light tone), plus mid mottling.
3. **Flush** (vertex mask R): cheeks, nose, ears, knuckles, mixed toward `flush` at 0.28.
4. **Chromophores** (`skin_chroma`): blotches, chromatic grain, face thirds, red joints, yellow
   palms and soles, veins in their zones, violet under-eyes. See section 1.
5. **Pigment marks**: freckles (zone mask A, upper body/face), rare large moles, and a body-wide
   layer of small moles and freckles in two sizes (voronoi 90 and 300, chosen cells by random
   colour, several browns `#4a2a1c..#8a5a3c`).
6. **Lips** (`lips_shape`), per pixel, see section 4.
7. **Stubble** (vertex mask B through `beard_zone`), see section 5.
8. **Pores darkening** of the colour (pores × 0.3 toward `skin2`).
9. **Roughness**: 0.5 + pores; lips smoother (−0.18); T-zone oilier.
10. **Imperfections** (`skin_imperfections`), see section 3.
11. **Arm hair** (attribute `hairzone`), see section 5.
12. `m.set(...)` with bump strength 0.55, distance 0.0007 (sub-millimetre).

## 3. Imperfections: skin must look lived in

Too clean = CG. For a period piece (medieval) push them further; for a glossy future scene, pull back.
- **Blotchy redness** at hand scale (noise 9), tint toward flush ×0.1.
- **Active blemishes**: rare voronoi cells (`rare_spots(m, 55, 0.02, 0.09, seed)`), red `#a8443a`
  ×0.5, raised (height +0.6), with a pale tiny head.
- **Old marks**: flat faded brown-red spots, scale 70, ×0.3.
- **Scars**: thin lines from voronoi distance-to-edge on stretched, rotated coordinates, only
  inside a few rare large cells; pale `#e8c8b4`, sunken (height −0.5), a bit shinier.
- **Broken capillaries**: thin noise ridges (scale 120) masked by the flush zone, `#b0302a` ×0.22.
- **T-zone**: bigger open pores and lower roughness down the nose and across the forehead.
- **Dry patches**: low-frequency noise, ashy lighter colour and rougher, with tiny flakes.
- **Dirt / grime** (`spec["grime"]`, 0.4–0.7 for the medieval cast): a cavity-weighted dark layer
  (pointiness or AO while baking) on hands, nails, neck creases and feet, warm grey-brown
  `#4a3a2a`, plus a large noise of smudges ×0.1–0.25. Keep it off the lips and eye whites.
- Use a different `seed` per layer in `rare_spots` so marks don't line up.

## 4. Lips

- Vertex masks are **too coarse** for lips (few vertices there: the shape came out round and
  blurry). Draw them per pixel in object space in `lips_shape(m, j)`; the bake writes the crisp
  shape into the UV texture.
- Mouth centre: MakeHuman's `joint-mouth` sits at the nose. Use the centre of
  `helper-upper-teeth` minus 4 mm in z.
- Shape: half width 25 mm, upper height 8.5 mm with a cupid's bow (two peaks at |u|≈0.2 and a
  1.6 mm dip at the centre), lower lip 10.5 mm and fuller (`span**0.7`). Edge softness 1.1 mm.
  Only on the front (`y < mouth.y − 4 mm`).
- Colour: spec `lips` mixed ×0.9, a darker parting line `#2a1210` (gaussian 0.9 mm under the
  centre), fine vertical creases (voronoi edge on coordinates squashed in z), lower roughness.
- Lip colour per character: dark skin `#4e2420`, pale `#9c4f4a`, warm `#a35a58`. Lips are skin
  with more blood showing through; never pure pink or red.

## 5. Face and body hair as colour

- **Stubble / beard shadow** (`beard_zone`, strength `spec['stubble']`): soft-edged zone with
  moustache, chin, jaw, lower cheeks rising to the sideburns, down the neck under the jaw; off the
  lips, thinner under the lower lip. Patchy growth (noise 28), a grey-blue shadow under the skin
  ×0.22, short dark hairs from two voronoi scales (3600, 6000) in the hair colour ×0.45, tiny
  height. Keep it soft: "manchas muito suaves".
- **Arm hair** (`arm_hair`, strength `spec['body_hair']`, men ~0.85, women 0.2–0.35): densest on
  the outer forearm, lighter on the upper arm, a little on the back of the hand. Patches (noise 18)
  of a slightly darker tone, plus short strokes from noise stretched along the arm.
- Real hair (head, brows, lashes) uses MakeHuman CC0 cards with ROUND alpha (glTF MASK), not
  particles: particles don't export to glTF/three.js.

## 6. Subsurface and lighting

- Renders only (not in glTF): Subsurface weight 0.35, radius (1.0, 0.35, 0.18) — red scatters
  furthest, as measured for human skin — scale 3.5 mm.
- Specular: roughness ~0.5 on skin, 0.32 on lips, oilier T-zone. Hair: roughness 0.62, specular
  IOR level 0.25 (else a white patch on the cap).
- Portrait lights: key 160 W, fill 35 W, rim 220 W area lights, AgX view. Check under a warm and a
  cool light: good skin keeps its reds and blue-greens in both.

## 7. Pitfalls already hit

- A ColorRamp clamps its input to 0..1: feeding a raw height in metres (waist at ~1 m) never
  reaches the stops. Remap first: `(z − waist)/width + 0.5` with clamp.
- Vertex masks for small features (lips, scars) look blurry; use per-pixel object-space math.
- Lips placed from `joint-mouth` end up on the nose ("clown nose").
- Saturated MIX for blood/veins looks like make-up; use near-white MULTIPLY tints.
- One noise for all colour variation gives a single-hue skin; give each chromophore its own noise.

## 8. Workflow and checks

```bash
python3 tools/cinema/real.py /tmp/chars/out /tmp/chars/shots tomas amara mei > /tmp/chars/all.log 2>&1
```
- Takes ~6–7 min per character (skin bake 4096, outfit 2048, renders). Watch for `^BUILT` or
  `Traceback` in the log.
- Look at `/tmp/chars/shots/<id>-portrait.jpg` and `-full.jpg` yourself before sending them:
  lips outline crisp; forehead warmer and lower face cooler than the cheeks; veins only faintly
  visible at temples and wrists; no single flat hue across the cheek; moles and blemishes
  present but rare; stubble soft; no plastic sheen.
- Compare the three skin tones side by side (contact sheet); the chromophores should read on all
  of them, much less on the darkest.
