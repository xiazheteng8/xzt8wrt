"""Install branding, default LAN address, and the authenticated LuCI setup wizard."""
import argparse
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
ART = '               __  ____                __ \n   _  ______  / /_( __ )_      _______/ /_\n  | |/_/_  / / __/ __  | | /| / / ___/ __/\n _>  <  / /_/ /_/ /_/ /| |/ |/ / /  / /_  \n/_/|_| /___/\\__/\\____/ |__/|__/_/   \\__/\n'

def banner(version, platform, profile):
    label = {'full':'高大全版','lite':'精简版'}.get(profile,profile)
    return '\n' + '\n'.join(line.rstrip() for line in ART.splitlines()) + '\n' + '\n           BE FREE AND UNAFRAID\n' + ' ' + '-'*57 + '\n xzt8wrt / ImmortalWrt ' + version + ' / ' + label + '\n 平台：' + platform + ' · 默认 IP：192.168.11.1\n 首次登录：LuCI → 设置向导（已有配置以实际地址为准）\n' + ' ' + '-'*57 + '\n'

def install(output, version, platform, profile):
    def put(name, content, mode=0o644):
        path = output / name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(content)
        path.chmod(mode)
    put('etc/banner',banner(version,platform,profile))
    put('etc/xzt8wrt-build.json',json.dumps({'version':version,'platform':platform,'profile':profile,'wizard':2,'features':['single-lan-v2','smartdns-defaults-v1','admin-domain-v1'] + (['ext4-grow-v1'] if platform == 'x86' else [])},ensure_ascii=False,indent=2)+'\n')
    put('www/luci-static/resources/view/xzt8wrt/setup.js',(ROOT/'setup-wizard.js').read_text())
    put('www/index.html', '<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=/cgi-bin/luci/admin/setup"><title>xzt8wrt 设置向导</title></head><body><a href="/cgi-bin/luci/admin/setup">打开 xzt8wrt 设置向导</a></body></html>')
    menu={'admin/setup':{'title':'设置向导','order':1,'action':{'type':'view','path':'xzt8wrt/setup'},'depends':{'acl':['luci-app-xzt8wrt-setup']}}}
    put('usr/share/luci/menu.d/luci-app-xzt8wrt-setup.json',json.dumps(menu,ensure_ascii=False,indent=2))
    acl={'luci-app-xzt8wrt-setup':{'description':'xzt8wrt 网络设置向导','read':{'uci':['network','dhcp','firewall','smartdns'],'ubus':{'luci-rpc':['getBoardJSON','getNetworkDevices','getWirelessDevices','getHostHints'],'network':['get_proto_handlers'],'network.device':['status'],'network.interface':['dump']}},'write':{'uci':['network','dhcp','firewall','smartdns']}}}
    put('usr/share/rpcd/acl.d/luci-app-xzt8wrt-setup.json',json.dumps(acl,ensure_ascii=False,indent=2))
    for name in ('network-policy', 'network-runtime'):
        put('usr/sbin/xzt8wrt-' + name, (ROOT/(name+'.sh')).read_text(), 0o755)
    put('etc/sysctl.d/99-xzt8wrt-network.conf', 'net.ipv4.ip_forward=1\nnet.ipv4.conf.all.send_redirects=0\nnet.ipv4.conf.default.send_redirects=0\nnet.ipv4.conf.all.accept_redirects=0\nnet.ipv4.conf.default.accept_redirects=0\n')
    put('etc/init.d/xzt8wrt-network', '#!/bin/sh /etc/rc.common\nSTART=18\nstart() { /usr/sbin/xzt8wrt-network-runtime; }\n', 0o755)
    link=output/'etc/rc.d/S18xzt8wrt-network'
    link.parent.mkdir(parents=True,exist_ok=True)
    if not link.exists(): link.symlink_to('../init.d/xzt8wrt-network')
    put('etc/hotplug.d/iface/99-xzt8wrt-network', '#!/bin/sh\n[ "$INTERFACE" = lan ] || exit 0\ncase "$ACTION" in ifup|ifupdate) /usr/sbin/xzt8wrt-network-runtime ;; esac\n', 0o755)
    put('etc/uci-defaults/99z-xzt8wrt-network', (ROOT/'network-defaults.sh').read_text(), 0o755)
    # Board defaults are consumed only when OpenWrt generates a new network config.
    # Upgrades retaining /etc/config/network keep their existing IP and gateway.
    put('etc/board.d/99-xzt8wrt-address', '''#!/bin/sh
. /lib/functions/uci-defaults.sh
board_config_update
ucidef_set_interface lan ipaddr 192.168.11.1 netmask 255.255.255.0
board_config_flush
''',0o755)
    if platform == 'x86':
        put('usr/sbin/xzt8wrt-expand-root',(ROOT/'expand-root.sh').read_text(),0o755)
        put('etc/init.d/xzt8wrt-expand-root', '''#!/bin/sh /etc/rc.common
START=19
start() {
 /usr/sbin/xzt8wrt-expand-root >> /tmp/xzt8wrt-expand-root.log 2>&1 &
}
''',0o755)
        target=output/'etc/rc.d/S19xzt8wrt-expand-root'
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists(): target.symlink_to('../init.d/xzt8wrt-expand-root')
    put('etc/uci-defaults/97-xzt8wrt-storage', '''#!/bin/sh
[ -x /etc/init.d/dockerd ] || exit 0
old="$(uci -q get dockerd.globals.data_root)"
case "$old" in ''|/opt/docker) ;; *) exit 0;; esac
# Keep an existing Docker installation and its configured path during upgrades.
[ ! -d /opt/docker/containers ] && [ ! -d /opt/docker/image ] || exit 0
uci -q get dockerd.globals >/dev/null || uci set dockerd.globals=globals
mkdir -p /srv/docker
uci set dockerd.globals.data_root='/srv/docker'
uci commit dockerd
exit 0
''',0o755)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('output',type=pathlib.Path)
    parser.add_argument('--version',required=True)
    parser.add_argument('--platform',required=True)
    parser.add_argument('--profile',required=True)
    args=parser.parse_args()
    install(args.output,args.version,args.platform,args.profile)
