"""Read successful kernel baselines across independently published releases."""
import json
import os
import pathlib
import subprocess
import tempfile

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


if __name__ == '__main__':
    print(json.dumps(baseline()))
