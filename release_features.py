"""Chinese release guidance, tied to feature metadata in actual firmware images."""
import json
import sys

FEATURES = {'single-lan-v2':'单 LAN 旁路由向导', 'smartdns-defaults-v1':'SmartDNS 预配置', 'admin-domain-v1':'xzt8.wrt 管理入口'}

def render_features(state):
    if not any(v.get('xzt8wrt_features') for v in state.values()):
        return ['## 功能提示', '', '此快照未记录新版网络功能标记，请以各 ZIP 内配置为准。']
    lines=['## 首次联网与本地管理', '', '| 固件组合 | 实际包含的新版网络功能 |', '| --- | --- |']
    for key,value in sorted(state.items()):
        found=[label for flag,label in FEATURES.items() if flag in value.get('xzt8wrt_features',[])]
        lines.append('| '+key.replace('/full',' / 高大全版').replace('/lite',' / 精简版')+' | '+('、'.join(found) if found else '沿用旧构建，未记录新版网络功能')+' |')
    lines += ['', '新装默认 IP：`192.168.11.1`。若主路由也是此地址，先隔离配置，将旁路由改为同网段空闲地址（例如 `192.168.11.2/24`）。保留配置升级沿用原地址。',
              '单网口物理机 / 虚拟机：向导选择“旁路由”，保留一个 LAN 即可。填写上级网关与 DNS，启用默认勾选的 IPv4 NAT；向导会关闭自身 DHCP/IPv6 通告、解除旧 WAN 的同网卡绑定，并配置 LAN 转发。新版关闭 ICMP 重定向，避免客户端绕过旁路由。',
              '其他终端要经过旁路由上网，仍须把默认网关指向旁路由；群晖 VMM 网卡应连接可访问主路由的外部虚拟交换机，且 VLAN / 网段一致。',
              'SmartDNS 预配置使用本地 6053 端口，dnsmasq 保留 53 端口；预置 `223.5.5.5`、`119.29.29.29`，并为 dnsmasq 保留直接备用上游。可以在设置向导中修改 DNS 或关闭 SmartDNS。已有自定义 DNS 配置不强制覆盖。',
              '本地管理入口：`http://xzt8.wrt/`，自动打开设置向导。客户端 DNS 必须指向旁路由，或在主路由添加 `xzt8.wrt → 旁路由实际 IP` 的本地记录。浏览器安全 DNS/DoH 可能绕过该记录；解析失败时直接使用实际 IP。别名随 LAN 地址更新。',
              '网络设置使用 LuCI 带回滚的应用流程；更换管理 IP 后请连接新地址并及时确认。IPv6 旁路转发、运营商 VLAN 与复杂多 WAN 不由此 IPv4 向导自动处理。',
              'x86 自动扩容适用于直接挂载的 ext4 根分区及其后的空闲空间；其他已有分区会被保留。虚拟机需先由宿主机扩大虚拟硬盘；SquashFS 不自动扩容。Docker 与根目录共享可用容量，升级前仍需备份容器数据。']
    return lines

if __name__=='__main__':
    print('\n'.join(render_features(json.load(open(sys.argv[1])))))
