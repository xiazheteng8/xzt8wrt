# 🌳 ARM 设备适配层

这里是 xzt8wrt 的 ARM 适配入口，构建时实际使用。`targets.json` 存放 17 个目标的配置、官方驱动树路径和本地补丁登记表；不是完整 Linux 源码副本。

## 普通用户怎么用？

1. 打开 [固件工坊](https://xiazheteng8.github.io/xzt8wrt/)，选择准确型号和版本。
2. 按页面给出的参数启动 GitHub Actions，初次建议勾选 `configure_only`。
3. 构建脚本下载最新正式稳定版源码，读取本目录配置，检查官方驱动树存在，再应用该目标登记的补丁和设备文件。
4. 配置验证通过后再运行完整构建。成功后每个任务立即发布固件，失败时查看诊断文件。

[AP120C-AC 精简版快捷入口](https://xiazheteng8.github.io/xzt8wrt/?device=ipq40xx%2Fgeneric%2Falfa-network_ap120c-ac&profile=lite)只是预选参数，不会自动启动编译，也不保证已有下载。

## 驱动源码在哪里？

GitHub 编译机下载的源码目录是 `immortalwrt/`，其中：

| 设备平台 | 官方驱动、DTS 与镜像定义所在目录 |
| --- | --- |
| Rockchip（R2S/R4S/R66S/R68S 等） | `target/linux/rockchip/` |
| MediaTek（TR3000、红米 AX6000 等） | `target/linux/mediatek/` |
| IPQ40xx（AP120C-AC 等） | `target/linux/ipq40xx/` |
| IPQ50xx/60xx/807x | `target/linux/qualcommax/` |
| 其他 ARM | 以 `targets.json` 的 `upstream_tree` 为准 |

网卡、无线芯片等额外软件包通过本轮官方 feeds 获取。x86 不读取、不应用 ARM 适配层，原有配置不变。

## 当前接入状态

当前目标的 `driver_source` 为 `official-stable`，`patches` 和 `overlays` 为空：沿用官方稳定版已有驱动和设备定义。新建适配层不等于导入了 Kwrt 的所有驱动，也不代表目录内设备全部编译或实机验证通过。Kwrt 特有的 88 个待适配项仍未开放。

不执行 Kwrt 的远程 DIY 脚本，不整棵替换内核/启动树。需要其额外驱动时，先核对依赖、许可和准确设备布局，迁移成下面的本地、固定版本适配，再做完整编译和实机测试。

## 开发者如何登记补丁？

例如未来给某个目标增加一项已经审核的补丁，在本目录创建 `patches/平台/0001-说明.patch`，然后在对应目标的 `patches` 数组登记：

```json
{
  "path": "patches/平台/0001-说明.patch",
  "sha256": "补丁文件的完整SHA256",
  "versions": ["25.12.2"],
  "device": "准确的设备ID"
}
```

`device` 可省略，表示该目标通用补丁；填写后仅允许匹配的单设备构建。如果批量组选中了此设备，构建会停止，要求改用 `custom + device`，避免让一个型号的分区改动影响整组。

- 哈希通过 `shasum -a 256 补丁路径`（macOS）或 `sha256sum 补丁路径`（Linux）计算。
- 只有列入 `versions` 的正式版才能应用；新版发布后必须重新检查并更新登记，不会静默跳过。
- 依登记顺序运行 `git apply --check` 和 `git apply`，不支持模糊忽略失败。
- 修改范围只允许该 ARM 驱动树、`target/linux/generic/` 和 `package/boot/`。通用内核改动也只作用于本次 ARM 源码工作目录。
- 所有文件必须位于本仓库 `devices/` 内，不在构建时下载或执行第三方脚本。
- 每次适配应使用干净的源码工作目录，失败后不要反复对已经改过的目录套补丁。

## 添加 DTS 或驱动源文件

在 `devices/files/平台/` 中保存实际文件，在对应目标的 `overlays` 数组登记：

```json
{
  "path": "files/平台/设备.dts",
  "destination": "target/linux/该平台/正确的上游相对路径/设备.dts",
  "sha256": "源文件的完整SHA256",
  "versions": ["25.12.2"],
  "device": "准确的设备ID"
}
```

设备树和驱动源码路径必须根据上游真实目录填写；文件覆盖范围同样受限，不能写出源码目录。当前覆盖入口用于驱动、DTS 与启动源文件，通用固件设置仍在仓库根目录的 `files/`。单纯增加一个 DTS 还不够，还需要正确的内核配置、镜像定义和启动布局。

新增目标时，还要核对 `docs/catalog.json`、`config`、`device_prefix` 和 `disk_images`。未知目标默认停止，不会猜测配置。

## 如何确认本轮应用了什么？

成功产物和每台设备的 ZIP 会附带：

- `arm-adaptation.json`：目标、设备、正式版本、适配清单哈希和已应用项。
- `arm-adaptation.diff`：已跟踪的驱动/启动源文件差异；新覆盖文件的来源和哈希记录在 JSON 中。

数组为空且 diff 为空代表本轮直接使用官方驱动树。构建通过仍需验证启动、有线网口、Wi-Fi、存储和刷机/恢复流程。
