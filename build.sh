#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SOURCE="${SOURCE_DIR:-$ROOT/immortalwrt}"
PROFILE="${PROFILE:-full}"
PLATFORM="${PLATFORM:-x86}"
python3 "$ROOT/build-support.py" config --platform "$PLATFORM" --profile "$PROFILE" > "$ROOT/requested.config"
if [[ -n "${SOURCE_REF:-}" && -n "${SOURCE_COMMIT:-}" && -n "${SOURCE_VERSION:-}" ]]; then
  python3 -c 'import json,os; print(json.dumps({"ref":os.environ["SOURCE_REF"],"commit":os.environ["SOURCE_COMMIT"],"version":os.environ["SOURCE_VERSION"]}))' > "$ROOT/source.json"
else
  python3 "$ROOT/build-support.py" resolve > "$ROOT/source.json"
fi
REF="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["ref"])' "$ROOT/source.json")"
COMMIT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["commit"])' "$ROOT/source.json")"
VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$ROOT/source.json")"
if [[ ! -d "$SOURCE/.git" ]]; then
  git clone --depth 1 --branch "$REF" https://github.com/immortalwrt/immortalwrt.git "$SOURCE"
fi
cd "$SOURCE"
[[ "$(git rev-parse HEAD)" == "$COMMIT" ]] || { echo "Source mismatch: use a fresh SOURCE_DIR for $REF" >&2; exit 1; }
./scripts/feeds update -a
./scripts/feeds install -a
python3 "$ROOT/build-support.py" fix-rust --source "$SOURCE"
cp "$ROOT/requested.config" .config
cp .config requested.config
cp "$ROOT/source.json" source.json
if [[ -n "${SOURCE_KERNEL:-}" ]]; then
  printf '%s\n' "$SOURCE_KERNEL" > kernel-source.json
else
  python3 "$ROOT/build-support.py" kernel --platform "$PLATFORM" --version "$VERSION" > kernel-source.json
fi
make defconfig
python3 "$ROOT/check-config.py" requested.config .config
mkdir -p files/etc/uci-defaults
cp -a "$ROOT/files/." files/
chmod 0755 files/etc/uci-defaults/99-xzt8wrt
printf '\n  xzt8wrt\n  ImmortalWrt %s / %s / %s\n\n' "$VERSION" "$PLATFORM" "$PROFILE" > files/etc/banner
printf '%s\n' "$PROFILE" > files/etc/xzt8wrt-profile
git rev-parse HEAD > source-version.txt
./scripts/feeds list -s > feeds-version.txt
[[ "${PREPARE_ONLY:-0}" != 1 ]] || exit 0
make download -j8
make -j"${JOBS:-2}" BUILD_LOG=1 || make -j1 V=s BUILD_LOG=1
ARTIFACTS="$ROOT/artifacts/$PLATFORM-$PROFILE"
rm -rf "$ARTIFACTS"
python3 "$ROOT/build-support.py" collect --platform "$PLATFORM" --source "$SOURCE" --output "$ARTIFACTS"
