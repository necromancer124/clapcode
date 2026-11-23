# clapcode

**Coded, not generated.** Short explainer and demo videos that Claude writes as code and renders to MP4.

Ask for an explainer, a product demo, an animated diagram, a title card or a short 2D or 3D animation. Claude first writes a scene-by-scene brief: goal, length, look, and every caption with its timing. It waits for your go. Then it builds the video as HTML, CSS, SVG and JavaScript (or real, lit 3D with the bundled three.js), renders it frame by frame into an MP4, and checks stills of every scene against the brief before calling it done.

No image or video model is involved. Every shape, number and word on screen is exactly what's in the source file, so you can read it, fix a typo and render again.

![A 3D product tutorial made with clapcode: a noodle cup is opened, filled from a kettle, closed, timed and stirred](https://raw.githubusercontent.com/necromancer124/clapcode/main/docs/noodle-tutorial-3d.gif)

## Install

```
/plugin install clapcode --marketplace necromancer124/clapcode
```

Then start a new session. Claude uses the skill on its own when you ask for a video, or you can call it with `/clapcode:clapcode`.

## Good for
- Product and feature demos, technical explainers and process walkthroughs
- Animated diagrams, data stories, title cards, logo reveals, intros and outros
- 3D product shots with real lighting, soft shadows and camera moves

Not for realistic people, faces, places or camera-style footage. clapcode makes clean motion graphics: precise, editable and repeatable, but drawn, not filmed.

## What you need for rendering
- Python 3.10 or later
- Playwright for Python with Chromium (or an installed Chrome or Edge): see the official guide at https://playwright.dev/python/docs/intro
- ffmpeg on your PATH: see https://ffmpeg.org/download.html

Writing the brief needs none of these. Nothing is installed automatically.

## What the plugin runs, sends and fetches
- **Runs, only when a video is rendered:** `skills/clapcode/scripts/render.py` with your local Python. It starts a headless Chromium, Chrome or Edge through Playwright, serves the folder of the page being rendered on a private `127.0.0.1` port while it runs, and pipes frames to your local ffmpeg.
- **Sends:** nothing. There are no hooks, no MCP servers, no telemetry and no API keys. Rendered files stay on your machine.
- **Fetches:** nothing by default. The renderer blocks every request that is not for the local page folder unless you pass `--allow-network`.
- **Bundled code:** `skills/clapcode/assets/vendor/three/` holds three.js 0.187.0, copied unmodified from the official npm package (MIT; see its `LICENSE` and `VERSION.txt`), so 3D videos render offline.

## Is it "AI-generated"?
It's made by an AI assistant writing code. It's not synthetic footage: no model invents pixels, and the renderer adds no watermark. If you publish a video, check the disclosure rules of the platform you post on.

More examples, the source and the tests: https://github.com/necromancer124/clapcode

MIT licensed. See `LICENSE`.
