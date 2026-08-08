#!/usr/bin/env bash
# slssteam_install.sh — SLSsteam kurulum betiği
# GameLauncher tarafından çağrılır: bash slssteam_install.sh [install|uninstall]
set -euo pipefail

SLS_INSTALL_DIR="$HOME/.local/share/SLSsteam"
FLATPAK_SLS_DIR="$HOME/.var/app/com.valvesoftware.Steam/.local/share/SLSsteam"
SLS_CONFIG_DIR="$HOME/.config/SLSsteam"
FLATPAK_CONFIG_DIR="$HOME/.var/app/com.valvesoftware.Steam/.config/SLSsteam"
FLATPAK_STEAM_DIR="$HOME/.var/app/com.valvesoftware.Steam/.steam/steam"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

is_flatpak() { [ -d "$FLATPAK_STEAM_DIR" ]; }

download_slssteam() {
    echo "Fetching latest SLSsteam release tag..."
    local TAG
    TAG=$(curl -sSL --connect-timeout 15 --max-time 30 \
        -o /dev/null -w "%{url_effective}" \
        "https://github.com/AceSLS/SLSsteam/releases/latest" 2>/dev/null)
    TAG="${TAG##*/}"
    echo "Downloading SLSsteam $TAG..."
    wget -q --show-progress \
        -O "$TMP_DIR/SLSsteam-Any.7z" \
        "https://github.com/AceSLS/SLSsteam/releases/download/$TAG/SLSsteam-Any.7z"
    echo "Extracting..."
    7z x "$TMP_DIR/SLSsteam-Any.7z" -o"$TMP_DIR/extracted" -aoa > /dev/null
    echo "$TAG"
}

install_slssteam() {
    local TAG
    TAG=$(download_slssteam)

    local BIN_DIR="$TMP_DIR/extracted/bin"
    if [ ! -f "$BIN_DIR/SLSsteam.so" ]; then
        echo "ERROR: SLSsteam.so not found in archive" >&2
        exit 1
    fi

    if is_flatpak; then
        echo "Flatpak Steam detected, installing to $FLATPAK_SLS_DIR"
        mkdir -p "$FLATPAK_SLS_DIR"
        mkdir -p "$FLATPAK_CONFIG_DIR"
        cp -f "$BIN_DIR/library-inject.so" "$FLATPAK_SLS_DIR/"
        cp -f "$BIN_DIR/SLSsteam.so"       "$FLATPAK_SLS_DIR/"
        local CFG_TARGET="$FLATPAK_CONFIG_DIR/config.yaml"
    else
        echo "Native Steam detected, installing to $SLS_INSTALL_DIR"
        mkdir -p "$SLS_INSTALL_DIR"
        mkdir -p "$SLS_CONFIG_DIR"
        cp -f "$BIN_DIR/library-inject.so" "$SLS_INSTALL_DIR/"
        cp -f "$BIN_DIR/SLSsteam.so"       "$SLS_INSTALL_DIR/"
        local CFG_TARGET="$SLS_CONFIG_DIR/config.yaml"
    fi

    # Sadece config yoksa varsayılan kopyala
    if [ ! -f "$CFG_TARGET" ] && [ -f "$TMP_DIR/extracted/res/config.yaml" ]; then
        cp "$TMP_DIR/extracted/res/config.yaml" "$CFG_TARGET"
        echo "Default config.yaml installed."
    fi

    echo "SLSsteam $TAG installed successfully."
}

uninstall_slssteam() {
    echo "Uninstalling SLSsteam..."
    rm -rf "$SLS_INSTALL_DIR"
    rm -rf "$FLATPAK_SLS_DIR"
    rm -rf "$SLS_CONFIG_DIR"
    rm -rf "$FLATPAK_CONFIG_DIR"
    echo "SLSsteam removed."
}

case "${1:-install}" in
    install)   install_slssteam ;;
    uninstall) uninstall_slssteam ;;
    *)
        echo "Usage: $0 [install|uninstall]" >&2
        exit 1
        ;;
esac
