"""Resolve official stable sources, generate target configs and verify images."""
import argparse
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
REPO = 'https://github.com/immortalwrt/immortalwrt.git'
TARGETS = {
    'x86': ('x86', '64', ['generic']),
    'rockchip': ('rockchip', 'armv8', [
        'friendlyarm_nanopi-r2s', 'friendlyarm_nanopi-r4s',
        'friendlyarm_nanopi-r5s', 'friendlyarm_nanopi-r6s',
        'lunzn_fastrhino-r66s', 'lunzn_fastrhino-r68s']),
    'filogic': ('mediatek', 'filogic', [
        'cudy_tr3000-v1', 'cudy_tr3000-256mb-v1', 'cudy_tr3000-v1-ubootmod',
        'xiaomi_redmi-router-ax6000-stock', 'xiaomi_redmi-router-ax6000-ubootmod',
        'asus_tuf-ax6000', 'glinet_gl-mt3000', 'glinet_gl-mt6000']),
}


def resolve():
    # Official releases are tags, not GitHub Releases/latest.
    with urllib.request.urlopen('https://downloads.immortalwrt.org/', timeout=60) as response:
        html = response.read().decode()
    versions = re.findall(r'href=["\'](?:\./)?releases/(\d+\.\d+\.\d+)/targets/', html)
    if not versions:
        raise RuntimeError('Official download page contains no stable release')
    version = max(versions, key=lambda v: tuple(map(int, v.split('.'))))
    ref = 'v' + version
    refs = subprocess.check_output(
        ['git', 'ls-remote', REPO, 'refs/tags/' + ref, 'refs/tags/' + ref + '^{}'], text=True)
    mapping = dict(line.split()[::-1] for line in refs.splitlines())
    commit = mapping.get('refs/tags/' + ref + '^{}', mapping.get('refs/tags/' + ref))
    if not commit or not re.fullmatch('[0-9a-f]{40}', commit):
        raise RuntimeError('Cannot resolve official stable tag')
    return {'version': version, 'ref': ref, 'commit': commit}


def config(platform, profile):
    target, subtarget, devices = TARGETS[platform]
    if platform == 'filogic' and profile == 'full':
        raise ValueError('Filogic flash routers currently support lite only')
    lines = [f'CONFIG_TARGET_{target}=y', f'CONFIG_TARGET_{target}_{subtarget}=y']
    if platform == 'x86':
        lines += ['CONFIG_TARGET_x86_64_DEVICE_generic=y', 'CONFIG_GRUB_IMAGES=y',
                  'CONFIG_GRUB_EFI_IMAGES=y']
        lines += [f'CONFIG_PACKAGE_{p}=y' for p in (
            'kmod-igc', 'kmod-igb', 'kmod-e1000e', 'kmod-r8169',
            'kmod-usb-net-rtl8152', 'kmod-usb-net-asix-ax88179', 'kmod-vmxnet3')]
    else:
        lines += ['CONFIG_TARGET_MULTI_PROFILE=y', 'CONFIG_TARGET_PER_DEVICE_ROOTFS=y',
                  '# CONFIG_TARGET_ALL_PROFILES is not set']
        lines += [f'CONFIG_TARGET_DEVICE_{target}_{subtarget}_DEVICE_{d}=y' for d in devices]
    lines += ['CONFIG_TARGET_ROOTFS_SQUASHFS=y']
    if platform != 'filogic':
        lines += ['CONFIG_TARGET_ROOTFS_EXT4FS=y', 'CONFIG_TARGET_IMAGES_GZIP=y',
                  'CONFIG_TARGET_KERNEL_PARTSIZE=64',
                  f'CONFIG_TARGET_ROOTFS_PARTSIZE={2048 if profile == "full" else 512}']
    else:
        lines += ['# CONFIG_TARGET_ROOTFS_EXT4FS is not set', 'CONFIG_TARGET_ROOTFS_INITRAMFS=y']
    lines += (ROOT / 'seed.config').read_text().splitlines()
    lines += (ROOT / 'profiles' / (profile + '.config')).read_text().splitlines()
    return '\n'.join(lines) + '\n'


def collect(platform, source, output):
    target, subtarget, devices = TARGETS[platform]
    directory = source / 'bin' / 'targets' / target / subtarget
    metadata = json.loads((directory / 'profiles.json').read_text())
    # make can skip oversized images without failing. Require every device.
    for device in devices:
        images = metadata['profiles'].get(device, {}).get('images', [])
        upgrades = [item for item in images if item.get('type') == 'sysupgrade']
        if platform == 'x86':
            upgrades = [item for item in images if item.get('type') in ('combined', 'combined-efi')
                        and item['name'].endswith('.img.gz')]
            if {item['type'] for item in upgrades} != {'combined', 'combined-efi'}:
                raise RuntimeError('Missing x86 BIOS or UEFI disk image')
        if not upgrades:
            raise RuntimeError(f'Missing sysupgrade image for {device}; check image size/build logs')
        for item in images:
            image = directory / item['name']
            if not image.is_file():
                raise RuntimeError(f'Missing image: {image.name}')
            if hashlib.sha256(image.read_bytes()).hexdigest() != item['sha256']:
                raise RuntimeError(f'Checksum mismatch: {image.name}')
    output.mkdir(parents=True, exist_ok=True)
    for path in directory.iterdir():
        if path.is_file():
            shutil.copy2(path, output / path.name)
    for name in ('.config', 'requested.config', 'source-version.txt', 'feeds-version.txt', 'source.json'):
        shutil.copy2(source / name, output / name)
    (output / 'kernel-version.json').write_text(json.dumps(metadata['linux_kernel'], indent=2) + '\n')
    (output / 'devices.json').write_text(json.dumps(devices, indent=2) + '\n')
    sums = []
    for path in sorted(output.iterdir()):
        if path.is_file():
            sums.append(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name)
    (output / 'xzt8wrt-sha256sums').write_text('\n'.join(sums) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['resolve', 'config', 'collect'])
    parser.add_argument('--platform', choices=TARGETS, default='x86')
    parser.add_argument('--profile', choices=['full', 'lite'], default='full')
    parser.add_argument('--source', type=pathlib.Path)
    parser.add_argument('--output', type=pathlib.Path)
    args = parser.parse_args()
    if args.command == 'resolve':
        print(json.dumps(resolve()))
    elif args.command == 'config':
        print(config(args.platform, args.profile), end='')
    else:
        collect(args.platform, args.source, args.output)


if __name__ == '__main__':
    main()
