# ARM 设备参考与接入范围

参考仓库：https://github.com/kiddin9/Kwrt/tree/25.12
参考提交：`4ccbbc769b08ecc9d7c80c3f3de651988b6234a0`
设备列表来源：https://openwrt.ai/json/v1/releases/25.12/overview.json
交叉核对版本：ImmortalWrt 25.12.2。

Kwrt 是构建和发布编排项目，包含目标配置、DIY 修改、软件源和在线构建相关流程；不能仅凭仓库文件就确认其所有型号或插件已稳定运行。其部分 Rockchip DIY 会替换 target/linux/rockchip 和 package/boot，并下载其他分支的补丁。它也使用作者自己的部署凭据、服务和外部资源，因此不适合整套覆盖本项目的稳定版构建链。

本次接入的是 ARM 平台与准确设备目录、受限的单设备构建入口。设备驱动、内核、启动组件仍来自本轮解析的 ImmortalWrt 正式稳定版。x86 不采用 Kwrt 配置，也不更改已跑通的 x86 插件和分区配置。现有定时批量组合保持原样。

目录列出 485 个配置匹配项和 88 个待适配项。各项目前均为 configuration-only，表示源码配置可匹配，尚未逐台云端编译和实机测试。构建时仍执行 defconfig 严格检查、实际镜像存在性与 SHA256 校验；未生成该设备有效镜像的任务不会发布成功记录。首次安装可能需要专用引导、过渡固件或恢复步骤，目录不会生成通用过渡固件。

## 更新目录

在本地取得 Kwrt 25.12 参考仓库后执行：

```bash
git clone --filter=blob:none --no-checkout --depth 1 --branch 25.12 https://github.com/kiddin9/Kwrt.git kwrt-reference
python3 sync-arm-catalog.py --kwrt-directory kwrt-reference --version 25.12.2
python3 test-build-support.py
```

脚本只读取参考配置与公开 JSON，不执行 Kwrt DIY 脚本。提交更新后的 docs/catalog.json 前检查新增设备、目标、分区和布局。参考目录固定在提交中；运行构建时不会自动执行第三方脚本。每次构建仍自动选择最新正式稳定版，旧目录中已被上游移除的设备会在配置检查阶段失败，需要更新目录。

## 参考来源许可

感谢 Kwrt、OpenWrt、ImmortalWrt 与设备适配贡献者。下列许可保留 Kwrt 仓库中构建编排参考来源的原始声明；各固件组件仍遵循各自上游许可。

```text
MIT License

Copyright (c) 2019 P3TERX

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
