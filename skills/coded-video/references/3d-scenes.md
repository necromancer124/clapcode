# 3D scenes with Three.js

Use real 3D when the brief asks for depth, a product, a device, a mechanism, an exploded view, or a "premium" look. The starter is `../assets/template-3d.html`, with three.js 0.187.0 bundled in `../assets/vendor/three/` (MIT, see its `LICENSE` and `VERSION.txt`).

## Set up
1. Copy `assets/template-3d.html` **and** the whole `assets/vendor/` folder into the project folder, so the page sits next to `vendor/`. The import map in the template points at `./vendor/three/`.
2. Preview with a local server from the project folder, because ES modules do not load from `file://`:
   ```sh
   python -m http.server 8000
   ```
   Then open `http://127.0.0.1:8000/index.html` (add `?t=3.2` to freeze a moment). `render.py` serves the folder itself, so rendering needs no server.
3. Only files inside the project folder are served. Keep models, textures and fonts there.

## The rules that keep 3D deterministic
- `renderAt(t)` sets every transform, camera value, material value and light from `t`, then calls `renderer.render(scene, camera)` once at the end. Never use `THREE.Clock`, `requestAnimationFrame` loops or `renderer.setAnimationLoop` for the video.
- Build the scene once at load time. `renderAt` only changes values; it never adds or removes objects each frame.
- Create the renderer with `preserveDrawingBuffer: true` so each captured frame is the one just drawn.
- Animation clips from a loaded model: create an `AnimationMixer` once, then in `renderAt` call `mixer.setTime(t)`. Never call `mixer.update(delta)`.
- Particles, dust and jitter: precompute positions with the seeded `rng` at load time, then move them as a function of `t`.
- `--gl swiftshader` gives identical pixels on every machine; the default `--gl gpu` is about 3–4× faster on machines with a GPU.

## Looks that read as "presentable"
**Lighting** (the biggest single upgrade over flat 2D):
- `scene.environment` from `RoomEnvironment` for soft reflections, with `scene.environmentIntensity` around 0.4–0.7.
- One directional key light that casts shadows, high and to one side. Optionally a weak rim light behind the subject to separate it from a dark background.
- `THREE.NeutralToneMapping` keeps brand colours close to their hex values; ACES makes oranges and reds look washed out.
- A `ShadowMaterial` ground keeps the background gradient visible while still grounding the object. `VSMShadowMap` with `shadow.radius` 8–16 gives soft contact shadows.

**Materials:**
- `MeshStandardMaterial` with roughness 0.3–0.6 for most surfaces; metalness 0 unless it is actually metal.
- Labels and printed surfaces: draw them on a 2D canvas (`CanvasTexture`, `colorSpace = SRGBColorSpace`) so text and numbers stay exact and editable.
- Glass or liquid: `MeshPhysicalMaterial` with `transmission`, or a simple translucent `MeshStandardMaterial` with `transparent: true` and `opacity` 0.5–0.8. Never cover a label with an opaque liquid colour.

**Geometry without a modelling tool:**
- `RoundedBoxGeometry` (bundled addon) for boxes, devices, cards and packaging. Sharp boxes look cheap.
- `LatheGeometry` for anything round: cups, bowls, bottles, lids, cans. Define the profile as points and spin it.
- `CylinderGeometry`, `TorusGeometry`, `CapsuleGeometry`, `TubeGeometry` along a `CatmullRomCurve3` for cables, steam and pipes.
- Group parts in `THREE.Group`s so a lid, a sachet or a panel can move on its own.

**Camera:**
- A slow orbit or push-in during each scene; cut or ease between framings at scene changes. Never leave the camera dead still for a whole video.
- 25–35° field of view for product shots; orthographic camera for clean isometric diagrams.
- Frame the subject so text has its own space: aim `camera.lookAt` off-centre rather than squeezing text over the object.

**Text:** keep titles, captions and numbers in the HTML overlay on top of the canvas: crisp at any scale, exact fonts, easy to edit. Pin callouts to 3D points by projecting them (`toScreen` in the template), and clamp labels inside the safe margin.

## Recipes
Lid peeling back on a hinge (lid in its own group, pivot at the hinge edge):
```js
lidPivot.rotation.x = lerp(0, -1.9, prog(t, 2.0, 3.0, ease.inOutCubic));
```

Water level rising inside a cup (a cylinder scaled from the bottom):
```js
const fill = prog(t, 4.0, 6.0, ease.inOutCubic);
water.scale.y = Math.max(0.001, fill);
water.position.y = cupBottom + (fill * waterHeight) / 2;
```

Steam: three `TubeGeometry` ribbons, opacity and vertical offset from `t`:
```js
steam.forEach((s, i) => {
  s.material.opacity = 0.35 * prog(t, 5 + i * 0.2, 5.6 + i * 0.2);
  s.position.y = base + ((t * 0.25 + i / 3) % 1) * 0.4;
});
```

Exploded view: move each part along its own axis with a stagger, then bring them back.

Countdown timer: an HTML overlay number with `countUp` from 180 to 0, plus a `RingGeometry` whose `thetaLength` shrinks with the same progress.

## Performance
- About 0.3 s per full-HD frame on a GPU, about 1 s with software rendering, for a scene like the template. A 15 s video is 450 frames: a few minutes on a GPU, 5–10 minutes in software.
- Draft with `--scale 0.5` and a section at a time (`--start`/`--end`), then render the final at full size.
- Shadow maps of 1024–2048 are enough. Keep one shadow-casting light.
