"""Check a portrait render the way a painter does: posterize the skin to see its hidden colours,
and measure how much of it leans red, yellow, green, blue or violet. Flat CG skin shows one hue
family; real skin shows several, with warm lights and cooler shadows.

    python3 tools/cinema/skin_check.py shots/tomas-portrait.jpg out/tomas-skin.png

Writes a sheet (render | posterized skin | hue swatches) and prints the hue shares and the warm/cool
balance of light vs shadow skin.
"""
import colorsys
import sys

import numpy as np
from PIL import Image, ImageDraw

FAMILIES = (('red', 345, 15), ('orange', 15, 35), ('yellow', 35, 65), ('green', 65, 170),
            ('blue', 170, 260), ('violet', 260, 345))


def family(h):
    for name, lo, hi in FAMILIES:
        if (lo <= h < hi) if lo < hi else (h >= lo or h < hi):
            return name
    return 'red'


def skin_pixels(img):
    """Pixels that look like skin in the face area: not background grey, not hair-dark, not white."""
    a = np.asarray(img.convert('RGB')).astype(np.float32) / 255
    h, w, _ = a.shape
    box = a[int(h * 0.3):int(h * 0.75), int(w * 0.3):int(w * 0.7)]
    flat = box.reshape(-1, 3)
    mx, mn = flat.max(1), flat.min(1)
    sat = (mx - mn) / np.maximum(mx, 1e-4)
    keep = (mx > 0.18) & (mx < 0.97) & (sat > 0.08) & (flat[:, 0] >= flat[:, 2])
    return box, flat[keep]


def report(path, out=None):
    img = Image.open(path)
    box, px = skin_pixels(img)
    hsv = np.array([colorsys.rgb_to_hsv(*p) for p in px[::7]])
    counts = {name: 0 for name, _, _ in FAMILIES}
    for h_, s_, v_ in hsv:
        counts[family(h_ * 360)] += 1
    total = max(1, len(hsv))
    print(path)
    for name, _, _ in FAMILIES:
        print('  %-7s %5.1f%%' % (name, 100 * counts[name] / total))
    v = hsv[:, 2]
    light, dark = hsv[v > np.quantile(v, 0.7)], hsv[v < np.quantile(v, 0.3)]
    warm = lambda part: np.mean(np.cos(np.radians(part[:, 0] * 360 - 20)))
    print('  warmth of lights %.2f, of shadows %.2f (lights should be warmer)' % (
        warm(light), warm(dark)))
    print('  hue spread (std, degrees) %.1f' % np.degrees(np.std(np.unwrap(np.radians(hsv[:, 0] * 360)))))
    if out:
        crop = Image.fromarray((box * 255).astype(np.uint8))
        poster = crop.quantize(10, method=Image.Quantize.MEDIANCUT)
        colours = poster.getpalette()[:30]
        sheet = Image.new('RGB', (crop.width * 2 + 120, crop.height), 'white')
        sheet.paste(crop, (0, 0))
        sheet.paste(poster.convert('RGB'), (crop.width, 0))
        d = ImageDraw.Draw(sheet)
        step = crop.height // 10
        for i in range(10):
            d.rectangle([crop.width * 2 + 10, i * step + 4, crop.width * 2 + 110, (i + 1) * step - 4],
                        fill=tuple(colours[i * 3:i * 3 + 3]))
        sheet.save(out)


if __name__ == '__main__':
    report(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
