<div align="center">
  <h1>🎮 Nebula Launcher (GameLauncher for Linux)</h1>
  <p><b>A modern, high-performance Steam Game, DLC & Multiplayer Fix Manager for Linux.</b></p>
  
  [![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
  [![PySide6](https://img.shields.io/badge/UI-PySide6-green.svg)](https://wiki.qt.io/Qt_for_Python)
  [![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
</div>

---

## ✨ Key Features

- **💎 Cyber-Dark Modern UI:** Designed from the ground up with deep acrylic dark theme, glowing hover effects, and responsive flow card layouts.
- **⚡ HubcapDB REST API Integration:** Browse games, search with Steam AppIDs, download manifests, and inspect DLCs with live quota monitoring.
- **🛠️ Smart Multiplayer Fix Engine:** Integrated unified Online-Fix and FreeTP scraper with smart exact-match relevance scoring (filters out spin-offs and DLCs).
- **📊 Real Storage Engine:** Scans real game directory byte sizes from `steamapps/common/` with live GB usage counters.
- **🎨 SteamGridDB v2 Support:** Automatically pulls top community-rated 600x900 vertical posters with seamless Steam Akamai CDN fallback.
- **🔄 Live Steam Process Monitor & Restarter:** Real-time Steam online/offline detection with one-click multi-stage graceful restart.
- **📦 Depot & DLC Granular Selection:** Exclude unneeded DLCs or depots before downloading.

---

## 🚀 Quick Install (Single Command)

Just copy-paste this one-liner in your terminal — it handles everything automatically (dependencies, virtual environment, desktop icon, and CLI commands):

```bash
curl -fsSL https://raw.githubusercontent.com/KadirBerkpolat1/GameLauncher/main/install.sh | bash
```

*Or via jsDelivr CDN:*
```bash
curl -fsSL https://cdn.jsdelivr.net/gh/KadirBerkpolat1/GameLauncher@main/install.sh | bash
```

---

## 💻 Manual Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/KadirBerkpolat1/GameLauncher.git
   cd GameLauncher
   ```

2. **Run the installer:**
   ```bash
   ./install.sh
   ```

3. **Launch the application:**
   ```bash
   gamelauncher
   # or
   nebula
   ```

---

## 🗑️ Uninstallation

To remove Nebula Launcher and all its cached environments:

```bash
curl -fsSL https://raw.githubusercontent.com/KadirBerkpolat1/GameLauncher/main/uninstall.sh | bash
```
