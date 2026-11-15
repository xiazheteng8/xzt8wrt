"""Read successful kernel baselines across independently published releases."""
import json
import os
import pathlib
import subprocess
import tempfile
import sys
import re
import hashlib
import base64
import datetime
import time

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
    pages = json.loads(subprocess.check_output([
        'gh', 'api', '--paginate', '--slurp', f'repos/{repo}/releases'
    ]))
    releases = sorted([r for page in pages for r in page], key=lambda r:r['published_at'] or '', reverse=True)
    tags = [r['tag_name'] for r in releases if not r['draft'] and not r['prerelease']
            and any(a['name'] == 'kernel-state.json' for a in r['assets'])]
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


def kernel_tag(state, scope=''):
    fingerprints = sorted({value['fingerprint'] for value in state.values()})
    if not fingerprints or any(not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-r[0-9]+', f) for f in fingerprints):
        raise ValueError('Missing or invalid compiled kernel fingerprint')
    if not scope:
        platforms = sorted({key.rsplit('/', 1)[0] for key in state})
        profiles = sorted({key.rsplit('/', 1)[1] for key in state})
        scope = '-'.join(platforms + profiles)
    if not re.fullmatch(r'[a-zA-Z0-9_.-]+', scope):
        scope = 'custom-' + hashlib.sha256(scope.encode()).hexdigest()[:12]
    return '_'.join(fingerprints) + '-' + scope


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


def update_download_index():
    repo = os.environ['GH_REPO']
    for attempt in range(3):
        pages = json.loads(subprocess.check_output(['gh','api','--paginate','--slurp',f'repos/{repo}/releases']))
        records = []
        for r in sorted([r for page in pages for r in page],key=lambda r:r['published_at'] or '',reverse=True):
            if r['draft'] or r['prerelease'] or not any(a['name']=='kernel-state.json' for a in r['assets']):
                continue
            records.append({k:r[k] for k in ('tag_name','name','published_at','html_url')} | {
                'assets':[{k:a.get(k) for k in ('name','size','browser_download_url','digest')} for a in r['assets']]})
            if len(records)>=50:break
        body={'schema':1,'repository':repo,'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'releases':records}
        path=f'repos/{repo}/contents/docs/downloads.json'
        current=subprocess.run(['gh','api',path],capture_output=True,text=True)
        payload={'message':'更新已完成固件下载索引','branch':'main','content':base64.b64encode((json.dumps(body,ensure_ascii=False,indent=2)+'\n').encode()).decode()}
        if current.returncode==0:payload['sha']=json.loads(current.stdout)['sha']
        elif '404' not in current.stderr:raise RuntimeError(current.stderr)
        result=subprocess.run(['gh','api',path,'--method','PUT','--input','-'],input=json.dumps(payload),capture_output=True,text=True)
        if result.returncode==0:
            print('Published static download index for '+repo)
            return
        if attempt==2:raise RuntimeError(result.stderr)
        time.sleep(2)


if __name__ == '__main__':
    if len(sys.argv) == 1 or sys.argv[1] == 'baseline':
        print(json.dumps(baseline()))
    elif sys.argv[1] == 'index':
        update_download_index()
    elif sys.argv[1] == 'tag':
        print(kernel_tag(json.loads(pathlib.Path(sys.argv[2]).read_text()), sys.argv[3] if len(sys.argv) > 3 else ''))
    elif sys.argv[1] == 'legacy':
        print(prepare_legacy(pathlib.Path(sys.argv[2]), sys.argv[3]))
    else:
        raise ValueError('Unknown command')
