"""Publish a new immutable snapshot of latest successful popular-device images."""
import concurrent.futures
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import tempfile
import uuid
import release_features
import sys

ROOT = pathlib.Path(__file__).resolve().parent
REPO = os.environ.get('GH_REPO', '')
KEYS = {'x86/full', 'x86/lite', 'rockchip/full', 'rockchip/lite', 'filogic/lite'}


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', path]))


def key_for_asset(name, devices):
    for d in devices:
        for profile in ('full', 'lite'):
            for label in (profile, {'full': '高大全版', 'lite': '精简版'}[profile]):
                stem = f"-{d['platform']}-{d['id']}-{label}"
                if (d['platform'] == 'x86' and re.search(re.escape(stem) + r'-(img|qcow2|vmdk|vdi|vhdx)-(bios|uefi)-(squashfs|ext4)\.zip$', name)) or any(name.endswith(stem + ending) for ending in ('.zip', '-qcow2.zip', '-vmdk.zip', '-vdi.zip', '-vhdx.zip')):
                    return d['platform'] + '/' + profile
    return None


def publish(directory):
    directory = pathlib.Path(directory)
    incoming = json.loads((directory / 'kernel-state.json').read_text())
    incoming = {k: v for k, v in incoming.items() if k in KEYS}
    devices = json.loads((ROOT / 'docs/release-devices.json').read_text())['devices']
    # No selected popular firmware means no new public Release.
    for path in directory.glob('*.zip'):
        if key_for_asset(path.name, devices) not in incoming:
            path.unlink()
    if not list(directory.glob('*.zip')):
        raise ValueError('No publishable popular-device firmware')
    state = dict(incoming)
    origins = {k: '本轮更新' for k in incoming}
    pages = json.loads(subprocess.check_output(['gh', 'api', '--paginate', '--slurp', f'repos/{REPO}/releases']))
    downloads = []
    with tempfile.TemporaryDirectory() as temporary:
        temp = pathlib.Path(temporary)
        for release in sorted([r for page in pages for r in page], key=lambda r:r['published_at'] or '', reverse=True):
            if release['draft'] or release['prerelease'] or not any(a['name'] == 'kernel-state.json' for a in release['assets']):
                continue
            marker_dir = temp / str(release['id'])
            marker_dir.mkdir()
            subprocess.run(['gh', 'release', 'download', release['tag_name'], '--repo', REPO,
                            '--pattern', 'kernel-state.json', '--dir', str(marker_dir)], check=True)
            previous = json.loads((marker_dir / 'kernel-state.json').read_text())
            for key in KEYS - state.keys():
                matches = [a for a in release['assets'] if key_for_asset(a['name'], devices) == key]
                if key not in previous or not matches:
                    continue
                state[key] = previous[key]
                origins[key] = '沿用成功版本 ' + release['tag_name']
                downloads.extend((release['tag_name'], a['name'], a.get('digest')) for a in matches)
            if KEYS <= state.keys():
                break
        def download(item):
            tag, name, digest = item
            subprocess.run(['gh', 'release', 'download', tag, '--repo', REPO, '--pattern', name,
                            '--dir', str(directory)], check=True)
            if digest:
                actual = 'sha256:' + hashlib.sha256((directory / name).read_bytes()).hexdigest()
                if actual != digest:
                    raise ValueError('Copied firmware digest mismatch: ' + name)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(download, downloads))
    (directory / 'kernel-state.json').write_text(json.dumps(state, indent=2) + '\n')
    sums = [hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name for p in sorted(directory.glob('*.zip'))]
    (directory / 'SHA256SUMS').write_text('\n'.join(sums) + '\n')
    fingerprints = sorted({v['fingerprint'] for v in incoming.values()})
    if any(not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-r[0-9]+', f) for f in fingerprints):
        raise ValueError('Invalid compiled kernel version')
    timestamp = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).strftime('%Y%m%d-%H%M%S')
    tag = '_'.join(fingerprints) + '-' + timestamp + '-' + uuid.uuid4().hex[:4]
    lines = ['# xzt8wrt 常见机型固件', '', '本次发布汇总各平台最新成功固件，仅重新编译内核有变化的组合。',
             '不同平台可能沿用不同正式版本，实际版本、内核和插件以各 ZIP 内的元数据为准。历史 Release 不覆盖。', '',
             '| 平台 / 版本 | 实际内核 | 来源 |', '| --- | --- | --- |']
    for key in sorted(state):
        lines.append(f"| {key} | {state[key]['fingerprint']} | {origins[key]} |")
    missing = sorted(KEYS - state.keys())
    if missing:
        lines += ['', '尚无成功固件：' + '、'.join(missing) + '，不提供占位下载。']
    lines += ['', '下载与你的完整型号、硬件版本和引导布局一致的 ZIP，并核对 SHA256SUMS。',
              'IMG 用于写盘；QCOW2 用于 PVE/KVM，VMDK 用于 VMware，VDI 用于 VirtualBox，VHDX 用于 Hyper-V（仅在实际生成时提供）。',
              'TR3000 等首次安装可能需要厂商中间固件；不要把 sysupgrade 当作通用中间固件。构建成功不代表实机测试。',
              '', '固件工坊：https://xiazheteng8.github.io/xzt8wrt/',
              '其他机型仅提供自建教程，不纳入本站固定发布名单。',
              'Release 标签对应发布快照；原始源码、构建配置和内核信息保留在 ZIP 内。']
    lines += ['', *release_features.render_features(state)]
    notes = directory / '发行说明.md'
    notes.write_text('\n'.join(lines) + '\n')
    subprocess.run(['gh', 'release', 'create', tag, '--repo', REPO, '--target', 'main',
                    '--title', 'xzt8wrt｜内核 ' + '_'.join(fingerprints) + '｜' + timestamp,
                    '--notes-file', str(notes)], check=True)
    subprocess.run(['gh', 'release', 'upload', tag, '--repo', REPO,
                    *map(str, sorted(directory.glob('*.zip'))), str(directory / 'SHA256SUMS')], check=True)
    # The completion marker is uploaded last; incomplete Releases are not baselines.
    subprocess.run(['gh', 'release', 'upload', tag, '--repo', REPO, str(directory / 'kernel-state.json')], check=True)
    subprocess.run(['gh', 'release', 'edit', tag, '--repo', REPO, '--latest'], check=True)
    # GitHub sanitizes non-ASCII filenames; use Chinese asset labels for identification.
    for asset in api(f'repos/{REPO}/releases/tags/{tag}')['assets']:
        label = asset['name'].replace('-full', '-高大全版').replace('-lite', '-精简版')
        subprocess.run(['gh', 'api', '--method', 'PATCH', f"repos/{REPO}/releases/assets/{asset['id']}", '-f', 'label=' + label], check=True, stdout=subprocess.DEVNULL)
    url = f'https://github.com/{REPO}/releases/tag/{tag}'
    print(url)
    index = subprocess.run([sys.executable, str(ROOT / 'release-support.py'), 'index'])
    if index.returncode:
        print('下载索引更新失败，固件已发布，可直接访问 Releases。')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
            summary.write('已发布：' + url + '\n')


if __name__ == '__main__':
    import sys
    publish(sys.argv[1])
