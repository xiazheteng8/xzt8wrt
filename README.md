# xzt8wrt

ImmortalWrt 25.12.2，x86_64 高大全版 / 精简版。源码固定至官方发布提交 `4fc16f2985a358bd43bb522e43f05395fcbd6ed5`，feeds 使用该版本自带的固定提交。

## 构建

进入 GitHub Actions → Build xzt8wrt → Run workflow。选择 `both`（双版本）、`full`（高大全）或 `lite`（精简）。成功后分别下载 `xzt8wrt-25.12.2-x86-64-full` / `xzt8wrt-25.12.2-x86-64-lite` artifact。每周日北京时间 03:00 自动构建双版本（UTC 周六 19:00；GitHub 定时任务可能延迟）。完整源码编译可能需要数小时；工作流失败时查看日志和 diagnostics，不能把工程包当成固件刷入。

也可在已安装 OpenWrt 编译依赖的 Ubuntu 24.04 上执行 `PROFILE=full bash build.sh` 或 `PROFILE=lite bash build.sh`。建议至少 8 GB 内存和 60 GB 可用磁盘。

## 配置

- 中文 LuCI / HTTPS，SSH 登录横幅和主机名为 xzt8wrt。
- Intel igc/igb/e1000e、Realtek r8169、USB RTL8152/AX88179、VMware vmxnet3；VirtIO 使用目标默认内核配置。通用不代表支持每一块网卡，无线驱动未盲目全选。
- PassWall、WireGuard、OpenVPN、ZeroTier、Docker、mwan3、PBR、SQM、DDNS、UPnP、SmartDNS、Adblock。
- Samba4、Aria2、磁盘管理、USB 存储、ext4/exFAT/NTFS3、网络与硬盘诊断工具。
- 两版代理界面均仅保留 PassWall，不安装 OpenClash；未内置订阅、节点或账号。
- 两版均包含 WOL、DDNS-GO、中文 LuCI / HTTPS 和常见 x86 网卡驱动。精简版以 Xray 为代理核心，去除 NAS、Docker、下载及额外 VPN 等组件。
- 高大全版额外包括 AdGuard Home、FRP 客户端/服务端、Tailscale、Syncthing、Transmission、rclone、NFS、MiniDLNA、文件管理、定时唤醒、流量统计、banIP、证书管理等；完整选择见 `profiles/full.config`，不包含所有互斥或设备专用软件包。
- 高大全版对 `files/etc/uci-defaults/99-xzt8wrt` 列明的扩展服务设置开机自启；仍保留软件包原有服务配置。需要账号、订阅、节点、共享目录或端口设置的服务须配置后才能工作。AdGuard Home / SmartDNS 等 DNS 服务需手动协调端口；不会同时强制接管 DNS。精简版扩展服务默认不自启。
- 高大全版根分区 2048 MiB，精简版 512 MiB，内核分区 64 MiB；生成 ext4 / squashfs，以及 BIOS / UEFI 两种启动镜像。

## 镜像选择

- UEFI：`generic-squashfs-combined-efi.img.gz`，常规首选。
- 传统 BIOS：`generic-squashfs-combined.img.gz`。
- ext4：适合明确需要可写根分区的用户，恢复出厂行为与 squashfs 不同。

这是 64 位 x86 固件，不适用于 ARM、普通家用路由器或 32 位老机器。安装前备份磁盘和配置，写入整盘镜像会覆盖目标盘。先核对 SHA256。Secure Boot 通常需要关闭。

LAN 地址、端口划分及登录策略继承官方 x86 目标默认设置，首次安装建议隔离接线、确认接口并设置 root 密码。不要凭网口外观猜 LAN/WAN。升级到官方固件不会保留这套自定义包和品牌定制；后续升级应继续使用本工程构建的镜像。

## 验证边界

本工程包含 make defconfig 后的严格选项检查，若软件包不存在或依赖导致选项丢失即停止。成功的 Actions 编译只证明构建通过；仍需在你的硬件或虚拟机上验证启动、网卡识别、存储及路由性能。

## 项目状态

双版本、每周构建和服务启用策略从下一次构建生效，不改变正在运行的首次构建。
ARM 仍处于计划阶段，具体型号与目标配置尚未确定；当前只生成 x86_64 镜像。
配置检查及编译验证以对应 Actions 结果为准，配置文件中选中不代表固件已经构建成功。
