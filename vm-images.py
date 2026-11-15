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
            for fmt in ('qcow2', 'vmdk', 'vdi', 'vhdx'):
                filename = f"xzt8wrt-{source['version']}-x86-generic-{flavor}-{fmt}.zip"
                generated = []
                with zipfile.ZipFile(output / filename, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                    for original, raw in raw_images:
                        destination = temp / (raw.stem + '.' + fmt)
                        args = ['qemu-img', 'convert', '-f', 'raw', '-O', fmt]
                        if fmt == 'vmdk':
                            args += ['-o', 'subformat=streamOptimized']
                        subprocess.run([*args, str(raw), str(destination)], check=True)
                        subprocess.run(['qemu-img', 'compare', '-f', 'raw', '-F', fmt, str(raw), str(destination)], check=True)
                        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
                        generated.append({'name': destination.name, 'format': fmt, 'sha256': digest,
                                          'source_name': original['name'], 'source_sha256': original['sha256'], 'boot': original['type']})
                        archive.write(destination, destination.name)
                        destination.unlink()
                    for name in ('source.json', '.config', 'requested.config', 'kernel-version.json', 'kernel-source.json',
                                 'source-patches.diff', 'legacy-build-metadata.json', 'custom-build.json'):
                        if (directory / name).is_file():
                            archive.write(directory / name, name)
                    archive.writestr('vm-images.json', json.dumps(generated, indent=2))
                    archive.writestr('SHA256SUMS', '\n'.join(i['sha256'] + '  ' + i['name'] for i in generated) + '\n')
                    archive.writestr('使用说明.txt', '由已通过校验的 x86 IMG 转换，qemu-img compare 验证虚拟磁盘内容一致；没有改动固件。\n按 BIOS/EFI 选择镜像，关闭虚拟机 Secure Boot，并按平台配置兼容网卡。虚拟机启动、网卡和接口划分仍需验证。\nQCOW2: PVE/KVM；VMDK: VMware；VDI: VirtualBox；VHDX: Hyper-V。\n')
                count += 1
    if count:
        (output / 'SHA256SUMS').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name for p in sorted(output.glob('*.zip'))) + '\n')
    print(f'Generated {count} verified virtual disk download bundles')


if __name__ == '__main__':
    convert(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]))
