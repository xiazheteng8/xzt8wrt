"""Versioned, local ARM adaptations applied to the official stable source tree."""
import hashlib
import json
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent / 'devices'


def definition(target):
    manifest = json.loads((ROOT / 'targets.json').read_text())
    if manifest.get('schema') != 1 or target not in manifest['targets']:
        raise ValueError('No reviewed ARM adaptation target: ' + target)
    return manifest['targets'][target]


def local_file(relative, digest):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise ValueError('Adaptation file must be inside devices/: ' + relative)
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError('Adaptation SHA256 mismatch: ' + relative)
    return path


def prepare(source, target, version, devices):
    config = definition(target)
    tree = source / config['upstream_tree']
    if not tree.is_dir():
        raise ValueError('Official ARM driver tree is missing: ' + str(tree))
    report = {'target': target, 'source_version': version, 'devices': devices,
              'driver_source': config['driver_source'], 'upstream_tree': config['upstream_tree'],
              'manifest_sha256': hashlib.sha256((ROOT / 'targets.json').read_bytes()).hexdigest(),
              'applied': []}
    # Validate every entry before modifying anything. Device-specific entries are
    # refused in a batch so one model's partition/DTS changes cannot affect peers.
    entries = []
    for kind in ('patches', 'overlays'):
        for entry in config[kind]:
            device = entry.get('device')
            if device and device not in devices:
                continue
            if device and devices != [device]:
                raise ValueError('Device-specific adaptation requires custom single-device build')
            if version not in entry['versions']:
                raise ValueError('Adaptation not reviewed for stable version ' + version)
            path = local_file(entry['path'], entry['sha256'])
            destination = None
            if kind == 'overlays':
                destination = (source / entry['destination']).resolve()
                if not destination.is_relative_to(source.resolve()):
                    raise ValueError('Overlay destination escapes source directory')
                allowed = [source / config['upstream_tree'], source / 'target/linux/generic',
                           source / 'package/boot']
                if not any(destination.is_relative_to(p.resolve()) for p in allowed):
                    raise ValueError('Overlay must target ARM drivers or boot files')
            else:
                stats = subprocess.check_output(['git', '-C', str(source), 'apply', '--numstat', str(path)], text=True)
                allowed = (config['upstream_tree'] + '/', 'target/linux/generic/', 'package/boot/')
                for line in stats.splitlines():
                    filename = line.split('\t', 2)[-1]
                    if not filename.startswith(allowed) or '..' in pathlib.PurePosixPath(filename).parts:
                        raise ValueError('Patch modifies files outside the selected ARM driver/boot tree')
            entries.append((kind, entry, path, destination))
    for kind, entry, path, destination in entries:
        if kind == 'patches':
            subprocess.run(['git', '-C', str(source), 'apply', '--check', str(path)], check=True)
            subprocess.run(['git', '-C', str(source), 'apply', str(path)], check=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        report['applied'].append({'kind': kind, **entry})
    diff = subprocess.check_output(['git', '-C', str(source), 'diff', '--binary', '--',
                                    'target/linux', 'package/boot'])
    (source / 'arm-adaptation.diff').write_bytes(diff)
    (source / 'arm-adaptation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(f'ARM adaptation: {target}, official stable driver tree; {len(entries)} local changes')
