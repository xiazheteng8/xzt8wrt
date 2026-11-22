#!/bin/sh
# Refresh the local administration name without committing UCI during apply/rollback.
/usr/sbin/xzt8wrt-network-policy
address="$(uci -q get network.lan.ipaddr | awk '{split($1,a,"/");print a[1]}')"
if ! printf '%s\n' "$address" | grep -Eq '^([0-9]{1,3}\.){3}[0-9]{1,3}$'; then
 exit 0
fi
hostfile=/tmp/xzt8wrt.hosts
record="$address xzt8.wrt"
[ "$(cat "$hostfile" 2>/dev/null)" != "$record" ] || exit 0
# In-place update preserves the inode mounted into dnsmasq's service jail.
printf '%s\n' "$record" > "$hostfile"
[ ! -x /etc/init.d/dnsmasq ] || /etc/init.d/dnsmasq reload >/dev/null 2>&1
