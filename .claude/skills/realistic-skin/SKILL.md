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

## 1b. What painters and hyperrealists do (and how it maps to the shader)

Studied: Sabrillu's coloured-pencil skin tutorial, Ioanna Ladopoulou's skin-tones tutorial,
Eternal3D's "How artists paint realistic skin", James Gurney's face colour zones (via Sefki
Ibrahim's digital-face write-up), and how hyperrealists build skin: Ron Mueck (tinted silicone
layered in depth, then veins and blemishes painted on top), oil glazers such as Roberto Bernardi
(many thin transparent glazes, each dried before the next, for optical depth).

| Painter's rule | Shader translation |
|---|---|
| Skin is never one colour; posterize a photo and blues, greens, purples, yellows appear. | Separate noise per chromophore, out of step; measure with `skin_check.py` (section 8). |
| Light areas warm and rosy, shadow areas cool (blue, green, grey). Balance warm and cool. | `convex` (pointiness high) gets a warm `#fff0e6` multiply; `concave` a cool `#e0e8de` one. |
| Darks stay saturated (reddish Van Dyke brown); black "kills" skin colour. | Concave also gets `#e8c4b4`; `skin2` shadow tones are saturated browns, never grey. |
| Three values (highlight, midtone, shadow), built light to dark in thin even layers. | Base ramp `skin2`→`skin`, then many low-opacity MULTIPLY layers (glazes), never one opaque coat. |
| Too pink? Add its complement, green, rather than grey. | `mute`: faint green patches, stronger inside the flush zones. |
| Forehead yellow, middle red, lower third blue-green; subtler on women. | Face thirds in `skin_chroma`; the lower third scales with `stubble` (0.45 women, up to 0.9 men). |
| Edges soft; details (pores, freckles, wrinkles, scars, follicles) suggested, never overdone. | Every mask has a soft falloff; marks are rare; amounts stay low (0.1–0.5). |
| Mueck: colour in depth first, surface detail last. | Order: base → chromophores → pigment → lips/hair → imperfections → grime. |
| Lighting changes the read: warm sun, cool interior, candle. | Check renders under warm and cool light; the albedo must survive both. |

## 1c. Five centuries of realist and hyperrealist flesh

What each tradition teaches, and what the shader takes from it.

| Who / when | How they made flesh | Shader lesson |
|---|---|---|
| Cennini (c. 1400), Italian tempera and fresco | Flesh over a **terre verte / verdaccio** (green-grey) underlayer; then thin red accents on cheeks and lips, verdaccio shadows, several flesh tones, the green left partly open at the edges. | Keep a faint green under-layer that shows in the half-tones and hollows (`concave` cool tint, `mute`), and put reds on top as accents. |
| Titian, Rubens (16th–17th c.) | Warm-cool optical mixing; Rubens's pearly cool half-tones between warm lights and warm reflected shadows; flesh built in thin layers and glazes over a toned ground. | Warm light, **cool half-tone at the turn of form**, warm (saturated) core shadows. Chromophore noises out of step so warm and cool sit side by side, not averaged. |
| Rembrandt, Velázquez (17th c.) | Impasto in the lights and transparent darks; Velázquez's economy: a few exact notes of colour at the right edges. | Texture and roughness live in the lights (pores, bump); darks stay smooth and saturated. Less but exact. |
| Ingres, Bouguereau (19th c. academics) | Bouguereau: glazes mostly in backgrounds and drapery; **flesh opaque**, translucence from careful modelling of value and colour notes; later works scumble thin light paint over a darker undertone, giving cool, soft, translucent half-tones. Ingres: porcelain smoothness, very soft edges. | A light, slightly cool layer over a darker warmer undertone reads as translucency. Skin is mostly soft-edged; hard edges only at the lip parting, nostrils and lids. |
| Sargent, Zorn (late 19th c.) | Sargent's *Madame X*: lead white, rose madder, vermilion, **viridian**, bone black: a green in the flesh. Zorn: ochre, vermilion or cadmium red, ivory black, white. Black with ochre gives the muted greens of shadow skin. | Even the most limited palette has red, yellow and a cool/green note. Never only browns. |
| Lucian Freud (20th c.) | Cremnitz white, heavy and worked; flesh full of greys, greens, violets; every bulge and vein mapped. | Older or rougher skin: more grey-green and violet, more relief, visible veins. |
| Antonio López, Chuck Close, photorealists (1960s on) | Close: the face as a grid of cells, each a small mix of colours that blend at a distance. | The fine **chromatic grain** (separate red, yellow and blue noise at pore scale) that blends into skin colour at a distance. |
| Hyperrealist painters (Alyssa Monks, Jason de Graaf, Roberto Bernardi and others) | Dozens of thin transparent glazes, each dried before the next; skin, sweat and reflections built up optically. | Many low-opacity MULTIPLY layers, never one opaque coat; a specular breakup layer for sweat and oil. |
| Ron Mueck, Sam Jinks, Patricia Piccinini (sculptors) | Pigment-tinted silicone **layered in depth** (gel-coat first), then veins, blemishes, freckles painted, and single hairs punched in. | The order in section 2: colour in depth first, surface marks after, hair last. |

## 1d. The face and body, part by part

**Lips (study).** The lips are a different tissue from the skin round them:
- *Colour.* The vermilion is thin, unkeratinised-looking skin over dense capillaries: the blood
  shows, never a separate pink. Redder at the centre of each lip, fading at the corners; the upper
  lip usually darker (it faces down), the lower lighter and fuller. The border is a soft
  transition, sharp only in places (cupid's bow peaks, centre of the lower lip): no dark outline.
  The darkest line is the parting.
- *Surface.* No pores, no hair, none of the skin's crossing lines. Fine **vertical furrows**
  (sulci labiorum, the "lip prints" of forensic cheiloscopy: complete or partial verticals,
  branched, crossing, reticular) run perpendicular to the parting, closer and deeper near it and
  fading towards the border, ~1 mm apart with finer ones between. Smooth, wet, slightly swollen
  ridges between the furrows. Small drier patches, paler and flaky, mostly on the lower lip.
- *Light.* Glossier than skin (roughness ~0.28 wet, ~0.45 dry); highlights on the centre of the
  lower lip, the bow peaks, a thin strip along the upper border: soft, with only a few tiny sharp
  glints. Strong subsurface (translucent, red).
- *Build.* `lips_shape` (mask, cupid's bow, parting) and `lip_surface` (furrows from a voronoi
  edge squashed ×0.07 in height so the cells run vertically, at 820 and 2000 per metre, wandering
  by a 0.3 mm noise offset, deeper near the parting; swell, dry flakes, centre redness). In the lip
  mask the skin's height, colour and roughness are *replaced*, not added to. Parting on the
  geometry's seam (11 mm under the upper-teeth helper), lip colour ×0.88.
- *Failure seen.* Dry flakes and swell bump at full strength sparkled as white specks; keep
  flakes ×0.05, swell ×0.04, roughness ≥0.34.
- *Failure seen.* Lips that carried the skin's crossing fine lines and pores read as "skin painted
  pink" and too textured.

**Eyes (study).** What makes an eye look alive, and how we build it:
- *Anatomy and numbers.* Eyeball ~24 mm across; the cornea is a smaller, steeper sphere
  (radius ~7.8 mm vs ~12 mm) that **stands proud of the eyeball** by about 0.5-1 mm, ~11.5-12 mm
  wide; refractive index ~1.376. The iris lies behind it, so it shows depth and parallax and the
  pupil looks magnified. Iris radius ~5.9 mm; pupil 2-8 mm (calm interior light ~3.5-4.5 mm).
- *Cornea and tear film = life.* A perfectly smooth wet surface over the whole eye: sharp
  catchlights (one big, shaped like the key light), reflections of the room, and the bright
  meniscus (tear line) along the lower lid, thicker at the bottom. Dry, matte eyes look dead.
  Build: the MakeHuman eye already has a cornea shell over the eyeball, mapped to a transparent
  texture corner (u > 0.85, v < 0.15) — it was invisible. `split_eyes` moves it to its own object
  with `cornea_material` (transmission 1, roughness 0, IOR 1.376) and bulges its front cap outward
  (4% of the eye radius at the centre of the iris — 6.5% bent the pupil off-centre, fading to 0 at 30° off axis).
- *Iris.* Radial stroma fibres (noise on seamless polar coordinates, stretched along the radius),
  crypts (dark pits), a lighter collarette ring round the pupil, darker outer rim, and a dark
  **limbal ring** at the edge (strong in the young, fading with age); the pupil pure black and big
  enough (r ≈ 0.35 of the iris). `eye_material` builds all of it from the eye UVs (iris centres
  (0.7052, 0.6955) and (0.2892, 0.2834), radius 0.112) and bakes to a 1024 texture.
- *Sclera.* Never white: ivory, slightly cool/grey next to the limbus, warmer and pinker towards
  the corners; fine red vessels near the surface that thicken and multiply away from the iris
  (thin ones stay sharp, deeper ones blur). Wet: roughness ~0.1.
- *Shadow.* The upper lid and lashes shade the top of the eyeball and iris: never light the eye
  evenly. Baking the eyeball's AO under the lids (with the cornea hidden from the bake) writes
  that shadow into the texture.
- *Inner corner.* The caruncle and plica: wet red-pink, the reddest point of the eye, spreading
  softly onto the side of the nose. `eye_area` paints it on the skin (core `#b84e4a`, wet).
- *Lid margins.* An even, slightly darker lash line along both lids (no patchiness), the soft
  fold of the upper lid above it, and the pink, mirror-smooth tear line on the lower margin.
- *Common failures.* Paper-white sclera, tiny pupil, no limbal ring, no cornea (flat painted
  iris), no catchlight, evenly lit top of the eye, no wet line: each one alone makes the eye read
  as a doll's.

**Nose.** The most sebaceous area: bigger pores, visible **sebaceous filaments** (grey-yellow, light,
not black dots), oilier (lower roughness), redder at the tip and alae; the alar crease and nostril
rims are the darkest small details. Translucent at the tip and the nostril edges in backlight.

Implemented: tiny rare blackheads (voronoi 1900, 7% of cells, dark `#2b2219`, slightly sunken) and
more frequent pale sebaceous filaments (`#cbbd9e`), both masked to the nose and the creases beside it.

**Ears.** Thin cartilage under thin skin: strongly translucent, they glow red against a back light,
redder at the rim and lobe, cooler and darker in the concha; few pores, a little fine hair on the
tragus in older men.

**Hands.** Knuckles red and wrinkled (concentric folds over the joints), back of the hand thin with
blue-green veins and a little hair on the back and the first finger joints; palms yellow-pink, full
of deep creases, no hair, more matte; fingertips red, nails pink over the bed with a white free edge
and a lighter half-moon, cuticles a little dry; dirt sits in the creases and under and around nails.

Implemented: concentric folds over the knuckles (spherical wave rings, darker-redder and sunken).

**Arms and legs.** Outer forearm hairiest; inner arm paler with veins; elbows rough, darker and
creased. Shins: bony, a little shinier, hairier on the front and outside; knees red and creased;
thighs paler and smoother.

**Bare feet.** Soles and heels thick yellow horn, calluses (rougher, paler, sometimes cracked at the
heel), redness at the toes, the ball of the foot and the heel; the top of the foot thin with veins and
tendons; a little hair on the big toe and its joint; for a period or outdoor character, dirt on the
soles, round the nails and in the toe creases.

Implemented: soles found by downward normal near the ground, yellow-pale horn and rougher; calluses
on heel and ball; fine dark cracks at the heel.

**Peach fuzz.** Vellus hair can't be modelled strand by strand at this scale: in renders use
Principled **Sheen** (weight 0.22, roughness 0.45, warm white tint) for the soft velvety rim glow.

**Body hair.** Vellus hair is everywhere and catches back-light as a soft halo (peach fuzz on
cheeks, especially on women). Terminal hair: forearms (outer), back of hands, first finger joints,
shins and thighs, big toe, chest and belly in men, **nape of the neck** under the hairline (fine,
in the hair colour, thinning downwards). Under hair cards always paint a **scalp**: hair-coloured
skin with roots and a broken-up hairline, so lifted cards never show bare skin
(`paint_scalp` + the scalp layer in `skin_material`).

## 1e. Porosity map: smooth and porous zones

Skin texture is not uniform; a single pore pattern at one depth everywhere reads as CG.
- Measured: facial features (pores, follicles) ~200-300 per cm2, i.e. 0.6-0.7 mm apart; pore
  openings 40-80 um; enlarged pores most prominent on the nose and forehead, then the cheeks
  (the malar region has thinner epidermis and more large pores); the chin couples sebum, roughness,
  pores and comedones; counts rise with age. Eyelid skin is the thinnest, with few lipids: almost
  poreless, fine crossing wrinkles. Lips: no pores, vertical lines. Neck: fine crosshatch.
- Texture runs finer on thin skin and softer on stretched or fatty skin; mask delicate edges
  (lid margins, lip border, nostrils).
- `porosity(m, j, lips)` gives 0..1: body 0.4; nose +0.6; inner cheeks +0.45; forehead +0.35;
  chin +0.3; eyelids/under-eye −0.45; temples −0.15; neck −0.12; lips 0; with a slow random
  wobble (×0.85–1.15).
- Pores: voronoi 1500 per metre (≈0.67 mm apart), radius 0.04–0.11 cell scaled by porosity, depth
  ×porosity. Micro grain (3200) ×porosity. Skin lines (1100) deeper where porous; very fine
  crossing lines (2600) where smooth. Flesh relief ×(0.12 + 0.15·porosity).
- Before this map the big pores sat 0.45 mm apart (about twice the real density) at one depth
  everywhere: the face read as uniformly rough and the grain slightly too big.

## 2. Layer order in the shader

Order matters; later layers sit on top. In `skin_material`:

1. **Relief / height** driven by the porosity map (section 1e): pores, micro grain, skin lines,
   fine lines on smooth skin, soft flesh relief.
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
- **Body hair** (`body_hair` + `nape_hair`, attribute `hairzone`, strength `spec['body_hair']`,
  men ~0.85, women 0.2–0.35; the nape at least 0.45 for everyone): outer forearm densest, upper arm
  lighter, back of the hand and first finger joints (back side only, from the vertex normal), front
  and outside of shins and thighs, the big toe, the nape under the hairline. Patches (noise 18)
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
- Measure the colour like a painter: `python3 tools/cinema/skin_check.py shots/<id>-portrait.jpg
  /tmp/<id>-skin.png` posterizes the face skin into 10 colours and prints its hue families, the
  warmth of light vs shadow skin and the hue spread. The flat, plastic baseline measured 95% one hue
  family with a 3.6° spread; the layered version 4.0° with visibly more warm/cool zones in the
  posterized panel. Hue spread alone under-reads multiply tints (they shift value and saturation
  more than hue): judge the posterized panel (several distinct zones: golden forehead, red cheeks
  and ears, cooler jaw) and the light-vs-shadow saturation, compare before/after, and always look.
- Lip colour ×0.72 read as no lips at all after moving them onto the parting; ×0.88 is the floor.
  Stubble with hair dots at 3600/6000 cells per metre is sub-pixel at portrait distance and vanishes:
  use 1800/3400 and a shadow of ×0.4.
- Look at `/tmp/chars/shots/<id>-portrait.jpg` and `-full.jpg` yourself before sending them:
  lips outline crisp; forehead warmer and lower face cooler than the cheeks; veins only faintly
  visible at temples and wrists; no single flat hue across the cheek; moles and blemishes
  present but rare; stubble soft; no plastic sheen.
- Compare the three skin tones side by side (contact sheet); the chromophores should read on all
  of them, much less on the darkest.

## 9. Sources studied

- Sabrillu, *How to draw skin tones with coloured pencils* (posterize to find hidden colours; cool
  blue/green in shadows, warm rosy lights; work light to dark in thin layers; dark accents last).
- Ioanna Ladopoulou, *Drawing skin tones with colored pencils* (three values; add reds to warm,
  greens and blues to mute and give dimension; black kills colour; green to correct too-pink).
- Eternal3D, *How artists paint realistic skin* (reds, blues, yellows, greens from blood flow;
  undertones; cool shadows; soft edges; restraint with details; light changes the read).
- Gurney's face colour zones via Sefki Ibrahim's digital-face write-up (texturing.xyz); 80.lv
  real-time skin texturing; The Rookies digital-double (red scatters furthest: 1.0/0.35/0.2).
- Cennini's verdaccio and terre verte flesh; Mark Walker, *Bouguereau at Work* (Art Renewal
  Center); Sargent's *Madame X* palette; the Zorn palette.
- Eye rendering notes (Unreal photorealistic character docs: limbus, wet sclera, iris depth;
  procedural meniscus thicker at the lower lid; surface vs deep sclera veins).
- Lips: vermilion border is a transition; darkest line at the parting; highlight zones
  (painters-online *How to paint mouths*, drawing guides). Nose: sebaceous filaments are light
  grey-yellow, nose pores larger. Ears and nose: high translucency, red glow in back light.
- mavenart.com's guide could not be read (the site blocks automated readers).
