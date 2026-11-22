#!/bin/sh
# Grow only a directly-mounted ext4 root, on the last partition of its boot disk.
# Never format disks, delete partitions, move their start, or touch SquashFS/ARM flash.
set -eu
meta=/etc/xzt8wrt-build.json
mountinfo=/proc/self/mountinfo
# Integration tests may substitute metadata and mountinfo, but only target loop devices.
if [ "${XZT_TEST_MODE:-0}" = 1 ]; then
 meta="${XZT_TEST_METADATA:?}"
 mountinfo="${XZT_TEST_MOUNTINFO:?}"
fi
[ -f "$meta" ] || exit 0
grep -q '"platform": "x86"' "$meta" || exit 0
mm="$(awk '$5=="/" { for(i=6;i<=NF;i++) if($i=="-" && $(i+1)=="ext4") { print $3; exit } }' "$mountinfo")"
[ -n "$mm" ] || exit 0
partpath="$(readlink -f "/sys/dev/block/$mm")"
[ -f "$partpath/partition" ] || exit 0
number="$(cat "$partpath/partition")"
diskpath="${partpath%/*}"
disk="${diskpath##*/}"
part="${partpath##*/}"
case "$disk" in loop[0-9]*) [ "${XZT_TEST_MODE:-0}" = 1 ] || exit 0 ;; sd[a-z]*|vd[a-z]*|xvd[a-z]*|nvme[0-9]*n[0-9]*|mmcblk[0-9]*) ;; *) exit 0;; esac
if [ "${XZT_TEST_MODE:-0}" = 1 ]; then
 case "$disk" in loop[0-9]*) ;; *) exit 1;; esac
fi
[ -b "/dev/$disk" ] && [ -b "/dev/$part" ] || exit 0
[ "$(blkid -s TYPE -o value "/dev/$part")" = ext4 ] || exit 0
start="$(cat "$partpath/start")"
# Any partition starting after root means this is not a simple whole-disk installation.
for sibling in "$diskpath"/*/partition; do
 [ -f "$sibling" ] || continue
 other="${sibling%/partition}"
 [ "$(cat "$other/start")" -le "$start" ] || { logger -t xzt8wrt '根分区之后还有其他分区，跳过自动扩容'; exit 0; }
done
size="$(cat "$partpath/size")"
total="$(cat "$diskpath/size")"
if [ "$((total-start-size))" -gt 262144 ]; then
 logger -t xzt8wrt "扩展启动盘最后的 ext4 根分区：/dev/$part"
 # --fix repairs the backup GPT after a virtual disk has been enlarged.
 parted --fix --script "/dev/$disk" resizepart "$number" 100% || { logger -t xzt8wrt '分区扩容未完成，保留现状，请在磁盘管理中检查'; exit 0; }
 partprobe "/dev/$disk" 2>/dev/null || true
fi
# Online ext4 growth is safe when the kernel has accepted the larger partition.
# If the kernel still holds the old size, a later normal reboot retries this step.
resize2fs "/dev/$part" || { logger -t xzt8wrt '根文件系统扩容暂未完成，正常重启后会重试'; exit 0; }
logger -t xzt8wrt 'ext4 根分区检查完成；Docker 与根目录共享可用容量'
