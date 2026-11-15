"""Read successful kernel baselines across independently published releases."""
import json
import os
import pathlib
import subprocess
import tempfile
import sys

SCHEDULED_KEYS = {'x86/full', 'x86/lite', 'rockchip/full', 'rockchip/lite', 'filogic/lite'}


def merge_newest_first(states):
    result = {}
    for state in states:
        for key, value in state.items():
            result.setdefault(key, value)
    return result


def baseline():
    repo = os.environ['GH_REPO']
    # GitHub returns releases newest first. Older releases may contain a combined
    # baseline; new releases contain only the job that actually succeeded.
    tags = subprocess.check_output([
        'gh', 'api', '--paginate', f'repos/{repo}/releases', '--jq',
        '.[] | select(.draft == false and .prerelease == false and any(.assets[]; .name == "kernel-state.json")) | .tag_name'
    ], text=True).splitlines()
    result = {}
    for tag in tags:
        with tempfile.TemporaryDirectory() as temporary:
            subprocess.run(['gh', 'release', 'download', tag, '--repo', repo,
                            '--pattern', 'kernel-state.json', '--dir', temporary], check=True)
            state = json.loads((pathlib.Path(temporary) / 'kernel-state.json').read_text())
        result = merge_newest_first([result, state])
        if SCHEDULED_KEYS <= result.keys():
            break
    return result


def prepare_legacy(input_dir, run_id):
    """Recover only metadata absent from earlier successful build artifacts."""
    count = 0
    for directory in sorted(input_dir.iterdir()):
        manifest = directory / 'profiles.json'
        if not directory.is_dir() or not manifest.is_file():
            continue
        metadata = json.loads(manifest.read_text())
        kernel = metadata['linux_kernel']
        recovered = []
        path = directory / 'kernel-source.json'
        if not path.exists():
            # Use the kernel actually compiled, not today's upstream release.
            value = {'version': str(kernel['version']), 'release': str(kernel['release']),
                     'fingerprint': str(kernel['version']) + '-r' + str(kernel['release'])}
            path.write_text(json.dumps(value, indent=2) + '\n')
            recovered.append(path.name)
        path = directory / 'source-patches.diff'
        if not path.exists():
            path.write_text('# Legacy build did not record source patches. See legacy-build-metadata.json.\n')
            recovered.append(path.name)
        if recovered:
            (directory / 'legacy-build-metadata.json').write_text(json.dumps({
                'source_run': run_id, 'artifact': directory.name, 'recovered_fields': recovered,
                'note': 'Kernel identity recovered from compiled profiles.json; original patch diff unavailable.'
            }, indent=2) + '\n')
        count += 1
    if not count:
        raise ValueError('No successful firmware artifacts found')
    return count


if __name__ == '__main__':
    if len(sys.argv) == 1 or sys.argv[1] == 'baseline':
        print(json.dumps(baseline()))
    elif sys.argv[1] == 'legacy':
        print(prepare_legacy(pathlib.Path(sys.argv[2]), sys.argv[3]))
    else:
        raise ValueError('Unknown command')
