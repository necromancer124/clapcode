# Motion patterns and pacing

All recipes use the helpers defined in `../assets/template.html`. Every value is computed from `t` (seconds), so any frame can be rendered on its own.

## Pacing
| Thing | Rule of thumb |
| --- | --- |
| Caption on screen | about 0.3 s per word + 1 s, never under 1.5 s |
| Entrance or exit | 0.3–0.6 s |
| Scene crossfade | 0.2–0.4 s |
| Hold after a key number appears | at least 1 s before it changes or leaves |
| Whole scene | 2–10 s; a 5 s video fits 2–3 scenes |
| Things moving at once | one main motion; supporting motion smaller and slower |

Start fast and end with a hold: the last 0.5–1 s should be still, so the final frame works as a thumbnail.

## Easing
- `ease.outCubic`: things arriving (entrances, a bar reaching its value).
- `ease.inCubic`: things leaving.
- `ease.inOutCubic`: things moving from one place to another.
- `ease.outBack`: a small overshoot for playful pops; avoid in technical videos.
- `ease.linear`: only for constant motion such as a rotating dial or a scrolling ticker.

## Recipes
Progress of an animation between two times, eased:
```js
const p = prog(t, 1.0, 1.6, ease.outCubic);   // 0 before 1.0 s, 1 after 1.6 s
```

Fade and slide in:
```js
el.style.opacity = p;
el.style.transform = `translateY(${lerp(40, 0, p)}px)`;
```

Draw an SVG line or outline on:
```js
drawOn(pathEl, prog(t, 0.2, 1.2, ease.inOutCubic));
```

Count a number up, holding the final value:
```js
countUp(numEl, prog(t, 2.0, 3.4, ease.outCubic), 0, 99.98, 2, '%');
```

Type text on, character by character:
```js
typeOn(labelEl, prog(t, 1.0, 2.0, ease.linear), 'Ready in 3 steps');
```

Stagger a list (each item 0.12 s after the previous):
```js
items.forEach((el, i) => {
  const p = prog(t, 1.0 + i * 0.12, 1.5 + i * 0.12, ease.outCubic);
  el.style.opacity = p;
  el.style.transform = `translateX(${lerp(-30, 0, p)}px)`;
});
```

Grow a bar to a value:
```js
bar.style.transform = `scaleY(${prog(t, 2.2, 3.0, ease.outCubic) * value / max})`;
// with CSS: transform-origin: bottom;
```

Move along a path:
```js
const L = path.getTotalLength();
const pt = path.getPointAtLength(L * prog(t, 1, 3, ease.inOutCubic));
dot.setAttribute('cx', pt.x); dot.setAttribute('cy', pt.y);
```

Exploded view (parts separate, labels appear one at a time):
```js
parts.forEach((el, i) => {
  const p = prog(t, 1 + i * 0.25, 1.6 + i * 0.25, ease.outCubic);
  el.style.transform = `translateY(${-i * 60 * p}px)`;
  labels[i].style.opacity = prog(t, 1.4 + i * 0.25, 1.7 + i * 0.25);
});
```

Camera pan or zoom: wrap the scene in one element and transform it:
```js
world.style.transform = `translate(${lerp(0, -400, p)}px, 0) scale(${lerp(1, 1.3, p)})`;
```

Deterministic jitter or particles:
```js
const r = rng(42);                       // create once, outside renderAt
const stars = Array.from({ length: 80 }, () => ({ x: r() * 1920, y: r() * 1080 }));
```

A pulse that repeats every second, computed from `t`:
```js
const pulse = 1 + 0.06 * Math.sin(t * Math.PI * 2);
```

## Things to avoid
- Starting a CSS transition on a class change: transitions depend on wall-clock time. Use `prog` instead.
- Video or GIF elements inside the page: their playback is not tied to `t`.
- More than two typefaces, or text over busy backgrounds.
- Motion that never settles: viewers need still moments to read.
