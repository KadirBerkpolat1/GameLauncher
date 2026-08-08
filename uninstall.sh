#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────
#  GameLauncher - Kaldırma Betiği (Linux)
# ─────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="$HOME/.local/share/GameLauncher"
BIN_LINK="$HOME/.local/bin/gamelauncher"
DESKTOP_FILE="$HOME/.local/share/applications/gamelauncher.desktop"
CONFIG_DIR="$HOME/.config/GameLauncher"

echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║      GameLauncher - Kaldırma Betiği      ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo

# ── Onay ──
read -rp "GameLauncher kaldırılacak. Emin misiniz? [e/H]: " CONFIRM
if [[ ! "$CONFIRM" =~ ^[eEyY]$ ]]; then
    echo "İptal edildi."
    exit 0
fi

echo

# ── 1. Uygulama dosyaları ──
echo -e "${YELLOW}[1/4]${NC} Uygulama dosyaları siliniyor..."
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
    echo -e "  ${GREEN}✓${NC} $INSTALL_DIR silindi"
else
    echo -e "  ${YELLOW}~${NC} Zaten mevcut değil"
fi

# ── 2. Çalıştırılabilir link ──
echo -e "${YELLOW}[2/4]${NC} Çalıştırılabilir link kaldırılıyor..."
if [ -f "$BIN_LINK" ]; then
    rm -f "$BIN_LINK"
    echo -e "  ${GREEN}✓${NC} $BIN_LINK silindi"
else
    echo -e "  ${YELLOW}~${NC} Zaten mevcut değil"
fi

# ── 3. Masaüstü kısayolu ──
echo -e "${YELLOW}[3/4]${NC} Masaüstü kısayolu kaldırılıyor..."
if [ -f "$DESKTOP_FILE" ]; then
    rm -f "$DESKTOP_FILE"
    echo -e "  ${GREEN}✓${NC} $DESKTOP_FILE silindi"
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    fi
else
    echo -e "  ${YELLOW}~${NC} Zaten mevcut değil"
fi

# ── 4. Ayarlar (opsiyonel) ──
echo -e "${YELLOW}[4/4]${NC} Uygulama ayarları..."
if [ -d "$CONFIG_DIR" ]; then
    read -rp "  Uygulama ayarlarını da silmek ister misiniz? ($CONFIG_DIR) [e/H]: " DEL_CONFIG
    if [[ "$DEL_CONFIG" =~ ^[eEyY]$ ]]; then
        rm -rf "$CONFIG_DIR"
        echo -e "  ${GREEN}✓${NC} Ayarlar silindi"
    else
        echo -e "  ${YELLOW}~${NC} Ayarlar korundu"
    fi
else
    echo -e "  ${YELLOW}~${NC} Ayar dizini bulunamadı"
fi

echo
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Kaldırma Başarıyla Tamamlandı!     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo
echo -e "  ${CYAN}Not:${NC} SLSsteam ayrı bir yazılımdır ve bu betik tarafından kaldırılmaz."
echo -e "       SLSsteam'i kaldırmak için: ${YELLOW}~/.local/share/SLSsteam/setup.sh uninstall${NC}"
echo
