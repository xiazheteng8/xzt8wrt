#!/bin/sh
# Only initialize the stock, empty SmartDNS configuration. Preserve user setups.
[ -x /etc/init.d/smartdns ] || exit 0
uci -q get dhcp.@dnsmasq[0] >/dev/null || exit 0
case " $(uci -q get dhcp.@dnsmasq[0].addnhosts) " in
 *' /tmp/xzt8wrt.hosts '*) ;;
 *) uci add_list dhcp.@dnsmasq[0].addnhosts='/tmp/xzt8wrt.hosts';uci commit dhcp;;
esac
/usr/sbin/xzt8wrt-network-runtime >/dev/null 2>&1
[ "$(uci -q get smartdns.@smartdns[0].enabled)" != 1 ] || /etc/init.d/smartdns enable
[ -z "$(uci -q show smartdns | grep '=server$')" ] || exit 0
[ "$(uci -q get smartdns.@smartdns[0].enabled)" != 1 ] || exit 0
uci -q get smartdns.@smartdns[0] >/dev/null || uci add smartdns smartdns >/dev/null
uci set smartdns.@smartdns[0].enabled='1'
uci set smartdns.@smartdns[0].port='6053'
uci set smartdns.@smartdns[0].bind_device='1'
uci set smartdns.@smartdns[0].bind_device_name='lo'
uci set smartdns.@smartdns[0].ipv6_server='0'
uci set smartdns.@smartdns[0].tcp_server='1'
uci set smartdns.@smartdns[0].auto_set_dnsmasq='0'
uci set smartdns.@smartdns[0].cache_size='1024'
uci set smartdns.@smartdns[0].prefetch_domain='1'
uci set smartdns.@smartdns[0].serve_expired='1'
uci set smartdns.@smartdns[0].speed_check_mode='ping,tcp:443'
uci set smartdns.xzt_up1=server
uci set smartdns.xzt_up1.enabled='1'
uci set smartdns.xzt_up1.type='udp'
uci set smartdns.xzt_up1.ip='223.5.5.5'
uci set smartdns.xzt_up2=server
uci set smartdns.xzt_up2.enabled='1'
uci set smartdns.xzt_up2.type='udp'
uci set smartdns.xzt_up2.ip='119.29.29.29'
uci commit smartdns
# Keep port 53 and DHCP on dnsmasq; never turn off its rebind protection.
uci -q delete dhcp.@dnsmasq[0].server
uci add_list dhcp.@dnsmasq[0].server='127.0.0.1#6053'
uci add_list dhcp.@dnsmasq[0].server='223.5.5.5'
uci add_list dhcp.@dnsmasq[0].server='119.29.29.29'
uci set dhcp.@dnsmasq[0].noresolv='1'
uci set dhcp.@dnsmasq[0].strictorder='1'
uci commit dhcp
/etc/init.d/smartdns enable
/etc/init.d/smartdns start >/dev/null 2>&1
/etc/init.d/dnsmasq reload >/dev/null 2>&1
exit 0
