#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────
#  Nebula Launcher (GameLauncher) - Kaldırma Betiği (Linux)
#  Repo klonlamadan da çalışır:
#    curl -fsSL https://raw.githubusercontent.com/KadirBerkpolat1/GameLauncher/main/uninstall.sh | bash
# ─────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

APP_NAME="Nebula Launcher"
BIN_NAME="gamelauncher"
INSTALL_DIR="$HOME/.local/share/GameLauncher"
BIN_LINK="$HOME/.local/bin/$BIN_NAME"
DESKTOP_FILE="$HOME/.local/share/applications/$BIN_NAME.desktop"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
CONFIG_DIR="$HOME/.config/GameLauncher"
SLS_DIR="$HOME/.local/share/SLSsteam"

# ── Yardımcı: onay sorusu ──
# curl | bash ile çalışırken stdin borudur; o zaman /dev/tty'den okur.
# TTY yoksa (otomatik/CI) varsayılan "hayır" döner.
ask() {
    local prompt="$1"
    if [ -t 0 ]; then
        read -rp "$prompt" REPLY
    elif [ -e /dev/tty ]; then
        read -rp "$prompt" REPLY < /dev/tty
    else
        REPLY=""
    fi
}

echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║      $APP_NAME - Kaldırma Betiği      ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo

# ── Onay ──
ask "$APP_NAME kaldırılacak. Emin misiniz? [e/H]: "
if [[ ! "$REPLY" =~ ^[eEyY]$ ]]; then
    echo "İptal edildi."
    exit 0
fi

echo

# ── 1. Uygulama dosyaları ──
echo -e "${YELLOW}[1/6]${NC} Uygulama dosyaları siliniyor..."
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
    echo -e "  ${GREEN}✓${NC} $INSTALL_DIR silindi"
else
    echo -e "  ${YELLOW}~${NC} Zaten mevcut değil"
fi

# ── 2. Çalıştırılabilir link ──
echo -e "${YELLOW}[2/6]${NC} Çalıştırılabilir link kaldırılıyor..."
if [ -f "$BIN_LINK" ]; then
    rm -f "$BIN_LINK"
    echo -e "  ${GREEN}✓${NC} $BIN_LINK silindi"
else
    echo -e "  ${YELLOW}~${NC} Zaten mevcut değil"
fi

# ── 3. Masaüstü kısayolu + ikon ──
echo -e "${YELLOW}[3/6]${NC} Masaüstü kısayolu ve ikon kaldırılıyor..."
if [ -f "$DESKTOP_FILE" ]; then
    rm -f "$DESKTOP_FILE"
    echo -e "  ${GREEN}✓${NC} $DESKTOP_FILE silindi"
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    fi
else
    echo -e "  ${YELLOW}~${NC} Kısayol zaten mevcut değil"
fi

if [ -d "$ICON_DIR" ]; then
    rm -f "$ICON_DIR"/gamelauncher.* 2>/dev/null || true
fi

# ── 4. Uygulama ayarları + DDMod ──
echo -e "${YELLOW}[4/6]${NC} Uygulama ayarları ve DDMod kurulumu..."
if [ -d "$CONFIG_DIR" ]; then
    ask "  Uygulama ayarlarını da silmek ister misiniz? ($CONFIG_DIR) [e/H]: "
    if [[ "$REPLY" =~ ^[eEyY]$ ]]; then
        rm -rf "$CONFIG_DIR"
        echo -e "  ${GREEN}✓${NC} Ayarlar ve DDMod silindi"
    else
        echo -e "  ${YELLOW}~${NC} Ayarlar korundu"
    fi
else
    echo -e "  ${YELLOW}~${NC} Ayar dizini bulunamadı"
fi

# ── 5. SLSsteam (opsiyonel) ──
echo -e "${YELLOW}[5/6]${NC} SLSsteam (ayrı yazılım)..."
if [ -d "$SLS_DIR" ]; then
    ask "  SLSsteam de kaldırılsın mı? ($SLS_DIR) [e/H]: "
    if [[ "$REPLY" =~ ^[eEyY]$ ]]; then
        if [ -f "$SLS_DIR/setup.sh" ]; then
            bash "$SLS_DIR/setup.sh" uninstall 2>/dev/null || true
        fi
        rm -rf "$SLS_DIR"
        echo -e "  ${GREEN}✓${NC} SLSsteam silindi"
    else
        echo -e "  ${YELLOW}~${NC} SLSsteam korundu"
    fi
else
    echo -e "  ${YELLOW}~${NC} SLSsteam bulunamadı"
fi

# ── 6. Oturum kancaları (varsa) ──
echo -e "${YELLOW}[6/6]${NC} Oturum başlangıç girişleri temizleniyor..."
CLEANED_SHELLRC=0
for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
    if [ -f "$rc" ]; then
        sed -i '/gamelauncher/d; /GameLauncher/d' "$rc" 2>/dev/null || true
        CLEANED_SHELLRC=1
    fi
done
if [ "$CLEANED_SHELLRC" -eq 1 ]; then
    echo -e "  ${GREEN}✓${NC} Shell profillerinden 'gamelauncher' satırları temizlendi"
else
    echo -e "  ${YELLOW}~${NC} Temizlenecek profil bulunamadı"
fi

echo
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Kaldırma Başarıyla Tamamlandı!     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo
echo -e "  ${CYAN}Not:${NC} İndirilen oyunlar ve depotcache dosyaları Steam kütüphanesinde korundu."
echo -e "       Steam'deki 'slssteam' eklentisi Settings → Manage Plug-ins üzerinden kaldırılabilir."
echo
