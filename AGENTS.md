# clapcode

This repository holds one Claude Code plugin in `plugins/clapcode/` with one Agent Skill: `plugins/clapcode/skills/clapcode/SKILL.md`. Read it before making a video.

- Phase 1 is a written brief (`brief.md`). Show it and wait for the user's explicit go before building.
- Build the animation as HTML/CSS/SVG/JS driven by `window.renderAt(t)`, starting from `plugins/clapcode/skills/clapcode/assets/template.html`, or `template-3d.html` plus `assets/vendor/` for real 3D (see `references/3d-scenes.md`).
- Render with `python plugins/clapcode/skills/clapcode/scripts/render.py <page.html> --output output/video.mp4`; check stills with `--stills`.
- Use your own agent's file, shell, and browser tools. No model or API key is needed by the skill.

Repository checks: `python -m pip install -r requirements-dev.txt`, `python -m playwright install chromium`, ffmpeg on PATH, then `python -m unittest discover -s tests -v`.

Output goes to `output/` (gitignored). Do not claim tests passed or a video was checked unless that actually happened. Commits and publishing need the user's permission.
