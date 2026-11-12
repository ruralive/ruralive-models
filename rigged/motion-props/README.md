# Motion props

Twelve original, stylized props. Each GLB contains textured geometry and a named animation. The cycles run from four to twelve seconds at their authored playback speed.

| Prop | Action |
| --- | --- |
| Stone windmill | Four framed sails rotate around the mill axle |
| Coastal lighthouse | The lantern sweeps a full circle |
| Canal drawbridge | Both decks raise, hold and lower together |
| Tracked excavator | Boom, stick, bucket and upper carriage perform a dig-and-dump cycle |
| Steam locomotive | Wheels and crank pins turn together and carry the coupling rods |
| Assembly robot | The shoulder, elbow, turntable and fingers perform a reach-and-grip cycle |
| Wooden rowboat | Oars sweep and lift while the hull rolls gently |
| Observatory telescope | The azimuth and elevation hinges scan together |
| Brass gramophone | The record spins and the tonearm follows a short sweep |
| Pendulum clock | The pendulum swings and both hands turn at stylized speeds |
| Umbrella | Ribs unfold, hold and fold around the shaft |
| Fairground carousel | The platform turns while its horses rise and fall at staggered phases |

[File manifest](manifest.json) · [Licence](../../LICENSE)

Rebuild with Python, NumPy and Pillow from the repository root.

```sh
python tools/build_motion_props.py
blender -b -P tools/verify_expansion.py -- rigged/motion-props
```
