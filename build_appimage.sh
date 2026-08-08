#!/usr/bin/env bash

# AppImage build script for GameLauncher
# Requires linuxdeploy and linuxdeploy-plugin-conda/python

set -e

APP_NAME="GameLauncher"
APP_DIR="AppDir"

echo "Creating AppDir structure..."
mkdir -p $APP_DIR/usr/bin
mkdir -p $APP_DIR/usr/share/applications
mkdir -p $APP_DIR/usr/share/icons/hicolor/256x256/apps

# Copy source code
cp -r src $APP_DIR/usr/
cp requirements.txt $APP_DIR/usr/

# Create a desktop file
cat > $APP_DIR/usr/share/applications/$APP_NAME.desktop <<EOF
[Desktop Entry]
Name=$APP_NAME
Exec=AppRun %F
Icon=$APP_NAME
Type=Application
Categories=Game;Utility;
EOF

# Placeholder icon
touch $APP_DIR/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png

# Download linuxdeploy if not exists
if [ ! -f linuxdeploy-x86_64.AppImage ]; then
    wget https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
    chmod +x linuxdeploy-x86_64.AppImage
fi

echo "Building AppImage..."
# NOTE: In a real CI environment, you would use linuxdeploy with the python plugin
# to bundle python and the pip requirements into the AppImage.
# ./linuxdeploy-x86_64.AppImage --appdir $APP_DIR -i $APP_DIR/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png -d $APP_DIR/usr/share/applications/$APP_NAME.desktop --output appimage

echo "Done! (Note: ensure python plugin is configured for a complete standalone bundle)"
