"""Read Kwrt's public device inventory and match official stable ARM profiles.
Never executes Kwrt diy.sh or replaces the x86/boot/kernel trees.
"""
import argparse
import concurrent.futures
import datetime
import http.client
import time
import json
import pathlib
import re
import subprocess
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent


def fetch(url):
    cache = ROOT / '.catalog-cache' / (re.sub(r'[^a-zA-Z0-9.-]+', '_', url) + '.json')
    if cache.is_file():
        return json.loads(cache.read_text())
    for attempt in range(5):
        try:
            request_url = url if attempt == 0 else url + '?retry=' + str(time.time_ns())
            with urllib.request.urlopen(request_url, timeout=45) as response:
                result = json.load(response)
            cache.parent.mkdir(exist_ok=True)
            cache.write_text(json.dumps(result))
            return result
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, http.client.IncompleteRead, TimeoutError):
            if attempt == 4:
                raise
            print('Retrying profile download:', url, flush=True)
            time.sleep(1 + attempt)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--kwrt-directory', type=pathlib.Path, required=True)
    p.add_argument('--version', required=True)
    p.add_argument('--reference-overview', type=pathlib.Path)
    p.add_argument('--reference-models', type=pathlib.Path)
    args = p.parse_args()
    ref = json.loads(args.reference_overview.read_text()) if args.reference_overview else fetch('https://openwrt.ai/json/v1/overview.json')
    models = json.loads(args.reference_models.read_text()) if args.reference_models else fetch('https://openwrt.ai/json/v1/releases/25.12/overview.json')
    arches = ref['branches']['25.12']['targets']
    targets = [target for target, arch in arches.items() if arch.startswith(('arm', 'aarch64'))]
    commit = subprocess.check_output(['git', '-C', str(args.kwrt_directory), 'rev-parse', 'HEAD'], text=True).strip()
    folders = set(subprocess.check_output(['git', '-C', str(args.kwrt_directory), 'ls-tree', '--name-only', 'HEAD:devices'], text=True).splitlines())
    groups, devices, excluded = {}, [], []

    def load(target):
        folder = target.replace('/', '_')
        if folder not in folders:
            folder = target.split('/')[0]
        if folder not in folders:
            return target, None, 'No matching Kwrt device directory'
        try:
            profile = fetch(f'https://downloads.immortalwrt.org/releases/{args.version}/targets/{target}/profiles.json')
            cfg = subprocess.check_output(['git', '-C', str(args.kwrt_directory), 'show', f'HEAD:devices/{folder}/.config'], text=True)
            options = [line for line in cfg.splitlines() if re.fullmatch(r'CONFIG_TARGET_[a-zA-Z0-9_]+=y', line)
                       and line in (f'CONFIG_TARGET_{target.split("/")[0]}=y', f'CONFIG_TARGET_{target.replace("/", "_")}=y')]
            if not options:
                return target, None, 'No target config in Kwrt directory'
            return target, (profile, folder, options), None
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return target, None, 'Target unavailable in official stable release'
            raise

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        loaded = list(pool.map(load, targets))
    for target, data, reason in loaded:
        references = [item for item in models['profiles'] if item['target'] == target]
        if data is None:
            excluded.extend({'id': item['id'], 'target': target, 'reason': reason} for item in references)
            continue
        metadata, folder, options = data
        platform = {'rockchip/armv8': 'rockchip', 'mediatek/filogic': 'filogic'}.get(target, target.replace('/', '-'))
        config_prefix = max((line.removeprefix('CONFIG_TARGET_').removesuffix('=y') for line in options), key=len)
        soft = target.split('/')[0] in ('rockchip', 'bcm27xx', 'armsr', 'sunxi', 'amlogic')
        group = {'target': target, 'folder': folder, 'config': options, 'config_prefix': config_prefix,
                 'soft': soft, 'arch': metadata['arch_packages'], 'kernel': metadata['linux_kernel']}
        groups[platform] = group
        for item in references:
            device = metadata['profiles'].get(item['id'])
            if device is None:
                excluded.append({'id': item['id'], 'target': target, 'reason': 'Profile needs Kwrt-specific adaptation; not in official stable'})
                continue
            for title in item.get('titles', []):
                name = ' '.join(str(title.get(key, '')) for key in ('model', 'variant')).strip() or item['id']
                devices.append({'id': item['id'], 'uid': target + '/' + item['id'], 'name': name,
                                'brand': title.get('vendor', ''), 'platform': platform, 'target': target,
                                'layout': title.get('variant', '') or ('ubootmod' if 'ubootmod' in item['id'] else '按准确型号核对'),
                                'kind': 'soft' if soft else 'hard', 'full': soft,
                                'status': 'configuration-only', 'image_types': sorted({image['type'] for image in device.get('images', [])})})
    unique = {item['uid']: item for item in devices}
    result = {'reference': 'https://github.com/kiddin9/Kwrt/tree/25.12/devices', 'reference_commit': commit,
              'inventory_source': 'https://openwrt.ai/json/v1/releases/25.12/overview.json',
              'immortalwrt_version': args.version, 'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'groups': groups, 'devices': sorted(unique.values(), key=lambda item: (item['brand'].lower(), item['name'].lower())),
              'excluded': excluded}
    (ROOT / 'docs').mkdir(exist_ok=True)
    (ROOT / 'docs/catalog.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f"Matched {len(unique)} ARM profiles in {len(groups)} targets; {len(excluded)} reference profiles need adaptation.")


if __name__ == '__main__':
    main()
