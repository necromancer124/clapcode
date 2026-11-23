"""Package checks: skill metadata, plugin manifests, file references, privacy (no network)."""
from pathlib import Path
import json
import re
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'plugins/clapcode/skills/clapcode/SKILL.md'


class PackageTests(unittest.TestCase):
    def test_skill_frontmatter_uses_open_standard_fields(self):
        skills = list((ROOT / 'plugins/clapcode/skills').glob('*/SKILL.md'))
        self.assertEqual(skills, [SKILL])
        raw = SKILL.read_text(encoding='utf-8')
        self.assertTrue(raw.startswith('---\n'))
        parts = raw.split('---', 2)
        fm = yaml.safe_load(parts[1])
        self.assertEqual(fm['name'], SKILL.parent.name)
        self.assertRegex(fm['name'], r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
        self.assertTrue(0 < len(fm['description']) <= 1024)
        self.assertTrue(parts[2].strip())
        self.assertTrue(all(isinstance(k, str) and isinstance(v, str) for k, v in fm.get('metadata', {}).items()))
        self.assertFalse(set(fm) - {'name', 'description', 'license', 'compatibility', 'metadata', 'allowed-tools'})

    def test_skill_file_references_exist(self):
        text = SKILL.read_text(encoding='utf-8')
        refs = re.findall(r'`((?:references|assets|scripts)/[^`\s]+\.(?:md|html|py))`', text)
        self.assertTrue(refs)
        for ref in refs:
            self.assertTrue((SKILL.parent / ref).is_file(), ref)

    def test_skill_keeps_the_go_gate(self):
        text = SKILL.read_text(encoding='utf-8')
        self.assertIn('explicit go', text)
        self.assertIn('brief.md', text)

    def test_vendored_three_is_complete_and_licensed(self):
        vendor = ROOT / 'plugins/clapcode/skills/clapcode/assets/vendor/three'
        for name in ('three.module.js', 'three.core.js', 'LICENSE', 'VERSION.txt',
                     'addons/RoundedBoxGeometry.js', 'addons/RoomEnvironment.js'):
            self.assertTrue((vendor / name).is_file(), name)
        self.assertIn('MIT License', (vendor / 'LICENSE').read_text(encoding='utf-8'))
        self.assertIn("from './three.core.js'", (vendor / 'three.module.js').read_text(encoding='utf-8'))
        page = (ROOT / 'plugins/clapcode/skills/clapcode/assets/template-3d.html').read_text(encoding='utf-8')
        self.assertIn('./vendor/three/three.module.js', page)

    def test_claude_plugin_manifests_match(self):
        plugin = json.loads((ROOT / 'plugins/clapcode/.claude-plugin/plugin.json').read_text(encoding='utf-8'))
        market = json.loads((ROOT / '.claude-plugin/marketplace.json').read_text(encoding='utf-8'))
        self.assertEqual(plugin['name'], 'clapcode')
        self.assertRegex(plugin['version'], r'^\d+\.\d+\.\d+$')
        self.assertEqual(plugin['license'], 'MIT')
        self.assertIn('github.com/necromancer124/clapcode', plugin['repository'])
        self.assertTrue(market['owner']['name'])
        entries = [p for p in market['plugins'] if p['name'] == plugin['name']]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['source'], './plugins/clapcode')
        self.assertTrue((ROOT / entries[0]['source'] / '.claude-plugin/plugin.json').is_file())
        self.assertEqual(entries[0]['version'], plugin['version'])

    def test_no_machine_paths_or_tokens(self):
        forbidden = ['C:\\Users\\', 'C:/Users/', '/c/Users/', '/home/', '/Users/']
        for path in ROOT.rglob('*'):
            if not path.is_file() or {'.git', '__pycache__', 'output', 'vendor'} & set(path.parts) or path == Path(__file__):
                continue
            if path.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.mp4', '.gif'):
                # Only the plugin icon and showcase media in docs/ belong in the repo.
                allowed = path == ROOT / 'plugins/clapcode/.claude-plugin/icon.png' or path.parent == ROOT / 'docs'
                self.assertTrue(allowed, f'Unexpected media file: {path}')
                # Anthropic's plugin directory refuses any file over 5 MiB.
                self.assertLess(path.stat().st_size, 5 * 1024 * 1024, f'Media file too large for the plugin directory: {path}')
                continue
            text = path.read_text(encoding='utf-8')
            for token in forbidden:
                self.assertNotIn(token, text, str(path))
            self.assertNotRegex(text, r'gh[pousr]_[A-Za-z0-9]{30,}')


if __name__ == '__main__':
    unittest.main()
