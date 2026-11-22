#!/usr/bin/env bash
# Only newly-created temporary loop disks are modified by this integration test.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
fixture="$(mktemp -d)"
loopdev=''
cleanup() {
  mountpoint -q "$fixture/root" && sudo umount "$fixture/root" || true
  [[ -z "$loopdev" ]] || sudo losetup -d "$loopdev"
  rm -rf "$fixture"
}
trap cleanup EXIT
mkdir "$fixture/root"
printf '{"platform": "x86"}\n' > "$fixture/meta.json"
for scenario in expand preserve; do
  truncate -s 256M "$fixture/disk.img"
  sudo parted -s "$fixture/disk.img" mklabel gpt mkpart boot fat32 1MiB 17MiB mkpart root ext4 17MiB 81MiB
  if [[ "$scenario" == preserve ]]; then
    sudo parted -s "$fixture/disk.img" mkpart data ext4 81MiB 129MiB
  fi
  loopdev="$(sudo losetup -f --show -P "$fixture/disk.img")"
  part="${loopdev}p2"
  sudo mkfs.ext4 -q -F "$part"
  sudo mount "$part" "$fixture/root"
  printf 'xzt8wrt-sentinel\n' | sudo tee "$fixture/root/sentinel" >/dev/null
  before="$(sudo blockdev --getsz "$part")"
  initial_start="$(cat "/sys/class/block/${part##*/}/start")"
  major_hex="$(stat -c %t "$part")";minor_hex="$(stat -c %T "$part")"
  majmin="$(printf '%d:%d' "0x$major_hex" "0x$minor_hex")"
  printf '36 25 %s / / rw - ext4 %s rw\n' "$majmin" "$part" > "$fixture/mountinfo"
  sudo env XZT_TEST_MODE=1 XZT_TEST_METADATA="$fixture/meta.json" XZT_TEST_MOUNTINFO="$fixture/mountinfo" sh "$ROOT/expand-root.sh"
  after="$(sudo blockdev --getsz "$part")"
  [[ "$(cat "/sys/class/block/${part##*/}/start")" == "$initial_start" ]]
  [[ "$(cat "$fixture/root/sentinel")" == xzt8wrt-sentinel ]]
  if [[ "$scenario" == expand ]]; then
    [[ "$after" -gt "$before" ]]
    [[ "$(df -B1 --output=size "$fixture/root" | tail -1)" -gt 200000000 ]]
    # Running again must preserve data and partition geometry.
    sudo env XZT_TEST_MODE=1 XZT_TEST_METADATA="$fixture/meta.json" XZT_TEST_MOUNTINFO="$fixture/mountinfo" sh "$ROOT/expand-root.sh"
    [[ "$(sudo blockdev --getsz "$part")" == "$after" ]]
  else
    [[ "$after" == "$before" ]]
    sudo parted -ms "$loopdev" print | awk -F: '$1==3 {found=1} END{exit !found}'
  fi
  echo "Storage scenario passed: $scenario"
  sudo umount "$fixture/root"
  sudo losetup -d "$loopdev"; loopdev=''
  rm "$fixture/disk.img"
done
