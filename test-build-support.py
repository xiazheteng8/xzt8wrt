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
    def test_arm_patch_validation_and_real_application(self):
        arm = support.arm_support
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            adaptations = root / 'devices'
            source = root / 'source'
            adaptations.mkdir()
            (source / 'target/linux/rockchip').mkdir(parents=True)
            support.subprocess.run(['git', 'init', str(source)], check=True, capture_output=True)
            driver = source / 'target/linux/rockchip/demo'
            driver.write_text('before\n')
            support.subprocess.run(['git', '-C', str(source), 'add', '.'], check=True)
            content = ('diff --git a/target/linux/rockchip/demo b/target/linux/rockchip/demo\n'
                       '--- a/target/linux/rockchip/demo\n+++ b/target/linux/rockchip/demo\n'
                       '@@ -1 +1 @@\n-before\n+after\n')
            (adaptations / 'test.patch').write_text(content)
            entry = {'path': 'test.patch', 'sha256': hashlib.sha256(content.encode()).hexdigest(),
                     'versions': ['25.12.2'], 'device': 'test-device'}
            definition = {'upstream_tree': 'target/linux/rockchip', 'driver_source': 'official-stable',
                          'patches': [entry], 'overlays': []}
            def save():
                (adaptations / 'targets.json').write_text(json.dumps({'schema': 1, 'targets': {'rockchip/armv8': definition}}))
            save()
            with patch.object(arm, 'ROOT', adaptations):
                with self.assertRaises(ValueError):
                    arm.prepare(source, 'rockchip/armv8', '26.1.0', ['test-device'])
                with self.assertRaises(ValueError):
                    arm.prepare(source, 'rockchip/armv8', '25.12.2', ['test-device', 'other-device'])
                entry['sha256'] = '0'*64
                save()
                with self.assertRaises(ValueError):
                    arm.prepare(source, 'rockchip/armv8', '25.12.2', ['test-device'])
                self.assertEqual(driver.read_text(), 'before\n')
                entry['sha256'] = hashlib.sha256(content.encode()).hexdigest()
                save()
                arm.prepare(source, 'rockchip/armv8', '25.12.2', ['test-device'])
                self.assertEqual(driver.read_text(), 'after\n')
                report = json.loads((source / 'arm-adaptation.json').read_text())
                self.assertEqual(report['applied'][0]['sha256'], entry['sha256'])
                self.assertIn('+after', (source / 'arm-adaptation.diff').read_text())
                with self.assertRaises(ValueError):
                    arm.local_file('../test.patch', entry['sha256'])
                bad = content.replace('rockchip/demo', 'x86/demo')
                (adaptations / 'test.patch').write_text(bad)
                entry['sha256'] = hashlib.sha256(bad.encode()).hexdigest()
                save()
                with self.assertRaises(ValueError):
                    arm.prepare(source, 'rockchip/armv8', '25.12.2', ['test-device'])

    def test_arm_config_manifest_matches_catalog(self):
        catalog = json.loads((support.ROOT / 'docs/catalog.json').read_text())
        for group in catalog['groups'].values():
            definition = support.arm_support.definition(group['target'])
            self.assertEqual(definition['config'], group['config'])
            self.assertEqual(definition['device_prefix'], group['config_prefix'])
    def test_legacy_release_metadata_uses_compiled_kernel(self):
        spec = importlib.util.spec_from_file_location('releases', support.ROOT / 'release-support.py')
        releases = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(releases)
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            artifact = root / 'xzt8wrt-25.12.2-x86-lite'
            artifact.mkdir()
            (artifact / 'profiles.json').write_text(json.dumps({'linux_kernel': {'version': '6.12.103', 'release': '1'}}))
            (root / 'xzt8wrt-diagnostics-full').mkdir()
            self.assertEqual(releases.prepare_legacy(root, '123'), 1)
            self.assertEqual(json.loads((artifact / 'kernel-source.json').read_text())['fingerprint'], '6.12.103-r1')
            self.assertIn('did not record', (artifact / 'source-patches.diff').read_text())
            marker = artifact / 'kernel-source.json'
            original = marker.read_bytes()
            releases.prepare_legacy(root, '123')
            self.assertEqual(marker.read_bytes(), original)

    def test_independent_release_baselines_keep_newest_success(self):
        spec = importlib.util.spec_from_file_location('releases', support.ROOT / 'release-support.py')
        releases = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(releases)
        states = [{'x86/lite': {'fingerprint': 'new'}},
                  {'rockchip/full': {'fingerprint': 'new-arm'}},
                  {'x86/lite': {'fingerprint': 'old'}, 'x86/full': {'fingerprint': 'old-full'}}]
        merged = releases.merge_newest_first(states)
        self.assertEqual(merged['x86/lite']['fingerprint'], 'new')
        self.assertEqual(merged['x86/full']['fingerprint'], 'old-full')
        self.assertEqual(merged['rockchip/full']['fingerprint'], 'new-arm')
        self.assertNotIn('filogic/lite', merged)
        self.assertEqual(releases.merge_newest_first([]), {})

    def test_arm_catalog_is_allowlisted_and_keeps_x86_separate(self):
        catalog = json.loads((support.ROOT / 'docs/catalog.json').read_text())
        for device in catalog['devices']:
            config = support.config('custom', 'lite', device['uid'])
            self.assertNotIn('CONFIG_TARGET_x86', config)
            self.assertNotIn('CONFIG_GRUB_', config)
            self.assertNotIn('CONFIG_PACKAGE_kmod-igc', config)
            group = catalog['groups'][device['platform']]
            self.assertIn('CONFIG_TARGET_DEVICE_' + group['config_prefix'] + '_DEVICE_' + device['id'] + '=y', config)
            if not device['full']:
                self.assertNotIn('CONFIG_TARGET_ROOTFS_PARTSIZE=', config)
                with self.assertRaises(ValueError):
                    support.config('custom', 'full', device['uid'])
        with self.assertRaises(ValueError):
            support.config('custom', 'lite', 'x86/64/generic')
        with self.assertRaises(ValueError):
            support.config('x86', 'lite', catalog['devices'][0]['uid'])

    def test_custom_device_collection_does_not_stamp_whole_platform(self):
        catalog = json.loads((support.ROOT / 'docs/catalog.json').read_text())
        selected = next(d for d in catalog['devices'] if d['platform'] == 'sunxi-cortexa53')
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            source = root / 'source'
            directory = source / 'bin/targets' / selected['target']
            directory.mkdir(parents=True)
            name = selected['id'] + '-sdcard.img.gz'
            (directory / name).write_bytes(b'image')
            metadata = {'target': selected['target'], 'linux_kernel': {'version': 'test'}, 'profiles': {
                selected['id']: {'images': [{'name': name, 'type': 'sdcard', 'sha256': hashlib.sha256(b'image').hexdigest()}]}}}
            (directory / 'profiles.json').write_text(json.dumps(metadata))
            for filename in ('.config', 'requested.config', 'source-version.txt', 'feeds-version.txt', 'source.json', 'kernel-source.json', 'source-patches.diff'):
                value = {'ref': 'vtest', 'version': 'test', 'commit': 'a'*40} if filename == 'source.json' else {'fingerprint': 'test'}
                (source / filename).write_text(json.dumps(value))
            artifact = root / 'artifacts/custom-lite'
            support.collect('custom', source, artifact, selected['uid'])
            with patch.dict(support.os.environ, {'KERNEL_BASELINE_JSON': '{"x86/lite":{"fingerprint":"keep"}}'}):
                self.assertEqual(support.bundle(root / 'artifacts', root / 'release'), 1)
            state = json.loads((root / 'release/kernel-state.json').read_text())
            self.assertEqual(set(state), {'x86/lite', selected['uid'] + '/lite'})
            self.assertEqual(state['x86/lite']['fingerprint'], 'keep')

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

    def test_kernel_schedule_skips_unchanged_and_retries_missing(self):
        kernels = {p: {'fingerprint': '6.12.103-r1'} for p in support.TARGETS}
        baseline = {p + '/' + v: {'fingerprint': '6.12.103-r1'} for p, v in
                    [('x86','full'), ('x86','lite'), ('rockchip','full'), ('rockchip','lite'), ('filogic','lite')]}
        jobs, skipped = support.build_plan('all', 'both', True, baseline, kernels)
        self.assertEqual(jobs, [])
        self.assertEqual(len(skipped), 5)
        kernels['rockchip'] = {'fingerprint': '6.12.104-r1'}
        jobs, _ = support.build_plan('all', 'both', True, baseline, kernels)
        self.assertEqual([(j['platform'], j['profile']) for j in jobs], [('rockchip','full'), ('rockchip','lite')])
        baseline.pop('x86/full')
        jobs, _ = support.build_plan('x86', 'both', True, baseline, kernels)
        self.assertEqual([j['profile'] for j in jobs], ['full'])
        jobs, _ = support.build_plan('x86', 'both', False, baseline, kernels)
        self.assertEqual(len(jobs), 2)

    def test_rust_host_fix_preserves_protocol_packages(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            package = root / 'feeds/packages'
            (package / 'lang/rust').mkdir(parents=True)
            subprocess = __import__('subprocess')
            subprocess.run(['git', 'init', str(package)], check=True, capture_output=True)
            makefile = package / 'lang/rust/Makefile'
            makefile.write_text('HOST_CONFIGURE_ARGS = --set=llvm.download-ci-llvm=true\n$(eval $(call HostBuild))\n')
            support.fix_rust_host(root)
            self.assertIn('llvm.download-ci-llvm=false', makefile.read_text())
            self.assertIn('llvm.link-jobs=1', makefile.read_text())

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
                for name in ('.config', 'requested.config', 'source-version.txt', 'feeds-version.txt', 'source.json', 'kernel-source.json', 'source-patches.diff'):
                    (source / name).write_text(json.dumps({'version': '1.0.0', 'ref': 'v1.0.0', 'commit': 'a'*40}) if name == 'source.json' else json.dumps({'fingerprint': '6.12.103-r1'}) if name == 'kernel-source.json' else 'test')
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
