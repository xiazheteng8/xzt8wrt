"""Plan and assemble custom firmware with the official ImageBuilder."""
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
import plugin_support as plugins

ROOT = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('support', ROOT / 'build-support.py')
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)


def device(uid):
    if uid == 'x86/64/generic':
        return {'id': 'generic', 'uid': uid, 'platform': 'x86', 'target': 'x86/64', 'kind': 'soft'}
    selected, _ = support.arm_selection(uid)
    return selected


def plan(uid, raw, version="latest"):
    selected = device(uid)
    names = plugins.selection(raw)
    source = support.resolve(version)
    target = selected['target']
    base = f"https://downloads.immortalwrt.org/releases/{source['version']}/targets/{target}/"
    with urllib.request.urlopen(base + 'sha256sums', timeout=60) as response:
        sums = response.read().decode()
    prefix = f"immortalwrt-imagebuilder-{source['version']}-{target.replace('/', '-')}.Linux-x86_64.tar."
    builders = [(digest, name.lstrip('*')) for digest, name in re.findall(r'^([0-9a-f]{64})\s+(.+)$', sums, re.M)
                if name.lstrip('*').startswith(prefix)]
    external = any(plugins.options()[name].get('external') for name in names)
    selected.update({'plugins': names, 'packages': plugins.packages(names), 'signature': plugins.identity(uid, names),
                     'source': source, 'builder': ({'url': base + builders[0][1], 'sha256': builders[0][0]} if builders else None),
                     'fast_available': bool(builders) and not external,
                     'publish': plugins.release_allowed(uid),
                     'source_platform': 'x86' if selected['platform'] == 'x86' else 'custom'})
    return selected


def fast(data):
    if not data['fast_available']:
        raise ValueError('No compatible official prebuilt set. Use method=source or auto.')
    archive = ROOT / 'imagebuilder.tar'
    subprocess.run(['curl', '--fail', '--location', '--retry', '3', '--retry-all-errors',
                    data['builder']['url'], '--output', str(archive)], check=True)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != data['builder']['sha256']:
        raise ValueError('Official ImageBuilder SHA256 mismatch')
    destination = ROOT / 'imagebuilder'
    destination.mkdir(exist_ok=True)
    subprocess.run(['tar', '-xf', str(archive), '-C', str(destination), '--strip-components=1'], check=True)
    overlay = ROOT / 'custom-files'
    shutil.copytree(ROOT / 'files', overlay, dirs_exist_ok=True)
    plugins.custom_defaults(overlay)
    (overlay / 'etc/banner').write_text('\n  xzt8wrt / official ImageBuilder / custom\n')
    (overlay / 'etc/xzt8wrt-profile').write_text('lite\n')
    args = ['make', 'image', 'PROFILE=' + data['id'], 'PACKAGES=' + ' '.join(data['packages'] + ['-dnsmasq']),
            'FILES=' + str(overlay), 'EXTRA_IMAGE_NAME=xzt8wrt-' + data['signature']]
    if data['kind'] == 'soft':
        args.append('ROOTFS_PARTSIZE=512')
    subprocess.run(args, cwd=destination, check=True)
    output = destination / 'bin/targets' / data['target']
    manifest = json.loads((output / 'profiles.json').read_text())
    images = manifest['profiles'][data['id']]['images']
    primary = {'sysupgrade', 'nand-sysupgrade', 'WN573HX3-sysupgrade', 'sdcard', 'combined-efi', 'trx', 'bin', 'firmware'}
    if data['platform'] == 'x86':
        images = [i for i in images if i['type'] in ('combined', 'combined-efi') and i['name'].endswith('.img.gz')]
        if {i['type'] for i in images} != {'combined', 'combined-efi'}:
            raise ValueError('Missing BIOS or EFI image')
    elif not any(i['type'] in primary for i in images):
        raise ValueError('No complete device image generated; possible flash size limit')
    installed = set()
    for path in output.glob('*.manifest'):
        installed.update(line.split()[0] for line in path.read_text().splitlines() if line.strip())
    required = {p for p in data['packages'] if p.startswith('luci-app-')}
    if not required <= installed:
        raise ValueError('Requested plugins missing from built package manifest: ' + ', '.join(sorted(required - installed)))
    metadata = {'schema': 1, 'device': data['uid'], 'plugins': data['plugins'], 'packages': data['packages'],
                'signature': data['signature'], 'method': 'imagebuilder', 'official_builder': data['builder'],
                'source': data['source'], 'kernel': manifest['linux_kernel']}
    release = ROOT / 'release-output'
    release.mkdir(exist_ok=True)
    filename = f"xzt8wrt-{data['source']['version']}-{data['platform']}-{data['id']}-custom-{data['signature']}.zip"
    checksums = []
    with zipfile.ZipFile(release / filename, 'w', compression=zipfile.ZIP_STORED) as bundle:
        for item in images:
            path = (output / item['name']).resolve()
            if not path.is_relative_to(output.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
                raise ValueError('Invalid image file or checksum')
            bundle.write(path, path.name)
            checksums.append(item['sha256'] + '  ' + path.name)
        for path in output.glob('*.manifest'):
            bundle.write(path, path.name)
        bundle.writestr('custom-build.json', json.dumps(metadata, ensure_ascii=False, indent=2))
        bundle.writestr('images.json', json.dumps(images, indent=2))
        bundle.writestr('xzt8wrt-sha256sums', '\n'.join(checksums) + '\n')
        bundle.writestr('READ-BEFORE-FLASHING.txt', 'Exact device: ' + data['uid'] + '\nVerify hardware and bootloader layout. Build success is not a hardware test.\nProxy services are disabled until configured; enable only the service you intend to use.\n')
    kernel = manifest['linux_kernel']
    state = {'custom/' + data['signature']: {'version': str(kernel['version']), 'release': str(kernel['release']),
             'fingerprint': str(kernel['version']) + '-r' + str(kernel['release'])}}
    (output / 'custom-build.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    (output / 'source.json').write_text(json.dumps(data['source']))
    (release / 'kernel-state.json').write_text(json.dumps(state, indent=2) + '\n')
    sums = [hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name for path in release.glob('*.zip')]
    (release / 'SHA256SUMS').write_text('\n'.join(sums) + '\n')


if __name__ == '__main__':
    if sys.argv[1] == 'plan':
        data = plan(os.environ['SELECT_DEVICE'], os.environ.get('SELECT_PLUGINS', ''), os.environ.get('SELECT_VERSION', 'latest'))
        (ROOT / 'custom-plan.json').write_text(json.dumps(data, ensure_ascii=False, indent=2))
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            values = {'platform': data['source_platform'], 'device': '' if data['platform'] == 'x86' else data['uid'],
                      'signature': data['signature'], 'publish': 'true' if data['publish'] else 'false', 'fast': 'true' if data['fast_available'] else 'false', **data['source']}
            for key, value in values.items():
                output.write(key + '=' + value + '\n')
    else:
        fast(json.loads((ROOT / 'custom-plan.json').read_text()))
