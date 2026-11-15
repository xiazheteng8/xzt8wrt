# 🛠️ xzt8wrt 固件构建教程｜Fork 后，点几下就能云端编译

欢迎使用 **xzt8wrt**！这是一个基于 **ImmortalWrt** 的固件构建项目，适用于部分 x86 软路由、ARM 软路由和 ARM 无线路由器。

即使你不会写代码，也可以照着本页，把项目复制到自己的 GitHub 账号里，然后使用 GitHub 免费提供给公开仓库的标准云端运行器编译。实际可用额度和政策以你的 GitHub 账号为准。

> 💡 **代码保存在 GitHub，编译也在 GitHub 上进行。启动构建后可以关闭网页，也可以关闭电脑，不会中断云端编译。**
>
> 📌 本仓库提供的是构建脚本和配置，不是可以直接刷入路由器的固件。要先完成下面的编译步骤，再下载生成的镜像。
>
> 🧪 新增设备目前是“已加入构建配置、待云端编译与实机验证”的状态，不代表已经在每台机器上测试通过。

---

## 🌐 网页选择设备与下载成品

👉 **[打开 xzt8wrt 固件工坊](https://xiazheteng8.github.io/xzt8wrt/)**

📡 **[直接选择 ALFA Network AP120C-AC 精简版](https://xiazheteng8.github.io/xzt8wrt/?device=ipq40xx%2Fgeneric%2Falfa-network_ap120c-ac&profile=lite)**。此链接只是预选设备和版本，不代表已有成品，也不会自动启动编译；可以在左侧切换其他型号。

本仓库还提供一个静态“固件工坊”网站，源码在 `docs/index.html`。它可以搜索设备、查看精简 / 高大全版说明、查询真实已发布固件，并给出 GitHub 构建入口与参数。网页不会直接替你启动构建，需要在 GitHub 点击确认。

**自己 Fork 后开启网站：** 进入 **Settings → Pages → Build and deployment**，选择 **Deploy from a branch**，分支选 `main`，目录选 `/docs`，点击 **Save**。等待 GitHub 完成 Pages 部署后，该页面会显示你的网站地址，通常为 `https://你的用户名.github.io/仓库名/`。网页会自动识别自己的仓库，也可以手动切换到自己的 Fork。

**只想下载已经编译好的固件：** 在网站选好准确型号与版本，查看“已编译固件下载”。每个“平台＋版本”任务完整构建成功后，会立即把该组每台设备的镜像单独打成 ZIP，发布到该任务独立的 **Release**，不用等待其他构建任务结束，网站从真实发布记录生成下载链接。尚未构建成功或本轮未发布的型号不会显示下载按钮。每个包包含实际生成的镜像、`images.json`、源码信息、编译配置和镜像校验清单，Release 另有 ZIP 校验文件 `SHA256SUMS`。

部分硬路由首次刷机可能需要专用过渡步骤。包内只包含该目标实际生成的 factory / initramfs / recovery 等镜像，不保证某个型号所需的所有中间固件都在包中。请按该型号与引导布局的安装文档操作，不能把这些文件当成通用中间固件。

---

## 📖 先用一分钟认识几个词

| 页面上的词 | 你可以这样理解 |
| --- | --- |
| GitHub | 保存代码、运行云端编译的网站 |
| 仓库 / Repository | 这个项目在 GitHub 上的文件夹 |
| Fork | 把项目复制一份，放到你自己的账号下 |
| Actions | GitHub 提供的自动运行任务功能，本项目用它编译固件 |
| Workflow | 一套自动执行的步骤，本项目名叫 `Build xzt8wrt` |
| Run workflow | 手动开始一次构建 |
| Artifact / Artifacts | 构建完成后可下载的文件包 |
| 固件 / 镜像 | 最后写入路由器或启动盘的系统文件 |
| stock / ubootmod | 两种不同的引导和分区布局，不能混用镜像 |

**整个过程：** 登录 GitHub → Fork 项目 → 启用 Actions → 选择设备与版本 → 开始构建 → 等待完成 → 下载并核对固件。

---

## ✅ 第一步：准备好这些东西

- 一个可以登录的 [GitHub 账号](https://github.com/)。没有账号，先点击网站的 **Sign up** 注册。
- 能正常访问 GitHub 的浏览器。新手建议使用电脑浏览器；手机页面的按钮位置可能不同。
- 确认自己的设备**品牌、完整型号、硬件版本、闪存版本和现有引导布局**。例如“红米 AX6000”和“小米 AX6000”不能当成同一台机器。
- 给构建留出时间：完整源码编译通常需要数小时，首次构建不一定一次成功。

**不需要**在自己电脑上安装 Linux、编译器或下载整个 ImmortalWrt 源码，也不需要把账号密码、订阅地址或节点上传到公开仓库。

---

## 🍴 第二步：Fork 到你自己的仓库

1. 登录 GitHub 后，打开本项目：[xiazheteng8/xzt8wrt](https://github.com/xiazheteng8/xzt8wrt)。
2. 在页面右上方找到 **Fork**，点击它。也可以直接打开 [Fork 页面](https://github.com/xiazheteng8/xzt8wrt/fork)。
3. 在新页面里：
   - **Owner**：选择你自己的 GitHub 用户名。
   - **Repository name**：可以保持 `xzt8wrt`，也可以起一个自己喜欢的名字。
   - **Copy the main branch only**：一般保持默认即可。
4. 点击 **Create fork**，等待复制完成。
5. 看一眼地址栏：应变成 `https://github.com/你的用户名/你的仓库名`。

> ✅ 后面的操作都在**你自己的仓库**里进行。不要回到原作者仓库找构建结果，否则可能下载到别人的任务产物。

---

## ⚙️ 第三步：启用 GitHub Actions

1. 打开你自己 Fork 出来的仓库。
2. 点击上方的 **Actions** 标签。
3. 如果出现提示按钮 **I understand my workflows, go ahead and enable them**，点击启用。
4. 在左侧找到并点击 **Build xzt8wrt**。

如果看不到工作流，先确认 Fork 的文件里有 `.github/workflows/build.yml`，然后刷新页面。

如果提示仓库不允许 Actions，进入 **Settings → Actions → General**，按页面提示允许本项目使用的 Actions。普通个人公开仓库一般不需要额外设置。

> 🔐 准备任务使用只读仓库权限；各构建任务为发布固件，使用内置 `GITHUB_TOKEN` 写入本仓库 Releases。无需新建 PAT / Token，也不需要在 Secrets 里填写 GitHub 密码、代理账号或订阅。

---

## 🖱️ 第四步：手动开始一次构建

在 **Actions → 左侧 Build xzt8wrt** 页面：

1. 找到右侧的 **Run workflow** 按钮，点击展开。
2. **Use workflow from** 保持 `main`。
3. 根据下面两张表选择平台和版本。
4. 最后点击弹出框里的绿色 **Run workflow**。
5. 等待任务列表出现新的一条 `Build xzt8wrt`。没有马上出现，可以稍等后刷新。

### 🧩 `platform`：你要给哪一类机器编译？

| 选择 | 适合什么设备 | 不确定时怎么选 |
| --- | --- | --- |
| `x86` | Intel / AMD 64 位软路由、迷你主机、虚拟机 | N100 等 x86 机器选它；仍需确认自己的机器是 x86_64 |
| `rockchip` | NanoPi R2S / R4S / R5S / R6S、FastRhino R66S / R68S | 这些 ARM 软路由选它 |
| `filogic` | 下文列出的 TR3000、红米 AX6000、TUF-AX6000、GL-MT3000 / MT6000 | 只支持下文列明的准确型号与布局 |
| `custom` | 扩展 ARM 目录中的单个准确机型 | 从网站复制 `device`，先做配置验证 |
| `all` | 原有三个批量平台（不含扩展目录） | 会生成更多文件、耗时更长；只给自己用，建议选具体平台 |

选择 `rockchip` 或 `filogic` 后，会为该组中已配置的每个型号分别生成文件；下载后仍须挑选与你的设备对应的那一个。

### 📦 `profile`：你想要哪个版本？

| 选择 | 中文含义 | 建议 |
| --- | --- | --- |
| `lite` | 精简版 | 新手、硬路由、只需要常用功能时，建议先选它 |
| `full` | 高大全版 | 需要 Docker、NAS、下载、更多 VPN 等功能的 x86 / Rockchip 设备 |
| `both` | 两版都编译 | 想比较两个版本时选择；Filogic 只生成精简版 |

**Filogic 不支持 `full` 单独构建。** 这类硬路由的闪存和分区容量有限，不宜直接塞入高大全版。选择 `platform=filogic` 时，请选 `lite` 或 `both`。

### 🧪 `configure_only`：只检查配置，要勾选吗？

- **想生成固件：不要勾选。**
- 想先检查源码、机型和插件选项能否正确匹配：可以勾选。
- 只检查配置的任务即使全部绿色，也**不会生成固件**，只会上传诊断配置。

### 📝 几个可以直接照选的例子

| 你的需求 | `platform` | `profile` | `configure_only` |
| --- | --- | --- | --- |
| 给 R2S / R4S / R66S / R68S 做精简固件 | `rockchip` | `lite` | 不勾选 |
| 给这些 ARM 软路由做高大全固件 | `rockchip` | `full` | 不勾选 |
| 给红米 AX6000 或 TR3000 做固件 | `filogic` | `lite` | 不勾选 |
| 给 x86 软路由做两个版本 | `x86` | `both` | 不勾选 |
| 只想先检查所有配置 | `all` | `both` | 勾选 |

---

## ⏳ 第五步：看懂构建状态，耐心等待

点击刚出现的任务，进入运行详情页。

| 状态 | 含义 | 你需要做什么 |
| --- | --- | --- |
| `Queued` / `Pending` | 正在排队，尚未开始或等待前一轮任务 | 等待即可，不用连续重复点击构建 |
| `In progress` | 正在运行 | 可以关闭网页或电脑，稍后再回来查看 |
| 绿色 ✅ / `Success` | 任务成功 | 进入下一步下载；注意是否只检查了配置 |
| 红色 ❌ / `Failure` | 任务失败 | 查看日志，不要把失败任务的诊断包当固件 |
| `Cancelled` | 任务被取消 | 需要时重新开始构建 |

每轮任务先执行 `prepare`，查找最新官方稳定版并确定本轮统一使用的源码提交。之后最多同时编译两个组合，其余组合会排队。

全平台双版本共有 **5 个组合**：`x86-full`、`x86-lite`、`rockchip-full`、`rockchip-lite`、`filogic-lite`。其中一组失败不一定代表其他组也失败，下载时要看你准备使用的那一组是否成功。

> ☕ “运行了很久”不一定是卡住。编译大型软件包可能长时间没有明显进度变化。可以点开任务中的步骤查看日志，避免反复创建重复构建。

---

## 📥 第六步：在哪里下载固件？

1. 进入你自己仓库的 **Actions**。
2. 点击你要下载的那次运行。
3. 确认要用的平台任务已经绿色成功。
4. 回到这次运行的总览页，往下找到 **Artifacts**。
5. 点击对应的文件包下载，通常会得到一个 `.zip` 压缩包。
6. 在电脑上解压，再从里面选择与你设备匹配的镜像。

文件包名称示例：

```text
xzt8wrt-25.12.2-x86-full
xzt8wrt-25.12.2-rockchip-lite
xzt8wrt-25.12.2-filogic-lite
```

上面的版本号只是示例，**实际名称会随官方最新稳定版变化**。

- `full` 是高大全版，`lite` 是精简版。
- 文件默认保留 **14 天**，过期后可以重新编译。
- 请保持 GitHub 登录状态；未登录时可能无法下载 Actions 的 Artifacts。
- 本项目同时提供 **Actions → Artifacts** 构建包，以及 **Releases** 中按具体设备打包的公开下载。网站读取 Releases；Artifacts 通常需要登录 GitHub。
- `xzt8wrt-diagnostics-...` 是日志 / 配置诊断包，**不能刷入路由器**。

---

## 🧭 第七步：从文件堆里选对自己的固件

### 💻 x86 软路由 / 虚拟机

| 文件名结尾 | 用途 |
| --- | --- |
| `generic-squashfs-combined-efi.img.gz` | UEFI 启动的完整磁盘镜像，常规选择 |
| `generic-squashfs-combined.img.gz` | 传统 BIOS 启动的完整磁盘镜像 |
| 带 `ext4` 的镜像 | 可写根分区方案，恢复出厂行为与 squashfs 不同，明确需要时再选 |

文件名前面还会带有 ImmortalWrt 版本和平台信息。`.gz` 是压缩格式，是否需要先解压取决于你使用的写盘工具。写盘会覆盖所选磁盘，务必核对目标盘。

### 🍓 ARM 软路由

选择文件名包含**准确设备名**的 `sysupgrade.img.gz`。例如：

```text
...friendlyarm_nanopi-r2s-squashfs-sysupgrade.img.gz
...friendlyarm_nanopi-r4s-squashfs-sysupgrade.img.gz
...lunzn_fastrhino-r66s-squashfs-sysupgrade.img.gz
...lunzn_fastrhino-r68s-squashfs-sysupgrade.img.gz
```

不要把 R66S 的镜像刷到 R68S，也不要把 NanoPi R6S 与 FastRhino R66S / R68S 混淆。首次写入 SD 卡 / eMMC 和已有系统中的升级，操作流程不同，请按设备说明进行。

### 📡 ARM 无线路由器 / 硬路由

这类设备对**型号、硬件版本和引导布局**要求更严格：

| 名称 / 文件类型 | 要理解的含义 |
| --- | --- |
| `stock` | 对应原厂分区 / 引导布局 |
| `ubootmod` | 对应 OpenWrt U-Boot 布局，前提是设备已完成对应改造 |
| `sysupgrade` | 通常用于已经运行兼容 OpenWrt / ImmortalWrt 系统后的升级 |
| `factory` | 某些设备用于从原厂系统迁移的镜像；不是每台设备都有，也不能一概直接刷 |
| `initramfs` / `recovery` | 通常用于临时启动、安装或恢复，不应当成普通升级镜像随意刷入 |

> ⚠️ **编译成功不等于可以随便刷。** 本项目不替你自动改分区、不刷 U-Boot，也不提供一种适合所有机器的通用刷机步骤。请先核实具体型号的官方安装说明，备份原系统和配置后再操作。不要看到名称里有“AX6000”就直接下载。

---

## 🔎 支持哪些具体设备？

以下是已经加入构建配置的目标，新增机型仍需云端构建和实机验证。

| 平台 | 品牌 / 完整型号 / 布局 | 可构建版本 |
| --- | --- | --- |
| x86 / 64 | Intel / AMD x86_64 通用 | 高大全 + 精简 |
| rockchip / armv8 | FriendlyARM NanoPi **R2S、R4S、R5S、R6S** | 高大全 + 精简 |
| rockchip / armv8 | Lunzn FastRhino **R66S、R68S** | 高大全 + 精简 |
| mediatek / filogic | Cudy **TR3000 v1** | 精简 |
| mediatek / filogic | Cudy **TR3000 256MB v1** | 精简 |
| mediatek / filogic | Cudy **TR3000 v1，OpenWrt U-Boot 布局** | 精简 |
| mediatek / filogic | 小米 **红米 Redmi Router AX6000，stock 布局** | 精简 |
| mediatek / filogic | 小米 **红米 Redmi Router AX6000，ubootmod 布局** | 精简 |
| mediatek / filogic | **ASUS TUF-AX6000** | 精简 |
| mediatek / filogic | **GL.iNet GL-MT3000、GL-MT6000** | 精简 |

这些设备已与官方稳定版的 [Rockchip 设备定义](https://github.com/immortalwrt/immortalwrt/blob/v25.12.2/target/linux/rockchip/image/armv8.mk)和 [Filogic 设备定义](https://github.com/immortalwrt/immortalwrt/blob/v25.12.2/target/linux/mediatek/image/filogic.mk)核对，设备清单在 `build-support.py` 的 `TARGETS` 中。

**请特别注意：**

- R2S 不等于 R2S Plus，R4S 不等于 R4SE / Enterprise。
- 红米 AX6000 不等于小米 Mi Router AX6000。
- TR3000 的不同闪存版本不能凭外观判断，更不能把 stock 和 ubootmod 固件混刷。
- 未列出的设备不代表可以使用“看起来很像”的其他型号镜像。

ARM 设备的网卡、Wi-Fi、固件与启动组件继承官方设备配置，每个设备使用独立根文件系统，不会把 x86 的网卡驱动直接套用到 ARM 上。

### 🆕 按 Kwrt / openwrt.ai 查找更多 ARM 设备

网站现在还读取 [扩展 ARM 目录](docs/catalog.json)：参考 Kwrt `25.12/devices` 的平台范围、openwrt.ai 的机型列表，并与 ImmortalWrt 25.12.2 官方镜像配置逐项匹配。目前有 **17 个目标、485 个 ARM 配置项**，覆盖 Rockchip、树莓派、Filogic、MT7622、IPQ40xx / IPQ806x / IPQ50xx / IPQ60xx / IPQ807x、MVEBU、Sunxi 等。列表可能包含同一设备的不同布局，不能按名称相似就互刷。

另有 **88 个参考项待适配**，包括官方稳定版没有对应定义的平台或型号。它们记录在目录的 `excluded` 中，不提供可用下载承诺。**配置匹配 ≠ 已编译成功 ≠ 已实机验证**；只有实际构建成功、校验通过并发布的镜像才会显示下载按钮。

小白操作步骤：

1. 在网站搜索品牌或完整型号，核对硬件版本、闪存与布局。
2. 选择精简版；扩展 ARM 硬路由暂只允许精简版，SD / eMMC 类软路由可选择高大全版。
3. 点击“前往 GitHub 构建”，按弹窗复制参数。扩展机型的 `platform` 为 `custom`，`device` 是完整的 `目标/子目标/设备ID`，不要自己简写。
4. 第一次建议勾选 `configure_only`，先检查官方源码能否识别该目标与所选插件。这一步成功只代表配置通过，不会生成固件。
5. 配置通过后，用相同参数再运行一次，取消勾选 `configure_only`，才是完整编译。
6. 等对应任务绿色成功，到 Releases 或网站下载该机型的 ZIP。遇到失败查看诊断文件，禁止用其他型号镜像代替。

例如：网站选择某个扩展 ARM 型号后，如果弹窗给出 `platform=custom`、`device=qualcommax/ipq807x/某设备ID`，就完整照抄。`device` 仅允许目录中的准确值，不能填写网址、命令或通配符。原有 x86、rockchip、filogic 批量构建时，`device` 留空。

**定时任务范围保持原来的 5 个组合**，不会每周自动编译几百个机型。扩展目录按需手动选择单设备，避免无意占满 Actions。x86 的设备、分区和插件配置保持原样，Kwrt 只作为 ARM 参考；它的私有部署、远程 DIY、整棵内核和启动树替换脚本没有导入。详细评估见 [ARM 参考说明](ARM-REFERENCE.md)。


---

## 📦 高大全版和精简版有什么区别？

| 项目 | 精简版 `lite` | 高大全版 `full` |
| --- | --- | --- |
| 中文 LuCI / HTTPS | ✅ | ✅ |
| SSH 横幅和主机名 `xzt8wrt` | ✅ | ✅ |
| PassWall | ✅，以 Xray 为核心 | ✅，包含更多可选协议组件 |
| WOL 网络唤醒 | ✅ | ✅ |
| DDNS-GO | ✅ | ✅ |
| Docker、NAS、下载等扩展 | 不安装 | ✅ |
| 额外 VPN、统计和管理插件 | 以必要功能为主 | 更丰富 |
| 扩展服务开机自启 | 默认关闭 | 对首次启动脚本列明的服务启用 |
| x86 / Rockchip 根分区 | 512 MiB | 2048 MiB |
| 闪存受限的 Filogic 硬路由 | ✅ | 暂不提供 |

高大全版还选择了 WireGuard、OpenVPN、ZeroTier、Tailscale、Docker、mwan3、PBR、SQM、DDNS、UPnP、SmartDNS、Adblock、AdGuard Home、Samba4、NFS、Aria2、Transmission、Syncthing、rclone、FRP、文件管理、磁盘管理和统计诊断等，完整清单见 `profiles/full.config`。

> 💡 两版都只保留 **PassWall** 代理界面，不安装 OpenClash。项目不内置订阅、节点、账号或密码。插件“安装了”不等于“配置好了”：PassWall 需要自己的节点，DDNS-GO 需要自己的域名与服务商配置，WOL 需要目标设备支持并启用唤醒。
>
> ⚙️ 高大全版会把 `files/etc/uci-defaults/99-xzt8wrt` 列明的扩展服务设置为开机自启，但仍保留各软件包原有配置。SmartDNS / AdGuard Home 等 DNS 服务要自行协调端口。保留旧配置升级时，首次启动默认设置不保证重新应用。

---

## 🗓️ 每周自动编译：电脑不用开机

默认安排在 **每周日北京时间凌晨 03:00** 先检查内核。只有最新正式稳定版的内核版本或内核包 release 与该平台 / 版本上一次成功发布的记录不同，才会构建；内核不变就跳过。没有成功记录时建立首份基线，失败任务不写成功记录。手动 Run workflow 可以重建同一内核。

Fork 后请先完成 Actions 启用，并确认 **Build xzt8wrt** 没有被禁用。GitHub 定时任务可能延迟；公开仓库长期没有活动时，定时任务可能自动停用，需要在 Actions 页面重新启用。详见 [GitHub 定时工作流说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)。

### 想换时间，怎么改？

1. 进入自己仓库的 **Code** 页面。
2. 依次打开 `.github` → `workflows` → `build.yml`。
3. 点击铅笔形状的编辑按钮。
4. 找到 `cron: '0 19 * * 6'`，修改成需要的时间。
5. 点击 **Commit changes**，按页面提示提交到 `main`。

GitHub 使用 UTC 时间，北京时间比 UTC 快 8 小时：**北京时间周日 03:00 = UTC 周六 19:00**。不要只改小时却忘记日期会跨天。新手如果不熟悉 cron，建议先保持默认。

---

## 🆕 “自动跟随最新稳定版”是什么意思？

每次构建都会从 [ImmortalWrt 官方下载页](https://downloads.immortalwrt.org/)查找最新的**正式稳定版**，再解析对应 Git 标签和源码提交。本轮所有平台使用同一份源码，feeds 使用该版本自带的固定提交。

- 官方发布了更新的稳定版：检查它的内核；内核有更新时，下一轮定时任务才构建该最新稳定版。
- 官方还没发布新稳定版、或新版内核没有变化：定时任务跳过，不重复编译。仅插件 / 软件包变化也不会触发定时编译。
- 不跟随 `master` / `SNAPSHOT` 开发版。
- 不单独替换成最新主线 Linux 内核，内核和驱动随官方稳定版。
- 若新版把插件改名、移除或改变依赖，严格检查可能报错，需要修复配置后重建。

想知道自己拿到的到底是什么版本，可以查看 Actions 的 `prepare` 摘要，或下载包中的：

| 文件 | 记录的内容 |
| --- | --- |
| `source.json` | 本轮稳定版版本、标签和源码提交 |
| `source-version.txt` | 实际源码提交 |
| `feeds-version.txt` | 软件包源提交 |
| `kernel-version.json` | 实际内核版本信息 |
| `.config` | 编译实际使用的配置；部分系统默认隐藏以点开头的文件 |

---

## 🧾 下载后如何核对文件有没有损坏？

产物带有校验清单 `xzt8wrt-sha256sums`。先把下载的 `.zip` **完整解压**，再在该目录运行相应命令。

**Windows PowerShell：**

```powershell
Get-FileHash .\你的固件文件名 -Algorithm SHA256
```

将输出的 SHA256 与 `xzt8wrt-sha256sums` 中同名文件对应的值比较，大小写可以不同，内容必须一致。文件名有空格时请加引号。

**macOS 终端：**

```sh
shasum -a 256 -c xzt8wrt-sha256sums
```

**Linux 终端：**

```sh
sha256sum -c xzt8wrt-sha256sums
```

出现不匹配时，先重新下载并完整解压，不要继续刷入。

构建脚本还会检查每个已选择设备是否真的生成了可用镜像，以及镜像哈希是否匹配。某台设备因容量超限没有生成镜像时，任务会报错，不会把“有几个文件”当作全部构建成功。

---

## 🔄 如何更新自己 Fork 的工程？

**源码自动跟随稳定版**，不等于你的 Fork 会自动获得本工程后续修改的教程、设备清单和工作流。

同步工程的方法：

1. 打开你自己仓库的 **Code** 页面。
2. 找到 **Sync fork**。
3. 点击 **Update branch**。
4. 回到 **Actions**，按需重新构建。

如果你修改过配置，先看清差异。出现冲突时不要随意覆盖自己的修改。构建使用的是启动任务时的工程提交，后续改文件不会改变已经运行中的那一轮。

---

## ❓ 新手常见问题

### 1. 为什么找不到 Run workflow？

确认是在**自己 Fork 的仓库**中，已经启用 Actions，并点开左侧 **Build xzt8wrt**。工作流文件需要在默认分支中。页面没更新时可以刷新。

### 2. 已经点击开始，可以关电脑吗？

可以。确认 Actions 列表已经出现新任务后，云端会继续执行。关闭浏览器不会取消任务。

### 3. 为什么绿色成功了，却找不到固件？

先检查是否勾选了 `configure_only`。勾选后只验证配置，不生成固件。也要进入**那次运行的总览页底部**找 Artifacts。只有实际编译成功的固件才会进入 Releases；只检查配置不会发布固件。

### 4. 为什么显示红色失败？

点击失败的任务，展开红色步骤，尤其是 **Build or validate firmware configuration**。可下载 `xzt8wrt-diagnostics-平台-版本` 查看配置与日志。常见原因包括源码 / 软件包下载失败、插件选项变化、编译错误、磁盘不足或固件超出设备分区容量。应定位首个有效错误，再修改或重试。

### 5. 下载包里文件很多，哪个可以刷？

先看本页“第七步”，确认完整型号、版本与布局。`.config`、`.manifest`、`.json`、校验文件和 diagnostics 都不是刷机镜像。遇到不确定的 `factory` / `recovery` / `ubootmod` 文件，先查具体设备安装说明。

### 6. 刷好后默认密码、IP、LAN / WAN 是什么？

本工程设置主机名和横幅为 `xzt8wrt`，其余登录策略、LAN 地址与接口划分继承官方设备默认配置。不能把某台设备的地址或端口规则直接套用到所有机器。首次启动建议隔离接线，确认接口并设置 root 密码。

### 7. 构建成功，是否代表设备一定能正常用？

不是。成功只证明编译及产物检查通过，仍需实机验证启动、网卡、Wi-Fi、存储、代理与路由功能。升级前备份，避免在没有恢复手段的情况下直接更换正在承担重要网络任务的系统。

### 8. 能不能添加其他插件或设备？

可以修改配置，但设备必须有正确的目标和镜像定义，不能只改文件名。插件也要核对依赖和容量。新手先使用现有配置构建成功，再逐项修改，方便出错时定位原因。

---

## 🧑‍💻 进阶：修改插件或本地编译

只想点网页构建的朋友可以跳过这一节。

插件配置分为：

- `seed.config`：两个版本共有的软件包。
- `profiles/lite.config`：精简版配置。
- `profiles/full.config`：高大全版配置。
- `build-support.py`：平台、设备列表、分区选项、稳定版解析和产物检查。
- `files/etc/uci-defaults/99-xzt8wrt`：主机名、语言与服务自启策略。

添加软件包的常见格式：

```text
CONFIG_PACKAGE_软件包名=y
```

提交后建议先勾选 `configure_only` 检查。`make defconfig` 之后，如果请求的插件被依赖关系丢弃、设备选项失效或该插件不存在，工作流会失败并提示；不要无差别全选互斥插件、其他架构驱动或所有大型软件包。

已经安装 OpenWrt 编译依赖的 **Linux** 环境，可执行：

```sh
PLATFORM=x86 PROFILE=lite bash build.sh
PLATFORM=rockchip PROFILE=full bash build.sh
PLATFORM=filogic PROFILE=lite bash build.sh
# 只检查配置
PREPARE_ONLY=1 PLATFORM=rockchip PROFILE=lite bash build.sh
# 检查辅助逻辑
python3 test-build-support.py
```

工作流使用 Ubuntu 24.04。完整构建建议至少 8 GB 内存和充足磁盘，多设备高大全版需要更多空间。更换源码版本或平台时应使用干净的源码目录，可以用 `SOURCE_DIR` 指向新目录。本地文件修改不会自动提交到 GitHub。

### 构建修复记录

Rust 1.96 的 LLVM CI 下载地址曾返回 404，导致高大全版失败。构建脚本改为从固定源码构建 LLVM，并限制编译与链接并行度；没有删除 Rust 协议组件。补丁保存在产物的 `source-patches.diff` 中。该路径编译时间较长，完整成功仍以 Actions 结果为准。内核定时判断依据与成功基线分别记录在 `kernel-source.json` / Release 的 `kernel-state.json`。


### 🚀 构建完成一组，就发布一组

例如 `x86-lite` 已完成、`rockchip-full` 还在编译，x86 精简版会先发布并可供网站下载。每个成功任务使用独立的 Release，避免并行任务覆盖镜像、校验文件或成功记录。网站刷新后会从最近的发布中查找该设备与版本的镜像。

当前批量任务仍按平台组编译：Rockchip 组内部需要该组选定设备均生成合格镜像后发布；`custom + device` 是单设备任务。配置验证不发布固件，失败或取消的任务不写成功基线。定时检查会合并各独立 Release 的最新成功内核记录，内核没变化仍然跳过。此流程从采用新工作流的下一次运行生效，已在运行或排队的旧任务不会自动切换。


### 🌳 ARM 驱动树与设备适配目录

本仓库的 ARM 适配入口在 [`devices/`](devices/README.md)，17 个目标的配置在 [`devices/targets.json`](devices/targets.json)。构建脚本实际读取这份配置，并在编译前检查、应用登记的本地补丁和文件覆盖。每项补丁必须绑定兼容的正式版本和 SHA256，失败就停止；设备专用改动必须通过 `custom + device` 单独构建，不能混入一整个批量平台。

真正的驱动源码、DTS 设备树与镜像定义，随官方稳定版源码下载到 `immortalwrt/target/linux/`。例如 Rockchip 在 `target/linux/rockchip/`，Filogic 在 `target/linux/mediatek/`，AP120C-AC 在 `target/linux/ipq40xx/`。软件包源通过官方 feeds 获取。

R2S、R4S、R66S、R68S、TR3000、红米 AX6000 等当前已匹配机型先沿用官方设备定义，适配清单的补丁数组为空，这是使用官方驱动的明确状态；没有把空目录当作新增驱动。Kwrt 的额外机型仍需逐项迁移并验证，88 个待适配项仍未开放。构建产物会附带 `arm-adaptation.json` / `arm-adaptation.diff`，记录实际使用的适配层和修改。x86 不读取或应用 ARM 适配层。
