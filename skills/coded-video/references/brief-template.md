# Video brief template

Copy this into `brief.md` in the working directory and fill it in. The brief is the source of truth for the build: scene order, timing, on-screen text, and every number must match it. Keep it short enough to read in two minutes.

```markdown
# Brief: <working title>

**Status:** draft, waiting for go   <!-- change to "approved" only after the user explicitly says go -->

## Goal
<One sentence: what the viewer should understand or feel by the end.>

## Audience and use
<Who watches, where (deck, website, social, README), with or without sound.>

## Format
- Length: <N> s
- Size: <1920×1080 | 1080×1920 | 1080×1080>, <30> fps
- Sound: <none | soundtrack file supplied by the user | captions are the script>

## Style
- Tone: <engineering, playful, calm, ...>. Every claim on screen is <a measurement | a mechanism | a quoted fact>.
- Colors: <background>, <main>, <accent>, <neutral>, with what each one means.
- Type: <font family, bundled file if exact look matters>, captions <= <8> words.
- Look: <flat 2D | isometric 2.5D | real 3D (Three.js)>, and why it fits the subject.
- Drawing style: <e.g. flat shapes, line art, soft-lit 3D with rounded edges>; no photos unless supplied.

## Scenes
1. **(0–<a> s) <Scene name>.**
   - Shows: <what is on screen>.
   - Motion: <what moves and how>.
   - Text: "<exact caption>".
2. **(<a>–<b> s) <Scene name>.**
   - Shows: ...
   - Motion: ...
   - Text: "..."
<!-- Scene ranges must be contiguous and end at the stated length. -->

## Accuracy rules
- <Facts that must match a source, with the source named.>
- <Things that must never appear, such as a part on the wrong side or an invented number.>

## Deliverables
- `output/<name>.mp4`
- The HTML source and this brief.
```

## Writing good scenes
- One idea per scene. If a scene needs two captions, it is probably two scenes.
- Name concrete things: "a bar grows from 0 to 72% over 1.2 s", not "the chart animates".
- Put the exact on-screen text in the brief, in quotes. The build copies it, it does not reword it.
- Give each caption enough time to read: see `motion-patterns.md`.
- Mark anything uncertain as an open question in the brief instead of guessing.

## Short example

```markdown
# Brief: Uptime in 5 seconds

**Status:** draft, waiting for go

## Goal
Show that the service stayed up 99.98% of last month.

## Format
- Length: 5 s
- Size: 1920×1080, 30 fps
- Sound: none

## Style
- Tone: calm, factual.
- Colors: deep blue background, white text, one green accent for "up".
- Type: system sans-serif; captions <= 6 words.

## Scenes
1. **(0–2 s) Title.** A thin line draws left to right under "Last month". Text: "Last month".
2. **(2–4.2 s) The number.** A counter climbs from 0.00% to 99.98%; a green ring fills to match. Text: "99.98% uptime".
3. **(4.2–5 s) Hold.** Everything holds; the ring pulses once.

## Accuracy rules
- 99.98% comes from the user's monitoring export; do not round it.
```
