import hashlib
import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('support', pathlib.Path(__file__).with_name('build-support.py'))
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)


class BuildSupportTests(unittest.TestCase):
    def test_configs_separate_architectures(self):
        for platform in support.TARGETS:
            for profile in ('full', 'lite'):
                if (platform, profile) == ('filogic', 'full'):
                    with self.assertRaises(ValueError):
                        support.config(platform, profile)
                    continue
                config = support.config(platform, profile)
                self.assertIn('CONFIG_PACKAGE_luci-app-passwall=y', config)
                self.assertIn('CONFIG_PACKAGE_luci-app-ddns-go=y', config)
                self.assertIn('# CONFIG_PACKAGE_luci-app-openclash is not set', config)
                if platform != 'x86':
                    self.assertNotIn('CONFIG_TARGET_x86', config)
                    self.assertNotIn('CONFIG_PACKAGE_kmod-igc', config)
                    self.assertNotIn('CONFIG_GRUB_', config)
                if platform == 'filogic':
                    self.assertNotIn('CONFIG_TARGET_ROOTFS_PARTSIZE=', config)
                keys = [line.split('=')[0] for line in config.splitlines() if line.startswith('CONFIG_')]
                self.assertEqual(len(keys), len(set(keys)))

    def test_latest_stable_numeric_order_and_peeled_tag(self):
        with patch.object(support.urllib.request, 'urlopen') as request, patch.object(support.subprocess, 'check_output') as git:
            request.return_value.__enter__.return_value.read.return_value = (
                b'<a href="releases/25.12.2/targets/">a</a>'
                b'<a href="releases/25.12.10/targets/">b</a>'
                b'<a href="releases/26.0.0-rc1/targets/">rc</a>')
            git.return_value = 'a'*40 + '\trefs/tags/v25.12.10\n' + 'b'*40 + '\trefs/tags/v25.12.10^{}\n'
            self.assertEqual(support.resolve(), {'version': '25.12.10', 'ref': 'v25.12.10', 'commit': 'b'*40})

    def test_require_every_device_and_verify_hash(self):
        for platform, (target, subtarget, devices) in support.TARGETS.items():
            with tempfile.TemporaryDirectory() as temporary:
                root = pathlib.Path(temporary)
                source = root / 'source'
                directory = source / 'bin' / 'targets' / target / subtarget
                directory.mkdir(parents=True)
                (directory / 'packages').mkdir()
                metadata = {'target': target + '/' + subtarget, 'profiles': {}, 'linux_kernel': {'version': 'test'}}
                for device in devices:
                    kinds = ('combined', 'combined-efi') if platform == 'x86' else ('sysupgrade',)
                    images = []
                    for kind in kinds:
                        name = f'{device}-{kind}.img.gz'
                        (directory / name).write_bytes(b'image')
                        images.append({'name': name, 'type': kind, 'sha256': hashlib.sha256(b'image').hexdigest()})
                    metadata['profiles'][device] = {'images': images}
                manifest = directory / 'profiles.json'
                manifest.write_text(json.dumps(metadata))
                for name in ('.config', 'requested.config', 'source-version.txt', 'feeds-version.txt', 'source.json'):
                    (source / name).write_text(json.dumps({'version': '1.0.0', 'ref': 'v1.0.0', 'commit': 'a'*40}) if name == 'source.json' else 'test')
                artifact = root / ('xzt8wrt-test-' + platform + '-lite')
                support.collect(platform, source, artifact)
                self.assertTrue((artifact / 'kernel-version.json').is_file())
                self.assertFalse((artifact / 'packages').exists())
                self.assertEqual(support.bundle(root, root / 'release'), len(devices))
                import zipfile
                with zipfile.ZipFile(next((root / 'release').glob('*.zip'))) as archive:
                    self.assertIn('images.json', archive.namelist())
                    self.assertIn('xzt8wrt-sha256sums', archive.namelist())
                missing = directory / metadata['profiles'][devices[0]]['images'][0]['name']
                missing.write_bytes(b'corrupted')
                with self.assertRaises(RuntimeError):
                    support.collect(platform, source, root / 'bad')
                missing.unlink()
                with self.assertRaises(RuntimeError):
                    support.collect(platform, source, root / 'bad')
                metadata['profiles'].pop(devices[0])
                manifest.write_text(json.dumps(metadata))
                with self.assertRaises(RuntimeError):
                    support.collect(platform, source, root / 'bad')


if __name__ == '__main__':
    unittest.main()
