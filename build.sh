#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SOURCE="${SOURCE_DIR:-$ROOT/immortalwrt}"
COMMIT=4fc16f2985a358bd43bb522e43f05395fcbd6ed5
if [[ ! -d "$SOURCE/.git" ]]; then
  git clone --depth 1 --branch v25.12.2 https://github.com/immortalwrt/immortalwrt.git "$SOURCE"
fi
cd "$SOURCE"
[[ "$(git rev-parse HEAD)" == "$COMMIT" ]] || { echo 'Unexpected source commit'; exit 1; }
./scripts/feeds update -a
./scripts/feeds install -a
cp "$ROOT/seed.config" .config
make defconfig
python3 "$ROOT/check-config.py" "$ROOT/seed.config" .config
mkdir -p files/etc/uci-defaults
cat > files/etc/banner <<'XZT8WRT_EOF'

               _   ___                _
 __  __ ____ _| |_| _ ) __ __ ___ _ _| |_
 \ \/ /|_ / ' \  _| _ \\ V  V / '_|  _|
  >  < /__|_||_\__|___/ \_/\_/|_|  \__|
 /_/\_\

                  xzt8wrt
         ImmortalWrt 25.12.2 / x86_64

XZT8WRT_EOF
cat > files/etc/uci-defaults/99-xzt8wrt <<'XZT8WRT_EOF'
#!/bin/sh
uci set system.@system[0].hostname='xzt8wrt'
uci set luci.main.lang='zh_cn'
uci commit system
uci commit luci
# Extra services are present for configuration, not automatically exposed.
for service in aria2 samba4 ttyd miniupnpd openvpn smartdns adblock sqm pbr ddns openclash passwall dockerd zerotier mwan3; do
    [ ! -x "/etc/init.d/$service" ] || "/etc/init.d/$service" disable
done
exit 0
XZT8WRT_EOF
chmod 0755 files/etc/uci-defaults/99-xzt8wrt
git rev-parse HEAD > source-version.txt
./scripts/feeds list -s > feeds-version.txt
make download -j8
make -j"${JOBS:-2}" BUILD_LOG=1 || make -j1 V=s BUILD_LOG=1
mkdir -p "$ROOT/artifacts"
cp bin/targets/x86/64/* "$ROOT/artifacts/"
cp .config source-version.txt feeds-version.txt "$ROOT/artifacts/"
cd "$ROOT/artifacts"
sha256sum *.img.gz > xzt8wrt-sha256sums
