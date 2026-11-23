"""Render a coded video to MP4 or still PNGs.

The page must define window.VIDEO = {width, height, fps, duration} and a pure
window.renderAt(t). Each frame is drawn at an exact time, captured by Playwright,
and piped to ffmpeg. Nothing is installed implicitly. Render trusted HTML only.
"""
import argparse
import functools
import http.server
import json
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
from pathlib import Path

SEEK = """async (t) => {
  const anims = document.getAnimations ? document.getAnimations() : [];
  for (const a of anims) { a.pause(); a.currentTime = t * 1000; }
  await window.renderAt(t);
}"""

CHECK = """() => {
  const v = window.VIDEO;
  if (!v || typeof v !== 'object') return 'window.VIDEO is missing';
  if (typeof window.renderAt !== 'function') return 'window.renderAt(t) is missing';
  const ok = (x, lo, hi) => typeof x === 'number' && isFinite(x) && x >= lo && x <= hi;
  if (!ok(v.width, 16, 7680) || !ok(v.height, 16, 7680)) return 'VIDEO.width and VIDEO.height must be 16-7680';
  if (!ok(v.fps, 1, 120)) return 'VIDEO.fps must be 1-120';
  if (!ok(v.duration, 0.04, 3600)) return 'VIDEO.duration must be 0.04-3600 seconds';
  return null;
}"""


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('input', help='Path to trusted local HTML')
    p.add_argument('--output', help='Destination .mp4')
    p.add_argument('--stills', help='Comma-separated times in seconds to save as PNGs, e.g. 0.5,2,4.5')
    p.add_argument('--stills-dir', default='output/stills', help='Folder for --stills (default: output/stills)')
    p.add_argument('--start', type=float, default=0.0, help='First second to render (default 0)')
    p.add_argument('--end', type=float, help='Last second to render (default: VIDEO.duration)')
    p.add_argument('--fps', type=float, help='Override VIDEO.fps')
    p.add_argument('--scale', type=float, default=1.0, help='Output scale, e.g. 0.5 for a half-size draft')
    p.add_argument('--crf', type=int, default=18, help='H.264 quality, 0-51, lower is better (default 18)')
    p.add_argument('--audio', help='Optional soundtrack; the video length wins')
    p.add_argument('--sheet', help='Also write a contact sheet PNG of the MP4: one frame per --sheet-every seconds')
    p.add_argument('--sheet-every', type=float, default=1.0, help='Seconds between contact-sheet frames (default 1)')
    p.add_argument('--browser', choices=('chromium', 'chrome', 'msedge'), default='chromium')
    p.add_argument('--ffmpeg', help='Path to ffmpeg (default: ffmpeg on PATH)')
    p.add_argument('--allow-network', action='store_true', help='Allow remote HTTP(S) requests')
    p.add_argument('--gl', choices=('gpu', 'swiftshader'), default='gpu',
                   help='WebGL for 3D pages: gpu (default, fast, falls back to software when there is no GPU) '
                        'or swiftshader (software only: slower, but looks the same on any machine)')
    args = p.parse_args(argv)

    source = Path(args.input).expanduser().resolve()
    if not source.is_file():
        p.error('Input HTML does not exist: ' + str(source))
    if source.suffix.lower() not in ('.html', '.htm'):
        p.error('Input must be an HTML file')
    if not args.output and not args.stills:
        p.error('Give --output video.mp4, --stills times, or both')
    if args.output and Path(args.output).suffix.lower() != '.mp4':
        p.error('--output must end in .mp4')
    if not 0 < args.scale <= 4:
        p.error('--scale must be greater than 0 and at most 4')
    if not 0 <= args.crf <= 51:
        p.error('--crf must be 0-51')
    if args.fps is not None and not 1 <= args.fps <= 120:
        p.error('--fps must be 1-120')
    if args.start < 0 or (args.end is not None and args.end <= args.start):
        p.error('--start must be >= 0 and --end must be greater than --start')
    if args.sheet and not args.output:
        p.error('--sheet needs --output (the sheet is made from the finished MP4)')
    if args.sheet and Path(args.sheet).suffix.lower() != '.png':
        p.error('--sheet must end in .png')
    if not 0.1 <= args.sheet_every <= 60:
        p.error('--sheet-every must be 0.1-60 seconds')
    if args.audio and not Path(args.audio).is_file():
        p.error('Audio file does not exist: ' + args.audio)
    if args.stills:
        try:
            args.still_times = [float(x) for x in args.stills.split(',') if x.strip()]
        except ValueError:
            p.error('--stills must be comma-separated numbers')
        if not args.still_times or any(x < 0 for x in args.still_times):
            p.error('--stills needs one or more times >= 0')
    else:
        args.still_times = []
    args.source = source
    return args


def find_ffmpeg(explicit):
    exe = explicit or shutil.which('ffmpeg')
    if not exe or not Path(exe).exists() and not shutil.which(exe):
        raise RuntimeError('ffmpeg not found. Install it from https://ffmpeg.org/download.html '
                           'or pass --ffmpeg PATH.')
    return exe


def probe(mp4):
    ffprobe = shutil.which('ffprobe')
    if not ffprobe:
        return None
    cmd = [ffprobe, '-v', 'error', '-select_streams', 'v:0', '-count_frames',
           '-show_entries', 'stream=width,height,nb_read_frames,avg_frame_rate:format=duration',
           '-of', 'json', str(mp4)]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        return None
    data = json.loads(out.stdout)
    s = data['streams'][0]
    num, den = (s.get('avg_frame_rate') or '0/1').split('/')
    return {'width': s['width'], 'height': s['height'], 'frames': int(s['nb_read_frames']),
            'fps': round(float(num) / float(den), 3) if float(den) else None,
            'duration': round(float(data['format']['duration']), 3)}


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Serves the project folder only. Fixed MIME types so ES modules load on every OS."""
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json',
                      '.wasm': 'application/wasm', '.svg': 'image/svg+xml', '.woff2': 'font/woff2',
                      '.glb': 'model/gltf-binary', '.gltf': 'model/gltf+json'}

    def log_message(self, *args):
        pass


def serve_folder(folder):
    """Serve `folder` on a random 127.0.0.1 port, so ES modules and fetch() work like on a website."""
    handler = functools.partial(_QuietHandler, directory=str(folder))
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, 'http://127.0.0.1:%d' % httpd.server_address[1]


def contact_sheet(ffmpeg, mp4, png, every, seconds):
    """One frame every `every` seconds, 480 px wide, in a grid of up to 5 columns."""
    count = max(1, int(seconds / every + 0.999))
    cols = min(5, count)
    rows = (count + cols - 1) // cols
    vf = 'fps=1/%s,scale=480:-2,tile=%dx%d:padding=8:color=white' % (every, cols, rows)
    out = subprocess.run([ffmpeg, '-y', '-loglevel', 'error', '-i', str(mp4), '-vf', vf, '-frames:v', '1', str(png)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError('Contact sheet failed: ' + out.stderr.strip())
    return {'png': str(png), 'frames': count, 'every_seconds': every}


def render(args):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError('Playwright for Python is not installed. Follow '
                           'https://playwright.dev/python/docs/intro') from None
    ffmpeg = find_ffmpeg(args.ffmpeg) if args.output else None
    errors, blocked, result = [], [], {}
    started = time.time()

    httpd, origin = serve_folder(args.source.parent)
    url = origin + '/' + urllib.parse.quote(args.source.name)

    with sync_playwright() as pw:
        launch = {'headless': True}
        if args.gl == 'swiftshader':
            launch['args'] = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
        else:
            launch['args'] = ['--ignore-gpu-blocklist', '--enable-gpu', '--enable-unsafe-swiftshader']
        if args.browser != 'chromium':
            launch['channel'] = args.browser
        try:
            browser = pw.chromium.launch(**launch)
        except Exception as exc:
            raise RuntimeError('Cannot launch browser. Install the Playwright Chromium browser '
                               '(https://playwright.dev/python/docs/browsers), or use '
                               '--browser chrome or --browser msedge. ' + str(exc)) from None
        try:
            context = browser.new_context(viewport={'width': 1920, 'height': 1080}, device_scale_factor=args.scale)
            context.add_init_script('window.__RENDERING__ = true;')
            def gate(route):
                if args.allow_network or route.request.url.startswith(origin + '/'):
                    route.continue_()
                else:
                    blocked.append(route.request.url)
                    route.abort()
            context.route('**/*', gate)
            page = context.new_page()
            page.on('pageerror', lambda exc: errors.append(str(exc)))
            page.goto(url, wait_until='load', timeout=60000)
            try:  # 3D pages may finish setting up after "load" (modules, async assets)
                page.wait_for_function('() => typeof window.renderAt === "function" && !!window.VIDEO', timeout=15000)
            except Exception:
                pass  # CHECK below reports exactly what is missing
            if errors:
                raise RuntimeError('Page JavaScript errors: ' + '; '.join(errors))
            page.evaluate('() => document.fonts.ready')
            page.evaluate('() => Promise.all([...document.images].map(i => i.decode().catch(() => null)))')
            problem = page.evaluate(CHECK)
            if problem:
                raise RuntimeError(problem)
            video = page.evaluate('() => window.VIDEO')
            page.set_viewport_size({'width': int(video['width']), 'height': int(video['height'])})
            if blocked:
                raise RuntimeError('Remote requests blocked (' + blocked[0] + '). Bundle assets locally or '
                                   'pass --allow-network with permission.')
            broken = page.evaluate('() => [...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.getAttribute("src"))')
            if broken:
                raise RuntimeError('Broken images: ' + ', '.join(map(str, broken)))
            if errors:
                raise RuntimeError('Page JavaScript errors: ' + '; '.join(errors))

            fps = args.fps or float(video['fps'])
            duration = float(video['duration'])
            end = min(args.end if args.end is not None else duration, duration)
            if args.start >= end:
                raise RuntimeError('--start is past the end of the video (%.3f s)' % duration)

            def seek(t):
                page.evaluate(SEEK, t)
                if errors:
                    raise RuntimeError('Page JavaScript error at t=%.3f s: %s' % (t, errors[0]))

            if args.still_times:
                out_dir = Path(args.stills_dir).expanduser().resolve()
                out_dir.mkdir(parents=True, exist_ok=True)
                stills = []
                for t in args.still_times:
                    t = min(t, duration)
                    seek(t)
                    path = out_dir / ('still_%07.3fs.png' % t)
                    page.screenshot(path=str(path))
                    stills.append(str(path))
                result['stills'] = stills

            if args.output:
                mp4 = Path(args.output).expanduser().resolve()
                mp4.parent.mkdir(parents=True, exist_ok=True)
                first, last = round(args.start * fps), round(end * fps)
                cmd = [ffmpeg, '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(fps), '-i', '-']
                if args.audio:
                    cmd += ['-i', str(Path(args.audio).resolve())]
                cmd += ['-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                        '-crf', str(args.crf), '-preset', 'medium', '-movflags', '+faststart']
                if args.audio:
                    cmd += ['-c:a', 'aac', '-b:a', '192k', '-shortest']
                cmd.append(str(mp4))
                proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    for n in range(first, last):
                        seek(n / fps)
                        proc.stdin.write(page.screenshot(type='png'))
                    proc.stdin.close()
                    stderr = proc.stderr.read().decode(errors='replace')
                    if proc.wait() != 0:
                        raise RuntimeError('ffmpeg failed: ' + stderr.strip())
                except BaseException:
                    proc.kill()
                    proc.wait()
                    raise
                result.update({'mp4': str(mp4), 'frames_written': last - first, 'fps': fps,
                               'start': args.start, 'end': end})
                result['measured'] = probe(mp4)
                if args.sheet:
                    sheet = Path(args.sheet).expanduser().resolve()
                    sheet.parent.mkdir(parents=True, exist_ok=True)
                    result['sheet'] = contact_sheet(ffmpeg, mp4, sheet, args.sheet_every, end - args.start)
        finally:
            browser.close()
            httpd.shutdown()

    result.update({'browser': args.browser, 'design_size': [video['width'], video['height']],
                   'scale': args.scale, 'seconds_elapsed': round(time.time() - started, 1)})
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        render(parse_args())
    except Exception as exc:
        print('Render failed: ' + str(exc), file=sys.stderr)
        sys.exit(1)
