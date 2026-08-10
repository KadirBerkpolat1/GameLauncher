#!/usr/bin/env bash
#
# Rebuilds the bundled modded DepotDownloaderMod Linux standalone from the
# SteamAutoCracks/DepotDownloaderMod fork (supports -depotkeys and -manifestfile).
#
# Output: assets/deps/DepotDownloaderMod
#
# Requires the .NET 9 SDK:  curl -fsSL https://dot.net/v1/dotnet-install.sh \
#   | bash -s -- --channel 9.0 --install-dir "$HOME/.dotnet"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
FORK_URL="https://github.com/SteamAutoCracks/DepotDownloaderMod.git"
FORK_TAG="DepotDownloaderMod_3.4.0.2"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

export DOTNET_CLI_TELEMETRY_OPTOUT=1
export DOTNET_NOLOGO=1
if [ -d "$HOME/.dotnet" ]; then
    export PATH="$HOME/.dotnet:$PATH"
fi

echo "Cloning fork (tag $FORK_TAG)..."
git clone --depth 1 --branch "$FORK_TAG" "$FORK_URL" "$WORKDIR/fork"

echo "Publishing linux-x64 self-contained single-file..."
dotnet publish "$WORKDIR/fork/DepotDownloader/DepotDownloaderMod.csproj" \
    -c Release -r linux-x64 --self-contained true \
    -p:PublishSingleFile=true -p:DebugType=none \
    -p:EnableCompressionInSingleFile=true \
    -o "$WORKDIR/publish"

echo "Verifying mod flags..."
if ! "$WORKDIR/publish/DepotDownloaderMod" 2>&1 | grep -q -- "-manifestfile"; then
    echo "ERROR: built binary does not support -manifestfile" >&2
    exit 1
fi

mkdir -p "$REPO_ROOT/assets/deps"
cp "$WORKDIR/publish/DepotDownloaderMod" "$REPO_ROOT/assets/deps/DepotDownloaderMod"
chmod +x "$REPO_ROOT/assets/deps/DepotDownloaderMod"
cp "$WORKDIR/publish/LICENSE" "$REPO_ROOT/assets/deps/LICENSE" 2>/dev/null || true

echo "Done: $REPO_ROOT/assets/deps/DepotDownloaderMod"
