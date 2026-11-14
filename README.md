# xzt8wrt

ImmortalWrt 25.12.2，x86_64 通用功能增强版。源码固定至官方发布提交 `4fc16f2985a358bd43bb522e43f05395fcbd6ed5`，feeds 使用该版本自带的固定提交。

## 构建

进入 GitHub Actions → Build xzt8wrt → Run workflow。成功后下载 `xzt8wrt-25.12.2-x86-64` artifact。完整源码编译可能需要数小时；工作流失败时查看日志和 diagnostics，不能把工程包当成固件刷入。

也可在已安装 OpenWrt 编译依赖的 Ubuntu 24.04 上执行 `bash build.sh`。建议至少 8 GB 内存和 60 GB 可用磁盘。

## 配置

- 中文 LuCI / HTTPS，SSH 登录横幅和主机名为 xzt8wrt。
- Intel igc/igb/e1000e、Realtek r8169、USB RTL8152/AX88179、VMware vmxnet3；VirtIO 使用目标默认内核配置。通用不代表支持每一块网卡，无线驱动未盲目全选。
- OpenClash、PassWall、WireGuard、OpenVPN、ZeroTier、Docker、mwan3、PBR、SQM、DDNS、UPnP、SmartDNS、Adblock。
- Samba4、Aria2、磁盘管理、USB 存储、ext4/exFAT/NTFS3、网络与硬盘诊断工具。
- 扩展服务默认关闭，需配置后手动启用；代理组件不能同时接管流量。OpenClash 首次使用需在界面下载兼容核心并导入自己的配置，未内置订阅和账号。
- 根分区 2048 MiB，内核分区 64 MiB；生成 ext4 / squashfs，以及 BIOS / UEFI 两种启动镜像。

## 镜像选择

- UEFI：`generic-squashfs-combined-efi.img.gz`，常规首选。
- 传统 BIOS：`generic-squashfs-combined.img.gz`。
- ext4：适合明确需要可写根分区的用户，恢复出厂行为与 squashfs 不同。

这是 64 位 x86 固件，不适用于 ARM、普通家用路由器或 32 位老机器。安装前备份磁盘和配置，写入整盘镜像会覆盖目标盘。先核对 SHA256。Secure Boot 通常需要关闭。

LAN 地址、端口划分及登录策略继承官方 x86 目标默认设置，首次安装建议隔离接线、确认接口并设置 root 密码。不要凭网口外观猜 LAN/WAN。升级到官方固件不会保留这套自定义包和品牌定制；后续升级应继续使用本工程构建的镜像。

## 验证边界

本工程包含 make defconfig 后的严格选项检查，若软件包不存在或依赖导致选项丢失即停止。成功的 Actions 编译只证明构建通过；仍需在你的硬件或虚拟机上验证启动、网卡识别、存储及路由性能。
