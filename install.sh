#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
#  Nebula Game Launcher - Automated Installer & Updater (Linux)
#  Single-line command:
#    curl -fsSL https://cdn.jsdelivr.net/gh/KadirBerkpolat1/GameLauncher@main/install.sh | bash
# ─────────────────────────────────────────────────────────────────────────────

# ANSI Color Codes
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

APP_NAME="Nebula Launcher"
BIN_NAME="gamelauncher"
ALT_BIN_NAME="nebula"
INSTALL_DIR="$HOME/.local/share/GameLauncher"
BIN_LINK="$HOME/.local/bin/$BIN_NAME"
ALT_BIN_LINK="$HOME/.local/bin/$ALT_BIN_NAME"
DESKTOP_FILE="$HOME/.local/share/applications/$BIN_NAME.desktop"
REPO_URL="https://github.com/KadirBerkpolat1/GameLauncher"
BRANCH="${BRANCH:-main}"

echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║${BOLD}${CYAN}            ✦  NEBULA GAME LAUNCHER INSTALLER  ✦             ${NC}${PURPLE}║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo

# ── 1. Resolve Source Files ──
echo -e "${CYAN}[1/6]${NC} Preparing repository source..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR"

if [ ! -f "$SOURCE_DIR/src/main.py" ] || [ ! -f "$SOURCE_DIR/requirements.txt" ]; then
    echo -e "  ${YELLOW}↓${NC} Fetching latest source archive from GitHub (${BRANCH})..."
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
    echo -e "  ${GREEN}✓${NC} Source ready: $SOURCE_DIR"
else
    echo -e "  ${GREEN}✓${NC} Using local source: $SOURCE_DIR"
fi

# ── 2. Check Python Environment ──
echo -e "${CYAN}[2/6]${NC} Checking Python runtime..."
if ! command -v python3 &> /dev/null; then
    echo -e "  ${RED}ERROR: python3 was not found on your system!${NC}"
    echo "  Please install Python 3.10+ using your package manager."
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "  ${GREEN}✓${NC} Found Python $PY_VERSION"

if ! python3 -m venv --help > /dev/null 2>&1; then
    echo -e "  ${RED}ERROR: python3-venv is missing!${NC}"
    echo "  Debian/Ubuntu: sudo apt install python3-venv"
    echo "  Arch/CachyOS:  sudo pacman -S python"
    exit 1
fi

# ── 3. Check System Extraction Tools (7z, innoextract) ──
echo -e "${CYAN}[3/6]${NC} Checking extraction helpers..."
MISSING_PKGS_ARCH=""
MISSING_PKGS_DEB=""
MISSING_PKGS_DNF=""

if ! (command -v 7z &> /dev/null || command -v 7za &> /dev/null || command -v 7zz &> /dev/null); then
    MISSING_PKGS_ARCH+=" p7zip"
    MISSING_PKGS_DEB+=" p7zip-full"
    MISSING_PKGS_DNF+=" p7zip p7zip-plugins"
fi

if ! command -v innoextract &> /dev/null; then
    MISSING_PKGS_ARCH+=" innoextract"
    MISSING_PKGS_DEB+=" innoextract"
    MISSING_PKGS_DNF+=" innoextract"
fi

if [ -n "$MISSING_PKGS_ARCH" ]; then
    echo -e "  ${YELLOW}! Recommended helper tools missing:${NC}$MISSING_PKGS_ARCH"
    if command -v pacman &> /dev/null && command -v sudo &> /dev/null; then
        echo -e "  ${YELLOW}→${NC} Install with: sudo pacman -S$MISSING_PKGS_ARCH"
    elif command -v apt-get &> /dev/null && command -v sudo &> /dev/null; then
        echo -e "  ${YELLOW}→${NC} Install with: sudo apt install$MISSING_PKGS_DEB"
    fi
else
    echo -e "  ${GREEN}✓${NC} Extraction helpers present"
fi

# ── 4. Synchronize Files ──
echo -e "${CYAN}[4/6]${NC} Installing application files → $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

rm -rf "$INSTALL_DIR/src"
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
echo -e "  ${GREEN}✓${NC} Core files synchronized"

# ── 5. Setup Isolated Python Virtual Environment ──
echo -e "${CYAN}[5/6]${NC} Setting up Python virtual environment..."
if [ ! -d "$INSTALL_DIR/venv" ]; then
    python3 -m venv "$INSTALL_DIR/venv"
    echo -e "  ${GREEN}✓${NC} Virtual environment created"
fi

"$INSTALL_DIR/venv/bin/python" -m pip install --quiet --upgrade pip
"$INSTALL_DIR/venv/bin/python" -m pip install --quiet -r "$INSTALL_DIR/requirements.txt"
echo -e "  ${GREEN}✓${NC} Python packages installed (PySide6, httpx, vdf, etc.)"

# ── 6. System Integration (Binaries & Desktop Icon) ──
echo -e "${CYAN}[6/6]${NC} Creating desktop entry and CLI shortcuts..."
mkdir -p "$(dirname "$BIN_LINK")"

# Executable launcher script
cat > "$BIN_LINK" << 'LAUNCHER'
#!/usr/bin/env bash
INSTALL_DIR="$HOME/.local/share/GameLauncher"
cd "$INSTALL_DIR"
exec "$INSTALL_DIR/venv/bin/python" src/main.py "$@"
LAUNCHER
chmod +x "$BIN_LINK"

# Secondary alias 'nebula'
cp "$BIN_LINK" "$ALT_BIN_LINK"
chmod +x "$ALT_BIN_LINK"

# Desktop Entry
mkdir -p "$(dirname "$DESKTOP_FILE")"
ICON_PATH="applications-games"

if [ -d "$SOURCE_DIR/assets/icons" ]; then
    ICON_SRC=$(find "$SOURCE_DIR/assets/icons" -maxdepth 1 \( -name '*.png' -o -name '*.svg' \) | head -n1 || true)
    if [ -n "$ICON_SRC" ]; then
        ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
        mkdir -p "$ICON_DIR"
        cp "$ICON_SRC" "$ICON_DIR/$BIN_NAME.png"
        ICON_PATH="$BIN_NAME.png"
    fi
fi

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=$APP_NAME
Comment=Cyber-Dark Linux Steam Game & DLC Manager
Exec=$BIN_LINK
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=Game;Utility;
Keywords=steam;game;dlc;launcher;nebula;
EOF

if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi
echo -e "  ${GREEN}✓${NC} Desktop integration complete"

# PATH warning if needed
if ! echo ":$PATH:" | grep -q ":$HOME/.local/bin:"; then
    echo
    echo -e "  ${YELLOW}! Note: '$HOME/.local/bin' is not in your PATH.${NC}"
    echo "    Add it by running: echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
fi

echo
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${BOLD}            ✦  Installation Completed Successfully! ✦         ${NC}${GREEN}║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "  Launch via Terminal:  ${CYAN}gamelauncher${NC}  or  ${CYAN}nebula${NC}"
echo -e "  Launch via Desktop:   Search for ${BOLD}${CYAN}$APP_NAME${NC} in your app launcher"
echo
