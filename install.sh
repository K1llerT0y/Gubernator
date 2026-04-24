#!/usr/bin/env bash
# gubr – Arch Linux Installer
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/gubernator"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

echo "==> Installing dependencies..."
sudo pacman -S --needed --noconfirm python-gobject gtk4 libadwaita vulkan-tools

echo "==> Creating directories..."
mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$HOME/.config/gubernator"

echo "==> Copying app..."
cp "$SCRIPT_DIR/icong.svg" "$INSTALL_DIR/icong.svg"
cp "$SCRIPT_DIR/gubernator.py" "$INSTALL_DIR/gubernator.py"
chmod +x "$INSTALL_DIR/gubernator.py"

echo "==> Creating launcher..."
cat > "$BIN_DIR/gubernator" <<EOF
#!/usr/bin/env bash
exec python3 "$INSTALL_DIR/gubernator.py" "\$@"
EOF
chmod +x "$BIN_DIR/gubernator"

echo "==> Creating desktop entry..."
cat > "$DESKTOP_DIR/gubernator.desktop" <<EOF
[Desktop Entry]
Name=Gubernator
Comment=One command, full control
Exec=$BIN_DIR/gubernator
Icon=$INSTALL_DIR/icong.svg
Terminal=false
Type=Application
Categories=Game;Settings;
Keywords=mangohud;gaming;gubr;overlay;proton;vsync;hdr;
EOF

echo ""
echo "✓ Done!"
echo ""
echo "Start the app:"
echo "  gubernator   (or via app menu: 'Gubernator')"
echo ""
echo "Tip: make sure ~/.local/bin is in your PATH:"
echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
