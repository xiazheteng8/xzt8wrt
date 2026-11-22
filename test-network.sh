#!/usr/bin/env bash
# All addresses, switches and services exist only inside temporary Linux namespaces.
set -euo pipefail
[[ "$(uname -s)" == Linux && "$EUID" == 0 ]] || { echo 'Run as root on a Linux CI runner'; exit 2; }
ROOT="$(cd "$(dirname "$0")" && pwd)"
SMARTDNS="$(realpath "${1:?SmartDNS binary required}")"
fixture="$(mktemp -d)"; prefix="xzt$$"
c="$prefix-c"; r="$prefix-r"; u="$prefix-u"; sw="$prefix-sw"
cleanup(){
 for ns in "$c" "$r" "$u" "$sw"; do
  ip netns pids "$ns" 2>/dev/null | xargs -r kill 2>/dev/null || true
  ip netns del "$ns" 2>/dev/null || true
 done
 rm -rf "$fixture"
}
trap cleanup EXIT
for ns in "$c" "$r" "$u" "$sw"; do ip netns add "$ns";ip -n "$ns" link set lo up;done
ip -n "$sw" link add br0 type bridge;ip -n "$sw" link set br0 up
for pair in "c:$c:100" "r:$r:2" "u:$u:1"; do
 IFS=: read -r label ns octet <<< "$pair"
 ip -n "$ns" link add lan type veth peer name "${label}-sw"
 ip -n "$ns" link set "${label}-sw" netns "$sw"
 ip -n "$sw" link set "${label}-sw" master br0
 ip -n "$sw" link set "${label}-sw" up
 ip -n "$ns" addr add "192.168.11.$octet/24" dev lan
 ip -n "$ns" link set lan up
done
ip -n "$c" route add default via 192.168.11.2
ip -n "$r" route add default via 192.168.11.1
ip -n "$u" link add internet type dummy;ip -n "$u" link set internet up
ip -n "$u" addr add 198.18.0.1/32 dev internet
ip netns exec "$r" sh "$ROOT/network-policy.sh"
[[ "$(ip netns exec "$r" cat /proc/sys/net/ipv4/conf/lan/send_redirects)" == 0 ]]
[[ "$(ip -n "$r" -o link show | wc -l)" == 2 ]] # lo + a single physical/virtual LAN
ip netns exec "$r" nft -f - <<'NFT'
table inet xzt_test {
 chain forward { type filter hook forward priority 0; policy drop;
  ct state established,related accept
  iifname "lan" oifname "lan" ip saddr 192.168.11.0/24 accept
 }
}
table ip xzt_nat {
 chain postrouting { type nat hook postrouting priority srcnat; policy accept;
  oifname "lan" ip saddr 192.168.11.0/24 masquerade
 }
}
NFT
ip netns exec "$u" nft -f - <<'NFT'
table ip observed {
 counter forwarded {}
 chain input { type filter hook input priority 0; policy accept;
  ip saddr 192.168.11.2 ip daddr 198.18.0.1 tcp dport 8080 counter name forwarded
 }
}
NFT
mkdir "$fixture/www";echo network-ok > "$fixture/www/index.html"
ip netns exec "$u" python3 -m http.server 8080 --bind 198.18.0.1 --directory "$fixture/www" > "$fixture/http.log" 2>&1 &
ip netns exec "$u" dnsmasq -k --conf-file= --port=5353 --listen-address=198.18.0.1 --bind-interfaces --no-hosts --no-resolv --address=/example.test/198.18.0.1 --address=/fallback.test/198.18.0.1 --pid-file="$fixture/up.pid" > "$fixture/up.log" 2>&1 &
ip netns exec "$u" dnsmasq -k --conf-file= --port=5354 --listen-address=198.18.0.1 --bind-interfaces --no-hosts --no-resolv --address=/example.test/198.18.0.2 --address=/fallback.test/198.18.0.1 --pid-file="$fixture/backup.pid" > "$fixture/backup.log" 2>&1 &
cat > "$fixture/smart.conf" <<EOF
bind 127.0.0.1:6053
server 198.18.0.1:5353
cache-size 0
log-file $fixture/smart.log
EOF
ip netns exec "$r" "$SMARTDNS" -f -c "$fixture/smart.conf" -p "$fixture/smart.pid" > "$fixture/smart.stdout" 2>&1 &
smart_pid=$!
printf '192.168.11.2 xzt8.wrt\n' > "$fixture/hosts"
ip netns exec "$r" dnsmasq -k --conf-file= --port=53 --listen-address=192.168.11.2,127.0.0.1 --bind-interfaces --no-hosts --no-resolv --strict-order --server=127.0.0.1#6053 --server=198.18.0.1#5354 --addn-hosts="$fixture/hosts" --pid-file="$fixture/dns.pid" > "$fixture/dns.log" 2>&1 &
dns_pid=$!
for attempt in {1..30}; do
 if ip netns exec "$c" curl -fsS --max-time 1 http://198.18.0.1:8080/ > "$fixture/result"; then break;fi
 sleep 1
done
[[ "$(cat "$fixture/result")" == network-ok ]]
ip netns exec "$r" ping -c 2 -W 2 198.18.0.1
ip netns exec "$c" ping -c 2 -W 2 198.18.0.1
ip -n "$c" route get 198.18.0.1 | grep -q 'via 192.168.11.2'
ip netns exec "$u" nft -j list counter ip observed forwarded | python3 -c 'import json,sys; assert any(v.get("counter",{}).get("packets",0)>0 for v in json.load(sys.stdin)["nftables"])'
[[ "$(ip netns exec "$c" dig +short +time=3 +tries=1 @192.168.11.2 xzt8.wrt A | tail -1)" == 192.168.11.2 ]]
[[ "$(ip netns exec "$r" dig +short +time=3 +tries=1 @127.0.0.1 -p 6053 example.test A | tail -1)" == 198.18.0.1 ]]
[[ "$(ip netns exec "$c" dig +short +time=3 +tries=1 @192.168.11.2 example.test A | tail -1)" == 198.18.0.1 ]]
# An address change must refresh the local name, without a permanent old-IP record.
printf '192.168.11.3 xzt8.wrt\n' > "$fixture/hosts";kill -HUP "$dns_pid";sleep 1
[[ "$(ip netns exec "$c" dig +short +time=3 +tries=1 @192.168.11.2 xzt8.wrt A | tail -1)" == 192.168.11.3 ]]
kill "$smart_pid";wait "$smart_pid" || true
[[ "$(ip netns exec "$c" dig +short +time=3 +tries=1 @192.168.11.2 fallback.test A | tail -1)" == 198.18.0.1 ]]
echo 'Single-LAN client routing, return-path NAT, no redirects, DNS alias refresh, SmartDNS and fallback passed'
