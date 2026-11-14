#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SOURCE="${SOURCE_DIR:-$ROOT/immortalwrt}"
PROFILE="${PROFILE:-full}"
case "$PROFILE" in full|lite) ;; *) echo "Unknown profile: $PROFILE" >&2; exit 2 ;; esac
COMMIT=4fc16f2985a358bd43bb522e43f05395fcbd6ed5
if [[ ! -d "$SOURCE/.git" ]]; then
  git clone --depth 1 --branch v25.12.2 https://github.com/immortalwrt/immortalwrt.git "$SOURCE"
fi
cd "$SOURCE"
[[ "$(git rev-parse HEAD)" == "$COMMIT" ]] || { echo 'Unexpected source commit'; exit 1; }
./scripts/feeds update -a
./scripts/feeds install -a
cat "$ROOT/seed.config" "$ROOT/profiles/$PROFILE.config" > .config
cp .config requested.config
make defconfig
python3 "$ROOT/check-config.py" requested.config .config
mkdir -p files/etc/uci-defaults
cp -a "$ROOT/files/." files/
chmod 0755 files/etc/uci-defaults/99-xzt8wrt
printf '%s\n' "$PROFILE" > files/etc/xzt8wrt-profile
git rev-parse HEAD > source-version.txt
./scripts/feeds list -s > feeds-version.txt
make download -j8
make -j"${JOBS:-2}" BUILD_LOG=1 || make -j1 V=s BUILD_LOG=1
ARTIFACTS="$ROOT/artifacts/$PROFILE"
mkdir -p "$ARTIFACTS"
find bin/targets/x86/64 -maxdepth 1 -type f -exec cp {} "$ARTIFACTS/" \;
cp .config requested.config source-version.txt feeds-version.txt "$ARTIFACTS/"
printf '%s\n' "$PROFILE" > "$ARTIFACTS/profile.txt"
cd "$ARTIFACTS"
sha256sum *.img.gz > xzt8wrt-sha256sums
