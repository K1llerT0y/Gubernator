#!/usr/bin/env bash
# gubr – Multi-Distro Installer
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/gubernator"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

# ── Detect distro ─────────────────────────────────────────
detect_distro() {
    if [ ! -f /etc/os-release ]; then
        echo "Error: Could not detect Linux distribution (/etc/os-release not found)."
        exit 1
    fi
    . /etc/os-release
    DISTRO="${ID,,}"          # lowercase, e.g. arch, ubuntu, fedora
    DISTRO_LIKE="${ID_LIKE,,}" # family fallback, e.g. "debian", "rhel fedora"
}

# ── Install dependencies ───────────────────────────────────
install_dependencies() {
    case "$DISTRO" in

        # ── Arch family ───────────────────────────────────
        arch | manjaro | endeavouros | cachyos | garuda)
            echo "==> Detected distro: $DISTRO (Arch family)"
            sudo pacman -S --needed --noconfirm \
                python-gobject gtk4 libadwaita vulkan-tools
            ;;

        # ── Debian / Ubuntu family ────────────────────────
        debian | ubuntu | linuxmint | pop | zorin | elementary)
            echo "==> Detected distro: $DISTRO (Debian family)"
            sudo apt-get update -y
            sudo apt-get install -y \
                python3-gi python3-gi-cairo \
                gir1.2-gtk-4.0 \
                gir1.2-adw-1 \
                libadwaita-1-0 \
                vulkan-tools
            ;;

        # ── Fedora ────────────────────────────────────────
        fedora)
            echo "==> Detected distro: $DISTRO (Fedora)"
            sudo dnf install -y \
                python3-gobject \
                gtk4 \
                libadwaita \
                vulkan-tools
            ;;

        # ── openSUSE ──────────────────────────────────────
        opensuse* | sles)
            echo "==> Detected distro: $DISTRO (openSUSE family)"
            sudo zypper install -y \
                python3-gobject \
                python3-gobject-cairo \
                typelib-1_0-Gtk-4_0 \
                libadwaita \
                vulkan-tools
            ;;

        # ── Fallback: check ID_LIKE ────────────────────────
        *)
            if echo "$DISTRO_LIKE" | grep -q "arch"; then
                echo "==> Detected distro: $DISTRO (Arch-like)"
                sudo pacman -S --needed --noconfirm \
                    python-gobject gtk4 libadwaita vulkan-tools

            elif echo "$DISTRO_LIKE" | grep -q "debian\|ubuntu"; then
                echo "==> Detected distro: $DISTRO (Debian-like)"
                sudo apt-get update -y
                sudo apt-get install -y \
                    python3-gi python3-gi-cairo \
                    gir1.2-gtk-4.0 \
                    gir1.2-adw-1 \
                    libadwaita-1-0 \
                    vulkan-tools

            elif echo "$DISTRO_LIKE" | grep -q "rhel\|fedora\|centos"; then
                echo "==> Detected distro: $DISTRO (RHEL/Fedora-like)"
                sudo dnf install -y \
                    python3-gobject \
                    gtk4 \
                    libadwaita \
                    vulkan-tools
            else
                echo "Error: Unsupported distribution: $DISTRO"
                echo "Please install the following dependencies manually:"
                echo "  python3-gobject, gtk4, libadwaita, vulkan-tools"
                exit 1
            fi
            ;;
    esac
}

# ── Main ──────────────────────────────────────────────────
detect_distro
install_dependencies

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
