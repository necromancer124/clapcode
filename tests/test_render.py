"""Real render checks. Skipped (with a reason) when Playwright, a browser, or ffmpeg is missing."""
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RENDER = ROOT / 'skills/clapcode/scripts/render.py'
TEMPLATE = ROOT / 'skills/clapcode/assets/template.html'
TEMPLATE_3D = ROOT / 'skills/clapcode/assets/template-3d.html'
BROWSER = os.environ.get('RENDER_BROWSER', 'chromium')

try:
    import playwright  # noqa: F401
    HAVE_PLAYWRIGHT = True
except ImportError:
    HAVE_PLAYWRIGHT = False


def psnr(a, b):
    out = subprocess.run(['ffmpeg', '-v', 'info', '-i', str(a), '-i', str(b), '-lavfi', 'psnr', '-f', 'null', '-'],
                         capture_output=True, text=True)
    match = re.search(r'average:(inf|[0-9.]+)', out.stderr)
    if not match:
        raise AssertionError('Could not compare frames: ' + out.stderr[-400:])
    return float('inf') if match.group(1) == 'inf' else float(match.group(1))


def run(*args):
    return subprocess.run([sys.executable, str(RENDER), *map(str, args), '--browser', BROWSER],
                          capture_output=True, text=True, timeout=600)


class CliTests(unittest.TestCase):
    def test_needs_output_or_stills(self):
        result = run(TEMPLATE)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--output', result.stderr)

    def test_rejects_non_mp4_output(self):
        result = run(TEMPLATE, '--output', 'out.gif')
        self.assertNotEqual(result.returncode, 0)


@unittest.skipUnless(HAVE_PLAYWRIGHT, 'Playwright is not installed')
class RenderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg/ffprobe not on PATH')
    def test_renders_exact_frames_size_and_duration(self):
        mp4 = self.tmp / 'clip.mp4'
        result = run(TEMPLATE, '--output', mp4, '--scale', '0.25', '--fps', '10', '--end', '2')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['frames_written'], 20)
        self.assertEqual(report['measured']['frames'], 20)
        self.assertEqual((report['measured']['width'], report['measured']['height']), (480, 270))
        self.assertAlmostEqual(report['measured']['duration'], 2.0, delta=0.11)

    def test_same_time_gives_identical_frame(self):
        a, b = self.tmp / 'a', self.tmp / 'b'
        for d in (a, b):
            result = run(TEMPLATE, '--stills', '0.8,3.3', '--stills-dir', d, '--scale', '0.25')
            self.assertEqual(result.returncode, 0, result.stderr)
        for name in ('still_000.800s.png', 'still_003.300s.png'):
            self.assertEqual((a / name).read_bytes(), (b / name).read_bytes(), name)

    @unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg not on PATH')
    def test_3d_template_renders_consistently_in_software_webgl(self):
        a, b = self.tmp / 'a3', self.tmp / 'b3'
        for d in (a, b):
            result = run(TEMPLATE_3D, '--stills', '3.5', '--stills-dir', d, '--scale', '0.25', '--gl', 'swiftshader')
            self.assertEqual(result.returncode, 0, result.stderr)
        name = 'still_003.500s.png'
        self.assertGreater((a / name).stat().st_size, 20000, '3D frame looks empty')
        # Software WebGL can differ by a few low bits between runs on some systems, so compare
        # pixels (PSNR) instead of bytes. 40 dB and above is visually identical.
        self.assertGreaterEqual(psnr(a / name, b / name), 40)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg/ffprobe not on PATH')
    def test_contact_sheet_is_written(self):
        mp4, sheet = self.tmp / 'c.mp4', self.tmp / 'sheet.png'
        result = run(TEMPLATE, '--output', mp4, '--scale', '0.25', '--fps', '10', '--end', '3', '--sheet', sheet)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['sheet']['frames'], 3)
        self.assertTrue(sheet.is_file() and sheet.stat().st_size > 1000)

    def test_missing_contract_fails_with_message(self):
        page = self.tmp / 'bad.html'
        page.write_text('<!doctype html><title>x</title><p>no contract</p>', encoding='utf-8')
        result = run(page, '--stills', '0')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('window.VIDEO is missing', result.stderr)

    def test_javascript_error_during_frame_fails(self):
        page = self.tmp / 'throws.html'
        page.write_text('<!doctype html><title>x</title><script>window.VIDEO={width:64,height:64,fps:10,duration:1};'
                        'window.renderAt=function(t){ if (t > 0.5) throw new Error("boom"); };</script>', encoding='utf-8')
        result = run(page, '--stills', '0.9')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('boom', result.stderr)

    def test_remote_assets_are_blocked(self):
        page = self.tmp / 'remote.html'
        page.write_text('<!doctype html><title>x</title><img src="https://example.com/a.png">'
                        '<script>window.VIDEO={width:64,height:64,fps:10,duration:1};window.renderAt=function(){};</script>',
                        encoding='utf-8')
        result = run(page, '--stills', '0')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Remote requests blocked', result.stderr)


if __name__ == '__main__':
    unittest.main()
