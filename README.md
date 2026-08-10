<div align="center">
  <h1>🎮 GameLauncher (Linux)</h1>
  <p><b>A modern, standalone Steam Game and DLC Manager for Linux.</b></p>
  
  [![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
  [![PySide6](https://img.shields.io/badge/UI-PySide6-green.svg)](https://wiki.qt.io/Qt_for_Python)
  [![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
</div>

---

## ✨ Features

- **HubcapDB REST API Integration:** Fully integrated with the official Hubcap API (`https://hubcapmanifest.com/api/v1`). Browse games, search with AppIDs, and download manifests and Lua files securely.
- **Built-in Installers:** One-click installation and uninstallation of **SLSsteam (Headcrab)** and **DepotDownloaderMod (DDMod)** directly from the UI.
- **Library & Downloads Manager:** Queue multiple games, track your download history, and automatically inject games into your Steam library and SLSsteam configuration.
- **Sleek UI/UX:** A native, hardware-accelerated dark theme built with PySide6, featuring tabbed settings, dynamic badges, and responsive flow layouts.
- **Direct Steam Integration:** Seamlessly restart Steam directly from the launcher to apply VDF/Lua manifest changes instantly.

## 📸 Screenshots

*(Add screenshots here showing the Store, Library, and Installer tabs)*

## 🚀 Installation

### Prerequisites
Make sure you have Python 3.11+ and `p7zip` installed on your system.

```bash
# Arch Linux
sudo pacman -S p7zip git python

# Debian / Ubuntu
sudo apt install p7zip-full git python3 python3-venv
```

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/KadirBerkpolat1/GameLauncher.git
   cd GameLauncher
   ```

2. **Run the installation script:**
   This will automatically set up the virtual environment, install dependencies,
   and create a desktop shortcut. Re-running it upgrades an existing install.
   ```bash
   ./install.sh
   ```

3. **Launch the application:**
   You can run it via the newly created desktop shortcut, or from the terminal:
   ```bash
   gamelauncher
   ```
   *(If `~/.local/bin` is not in your PATH, the installer will show how to add it.)*

## ⚙️ Configuration (API Key)

To fetch manifests and browse the store, you must provide a **HubcapDB API Key**:
1. Get your API key from [HubcapManifest](https://hubcapmanifest.com/api-keys).
2. Open GameLauncher and go to the **SLSsteam / Installer** tab on the left sidebar.
3. Paste your key into the **API Key Configuration** section and click **Save**.

## 🏗️ Architecture

- **`src/ui/`**: PySide6 widgets (Search, Library, Downloads, Game Cards, Settings).
- **`src/api/`**: The `HubcapClient` managing HTTP requests to the HubcapDB endpoints with proper rate-limit and auth handling.
- **`src/services/`**: 
  - `installer.py`: Asynchronous background installation of `.so` files and DLLs.
  - `download.py`: Extracts ZIP manifests, configures VDFs, and talks to DDMod.
- **`src/config/`**: Manages `settings.json` and SLSsteam's `config.yaml`.

## 🗑️ Uninstallation

If you wish to remove GameLauncher, its virtual environments, and downloaded metadata:

```bash
./uninstall.sh
```
*(Note: This does not delete the games you downloaded into your Steam library).*

## 🤝 Contributing
Pull requests are welcome! If you find a bug or want to suggest a feature, please open an issue.

---
<div align="center">
  <i>Built for the Linux gaming community.</i>
</div>
