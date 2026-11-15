"""Convert verified x86 disk images without rebuilding or altering firmware."""
import gzip
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import zipfile


def convert(input_dir, output):
    output.mkdir(parents=True, exist_ok=True)
    count = 0
    for manifest in input_dir.rglob('profiles.json'):
        metadata = json.loads(manifest.read_text())
        if metadata.get('target') != 'x86/64':
            continue
        directory = manifest.parent
        source = json.loads((directory / 'source.json').read_text())
        custom = json.loads((directory / 'custom-build.json').read_text()) if (directory / 'custom-build.json').is_file() else None
        flavor = 'custom-' + custom['signature'] if custom else directory.name.rsplit('-', 1)[-1]
        if not custom and flavor not in ('full', 'lite'):
            raise ValueError('Unknown x86 firmware profile')
        images = [i for i in metadata['profiles']['generic']['images']
                  if i['type'] in ('combined', 'combined-efi') and i['name'].endswith('.img.gz')]
        if {i['type'] for i in images} != {'combined', 'combined-efi'}:
            raise ValueError('Both BIOS and EFI source images are required')
        with tempfile.TemporaryDirectory() as temporary:
            temp = pathlib.Path(temporary)
            raw_images = []
            for item in images:
                image = (directory / item['name']).resolve()
                if not image.is_relative_to(directory.resolve()) or hashlib.sha256(image.read_bytes()).hexdigest() != item['sha256']:
                    raise ValueError('Invalid source IMG checksum or path')
                raw = temp / image.name[:-3]
                with gzip.open(image, 'rb') as compressed, raw.open('wb') as uncompressed:
                    shutil.copyfileobj(compressed, uncompressed)
                raw_images.append((item, raw))
            for fmt in ('img', 'qcow2', 'vmdk', 'vdi', 'vhdx'):
                for original, raw in raw_images:
                    boot = 'uefi' if original['type'] == 'combined-efi' else 'bios'
                    filesystem = original.get('filesystem') or ('squashfs' if 'squashfs' in original['name'] else 'ext4')
                    label = {'full': '高大全版', 'lite': '精简版'}.get(flavor, flavor)
                    filename = f"xzt8wrt-{source['version']}-x86-generic-{label}-{fmt}-{boot}-{filesystem}.zip"
                    destination = temp / (raw.stem + '.' + fmt)
                    if fmt == 'img':
                        destination = directory / original['name']
                    else:
                        args = ['qemu-img', 'convert', '-f', 'raw', '-O', fmt]
                        if fmt == 'vmdk':
                            args += ['-o', 'subformat=streamOptimized']
                        subprocess.run([*args, str(raw), str(destination)], check=True)
                        subprocess.run(['qemu-img', 'compare', '-f', 'raw', '-F', fmt, str(raw), str(destination)], check=True)
                    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
                    with zipfile.ZipFile(output / filename, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                        archive.write(destination, destination.name)
                        for name in ('source.json', '.config', 'requested.config', 'kernel-version.json', 'kernel-source.json',
                                     'source-patches.diff', 'legacy-build-metadata.json', 'custom-build.json'):
                            if (directory / name).is_file():
                                archive.write(directory / name, name)
                        archive.writestr('SHA256SUMS', digest + '  ' + destination.name + '\n')
                        archive.writestr('使用说明.txt', f'此包仅包含 {fmt.upper()} / {boot.upper()} / {filesystem} 镜像。\nIMG 用于物理机写盘；QCOW2 用于 PVE/KVM；VMDK 用于 VMware；VDI 用于 VirtualBox；VHDX 用于 Hyper-V。\n请按启动方式和文件系统选择，不需要下载其他类型。\n')
                    if fmt != 'img':
                        destination.unlink()
                    count += 1
            # Replace the old combined download only after every separate image succeeds.
            for ending in ('', '-qcow2', '-vmdk', '-vdi', '-vhdx'):
                for old_label in (flavor, {'full': '高大全版', 'lite': '精简版'}.get(flavor, flavor)):
                    (output / f"xzt8wrt-{source['version']}-x86-generic-{old_label}{ending}.zip").unlink(missing_ok=True)
    if count:
        (output / 'SHA256SUMS').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name for p in sorted(output.glob('*.zip'))) + '\n')
    print(f'Generated {count} verified virtual disk download bundles')


if __name__ == '__main__':
    convert(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]))
