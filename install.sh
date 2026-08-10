#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────
#  Nebula Launcher (GameLauncher) - Kurulum Betiği (Linux)
#  Tek komutla çalışır:
#    curl -fsSL https://cdn.jsdelivr.net/gh/KadirBerkpolat1/GameLauncher@main/install.sh | bash
#  Güvenli yeniden çalıştırılabilir: mevcut kurulumu yükseltir.
# ─────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

APP_NAME="Nebula Launcher"
BIN_NAME="gamelauncher"
INSTALL_DIR="$HOME/.local/share/GameLauncher"
BIN_LINK="$HOME/.local/bin/$BIN_NAME"
DESKTOP_FILE="$HOME/.local/share/applications/$BIN_NAME.desktop"
REPO_URL="https://github.com/KadirBerkpolat1/GameLauncher"
BRANCH="${BRANCH:-main}"

# ── Yardımcı: onay sorusu ──
# curl | bash ile çalışırken stdin borudur; o zaman /dev/tty'den okur.
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

echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║        ${APP_NAME} - Kurulum Betiği          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo

# ── 1. Kaynak dizin çözümü ──
echo -e "${YELLOW}[1/7]${NC} Kaynak hazırlanıyor..."
# curl | bash ile çalışırken BASH_SOURCE[0] boştur; ".." güvenli bir varsayılandır.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR"

if [ ! -f "$SOURCE_DIR/src/main.py" ] || [ ! -f "$SOURCE_DIR/requirements.txt" ]; then
    echo -e "  ${YELLOW}~${NC} Repo klasöründe değiliz, GitHub tarball indiriliyor..."
    TMP_DIR="$(mktemp -d)"
    trap 'rm -rf "$TMP_DIR"' EXIT
    if command -v curl &> /dev/null; then
        curl -fsSL -o "$TMP_DIR/gl.tar.gz" "$REPO_URL/archive/refs/heads/$BRANCH.tar.gz"
    elif command -v wget &> /dev/null; then
        wget -qO "$TMP_DIR/gl.tar.gz" "$REPO_URL/archive/refs/heads/$BRANCH.tar.gz"
    else
        git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMP_DIR/repo"
        SOURCE_DIR="$TMP_DIR/repo"
    fi
    if [ -f "$TMP_DIR/gl.tar.gz" ]; then
        tar -xzf "$TMP_DIR/gl.tar.gz" -C "$TMP_DIR"
        SOURCE_DIR="$TMP_DIR/GameLauncher-$BRANCH"
    fi
    echo -e "  ${GREEN}✓${NC} Kaynak hazır: $SOURCE_DIR"
else
    echo -e "  ${GREEN}✓${NC} Yerel repo kullanılıyor: $SOURCE_DIR"
fi

# ── 2. Python kontrolü ──
echo -e "${YELLOW}[2/7]${NC} Python kontrol ediliyor..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}HATA: python3 bulunamadı!${NC}"
    echo "  Arch:   sudo pacman -S python"
    echo "  Debian: sudo apt install python3 python3-venv python3-pip"
    echo "  Fedora: sudo dnf install python3 python3-pip"
    exit 1
fi

PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
    echo -e "${RED}HATA: Python 3.11+ gerekli (mevcut: $PY_MAJOR.$PY_MINOR)${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Python $PY_MAJOR.$PY_MINOR"

# python3-venv (ensurepip) kontrolü
if ! python3 -m venv --help > /dev/null 2>&1; then
    echo -e "${RED}HATA: python3-venv modülü bulunamadı!${NC}"
    echo "  Debian/Ubuntu: sudo apt install python3-venv"
    echo "  Arch (ayrı paket gerekmiyor, python ile gelir)."
    exit 1
fi

# ── 3. Sistem bağımlılıkları (7z) ──
echo -e "${YELLOW}[3/7]${NC} Sistem bağımlılıkları kontrol ediliyor..."
if command -v 7z &> /dev/null || command -v 7za &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} 7z mevcut"
else
    echo -e "  ${YELLOW}  ! 7z (p7zip) bulunamadı. SLSsteam kurulumu onsuz çalışmaz.${NC}"
    if command -v sudo &> /dev/null && [ -z "${NONINTERACTIVE:-}" ]; then
        ask "  p7zip otomatik kurulsun mu? [e/H]: "
        if [[ "$REPLY" =~ ^[eEyY]$ ]]; then
            if command -v pacman &> /dev/null; then
                sudo pacman -S --needed p7zip
            elif command -v apt-get &> /dev/null; then
                sudo apt-get update && sudo apt-get install -y p7zip-full
            elif command -v dnf &> /dev/null; then
                sudo dnf install -y p7zip p7zip-plugins
            else
                echo -e "${RED}    Dağıtım algılanamadı, elle kurun: 7z (p7zip)${NC}"
            fi
            if command -v 7z &> /dev/null || command -v 7za &> /dev/null; then
                echo -e "  ${GREEN}✓${NC} p7zip kuruldu"
            fi
        else
            echo -e "  ${YELLOW}  ~ Atlandı. Launcher yine de çalışır, SLSsteam kurulumu ise eksik kalır.${NC}"
        fi
    else
        echo "    Arch:   sudo pacman -S p7zip"
        echo "    Debian: sudo apt install p7zip-full"
        echo "    Fedora: sudo dnf install p7zip p7zip-plugins"
    fi
fi

# ── 4. Dosyaları kopyala ──
echo -e "${YELLOW}[4/7]${NC} Dosyalar kopyalanıyor → $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

cp -r "$SOURCE_DIR/src" "$INSTALL_DIR/"
cp "$SOURCE_DIR/requirements.txt" "$INSTALL_DIR/"
cp "$SOURCE_DIR/pyproject.toml" "$INSTALL_DIR/"

if [ -f "$SOURCE_DIR/LICENSE" ]; then
    cp "$SOURCE_DIR/LICENSE" "$INSTALL_DIR/"
fi
if [ -d "$SOURCE_DIR/assets" ]; then
    rm -rf "$INSTALL_DIR/assets"
    cp -r "$SOURCE_DIR/assets" "$INSTALL_DIR/"
fi
echo -e "  ${GREEN}✓${NC} Dosyalar kopyalandı"

# ── 5. Sanal ortam ve bağımlılıklar ──
echo -e "${YELLOW}[5/7]${NC} Python sanal ortamı hazırlanıyor..."
if [ ! -d "$INSTALL_DIR/venv" ]; then
    python3 -m venv "$INSTALL_DIR/venv"
    echo -e "  ${GREEN}✓${NC} Yeni sanal ortam oluşturuldu"
else
    echo -e "  ${YELLOW}~${NC} Mevcut sanal ortam kullanılıyor"
fi

"$INSTALL_DIR/venv/bin/python" -m pip install --quiet --upgrade pip

# Önce pip install . (console script + pyproject bağımlılıkları), başarısız olursa
# requirements.txt'e düş (ör. build backend indirilemiyorsa).
if (cd "$SOURCE_DIR" && "$INSTALL_DIR/venv/bin/python" -m pip install --quiet .); then
    echo -e "  ${GREEN}✓${NC} Bağımlılıklar pyproject üzerinden kuruldu"
    INSTALLED_AS_PACKAGE=1
else
    echo -e "  ${YELLOW}~${NC} pip install . başarısız, requirements.txt ile deneniyor..."
    "$INSTALL_DIR/venv/bin/python" -m pip install --quiet -r "$INSTALL_DIR/requirements.txt"
    INSTALLED_AS_PACKAGE=0
    echo -e "  ${GREEN}✓${NC} Bağımlılıklar requirements.txt üzerinden kuruldu"
fi

# ── 6. Çalıştırılabilir link ──
echo -e "${YELLOW}[6/7]${NC} Sistem entegrasyonu yapılıyor..."
mkdir -p "$(dirname "$BIN_LINK")"

if [ "${INSTALLED_AS_PACKAGE:-0}" -eq 1 ] && [ -x "$INSTALL_DIR/venv/bin/$BIN_NAME" ]; then
    # Console script paket olarak kuruldu. Bundled DDMod binary'sini de
    # site-packages'e taşı ki offline kurulumda BUNDLED_PATH bulunabilsin.
    PURELIB="$("$INSTALL_DIR/venv/bin/python" -c "import sysconfig; print(sysconfig.get_paths()['purelib'])")"
    rm -rf "$PURELIB/assets"
    cp -r "$INSTALL_DIR/assets" "$PURELIB/assets"
    cat > "$BIN_LINK" << LAUNCHER
#!/usr/bin/env bash
exec "$INSTALL_DIR/venv/bin/$BIN_NAME" "\$@"
LAUNCHER
    echo -e "  ${GREEN}✓${NC} Console script bağlandı ($BIN_NAME)"
else
    cat > "$BIN_LINK" << 'LAUNCHER'
#!/usr/bin/env bash
INSTALL_DIR="$HOME/.local/share/GameLauncher"
cd "$INSTALL_DIR"
exec "$INSTALL_DIR/venv/bin/python" src/main.py "$@"
LAUNCHER
    echo -e "  ${YELLOW}~${NC} Kaynak moduyla çalışan bağlantı oluşturuldu"
fi
chmod +x "$BIN_LINK"

# ── 7. Masaüstü kısayolu + ikon ──
mkdir -p "$(dirname "$DESKTOP_FILE")"

# assets/icons içinde bir ikon varsa ~/.local/share/icons altına kopyala.
ICON_PATH=""
if [ -d "$SOURCE_DIR/assets/icons" ]; then
    ICON_SRC=$(find "$SOURCE_DIR/assets/icons" -maxdepth 1 \( -name '*.png' -o -name '*.svg' \) | head -n1 || true)
    if [ -n "$ICON_SRC" ]; then
        ICON_NAME="gamelauncher"
        ICON_EXT="${ICON_SRC##*.}"
        ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
        mkdir -p "$ICON_DIR"
        cp "$ICON_SRC" "$ICON_DIR/$ICON_NAME.$ICON_EXT"
        ICON_PATH="$ICON_NAME.$ICON_EXT"
    fi
fi

if [ -z "$ICON_PATH" ]; then
    ICON_PATH="applications-games"
fi

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=$APP_NAME
Comment=Linux Steam Game & DLC Manager
Exec=$BIN_LINK
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=Game;Utility;
Keywords=steam;game;dlc;launcher;
EOF

if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi
echo -e "  ${GREEN}✓${NC} Masaüstü kısayolu oluşturuldu"

# ~/.local/bin PATH kontrolü
if ! echo ":$PATH:" | grep -q ":$(dirname "$BIN_LINK"):"; then
    echo
    echo -e "${YELLOW}  ! Not: '$HOME/.local/bin' PATH'inizde yok.${NC}"
    echo "    Shell profilinize şunu ekleyin:"
    echo "      echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
    echo "    Sonra: source ~/.bashrc"
fi

echo
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Kurulum Başarıyla Tamamlandı!       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo
echo -e "  Çalıştırmak için:  ${CYAN}$BIN_NAME${NC}"
echo -e "  Veya menüden:      ${CYAN}$APP_NAME${NC} uygulamasını arayın"
echo -e "  Kaldırmak için:    ${YELLOW}./uninstall.sh${NC} (repo) veya"
echo -e "    ${CYAN}curl -fsSL https://cdn.jsdelivr.net/gh/KadirBerkpolat1/GameLauncher@main/uninstall.sh | bash${NC}"
echo
