#!/bin/sh
# Keep IPv4 traffic on the configured single-LAN gateway instead of issuing redirects.
set -eu
printf '1\n' > /proc/sys/net/ipv4/ip_forward
for item in /proc/sys/net/ipv4/conf/*/send_redirects /proc/sys/net/ipv4/conf/*/accept_redirects; do
 [ ! -f "$item" ] || printf '0\n' > "$item"
done
