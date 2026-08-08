#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────
#  GameLauncher - Kurulum Betiği (Linux)
# ─────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

INSTALL_DIR="$HOME/.local/share/GameLauncher"
BIN_LINK="$HOME/.local/bin/gamelauncher"
DESKTOP_FILE="$HOME/.local/share/applications/gamelauncher.desktop"

echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       GameLauncher - Kurulum Betiği      ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo

# ── 1. Python kontrolü ──
echo -e "${YELLOW}[1/5]${NC} Python kontrol ediliyor..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}HATA: python3 bulunamadı!${NC}"
    echo "  Arch:   sudo pacman -S python"
    echo "  Debian: sudo apt install python3 python3-venv"
    echo "  Fedora: sudo dnf install python3"
    exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]); then
    echo -e "${RED}HATA: Python 3.11+ gerekli (mevcut: $PY_VERSION)${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Python $PY_VERSION"

# ── 2. 7z kontrolü (SLSsteam kurulumu için) ──
echo -e "${YELLOW}[2/5]${NC} Sistem bağımlılıkları kontrol ediliyor..."
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
echo -e "${YELLOW}[3/5]${NC} Dosyalar kopyalanıyor → $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# Kaynak dizini belirle (betiğin bulunduğu yer)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp -r "$SCRIPT_DIR/src" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/pyproject.toml" "$INSTALL_DIR/"

if [ -d "$SCRIPT_DIR/assets" ]; then
    cp -r "$SCRIPT_DIR/assets" "$INSTALL_DIR/"
fi
echo -e "  ${GREEN}✓${NC} Dosyalar kopyalandı"

# ── 4. Sanal ortam ve bağımlılıklar ──
echo -e "${YELLOW}[4/5]${NC} Python sanal ortamı oluşturuluyor..."
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r "$INSTALL_DIR/requirements.txt"
deactivate
echo -e "  ${GREEN}✓${NC} Bağımlılıklar kuruldu"

# ── 5. Masaüstü kısayolu ve çalıştırılabilir link ──
echo -e "${YELLOW}[5/5]${NC} Sistem entegrasyonu yapılıyor..."

mkdir -p "$(dirname "$BIN_LINK")"
cat > "$BIN_LINK" << 'LAUNCHER'
#!/usr/bin/env bash
INSTALL_DIR="$HOME/.local/share/GameLauncher"
source "$INSTALL_DIR/venv/bin/activate"
cd "$INSTALL_DIR"
python3 src/main.py "$@"
LAUNCHER
chmod +x "$BIN_LINK"

mkdir -p "$(dirname "$DESKTOP_FILE")"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=GameLauncher
Comment=Linux Steam Game & DLC Manager
Exec=$BIN_LINK
Icon=applications-games
Terminal=false
Type=Application
Categories=Game;Utility;
Keywords=steam;game;dlc;launcher;
EOF

# Masaüstü veritabanını güncelle
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         Kurulum Başarıyla Tamamlandı!    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo
echo -e "  Çalıştırmak için:  ${CYAN}gamelauncher${NC}"
echo -e "  Veya menüden:      ${CYAN}GameLauncher${NC} uygulamasını arayın"
echo
