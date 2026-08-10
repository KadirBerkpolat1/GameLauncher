#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────
#  Nebula Launcher (GameLauncher) - Kurulum Betiği (Linux)
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

echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║        ${APP_NAME} - Kurulum Betiği          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo

# ── 1. Python kontrolü ──
echo -e "${YELLOW}[1/6]${NC} Python kontrol ediliyor..."
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

# ── 2. Sistem bağımlılıkları (opsiyonel) ──
echo -e "${YELLOW}[2/6]${NC} Sistem bağımlılıkları kontrol ediliyor..."
MISSING=()
if ! command -v 7z &> /dev/null && ! command -v 7za &> /dev/null; then
    MISSING+=("7z (p7zip)")
fi

if [ ${#MISSING[@]} -gt 0 ]; then
    echo -e "${YELLOW}  ! Eksik opsiyonel bağımlılıklar: ${MISSING[*]}${NC}"
    echo "    Arch:   sudo pacman -S p7zip"
    echo "    Debian: sudo apt install p7zip-full"
    echo "    Fedora: sudo dnf install p7zip p7zip-plugins"
    echo -e "    ${YELLOW}SLSsteam kurulumu bu araç olmadan çalışmayacaktır.${NC}"
else
    echo -e "  ${GREEN}✓${NC} 7z mevcut"
fi

# ── 3. Dosyaları kopyala ──
echo -e "${YELLOW}[3/6]${NC} Dosyalar kopyalanıyor → $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp -r "$SCRIPT_DIR/src" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/pyproject.toml" "$INSTALL_DIR/"

if [ -f "$SCRIPT_DIR/LICENSE" ]; then
    cp "$SCRIPT_DIR/LICENSE" "$INSTALL_DIR/"
fi
if [ -d "$SCRIPT_DIR/assets" ]; then
    rm -rf "$INSTALL_DIR/assets"
    cp -r "$SCRIPT_DIR/assets" "$INSTALL_DIR/"
fi
echo -e "  ${GREEN}✓${NC} Dosyalar kopyalandı"

# ── 4. Sanal ortam ve bağımlılıklar ──
echo -e "${YELLOW}[4/6]${NC} Python sanal ortamı hazırlanıyor..."
if [ ! -d "$INSTALL_DIR/venv" ]; then
    python3 -m venv "$INSTALL_DIR/venv"
    echo -e "  ${GREEN}✓${NC} Yeni sanal ortam oluşturuldu"
else
    echo -e "  ${YELLOW}~${NC} Mevcut sanal ortam kullanılıyor"
fi

"$INSTALL_DIR/venv/bin/python" -m pip install --quiet --upgrade pip

# Önce pip install . (console script + pyproject bağımlılıkları), başarısız olursa
# requirements.txt'e düş (ör. build backend indirilemiyorsa).
if "$INSTALL_DIR/venv/bin/python" -m pip install --quiet . ; then
    echo -e "  ${GREEN}✓${NC} Bağımlılıklar pyproject üzerinden kuruldu"
    INSTALLED_AS_PACKAGE=1
else
    echo -e "  ${YELLOW}~${NC} pip install . başarısız, requirements.txt ile deneniyor..."
    "$INSTALL_DIR/venv/bin/python" -m pip install --quiet -r "$INSTALL_DIR/requirements.txt"
    INSTALLED_AS_PACKAGE=0
    echo -e "  ${GREEN}✓${NC} Bağımlılıklar requirements.txt üzerinden kuruldu"
fi

# ── 5. Çalıştırılabilir link ──
echo -e "${YELLOW}[5/6]${NC} Sistem entegrasyonu yapılıyor..."
mkdir -p "$(dirname "$BIN_LINK")"

if [ "${INSTALLED_AS_PACKAGE:-0}" -eq 1 ] && [ -x "$INSTALL_DIR/venv/bin/$BIN_NAME" ]; then
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

# ── 6. Masaüstü kısayolu ──
mkdir -p "$(dirname "$DESKTOP_FILE")"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=$APP_NAME
Comment=Linux Steam Game & DLC Manager
Exec=$BIN_LINK
Icon=applications-games
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
echo -e "  Kaldırmak için:    ${YELLOW}./uninstall.sh${NC}"
echo
