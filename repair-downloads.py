"""Republish verified split images whose Unicode asset names GitHub sanitized."""
import concurrent.futures
import hashlib
import json
import os
import pathlib
import re
import subprocess
import tempfile
import aggregate

repo = os.environ['GH_REPO']
tags = os.environ['SOURCE_TAGS'].split(',')
if not all(re.fullmatch(r'[A-Za-z0-9._-]+', tag) for tag in tags):
    raise ValueError('Invalid release tags')
devices = json.loads(pathlib.Path('docs/release-devices.json').read_text())['devices']
output = pathlib.Path('release-output'); output.mkdir()
state = {}; downloads = []
with tempfile.TemporaryDirectory() as temporary:
    for number, tag in enumerate(tags):
        directory = pathlib.Path(temporary) / str(number); directory.mkdir()
        release = aggregate.api(f'repos/{repo}/releases/tags/{tag}')
        subprocess.run(['gh','release','download',tag,'--repo',repo,'--pattern','SHA256SUMS','--pattern','kernel-state.json','--dir',str(directory)],check=True)
        sums = {}
        for line in (directory/'SHA256SUMS').read_text().splitlines():
            digest, name = line.split(None,1); sums[digest] = name.strip().lstrip('*')
        baseline = json.loads((directory/'kernel-state.json').read_text())
        groups = {}
        for asset in release['assets']:
            if not asset['name'].endswith('.zip'): continue
            digest = (asset.get('digest') or '').removeprefix('sha256:')
            original = sums.get(digest)
            if not original: raise ValueError('Missing checksum mapping: '+asset['name'])
            name = original.replace('高大全版','full').replace('精简版','lite')
            if pathlib.Path(name).name != name: raise ValueError('Invalid filename')
            key = aggregate.key_for_asset(name,devices)
            if not key or key not in baseline: continue
            if key.startswith('x86/') and not re.search(r'-(img|qcow2|vmdk|vdi|vhdx)-(bios|uefi)-(ext4|squashfs)\.zip$',name): continue
            groups.setdefault(key,[]).append((tag,asset['name'],name,digest))
        for key, assets in groups.items():
            if key not in state:
                state[key] = baseline[key]; downloads.extend(assets)
    def download(item):
        tag, remote, name, digest = item
        with tempfile.TemporaryDirectory() as folder:
            subprocess.run(['gh','release','download',tag,'--repo',repo,'--pattern',remote,'--dir',folder],check=True)
            path = pathlib.Path(folder)/remote
            if hashlib.sha256(path.read_bytes()).hexdigest()!=digest: raise ValueError('Checksum mismatch')
            path.replace(output/name)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(download,downloads))
(output/'kernel-state.json').write_text(json.dumps(state))
aggregate.publish(output)
