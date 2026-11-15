"""Allowlisted plugin selections; fixed firmware presets remain unchanged."""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
BASE = ['luci', 'luci-ssl', 'luci-i18n-base-zh-cn', 'luci-app-firewall',
        'luci-app-package-manager', 'luci-app-wol', 'luci-app-ddns-go', 'curl', 'ca-bundle', 'dnsmasq-full']


def options():
    return {p['id']: p for p in json.loads((ROOT / 'docs/plugins.json').read_text())['plugins']}


def selection(raw):
    names = sorted(set(raw.replace(',', ' ').split()))
    catalog = options()
    if len(names) > 64 or any(n not in catalog or not catalog[n]['supported'] for n in names):
        raise ValueError('Unknown or unadapted plugin: choose supported entries from the website')
    return names


def identity(uid, names):
    return hashlib.sha256((uid + '\n' + ','.join(sorted(names)) + '\nv1').encode()).hexdigest()[:32]


def packages(names):
    catalog = options()
    return sorted(set(BASE + [p for n in names for p in catalog[n]['packages']]))


def source_config(lines, raw):
    names = selection(raw)
    # Custom firmware starts from essential packages, not the frozen full preset.
    lines = [line for line in lines if 'CONFIG_PACKAGE_luci-app-passwall' not in line]
    lines += [f'CONFIG_PACKAGE_{p}=y' for p in packages(names)]
    for proxy in ['luci-app-passwall', 'luci-app-passwall2', 'luci-app-ssr-plus']:
        if proxy not in names:
            lines += [f'# CONFIG_PACKAGE_{proxy} is not set']
    if 'luci-app-passwall' in names:
        lines += ['CONFIG_PACKAGE_luci-app-passwall_INCLUDE_Xray=y']
    if 'luci-app-passwall2' in names:
        lines += ['CONFIG_PACKAGE_luci-app-passwall2_Basic_Core_Xray=y',
                  '# CONFIG_PACKAGE_luci-app-passwall2_Basic_Core_All is not set']
    if 'luci-app-ssr-plus' in names:
        lines += ['CONFIG_PACKAGE_luci-app-ssr-plus_INCLUDE_Xray=y']
    for proxy in names:
        if proxy in ('luci-app-passwall', 'luci-app-passwall2', 'luci-app-ssr-plus'):
            for feature in ['Shadowsocks_Rust_Client', 'Shadowsocks_Rust_Server', 'NaiveProxy', 'Shadow_TLS']:
                lines += [f'# CONFIG_PACKAGE_{proxy}_INCLUDE_{feature} is not set']
    # Preserve last assignment and avoid duplicate configuration requests.
    result = {}
    for line in lines:
        key = line.split('=', 1)[0] if line.startswith('CONFIG_') else line.split()[1] if line.startswith('# CONFIG_') else line
        result[key] = line
    return list(result.values())


def install_source(source, raw, uid):
    names = selection(raw)
    records = []
    for name in names:
        ref = options()[name].get('source')
        if not ref:
            continue
        checkout = source.parent / 'custom-plugin-sources' / name
        if not checkout.exists():
            checkout.mkdir(parents=True)
            subprocess.run(['git', 'init', str(checkout)], check=True)
            subprocess.run(['git', '-C', str(checkout), 'fetch', '--depth', '1', ref['url'], ref['commit']], check=True)
            subprocess.run(['git', '-C', str(checkout), 'checkout', '--detach', 'FETCH_HEAD'], check=True)
        actual = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != ref['commit']:
            raise ValueError('Custom plugin source commit mismatch')
        destination = source / 'package/xzt8wrt-custom' / name
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(checkout / ref['directory'], destination)
        records.append({'package': name, **ref})
    metadata = {'schema': 1, 'device': uid, 'plugins': names, 'packages': packages(names),
                'signature': identity(uid, names), 'method': 'source', 'external_sources': records}
    (source / 'custom-build.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')


def custom_defaults(directory):
    path = directory / 'etc/uci-defaults/98-xzt8wrt-custom'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('#!/bin/sh\nfor service in passwall passwall2 shadowsocksr; do\n [ ! -x /etc/init.d/$service ] || /etc/init.d/$service disable\ndone\nexit 0\n')
    path.chmod(0o755)


if __name__ == '__main__':
    import sys
    install_source(pathlib.Path(sys.argv[1]), os.environ.get('CUSTOM_PLUGINS', ''), os.environ['CUSTOM_DEVICE'])


def release_allowed(uid):
    return any(d['uid'] == uid for d in json.loads((ROOT / 'docs/release-devices.json').read_text())['devices'])
