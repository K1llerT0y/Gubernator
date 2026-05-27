# Gubernator – Developer & User Documentation

**Version:** 2.0  
**Platform:** Linux (GTK4 + libadwaita)  
**Language:** Python 3  
**File:** `gubernator.py`

---

## Table of Contents

1. [What is Gubernator?](#1-what-is-gubernator)
2. [How it works – the big picture](#2-how-it-works--the-big-picture)
3. [Dependencies and installation](#3-dependencies-and-installation)
4. [File and directory structure](#4-file-and-directory-structure)
5. [Code walkthrough – section by section](#5-code-walkthrough--section-by-section)
   - 5.1 [Imports](#51-imports)
   - 5.2 [Path constants](#52-path-constants)
   - 5.3 [DEFAULT_STATE – the single source of truth](#53-default_state--the-single-source-of-truth)
   - 5.4 [Color definitions](#54-color-definitions)
   - 5.5 [UI constants](#55-ui-constants)
   - 5.6 [Proton tweak definitions and the conflict map](#56-proton-tweak-definitions-and-the-conflict-map)
   - 5.7 [Helper functions](#57-helper-functions)
   - 5.8 [Persistence – global and per-game](#58-persistence--global-and-per-game)
   - 5.9 [Steam library and game discovery](#59-steam-library-and-game-discovery)
   - 5.10 [write_wrapper – the smart launcher script](#510-write_wrapper--the-smart-launcher-script)
   - 5.11 [write_game_env](#511-write_game_env)
   - 5.12 [build_conf – the MangoHud config generator](#512-build_conf--the-mangohud-config-generator)
   - 5.13 [GameRow – the sidebar game widget](#513-gamerow--the-sidebar-game-widget)
   - 5.14 [The GTK application – Gubernator and MainWindow](#514-the-gtk-application--gubernator-and-mainwindow)
   - 5.15 [The sidebar](#515-the-sidebar)
   - 5.16 [UI pages and tab system](#516-ui-pages-and-tab-system)
   - 5.17 [The MangoHud tab](#517-the-mangohud-tab)
   - 5.18 [The Proton-Tweaks tab](#518-the-proton-tweaks-tab)
   - 5.19 [The Proton Manager tab](#519-the-proton-manager-tab)
   - 5.20 [The ReShade tab](#520-the-reshade-tab)
   - 5.21 [Engine detection system](#521-engine-detection-system)
   - 5.22 [The Engine tab](#522-the-engine-tab)
   - 5.23 [Save path discovery](#523-save-path-discovery)
   - 5.24 [The Saves tab](#524-the-saves-tab)
   - 5.25 [The companion app tab](#525-the-companion-app-tab)
   - 5.26 [Callbacks and the write cycle](#526-callbacks-and-the-write-cycle)
   - 5.27 [The vkcube live preview](#527-the-vkcube-live-preview)
   - 5.28 [The conflict protection system](#528-the-conflict-protection-system)
6. [Data flow diagram](#6-data-flow-diagram)
7. [How to add a new MangoHud option](#7-how-to-add-a-new-mangohud-option)
8. [How to add a new Proton tweak](#8-how-to-add-a-new-proton-tweak)
9. [How to add a new engine to the Engine tab](#9-how-to-add-a-new-engine-to-the-engine-tab)
10. [MangoHud config key reference](#10-mangohud-config-key-reference)
11. [Proton environment variable reference](#11-proton-environment-variable-reference)
12. [External sources and further reading](#12-external-sources-and-further-reading)

---

## 1. What is Gubernator?

Gubernator is a desktop GUI application for Linux that lets you configure three things without ever opening a text editor:

- **MangoHud** – a performance overlay that shows FPS, temperatures, GPU/CPU load, RAM usage and more on top of games. It reads a plain-text config file (`MangoHud.conf`) every time a setting changes.
- **Proton environment variables** – shell variables that modify how Proton (Valve's Windows compatibility layer for Steam) behaves. Things like enabling NTSync, HDR, Wayland rendering, DXVK options, NVIDIA/AMD-specific tweaks and so on.
- **Engine-specific settings** – for Unreal Engine, RE Engine, Katana Engine, and others: directly read and write INI files, disable mouse smoothing, control motion blur, toggle Wine detection, and set FPS limits, all without opening a file manager.

The key design goal is that you **paste one line into Steam once per game** and then you never touch Steam settings again. All subsequent changes in Gubernator take effect immediately because Gubernator rewrites the config files on disk every time you flip a toggle.

A second design goal is **per-game customisation**: each game in your Steam library can have its own MangoHud layout, its own Proton tweaks, and even its own companion Windows app (e.g. an overlay, a trainer, or an achievement tool) that starts and stops alongside the game automatically.

A third design goal is **save file management**: Gubernator detects where each game stores its saves inside the Proton prefix and offers one-click export, import, and migration (e.g. copying saves from a native Linux build to the Proton version).

---

## 2. How it works – the big picture

```
User flips a toggle in the GUI
         │
         ▼
   self._set(key, value)        ← updates the in-memory state dict self.s
         │
         ▼
   self._do_write()
    ├─ save_settings(self.s)          → writes settings.json  (global)
    │   OR save_game_settings(...)    → writes games/<appid>.json  (per-game)
    ├─ build_conf(self.s)             → generates MangoHud.conf text
    ├─ write_conf(text)               → writes MangoHud.conf  (global)
    │   OR games/<appid>.conf         (per-game)
    ├─ write_wrapper(...)             → writes gubr-launch  (one-time, global)
    └─ write_game_env(...)            → writes games/<appid>.env  (per-game)
         │
         ▼
MangoHud detects file change and reloads instantly (no game restart needed)
```

The Steam launch command for every game is:

```
~/.config/gubernator/gubr-launch %command%
```

This bash script is smart: at runtime it reads the `$SteamAppId` environment variable that Steam sets automatically, then checks whether a per-game MangoHud config and a per-game Proton env file exist for that game. If they do, it uses them; otherwise it falls back to the global defaults. This means **one single launch command works for all games** regardless of whether they have per-game settings or not.

The script also handles:
- **Per-game Proton env**: sourced after global tweaks, so per-game settings override globals cleanly (including `unset` commands for global vars that should not apply to this game).
- **Extra launch arguments**: if a `<appid>-launch-args.txt` file exists (used for RE Engine Wine detection), its lines are appended to the game command.
- **Companion app**: if a companion script exists for the current AppID, the game is launched as a background process, the companion starts after a delay, and the wrapper waits for the game to exit before killing the companion.
- **MangoHud disable flag**: a `<appid>-nomangohud` empty file disables MangoHud injection for a specific game. A global flag in `settings.json` can disable it for all games.

---

## 3. Dependencies and installation

Install dependencies on Arch Linux:

```bash
sudo pacman -S python-gobject gtk4 libadwaita vulkan-tools
```

| Package | Why it is needed |
|---|---|
| `python-gobject` | Python bindings for GTK, GDK, GLib, Pango |
| `gtk4` | The GUI toolkit |
| `libadwaita` | GNOME HIG widget library (Adw.ActionRow, Adw.PreferencesGroup, Adw.SplitButton etc.) |
| `vulkan-tools` | Provides `vkcube`, used for the live MangoHud preview |

Run the app:

```bash
python3 gubernator.py
```

Or after running `install.sh`, simply:

```bash
gubernator
```

The `install.sh` script copies the file to `~/.local/share/gubernator/`, creates a launcher at `~/.local/bin/gubernator`, and adds a `.desktop` entry so it appears in your application menu.

---

## 4. File and directory structure

After first launch Gubernator creates these files:

```
~/.config/
├── MangoHud/
│   └── MangoHud.conf                     ← Global MangoHud config (read by MangoHud live)
└── gubernator/
    ├── settings.json                     ← Global GUI settings
    ├── hidden_appids.json                ← List of AppIDs hidden from the sidebar
    ├── proton_managed.json               ← Proton version manager state
    ├── gubr-launch                       ← Smart bash launcher script (chmod +x)
    └── games/
        ├── 123456.json                   ← Per-game settings for AppID 123456
        ├── 123456.conf                   ← Per-game MangoHud config for AppID 123456
        ├── 123456.env                    ← Per-game Proton env vars for AppID 123456
        ├── 123456-nomangohud             ← Empty flag file: disables MangoHud for this game
        ├── 123456-launch-args.txt        ← Extra launch arguments (one per line, e.g. RE Engine)
        └── 123456-companion.sh           ← Companion launcher script (created externally if used)
```

| File | Purpose |
|---|---|
| `MangoHud.conf` | Read by MangoHud overlay at game launch. Generated by `build_conf()`. |
| `settings.json` | Saves every global toggle, slider, color and Proton setting so they survive app restarts. Also stores `mangohud_disabled` flag. |
| `hidden_appids.json` | A JSON array of AppID strings the user has manually hidden from the sidebar. Managed by `load_hidden_appids()` / `save_hidden_appids()`. |
| `proton_managed.json` | Tracks state for the Proton version manager (e.g. last known latest tag). |
| `gubr-launch` | Smart bash script that selects per-game or global configs at runtime and launches the game. |
| `games/<appid>.json` | Per-game settings including MangoHud options, Proton tweaks, companion app config, and WINEDLLOVERRIDES for ReShade. |
| `games/<appid>.conf` | Per-game MangoHud config, used instead of the global one when Steam launches this game. |
| `games/<appid>.env` | Per-game Proton env vars, sourced by the global wrapper. Also contains `unset` commands for global vars that should not apply to this game. |
| `games/<appid>-nomangohud` | Empty flag file. When it exists, the wrapper exports `MANGOHUD=0` for this game, disabling the overlay. |
| `games/<appid>-launch-args.txt` | Extra command-line arguments appended to the game command. Currently used by RE Engine to pass `/WineDetectionEnabled:False`. |
| `games/<appid>-companion.sh` | Companion app launcher. Checked by the wrapper at runtime. |

---

## 5. Code walkthrough – section by section

### 5.1 Imports

```python
import gi, re
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, GLib, Pango
from pathlib import Path
import subprocess, signal, os, json, shlex, shutil, random
```

`gi` is the Python GObject Introspection library. It gives Python access to any GObject-based C library installed on the system. `gi.require_version()` must be called before any imports from `gi.repository` to lock in the correct version. The five imported modules are:

- `Gtk` – the core widget library (buttons, labels, switches, windows)
- `Adw` – libadwaita extensions (ActionRow, PreferencesGroup, SplitButton, ApplicationWindow)
- `Gdk` – lower-level display/color types (used for `Gdk.RGBA` and clipboard access)
- `GLib` – system utilities used by GTK (used here for `GLib.timeout_add()` and `GLib.idle_add()`)
- `Pango` – text layout library (used for `Pango.EllipsizeMode.END` to truncate long game names in the sidebar)

`re` is Python's regular expression module, used to parse Valve's VDF/ACF file format. `subprocess` launches vkcube and companion apps. `signal` and `os` kill those processes cleanly. `json` handles persistence. `pathlib.Path` is used for all file operations. `shlex` safely splits shell command strings into argument lists. `shutil` copies save files and finds executables on PATH. `random` drives the occasional humorous save status message.

### 5.2 Path constants

```python
CONFIG_DIR          = Path.home() / ".config" / "MangoHud"
CONFIG_FILE         = CONFIG_DIR / "MangoHud.conf"
GUBERNATOR_DIR      = Path.home() / ".config" / "gubernator"
WRAPPER_SCRIPT      = GUBERNATOR_DIR / "gubr-launch"
SETTINGS_FILE       = GUBERNATOR_DIR / "settings.json"
GAMES_DIR           = GUBERNATOR_DIR / "games"
HIDDEN_APPIDS_FILE  = GUBERNATOR_DIR / "hidden_appids.json"
STEAM_COMMAND       = f"{WRAPPER_SCRIPT} %command%"
```

All file paths are defined as module-level constants so they can be changed in one place. `Path.home()` returns the current user's home directory (e.g. `/home/alice`). The `/` operator on `Path` objects joins path segments.

`GAMES_DIR` holds all per-game files. `HIDDEN_APPIDS_FILE` stores the list of AppIDs the user has manually hidden from the sidebar.

`STEAM_COMMAND` is the string you paste into Steam → Game Properties → Launch Options.

**App icon path:**

```python
_LOGO_PATH = next(
    (str(p) for p in [
        Path(__file__).parent / "icong.svg",
        Path.home() / ".local/share/icons/hicolor/scalable/apps/io.gubernator.svg",
    ] if p.exists()),
    None,
)
```

Looks for the app logo SVG next to the script first, then in the standard XDG icon location. Returns `None` if neither exists. Used to show the app icon inside the vkcube preview button.

**Proton Version Manager constants:**

```python
COMPAT_DIR   = Path.home() / ".steam" / "root" / "compatibilitytools.d"
MANAGED_FILE = GUBERNATOR_DIR / "proton_managed.json"

PROTON_PLUS_FLATPAK = "com.github.DavidoTek.ProtonPlus"
PROTONUP_QT_FLATPAK = "net.davidotek.pupgui2"
APPIMAGE_DIRS       = [Path.home() / ".local/share/AppImage", Path.home() / "Applications"]
```

`COMPAT_DIR` is where Steam reads custom Proton builds from. `ALL_PROTON_LABELS` lists the known Proton family names shown in the Proton Manager tab. `_LABEL_PATTERNS` maps each label to a list of lowercase substrings used to match directory names.

### 5.3 DEFAULT_STATE – the single source of truth

`DEFAULT_STATE` is a flat Python dictionary that holds the default value for every MangoHud and display setting Gubernator manages. There is exactly one entry per setting. The types used are:

- `bool` – for toggles (on/off switches)
- `str` – for colors (6-character hex without `#`, e.g. `"e3673e"`), positions, dropdown selections
- `int` / `float` – for sliders and number inputs

This dict serves three purposes:

1. **Initial state** when no `settings.json` exists yet
2. **Fallback** when `settings.json` is missing a key (e.g. after adding a new option to a newer version)
3. **Type reference** so the rest of the code knows what kind of value to expect

`load_settings()` merges saved data on top of `DEFAULT_STATE`, so old settings files remain compatible when new keys are added.

Some keys end in `_text`. These control whether MangoHud shows a text label next to a metric. They are stored in state but are not currently exposed as separate UI controls.

The VSync keys are named `opengl_vsync` and `vulkan_vsync` in the state dict, but they are written to `MangoHud.conf` as `gl_vsync` and `vsync` respectively, because those are the actual MangoHud config key names.

A special key `mango_extra` is not in `DEFAULT_STATE` but is stored dynamically in `self.s` when the user types in the "Extra Config Lines" text area. It holds raw MangoHud config lines appended verbatim to the generated config. Because it has no default, `self.s.get("mango_extra", "")` is used wherever it is read.

The key `mangohud_disabled` is **not** in `DEFAULT_STATE`. It is stored directly in `settings.json` for the global profile and inferred from the presence of a `<appid>-nomangohud` file for per-game profiles. It is stored in `self.mangohud_disabled` on the window.

`gpu_index` defaults to `-1` (meaning "all GPUs"). When set to `0` or higher it writes `gpu_list=N` to the MangoHud config to show only that GPU.

### 5.4 Color definitions

```python
COLOR_KEYS = [
    ("gpu_color",          "GPU"),
    ("cpu_color",          "CPU"),
    ("media_player_color", "Media Player"),
    ("fps_color_1",        "FPS good"),
    ("fps_color_2",        "FPS medium"),
    ("fps_color_3",        "FPS bad"),
    ("engine_color",       "Engine"),
    ("frametime_color",    "Frametime"),
    ("wine_color",         "Wine / Proton"),
    ("battery_color",      "Battery"),
    ("network_color",      "Network"),
]
COLOR_KEY = [
    ("text_color",         "Text"),
    ("background_color",   "Background"),
    ("text_outline_color", "Text Outline"),
    ("ram_color",          "RAM/PRAM"),
    ("vram_color",         "VRAM/PVRAM"),
    ("io_color",           "IO Read/Write"),
]
MULTI_COLOR_KEYS = {"gpu_load_color", "core_load_color"}
```

There are two separate color lists because they are used in different places in the UI:

- **`COLOR_KEYS`** – colors that are visually paired with their feature toggle. For example, the GPU color picker appears in the same row as the "GPU Usage" toggle. `build_conf()` iterates this list to write those values to the config.
- **`COLOR_KEY`** – standalone colors that do not belong to a single toggle: text color, background, text outline, and the shared colors for RAM, VRAM, and IO. These are shown in the collapsible Colors expander at the bottom of the MangoHud tab.

`MULTI_COLOR_KEYS` is a set of special color keys whose values are comma-separated strings of multiple hex values (e.g. `"39f900,fdfd09,b22222"` for the three load color stops). MangoHud uses these for `gpu_load_color` and `core_load_color`. Because GTK's `ColorButton` only handles one color, these are shown as plain text entry fields instead.

### 5.5 UI constants

```python
POSITIONS = [
    ("top-left",0,0), ("top-center",0,1), ("top-right",0,2),
    ("middle-left",1,0), ("middle",1,1), ("middle-right",1,2),
    ("bottom-left",2,0), ("bottom-center",2,1), ("bottom-right",2,2),
]
POS_ARROWS = {
    "top-left":"↖", "top-center":"↑", "top-right":"↗",
    "middle-left":"←", "middle":"·", "middle-right":"→",
    "bottom-left":"↙", "bottom-center":"↓", "bottom-right":"↘",
}
FPS_PRESETS = [0, 60, 120, 144, 165, 240]
OPENGL_VSYNC = [("-1","Adaptive sync"), ("0","Off"), ("1","On"), ("n","Sync to refresh rate")]
VULKAN_VSYNC  = [("0","Adaptive VSync (FIFO_RELAXED_KHR)"), ("1","Off (IMMEDIATE_KHR)"),
                 ("2","Mailbox (VSync with uncapped FPS) (MAILBOX_KHR)"), ("3","On FIFO_KHR")]
```

These constants drive UI elements that have a fixed set of options:

- **`POSITIONS`** – each tuple is `(position_name, grid_row, grid_column)`. Used to build the 3×3 button grid for HUD position selection. `POS_ARROWS` maps each position to a Unicode arrow character that appears as the button label.
- **`FPS_PRESETS`** – the preset values shown as quick-pick buttons in the FPS Limit row. `0` is displayed as "Off". A custom text entry next to the buttons accepts any integer value.
- **`OPENGL_VSYNC` / `VULKAN_VSYNC`** – `(value, human_label)` pairs for the VSync dropdowns. The value is what gets written to `MangoHud.conf`. OpenGL and Vulkan use different numbering schemes, so they have separate lists.

### 5.6 Proton tweak definitions and the conflict map

Each Proton section is a list of tuples with the format:

```python
(env_var_string, display_title, subtitle_description, conflicts_list)
```

For example:

```python
("DXVK_ASYNC=1", "DXVK Async", "Async shader compilation – reduces stutter.", ["PROTON_USE_WINED3D=1"])
```

This means: the environment variable to export is `DXVK_ASYNC=1`, it is shown in the UI as "DXVK Async", its description says it reduces stutter, and it conflicts with `PROTON_USE_WINED3D=1`.

The `env_var_string` uses `=` to encode both the variable name and its value in a single string. `split("=", 1)` limits the split to one occurrence, which handles values that contain `=` themselves.

All sections are collected in `ALL_PROTON_SECTIONS`, which is a list of `(section_title, entries_list)` pairs. This drives the entire Proton-Tweaks tab UI with a single loop.

Current sections: **Sync Technology**, **Wayland & HDR**, **Wine & Compatibility**, **DXVK / VKD3D**, **NVIDIA**, **AMD / Mesa**, **Misc**.

**The conflict map** is built automatically at module load time by iterating `ALL_PROTON_SECTIONS` and making conflicts bidirectional. If entry A declares B as a conflict, the map will also say B conflicts with A. The result is `CONFLICT_MAP[key]` → set of conflicting keys.

### 5.7 Helper functions

**`hex_to_rgba(h)`** converts a 6-character hex string (e.g. `"e3673e"`) to a `Gdk.RGBA` object that GTK's `ColorButton` understands. It strips any `#` prefix, pads short strings to 6 chars, then divides each channel by 255 to get a float in the range 0.0–1.0.

**`rgba_to_hex(r)`** does the reverse: takes a `Gdk.RGBA` and returns a lowercase 6-char hex string for storage in the state dict.

**`detect_gpus()`** enumerates GPUs by reading the Linux kernel's PCI sysfs interface at `/sys/bus/pci/devices/`. It looks for devices where the `class` file starts with `0x03` (the PCI class code for display controllers). For each GPU it reads the `vendor` file to identify NVIDIA (`0x10de`), AMD (`0x1002`), or Intel (`0x8086`), and the `label` or `device` file for a human-readable name. Returns a list of `(index, name)` tuples. If fewer than 2 GPUs are found, the GPU selector dropdown is not shown in the UI.

**`sec_lbl(text)`** creates a styled heading label used above each preferences group in the UI. It left-aligns the text, applies the `"heading"` CSS class (which makes it bold and slightly larger), and adds margins.

**`adw_toggle(title, subtitle, active, cb, color_btn=None)`** is a factory for the most common UI pattern in the app: an `Adw.ActionRow` with a `Gtk.Switch` on the right. The optional `color_btn` parameter allows a `Gtk.ColorButton` to be inserted to the left of the switch in the same row. Returns a `(row, switch)` tuple.

### 5.8 Persistence – global and per-game

**Global settings:**

```python
def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            saved = json.loads(SETTINGS_FILE.read_text())
            state = dict(DEFAULT_STATE)
            state.update(saved)
            return state
        except:
            pass
    return dict(DEFAULT_STATE)
```

`load_settings()` reads `settings.json`, starts with a fresh copy of `DEFAULT_STATE`, and then overwrites only the keys that exist in the saved file. This means new keys added in a newer version automatically get their default values. Corrupted or unreadable JSON files fall back to defaults silently.

```python
def save_settings(state: dict):
    GUBERNATOR_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(state, indent=2))
```

**Per-game settings:**

```python
def load_game_settings(appid: str):
    path = GAMES_DIR / f"{appid}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except: pass
    return None

def save_game_settings(appid: str, state: dict):
    GAMES_DIR.mkdir(parents=True, exist_ok=True)
    (GAMES_DIR / f"{appid}.json").write_text(json.dumps(state, indent=2))
```

Per-game JSON files contain the full settings dict plus extra keys that only exist at the game level:

- `"use_custom": True/False` – whether this game uses its own settings or inherits the global ones
- `"companion_exec": str` – command to launch the companion app
- `"companion_env": str` – environment variables for the companion app (raw text, one per line)
- `"companion_autowrap": bool` – whether to show a crash popup when the companion exits unexpectedly
- `"reshade_winedll": str` – the WINEDLLOVERRIDES value currently applied for ReShade

`load_game_settings()` returns `None` if no JSON file exists for this AppID (meaning the game has never been individually configured).

**Hidden AppIDs:**

```python
def load_hidden_appids() -> set:
    if HIDDEN_APPIDS_FILE.exists():
        try:
            return set(json.loads(HIDDEN_APPIDS_FILE.read_text()))
        except: pass
    return set()

def save_hidden_appids(appids: set):
    GUBERNATOR_DIR.mkdir(parents=True, exist_ok=True)
    HIDDEN_APPIDS_FILE.write_text(json.dumps(sorted(appids), indent=2))
```

Stores AppID strings that the user has chosen to hide from the sidebar. A set is used in memory for O(1) lookup; the file stores a sorted list for stable diffs.

**Proton manager state:**

```python
def load_managed() -> dict:
    if MANAGED_FILE.exists():
        try:
            return json.loads(MANAGED_FILE.read_text())
        except: pass
    return {"auto_installed": []}
```

Tracks which Proton versions the manager has installed and their last known tags.

### 5.9 Steam library and game discovery

```python
def _acf_value(content: str, key: str) -> str:
    m = re.search(r'"' + re.escape(key) + r'"\s+"([^"]*)"', content, re.IGNORECASE)
    return m.group(1) if m else ""
```

Steam stores game metadata in `.acf` files (App Cache Files) using Valve's text-based KeyValues format (VDF). This function extracts a single field value using a regular expression.

```python
def _steam_library_dirs() -> list:
    dirs = []
    default = Path.home() / ".steam" / "steam" / "steamapps"
    if default.exists():
        dirs.append(default)
    vdf_path = default / "libraryfolders.vdf"
    if vdf_path.exists():
        content = vdf_path.read_text(errors="replace")
        for m in re.finditer(r'"path"\s+"([^"]+)"', content):
            extra = Path(m.group(1)) / "steamapps"
            if extra.exists() and extra not in dirs:
                dirs.append(extra)
    return dirs
```

Steam supports multiple library locations. `_steam_library_dirs()` reads `libraryfolders.vdf` and returns a list of every `steamapps/` directory that actually exists.

```python
def read_steam_games() -> list:
    """Return sorted list of (appid, name, install_path) tuples for all installed games."""
    games = []
    seen  = set()
    for steamapps in _steam_library_dirs():
        for acf in steamapps.glob("appmanifest_*.acf"):
            content    = acf.read_text(errors="replace")
            appid      = _acf_value(content, "appid")
            name       = _acf_value(content, "name")
            installdir = _acf_value(content, "installdir")
            if appid and name and appid not in seen:
                seen.add(appid)
                install_path = str(steamapps / "common" / installdir) if installdir else ""
                games.append((appid, name, install_path))
    return sorted(games, key=lambda x: x[1].lower())
```

`read_steam_games()` now returns **3-tuples** `(appid, name, install_path)`. The `install_path` is the full path to the game's installation directory (e.g. `~/.steam/steam/steamapps/common/Cyberpunk 2077`). This path is passed to `detect_engine()` in the sidebar to tag each `GameRow` with its detected engine, enabling engine-based search. All call sites that previously expected 2-tuples have been updated.

### 5.10 write_wrapper – the smart launcher script

`write_wrapper(proton_active, custom_vars, mangohud_disabled=False)` generates the single global bash script used for all games. It is regenerated every time global settings are saved. Key sections of the generated script:

**1. Global Proton tweaks** (from `proton_active` set and `custom_vars` text):

```bash
export DXVK_ASYNC="1"
export PROTON_USE_NTSYNC="1"
# … etc.
```

**2. Per-game Proton env** (sourced after globals so game-level settings win):

```bash
GAME_ENV="~/.config/gubernator/games/${SteamAppId}.env"
if [ -n "$SteamAppId" ] && [ -f "$GAME_ENV" ]; then
    set -a; source "$GAME_ENV"; set +a
fi
```

**3. MangoHud selection** – chooses per-game `.conf` or global `MangoHud.conf`, and handles the MangoHud disable flag:

```bash
GAME_CONF="~/.config/gubernator/games/${SteamAppId}.conf"
if [ -n "$SteamAppId" ] && [ -f "$GAME_CONF" ]; then
    export MANGOHUD_CONFIGFILE="$GAME_CONF"
else
    export MANGOHUD_CONFIGFILE="~/.config/MangoHud/MangoHud.conf"
fi
# If mangohud_disabled=True in global settings:
#   export MANGOHUD=0
# Otherwise:
if [ -n "$SteamAppId" ] && [ -f "~/.config/gubernator/games/${SteamAppId}-nomangohud" ]; then
    export MANGOHUD=0
elif [ "${MANGOHUD:-1}" != "0" ]; then
    export MANGOHUD=1
fi
```

**4. Extra launch arguments** (for RE Engine and similar):

```bash
_GC_ARGS_FILE="~/.config/gubernator/games/${SteamAppId}-launch-args.txt"
_GC_EXTRA_ARGS=()
if [ -n "$SteamAppId" ] && [ -f "$_GC_ARGS_FILE" ]; then
    while IFS= read -r _arg; do
        [ -n "$_arg" ] && _GC_EXTRA_ARGS+=("$_arg")
    done < "$_GC_ARGS_FILE"
fi
```

**5. Companion and game launch**:

```bash
_GC_COMPANION="~/.config/gubernator/games/${SteamAppId}-companion.sh"
if [ -n "$SteamAppId" ] && [ -f "$_GC_COMPANION" ]; then
    "$@" "${_GC_EXTRA_ARGS[@]}" &
    _GC_GAME_PID=$!
    _GC_DELAY=$(grep -m1 "COMPANION_DELAY=" "$_GC_COMPANION" | tr -dc '0-9')
    sleep "${_GC_DELAY:-5}"
    bash "$_GC_COMPANION" &
    wait "$_GC_GAME_PID"
    kill -TERM "$_GC_COMPANION_PID" 2>/dev/null
else
    exec "$@" "${_GC_EXTRA_ARGS[@]}"
fi
```

`exec "$@"` replaces the shell process with the game, which is important for Steam to correctly detect when the game starts and stops. When a companion exists, `exec` cannot be used because the wrapper must remain running to wait for the game and kill the companion.

`WRAPPER_SCRIPT.chmod(0o755)` makes the file executable. Without this, Steam cannot run it.

The `_env_vars(proton_active, custom_vars)` helper extracts `(var, val)` pairs from both the active Proton set and the custom variables text field. It uses `split("=", 1)` so values containing `=` are handled correctly.

### 5.11 write_game_env

```python
def write_game_env(appid, proton_active, custom_vars,
                   global_active=None, global_custom_vars="",
                   mangohud_disabled=False):
```

Generates the per-game `.env` file that the global wrapper sources for a specific game. The file:

1. Optionally writes `export MANGOHUD=0` first if `mangohud_disabled=True`.
2. Writes `export VAR="value"` for every active Proton variable.
3. Writes `unset VAR` for every variable that is active globally but not active for this game. This is necessary because the global wrapper already exported those variables before sourcing this file — without the `unset` they would silently bleed through.

```python
global_vars = _env_vars(global_active or set(), global_custom_vars)
to_unset = sorted({var for var, _ in global_vars if var not in per_game_var_names})
for var in to_unset:
    lines.append(f"unset {var}")
```

After `_do_write()` saves the game settings, it calls `save_nomangohud(appid, mangohud_disabled)` which creates or deletes the `<appid>-nomangohud` flag file:

```python
def save_nomangohud(appid: str, disabled: bool):
    path = GAMES_DIR / f"{appid}-nomangohud"
    if disabled:
        path.touch()
    else:
        path.unlink(missing_ok=True)
```

**Note on `write_companion_script()`**: This function still exists in the code but is **never called**. When per-game custom settings are saved, `_do_write()` deletes the companion script if it exists, rather than creating it. The wrapper script checks for the companion file at runtime, so this feature is currently inactive. The companion tab's "Manual Launch" button still works because it launches the app directly via `subprocess.Popen`, not through the companion script.

### 5.12 build_conf – the MangoHud config generator

`build_conf(s: dict)` takes the full state dict and produces the complete text of `MangoHud.conf` as a string. It uses two inner helper functions:

```python
def tog(k): return s.get(k, False)
def val(k): return s.get(k, DEFAULT_STATE.get(k))
```

**Important MangoHud behaviour**: Some options are enabled by default in MangoHud itself (fps, gpu_stats, cpu_stats, frame_timing). If your config file simply omits them, they still appear in the overlay. To turn them off you must write `fps=0` etc. explicitly. Gubernator always writes these explicitly:

```python
lines.append("fps=1" if tog("fps") else "fps=0")
lines.append("gpu_stats=1" if tog("gpu_stats") else "gpu_stats=0")
lines.append("cpu_stats=1" if tog("cpu_stats") else "cpu_stats=0")
```

For options that are off by default, the key is only written when the toggle is on:

```python
if tog("gpu_temp"): lines.append("gpu_temp")
```

**fps_only mode**: Writes `fps_only` and `legacy_layout=0`, activating MangoHud's compact FPS-only display.

**Colors**: All color values (stored as 6-char hex strings) are written directly. Both `COLOR_KEYS` and `COLOR_KEY` are iterated in two separate passes.

**Text outline**: When enabled, three keys are written together:

```python
if tog("text_outline"):
    lines.append("text_outline")
    lines.append(f"text_outline_color={val('text_outline_color')}")
    lines.append(f"text_outline_thickness={float(val('text_outline_thickness')):.1f}")
```

**VSync**: State keys `opengl_vsync` and `vulkan_vsync` are written using MangoHud's actual names `gl_vsync` and `vsync`.

**GPU index**: Written only when set to 0 or higher (−1 means "all GPUs"):

```python
if gpu_index is not None and int(gpu_index) >= 0:
    lines.append(f"gpu_list={int(gpu_index)}")
```

**Extra raw config lines**: The `mango_extra` key holds a raw multi-line string. Any non-empty lines from it are appended directly to the generated config, allowing advanced users to add any MangoHud option that doesn't have a UI control. This key has no entry in `DEFAULT_STATE`; it is read with `self.s.get("mango_extra", "")`.

The function ends by collapsing consecutive blank lines to keep the output file clean.

### 5.13 GameRow – the sidebar game widget

```python
class GameRow(Gtk.ListBoxRow):
    def __init__(self, appid, name, engine="unknown"):
        super().__init__()
        self.appid     = appid
        self.game_name = name
        self.engine    = engine
```

`GameRow` is a custom `Gtk.ListBoxRow` subclass that represents one entry in the sidebar list. Each row displays the game name on the first line (truncated with an ellipsis if too long) and a dimmed subtitle (`"AppID: 123456"` or `"Global Settings"`).

The special "Global / Default" row has `appid=None`. All per-game rows have their Steam AppID as a string.

The `engine` attribute is set from `detect_engine(install_path)` when the sidebar is built and is used by `_filter_games()` to enable engine-based search. Engine detection runs once at sidebar build time and at rescan time; it does not run again when a game is selected (the per-game result is re-run via `self._engine_detected` in `_switch_to()`).

### 5.14 The GTK application – Gubernator and MainWindow

```python
class Gubernator(Adw.Application):
    def __init__(self):
        super().__init__(application_id="io.gubernator")
        self.connect("activate", lambda app: MainWindow(application=app).present())
```

`Gubernator` is a thin wrapper around `Adw.Application`. The `application_id` is a reverse-domain string that uniquely identifies the app on the system.

`MainWindow` uses a **two-panel layout**: a resizable sidebar on the left and a flexible right panel. The sidebar lists all Steam games; the right panel shows the settings for whichever game is selected.

**Key instance variables:**

```python
self.s                    # full state dict – all settings live here
self.selected_appid       # None = Global, otherwise a Steam AppID string
self.selected_name        # display name of the currently selected game
self.use_custom           # True if this game has per-game settings enabled
self._current_tab_name    # name of the active tab, preserved across rebuilds

self.proton_active        # set of active Proton env var strings
self.proton_custom        # contents of the custom vars text area
self.companion_exec       # companion app command string
self.companion_env        # companion env vars (raw text)
self.companion_autowrap   # bool: show crash popup on unexpected exit
self.mangohud_disabled    # bool: disable MangoHud for this game/globally

self._selected_install_dir # absolute path to the game's installation directory
self._engine_detected      # engine string returned by detect_engine()

self._vkcube_proc         # subprocess.Popen handle for vkcube
self._companion_proc      # subprocess.Popen handle for companion app

# Widget reference dicts – reset each time the right panel rebuilds:
self._pos_btns            # position_name → Gtk.Button
self._fps_preset_btns     # preset_value → Gtk.Button
self._proton_switches     # env_var_string → Gtk.Switch
self._proton_callbacks    # env_var_string → callback closure
self._conflict_rows       # env_var_string → Adw.ActionRow
```

**Header bar** contains:
- **Preview button** (left) – launches or stops the vkcube live MangoHud preview. Shows the app logo (if found) alongside the label. Has a tooltip explaining that the preview uses global settings only.
- **Copy Steam Command** (left) – an `Adw.SplitButton` styled with custom CSS in Steam blue. Clicking the left part copies the launch command to the clipboard. Clicking the right arrow opens a popover showing the launcher script content and the current MangoHud config.
- **Status label** (right) – shows brief feedback messages like `"✓ saved"` or error descriptions. Messages are cleared after 2.5 seconds via `GLib.timeout_add`.
- **Save & Apply button** (right) – triggers an explicit `_do_write()`.

**Three state helpers:**

```python
def _tog(self, k): return bool(self.s.get(k, DEFAULT_STATE.get(k, False)))
def _val(self, k): return self.s.get(k, DEFAULT_STATE.get(k))
def _set(self, k, v): self.s[k] = v; self._do_write()
```

These are called throughout the UI-building code. `_set()` updates state and immediately triggers a full write to disk and MangoHud config regeneration.

### 5.15 The sidebar

The sidebar contains three parts:

**Search row** – a `Gtk.SearchEntry` that filters the list by game name or AppID (or by engine when engine search mode is active). Next to it are a filter button (funnel icon) and a rescan button (refresh icon). The rescan button calls `_rescan_games()` which removes all game rows, re-reads the Steam library, and rebuilds the list — useful when a new game has been installed while Gubernator is open.

**Filter popover** – opened by the funnel button, contains three sections:

1. **Auto-hide** – three checkboxes (default: on) that hide entries whose names contain `"proton"`, `"steam linux runtime"`, or `"steamworks"`. These filters are not saved across restarts.

2. **Engine Search** – a single checkbox (default: off, not saved). When enabled, the main search field matches `row.engine` instead of `row.game_name`. For example, typing `"unreal"` shows all Unreal Engine games. The engine names are the strings returned by `detect_engine()` (e.g. `"unreal"`, `"re_engine"`, `"godot"`, `"unity"`).

3. **Custom Hidden** – a search field labelled "Find game to hide…" and a scrollable list. When the search field is empty, the list shows only currently hidden games. When the user types, the list shows matching games (found or hidden) so they can be checked or unchecked. Checked games are added to `self._hidden_appids` and saved to `hidden_appids.json` immediately. Hidden games are excluded from the main game list.

`_filter_games(row)` applies all active rules in order:
1. `GameRow(appid=None)` (Global) is always visible.
2. Auto-hide rules (name keyword matching).
3. Hidden AppID set.
4. Search query: if engine search is active, match against `row.engine`; otherwise match against name or AppID.

`_fill_hidden_checks(games_data)` rebuilds the hidden-list widget. Each entry is a `Gtk.ListBoxRow` with `_appid` and `_name` attributes attached directly to the row object (not to a child widget). The filter function `_filter_hidden_list(row)` reads `self._hide_search_entry.get_text()` and returns `True` for:
- all rows when query is empty AND the row's AppID is currently hidden (shows only what's hidden)
- rows whose `_name` contains the query when typing (allows finding and toggling any game)

### 5.16 UI pages and tab system

The right panel contains a `Gtk.Notebook`. The notebook is rebuilt completely each time `_build_right_panel()` is called. The active tab is tracked **by name** (stored in `self._current_tab_name`) and restored after each rebuild using `tab_names.index(self._current_tab_name)`.

For per-game entries, a "Custom Settings" toggle appears above the notebook. When it is on, the notebook tabs are fully editable. When it is off, most tabs are read-only (showing global settings as a preview) but the **Engine** and **Saves** tabs remain fully accessible regardless, since they show filesystem information that does not depend on the settings state.

This is implemented with **per-page sensitivity** rather than disabling the whole notebook:

```python
editable = is_global or self.use_custom
tab_pages = [
    ("MangoHud",      self._page_mango(),     is_global, editable),
    ("Proton-Tweaks", self._page_proton(),    is_global, editable),
    ("Custom App",    self._page_companion(), False,     editable),
    ("Engine",        self._page_engine(),    False,     True),      # always accessible
    ("Reshade",       self._page_reshade(),   is_global, editable),
    ("Saves",         self._page_saves(),     False,     True),      # always accessible
]
if is_global:
    tab_pages.insert(2, ("Proton Manager", self._page_versions(), True, True))
```

For each tab: `page.set_sensitive(sensitive)` grays out the page content but the tab header remains clickable. Tab labels are shown in **bold** if they are the "home" tab for the current profile (bold = primary context).

When `_on_custom_toggle()` fires:
- **Enabling** custom settings: loads existing game data if present, otherwise copies global settings as a starting point, then calls `_do_write()`.
- **Disabling** custom settings: saves `{"use_custom": False}` to the game JSON, reloads global settings into `self.s`, and calls `_do_write()` so files are updated immediately.

Both cases rebuild the right panel via `GLib.idle_add(self._build_right_panel)`.

### 5.17 The MangoHud tab

`_page_mango()` builds the MangoHud tab. It uses `_make_full_row(title, subtitle, tog_key, color_key=None)` as the standard row factory. This creates an `Adw.ActionRow` with:
- An optional `Gtk.ColorButton` to the left of the switch (when `color_key` is provided).
- A `Gtk.Switch` on the right.
- `set_activatable_widget(sw)` so clicking anywhere on the row toggles the switch.

Groups in the tab:
- **Performance** – FPS, fps-only mode, frametime value, frame timing graph, frame count, FPS color change, FPS sampling period slider, FPS limit (preset buttons + custom text entry).
- **GPU** – GPU usage, temperatures, clocks, power, fan, voltage, load color change, efficiency, VRAM, process VRAM, GPU selector dropdown (only visible when multiple GPUs are detected).
- **CPU** – CPU usage, temperature, power, MHz, per-core load (with load color change and core bar graph), CPU efficiency, RAM, process RAM, swap.
- **IO** – disk read/write throughput.
- **Misc** – media player, wine version, resolution, clock (with "no label" variant), MangoHud version, CPU arch, GPU name, graphics API, Vulkan driver, gamemode, throttling status, battery, network.
- **Display** – sliders for font size (8–48 pt), corner radius (0–30), background alpha (0.0–1.0), text outline thickness (0.5–4.0); spinbox for table columns (1–6); HUD compact, horizontal, no-margin, no-display, text outline toggles; 3×3 HUD position grid.
- **VSync** – separate dropdowns for OpenGL and Vulkan present modes.
- **Colors** – collapsible expander showing `COLOR_KEY` color pickers (text, background, outline, RAM, VRAM, IO).
- **Extra Config Lines** – a monospace text area. Its content is stored as `mango_extra` in the settings dict and appended verbatim to the generated `MangoHud.conf`.

### 5.18 The Proton-Tweaks tab

`_page_proton()` builds the Proton-Tweaks tab. Its content:

**ProtonDB link** – a button at the top that opens `https://www.protondb.com/app/<appid>` in the browser when a game is selected, or the ProtonDB homepage when in Global mode. ProtonDB is a community database of game compatibility ratings and tips.

**Proton tweak sections** – iterates `ALL_PROTON_SECTIONS` and creates one toggle row per entry with conflict protection (see section 5.28).

**Special combined controls** in the Wayland & HDR section (appended after the normal rows):

- **Enable HDR** – a single toggle that activates both `PROTON_ENABLE_HDR=1` and `ENABLE_HDR_WSI=1` together, and automatically also activates `PROTON_ENABLE_WAYLAND=1`. When Wayland is manually turned off, HDR is automatically turned off too.

- **Disable MangoHud** – shown for all profiles (global and per-game). When enabled globally, sets `mangohud_disabled=True` in `self.s` and writes `export MANGOHUD=0` into the wrapper script. When enabled per-game, creates the `<appid>-nomangohud` flag file so the wrapper disables MangoHud only for that game.

**Custom Environment Variables** – a monospace text area at the bottom where users can enter raw `VAR=value` lines. These are treated the same as Proton tweak keys in `write_wrapper()` and `write_game_env()`.

### 5.19 The Proton Manager tab

Only shown when "Global / Default" is selected (the tab is inserted at index 2 in the global tab list). Provides a read-only view of installed Proton builds and quick access to external version managers.

**External Proton Tools** group – two rows for Proton Plus and ProtonUp-Qt. `find_external_tool(flatpak_id, appimage_names, exe_names)` checks:
1. If the Flatpak app is installed (`flatpak info`).
2. If any of the `exe_names` exist on `PATH` via `shutil.which`.
3. If any matching AppImage files exist in `~/.local/share/AppImage` or `~/Applications`.

If found, the button shows "Open" and launches the tool. If not found, the button shows "Get on GitHub" and opens the release page.

**Installed Proton Versions** – reads `~/.steam/root/compatibilitytools.d/` and categorizes each directory into one of the known families using `_LABEL_PATTERNS`. Each family is shown as a collapsible `Gtk.Expander` with version info. Directories that don't match any known family appear in an "Other" expander. A Refresh button at the top triggers a full panel rebuild.

**Credits** – attribution rows with "Open GitHub" buttons for Proton Plus (by Vysp3r) and ProtonUp-Qt (by DavidoTek).

### 5.20 The ReShade tab

ReShade is a post-processing injection framework for games. Gubernator provides a UI to download and configure `reshade-linux.sh` by kevinlekiller, which handles the actual installation.

**Installation group** (Global mode only, grayed in per-game mode) – a single "Install" button that:
1. Downloads `reshade-linux.sh` from the kevinlekiller GitHub repository to `~/reshade-linux.sh`.
2. Makes it executable.
3. Runs it in a terminal emulator (tried in order: gnome-terminal, konsole, xfce4-terminal, kitty, alacritty, foot, xterm).

If no terminal emulator is found, a dialog shows the raw command to run manually.

**Per-game controls** (hidden in Global mode):

- **Open ReShade** – runs `~/reshade-linux.sh` in a terminal for the selected game. Shows an error dialog if the script has not been downloaded yet.

- **Game Executable** – automatically detects the game's main `.exe` file using `_find_reshade_exe()`. For Unreal Engine games it searches for `*-Win64-Shipping.exe`. For REDengine it looks in `bin/x64/`. Shows a "Copy Path" button so the user can paste the path when the ReShade installer asks for it. Also shows the game folder with an "Open Folder" button.

- **WINEDLLOVERRIDES** – a group of radio buttons covering common DirectX configurations (DX9, DX10/11, DX12, OpenGL) plus a "None" option and a "Custom" text entry. Selecting a preset:
  - Writes `export WINEDLLOVERRIDES="<value>"` into the game's custom Proton vars (`proton_custom`).
  - Saves `reshade_winedll` in the game's JSON so the UI can restore the selected radio button on next open.
  - The entry `"None (disabled)"` removes the WINEDLLOVERRIDES line from the custom vars.

**Credits** – attribution row for kevinlekiller's reshade-steam-proton script with an "Open GitHub" button.

### 5.21 Engine detection system

`detect_engine(install_dir: str) -> str` takes the game's installation directory path and returns a lowercase engine identifier string. It checks for engine-specific files and directories in a fixed priority order:

| Return value | Detection heuristic |
|---|---|
| `"re_engine"` | `natives/` dir exists, or `re_chunk_*.pak` files found |
| `"unreal"` | `Engine/Binaries/` or `Content/Paks/` exists |
| `"unity"` | `UnityPlayer.dll` or `UnityPlayer.so` exists |
| `"godot"` | Any `*.pck` file found |
| `"red_engine"` | `REDprelauncher.exe` exists or `r4data/` dir exists |
| `"source"` | `hl2.exe` exists, or `GameInfo.txt` / `gameinfo.gi` found |
| `"creation"` | `Data/*.esm` or `Data/*.bsa` files found |
| `"gamemaker"` | `data.win` or `game.unx` exists |
| `"rpgmaker"` | `Game.rgss3a`, `Game.rgss2a`, or `www/data/` exists |
| `"cry_engine"` | `engine.pak`, `system.cfg`, `Bin64/`, `bin/win_x64/`, `Engine/`, or `engine/` exists |
| `"id_tech"` | Any `*.pk4` or `*.pk3` files found |
| `"decima"` | `database.bp` exists, or any `*.core` files found |
| `"katana"` | Any `*.fdata` files found |
| `"asura"` | Any `*.asr` or `*.asr.*` files found |
| `"unknown"` | None of the above matched |

The detection result is stored in `GameRow.engine` for sidebar search, and in `self._engine_detected` after a game is selected (re-run in `_switch_to()`).

**Unreal Engine config helpers:**

- `find_unreal_config_dir(appid)` – searches for the Unreal config directory inside the game's Proton prefix (`compatdata/<appid>/pfx/drive_c/users/steamuser/`). Tries three locations in order:
  1. `AppData/Local/[Game]/Saved/Config/WindowsClient/` (or `WindowsNoEditor` or `Windows`)
  2. `Documents/My Games/[Game]/Config/WindowsClient/`
  3. `Saved Games/[folder]/[folder]/Saved/Config/WindowsNoEditor/` (two-level wildcard)

- `read_unreal_ini(ini_path, section)` – reads a single section from an Unreal INI file using Python's `configparser`, case-insensitively matching the section name. Returns a dict of key→value pairs.

- `write_unreal_ini(ini_path, section, values)` – reads the existing INI file, updates the specified section with the given values dict, and writes it back. Creates the file and parent directories if needed.

**RE Engine helpers:**

- `save_re_engine_args(appid, wine_detection_enabled)` – writes `/WineDetectionEnabled:False` to `<appid>-launch-args.txt` when Wine detection should be disabled (needed for Ray Tracing), or deletes the file when it should be enabled.

**Katana Engine helpers:**

- `find_katana_config(appid)` – looks for `AppData/Local/KoeiTecmo/[Game]/Savedata/graphics_option.json` in the Proton prefix. Falls back to searching for `game.ini` in the game installation directory.
- `read_katana_fps(json_path)` – reads the first recognized FPS key from the graphics JSON (looks for keys named `fps`, `fps_limit`, `frame_rate`, `max_fps`, `framerate`). Returns `(key_name, current_value)`.
- `write_katana_fps(json_path, key, value, as_string)` – writes an FPS value back to the JSON, preserving the original type (some games store FPS as a string, others as an integer).

**Asura Engine helpers:**

- `find_asura_paths(appid)` – finds `AppData/Local/[gamedir]` (skipping known system directories) and within it `PC_ProfileSaves/[id]/` for save files.

**Decima Engine helpers:**

- `find_decima_config(appid)` – searches `Documents/[game]/[id_folder]/game_settings.cfg` in the Proton prefix.

### 5.22 The Engine tab

`_page_engine()` builds the Engine tab. The tab is always accessible (not grayed out when custom settings are off) because it shows filesystem information independent of Gubernator settings.

The content is built by `_fill_engine_content()` based on `self._engine_detected`:

**Global / Default selected** – shows a placeholder message "Select a game from the list".

**Unreal Engine** – shows the detected config directory with an "Open Folder" button. If the config directory is found, two toggle controls are shown:
- **Disable Mouse Smoothing** – writes `bEnableMouseSmoothing=False` and `bViewAccelerationEnabled=False` to `Input.ini` under the `[/Script/Engine.InputSettings]` section.
- **Disable Motion Blur** – writes `r.MotionBlur.Max=0`, `r.MotionBlurQuality=0`, and `r.DefaultFeature.MotionBlur=0` to `Engine.ini` under the `[SystemSettings]` section.

**RE Engine** – shows a "Wine Detection" toggle. When disabled, saves `/WineDetectionEnabled:False` to the launch args file. This is required to use Ray Tracing in RE Engine games running under Proton.

**Katana Engine** – shows the graphics config path, an FPS limit entry field (reads current value from the JSON, writes back on apply), and the `game.ini` path if found.

**Asura Engine** – shows the config folder path with an "Open Folder" button.

**Decima Engine** – shows the `game_settings.cfg` path with an "Open Folder" button.

**All other engines** – shows "No config available – [Engine] configs are not yet supported".

### 5.23 Save path discovery

The save path system supports multiple engines and Proton prefix layouts. Each engine has a dedicated function that returns a dict of path categories.

**`find_save_paths(appid, engine, name)`** – for Unreal Engine games. Returns `{"native": Path|None, "proton": Path|None}`.

- Native path: checks `~/.config/Epic/<name>/SaveGames/` and `~/.local/share/Epic/<name>/SaveGames/` (for games also available on Linux natively via Epic).
- Proton path: tries three locations inside the Proton prefix in order:
  1. `AppData/Local/[Game]/Saved/SaveGames/`
  2. `My Documents/My Games/[Game]/SaveGames/`
  3. `Saved Games/[folder]/[folder]/Saved/SaveGames/` (two-level wildcard)

**`find_save_paths_redengine(appid)`** – for CD Projekt Red games. Returns `{"proton": Path|None}`.
- Looks at `Saved Games/CD Projekt Red/` in the Proton prefix.

**`find_save_paths_creation(appid)`** – for Bethesda games. Returns `{"proton": Path|None}`.
- Looks at `My Documents/My Games/[Game]/Saves/`. Falls back to `My Documents/My Games/` if no `Saves/` subfolder is found.

**`find_save_paths_appdata(appid)`** – for GameMaker and RPG Maker games. Returns `{"local": Path|None, "roaming": Path|None}`.
- Returns paths to `AppData/Local` and `AppData/Roaming` inside the Proton prefix for the user to navigate manually.

**`find_save_paths_cryengine(appid)`** – for CryEngine games. Returns `{"my_games", "local", "local_low", "roaming"}`.
- Scans all four common Windows save locations in the Proton prefix.

**`find_asura_paths(appid)`** – for Asura Engine games. Returns `{"config": Path|None, "saves": Path|None}`.
- The saves are at `AppData/Local/[gamedir]/PC_ProfileSaves/[id]/`.

**`find_decima_config(appid)`** – for Decima Engine games. Returns the path to `game_settings.cfg` if found.

**Save file utilities:**

```python
def copy_saves(source, dest):    # recursive file copy, preserving structure
def export_saves_zip(source, zip_path):    # compress source dir to ZIP
def import_saves_zip(zip_path, dest):      # extract ZIP into dest dir
```

### 5.24 The Saves tab

`_page_saves()` builds the Saves tab. Like the Engine tab, it is always accessible regardless of the custom settings toggle. The tab's content is built by `_fill_saves_content()` and varies by engine.

**Global / Default selected** – shows a placeholder message.

**Cloud-only games** – a hardcoded set `CLOUD_ONLY_GAMES` (Hunt: Showdown, CS2, Dota 2, TF2, Apex Legends, etc.) shows a message explaining that saves are Steam Cloud only, with no local files to manage.

**Unreal Engine** – shows four groups:
- *Native Linux Saves* – the Epic Games save path (if found).
- *Proton Saves* – the Proton prefix save path (if found).
- *Migration* – two destructive-action buttons ("Copy Native → Proton" and "Copy Proton → Native"), shown only when both paths exist. Triggers a confirmation dialog before copying.
- *Backup* – "Export as ZIP" (opens a file save dialog) and "Import ZIP" (opens a file open dialog filtered to `.zip`).

**REDengine / Creation Engine** – shows only the Proton save path with "Open Folder" and backup buttons.

**GameMaker / RPG Maker** – shows AppData/Local and AppData/Roaming paths for manual navigation.

**CryEngine** – shows all four Windows save locations (Documents/My Games, Local, LocalLow, Roaming).

**Asura Engine** – shows the save subfolder with "Open Folder" and backup buttons.

**Source / Source 2 and others** – shows "Not supported yet" message.

### 5.25 The companion app tab

The "Custom App" tab (`_page_companion()`) is a per-game-only feature. When "Global / Default" is selected, the tab shows an info message.

**How it works end-to-end:**

The companion tab stores its configuration in the per-game JSON (`companion_exec`, `companion_env`, `companion_autowrap`). The global wrapper checks for a `<appid>-companion.sh` file at runtime. Note: currently `_do_write()` deletes the companion script file rather than creating it, so the automatic game-launch integration is inactive. The manual "Launch App" button always works because it launches the app directly.

**Controls in the tab:**

- **Manual Launch / Kill App** – a toggle button that starts or stops the companion using `subprocess.Popen`. When launched, uses the running game's exact Proton wine binary (found via `/proc` scanning) so the companion connects to the existing wineserver rather than starting a new one.
- **Crash Popup** – when enabled, shows a dialog with the exit code and up to 1200 characters of stdout/stderr if the companion exits unexpectedly (non-zero exit code or any output).
- **Command** – text entry for the full launch command (e.g. `wine /home/user/app.exe`). A browse button opens a file picker; for `.exe` files it prepends `wine` automatically.
- **App-only Environment Variables** – a monospace text area for `VAR=value` lines that are set in the companion's environment but do not affect the game process.
- **Auto-fill Proton Prefix** – detects the correct Wine environment automatically. Finds the game's `compatdata/<appid>/pfx` prefix and scans `/proc` for a wine process already using that prefix. If the game is running, uses its exact Proton wine binary (version matched). If not running, falls back to the newest Proton installation in `compatibilitytools.d`. Fills `WINEPREFIX=<path>` in the env textarea and updates the command's `wine` prefix.

**`_find_running_proton_wine(prefix)`** reads `/proc/<pid>/environ` for every running process, looking for one that has `WINEPREFIX` set to the target prefix and whose executable path contains "wine". Returns `(wine_binary, version_label, full_env_dict)` or `(None, "", None)`.

When manually launching, the game's Proton environment is used as the base (so DXVK library paths are inherited), but `LD_PRELOAD` is stripped because the Steam overlay `.so` files it contains will crash wine launched outside Pressure Vessel (Steam's sandbox container).

### 5.26 Callbacks and the write cycle

GTK uses a signal/callback pattern. When the user interacts with a widget, GTK fires a signal and calls connected Python functions.

**For toggles:**

```python
sw.connect("notify::active", lambda sw, _, k=key: self._set(k, sw.get_active()))
```

The default argument `k=key` captures the current value of `key` in the loop to avoid the Python closure trap (where all lambdas in a loop would share the last value of `key`).

**For sliders:**

```python
sc.connect("value-changed", lambda sc, kk=sk: self._set(kk, sc.get_value()))
```

**For color buttons:**

```python
cbtn.connect("color-set", lambda b, k=c_key: self._set(k, rgba_to_hex(b.get_rgba())))
```

**The `_do_write()` method** is the central write function:

```python
def _do_write(self):
    self.s["proton_active"] = list(self.proton_active)
    self.s["proton_custom"] = self.proton_custom
    mango_text = build_conf(self.s)

    if self.selected_appid is None:
        # Global
        self.s["mangohud_disabled"] = self.mangohud_disabled
        save_settings(self.s)
        write_conf(mango_text)
        write_wrapper(self.proton_active, self.proton_custom,
                      mangohud_disabled=self.mangohud_disabled)
    elif self.use_custom:
        # Per-game with custom settings enabled
        game_state = dict(self.s)
        game_state["use_custom"] = True
        game_state["companion_exec"]     = self.companion_exec
        game_state["companion_env"]      = self.companion_env
        game_state["companion_autowrap"] = self.companion_autowrap
        save_game_settings(self.selected_appid, game_state)
        (GAMES_DIR / f"{self.selected_appid}.conf").write_text(mango_text)
        write_game_env(self.selected_appid, self.proton_active, self.proton_custom,
                       global_active, global_custom,
                       mangohud_disabled=self.mangohud_disabled)
        save_nomangohud(self.selected_appid, self.mangohud_disabled)
    else:
        # Per-game with custom disabled – preview only, no files written
        mango_text = build_conf(load_settings())

    self.conf_preview.set_label(mango_text)
    self.script_preview.set_label(WRAPPER_SCRIPT.read_text())
    self._set_status(_save_label())
```

For global settings, the wrapper script is regenerated on every write because the user might have changed which global Proton tweaks are active. For per-game settings, only the per-game files change.

### 5.27 The vkcube live preview

```python
def _toggle_vkcube(self, btn):
    if self._vkcube_proc and self._vkcube_proc.poll() is None:
        os.killpg(os.getpgid(self._vkcube_proc.pid), signal.SIGTERM)
        self._vkcube_proc = None
        self._set_vkcube_btn_state(False)
    else:
        env = os.environ.copy()
        env["MANGOHUD"] = "1"
        env["MANGOHUD_CONFIGFILE"] = str(CONFIG_FILE)
        self._vkcube_proc = subprocess.Popen(
            ["vkcube"], env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid,
        )
        self._set_vkcube_btn_state(True)
        GLib.timeout_add(1000, self._poll_vkcube)
```

`vkcube` is a spinning Vulkan demo cube from `vulkan-tools`. It is used purely as a Vulkan application that MangoHud can hook into, so you can see overlay settings live without launching a game.

Key implementation details:
- `preexec_fn=os.setsid` creates a new process session so `os.killpg()` can kill vkcube and all its child processes cleanly.
- `stdout=subprocess.DEVNULL` and `stderr=subprocess.DEVNULL` discard vkcube's output so it doesn't pollute the terminal.
- `_poll_vkcube` is called every 1000ms by `GLib.timeout_add`. It resets the button state if vkcube was closed by the user. Returns `False` to stop the timer, or `True` to keep it running.
- When Gubernator is closed (`_on_close`), both vkcube and any running companion app are killed.

The preview button shows the app logo (`_LOGO_PATH`) when stopped and a media-stop icon when running. The button has a tooltip: `"Preview uses Global / Default settings only"` — vkcube has no AppID, so only the global MangoHud config applies.

### 5.28 The conflict protection system

The `_mkproton(key, conflicts)` method returns a callback function (a closure) that handles toggling a Proton option. When the user enables a switch:

1. Check `CONFLICT_MAP.get(key, [])` for keys that conflict.
2. Filter to those currently in `self.proton_active`.
3. If any conflicts are blocking:
   - `sw.handler_block_by_func(cb)` temporarily disconnects the callback.
   - `sw.set_active(False)` reverts the switch.
   - `sw.handler_unblock_by_func(cb)` reconnects the callback.
   - Conflicting rows get the `"error"` CSS class (red highlight) for 1.5 seconds via `GLib.timeout_add`.
   - A status message appears in the header bar.
4. If no conflicts, the key is added to `self.proton_active`.

**NTSync special case**: When `PROTON_USE_NTSYNC=1` is enabled, Gubernator automatically enables `PROTON_NO_ESYNC=1` and `PROTON_NO_FSYNC=1` (because NTSync replaces both Esync and Fsync). When NTSync is disabled, those two are automatically turned off. The same `handler_block_by_func` / `set_active` / `handler_unblock_by_func` pattern updates companion switches without triggering their own callbacks.

**HDR special case** (handled separately in `_page_proton()`): Enabling HDR automatically enables Wayland. Turning off Wayland automatically turns off HDR.

**Why `_proton_callbacks` was added**: `handler_block_by_func(cb)` requires the exact same closure object that was passed to `sw.connect()`. Since `_mkproton()` returns a new closure each time, the closure reference is stored in `self._proton_callbacks[key]` at build time and retrieved from there when needed for the NTSync and HDR automations.

---

## 6. Data flow diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MainWindow (GTK)                                    │
│                                                                               │
│  Sidebar                Right Panel                                          │
│  ─────────              ────────────────────────────────────────────────     │
│  search entry           [Custom Settings toggle – games only]                │
│  filter popover                                                               │
│  ├─ auto-hide           MangoHud  Proton  ProtonMgr  Companion               │
│  ├─ engine search       tab       tab     (global)   tab                     │
│  └─ custom hidden       toggles   tweaks  versions   exec/env                │
│                         sliders   +HDR    +credits   autofill                │
│  game list              colors    +dis.                                       │
│  ├─ Global / Default    position  mango                                       │
│  └─ [Steam games]       VSync     ProtonDB  Engine  ReShade  Saves           │
│       .engine attr                          tab     tab       tab             │
│                                             INI     exe/dll  paths           │
│  rescan btn             │           │         │         │       │             │
│  → _rescan_games()      └───────────┴─────────┴─────────┴───────┘            │
│                                     │                                         │
│                              _set(key,v) / _mkproton()                       │
│                                     │                                         │
│                               _do_write()                                    │
│                                     │                                         │
└─────────────────────────────────────┼─────────────────────────────────────────┘
                                      │
               ┌──────────────────────┼──────────────────────┐
               │                      │                       │
   [Global selected]    [Per-game + use_custom=True]    [Per-game + use_custom=False]
               │                      │                            │
   save_settings()       save_game_settings()          read global for preview only
   write_conf()          write game .conf               (no files written)
   write_wrapper()       write_game_env()
               │         save_nomangohud()
               ▼                      ▼
      MangoHud.conf         games/<appid>.conf
      gubr-launch           games/<appid>.env
                            games/<appid>-nomangohud (flag)
               │
               ▼
      MangoHud reads file change & reloads overlay
```

---

## 7. How to add a new MangoHud option

This is the most common change you will want to make. There are three places to update:

**Step 1 – Add to DEFAULT_STATE:**

```python
DEFAULT_STATE = {
    ...
    "my_new_option": False,   # add the key with its default value
    ...
}
```

**Step 2 – Add to build_conf():**

Find the appropriate section (Performance, GPU, CPU, IO, Misc, Display) and add the line:

```python
if tog("my_new_option"): lines.append("my_new_option")
```

If it is an option that is **enabled by default in MangoHud** and must be explicitly disabled, use:

```python
lines.append("my_new_option=1" if tog("my_new_option") else "my_new_option=0")
```

**Step 3 – Add a row to the UI in _page_mango():**

For a simple toggle without a color picker:

```python
some_group.add(self._make_full_row("My New Option", "Description", "my_new_option"))
```

For a toggle with a color picker (if the option has an associated color key):

```python
some_group.add(self._make_full_row("My New Option", "Description", "my_new_option", "some_color_key"))
```

If the new option has a color that should appear inline with its toggle, also add the color key to `COLOR_KEYS` so `build_conf()` writes it. If the color belongs in the standalone Colors expander, add it to `COLOR_KEY`.

That is all. `_set()` automatically triggers `_do_write()` which saves to disk and rewrites the MangoHud config.

---

## 8. How to add a new Proton tweak

**Step 1 – Add to the appropriate section list:**

```python
PROTON_MISC = [
    ...
    ("MY_VAR=value", "Display Title", "What this does and any warnings",
     ["CONFLICTING_VAR=value"]),   # empty list [] if no conflicts
]
```

The format is strictly `(env_var_string, title, subtitle, conflicts_list)`.

**Step 2 – Done.**

Because the Proton-Tweaks page is built by iterating `ALL_PROTON_SECTIONS`, the new entry automatically appears as a row in the UI with correct conflict checking. The conflict map is also rebuilt automatically at module load time.

If you need a new conflict that is bidirectional (both options should block each other), you only need to declare it in one direction — the conflict map builder makes it symmetric.

**Adding a mutually exclusive pair** (like Enable/Disable Xalia):

```python
("MY_VAR=on",  "Enable Feature",  "Enable …",  ["MY_VAR=off"]),
("MY_VAR=off", "Disable Feature", "Disable …", ["MY_VAR=on"]),
```

---

## 9. How to add a new engine to the Engine tab

**Step 1 – Add detection to `detect_engine()`:**

Add a new `if` block before the `return "unknown"` line:

```python
if (p / "some_engine_file.exe").exists():    return "my_engine"
```

Put more specific checks first (exact file existence) and more general checks later (glob patterns).

**Step 2 – Add helper functions** (if needed) for finding config files in the Proton prefix.

Follow the pattern of `find_unreal_config_dir()`, `find_katana_config()`, etc. Always iterate `_steam_library_dirs()` and look inside `compatdata/<appid>/pfx/drive_c/users/steamuser/`.

**Step 3 – Add a name to `ENGINE_NAMES` in `_fill_engine_content()`:**

```python
ENGINE_NAMES = {
    ...
    "my_engine": "My Engine Name",
}
```

**Step 4 – Add an `elif` block in `_fill_engine_content()`:**

```python
elif engine == "my_engine":
    cfg = find_my_engine_config(self.selected_appid)
    if cfg:
        row = Adw.ActionRow(title="Config path", subtitle=str(cfg))
        btn = Gtk.Button(label="Open Folder", valign=Gtk.Align.CENTER)
        btn.add_css_class("flat")
        btn.connect("clicked", lambda _, p=cfg.parent: subprocess.Popen(["xdg-open", str(p)]))
        row.add_suffix(btn)
        grp.add(row)
    else:
        grp.add(Adw.ActionRow(
            title="Config not found",
            subtitle="Launch the game at least once to generate the config",
        ))
```

**Step 5 – Add save path support in `_fill_saves_content()`** (if applicable):

Add an `elif engine == "my_engine":` block that calls your helper function and displays the save path with "Open Folder", export, and import buttons.

---

## 10. MangoHud config key reference

These are the MangoHud configuration keys used in `build_conf()` and their meaning. The full official reference is at the [MangoHud GitHub repository](https://github.com/flightlessmango/MangoHud).

| Config key | Default in MangoHud | Description |
|---|---|---|
| `fps=1/0` | **on** | FPS counter. Must explicitly write `=0` to disable. |
| `frametime=1/0` | off | Frametime value in milliseconds. |
| `frame_timing=1/0` | **on** | Frametime bar graph. Must write `=0` to disable. |
| `frame_count` | off | Total frame counter. |
| `fps_limit=N` | 0 | Cap FPS. 0 = disabled. |
| `fps_only` | off | Show only FPS, hide everything else. Use with `legacy_layout=0`. |
| `fps_color_change` | off | Color the FPS value based on thresholds. |
| `fps_sampling_period=N` | 500 | Sampling window for FPS calculation in ms. |
| `gpu_stats=1/0` | **on** | GPU usage percentage. Must write `=0` to disable. |
| `gpu_temp` | off | GPU temperature in °C. |
| `gpu_junction_temp` | off | GPU hotspot/junction temperature (AMD). |
| `gpu_core_clock` | off | GPU core clock in MHz. |
| `gpu_mem_clock` | off | GPU memory clock in MHz. Requires `vram`. |
| `gpu_mem_temp` | off | GPU memory temperature. Requires `vram`. |
| `gpu_power` | off | GPU power draw in watts. |
| `gpu_power_limit` | off | GPU power limit. |
| `gpu_fan` | off | GPU fan speed in RPM (AMD) or % (NVIDIA). |
| `gpu_voltage` | off | GPU voltage in mV (AMD only). |
| `gpu_load_change` | off | Color GPU stat based on load level. |
| `gpu_efficiency` | off | GPU efficiency in frames per joule. |
| `vram` | off | Total VRAM usage. |
| `proc_vram` | off | VRAM used by this process only. |
| `gpu_list=N` | all | Show only GPU number N (0-indexed). Uses `/sys/bus/pci/devices` index. |
| `cpu_stats=1/0` | **on** | CPU usage percentage. Must write `=0` to disable. |
| `cpu_temp` | off | CPU temperature in °C. |
| `cpu_power` | off | CPU power draw in watts. |
| `cpu_mhz` | off | CPU clock frequency. |
| `core_load` | off | Per-core CPU usage. |
| `core_load_change` | off | Color per-core usage by load level. |
| `core_bars` | off | Visual bar graph per CPU core. Requires `core_load`. |
| `cpu_efficiency` | off | CPU efficiency in frames per joule. |
| `ram` | off | Total system RAM usage. |
| `procmem` | off | RAM used by this process only. |
| `swap` | off | Swap space usage. |
| `io_read` | off | Disk read throughput. |
| `io_write` | off | Disk write throughput. |
| `media_player` | off | Current media player track via MPRIS (requires `playerctl`). |
| `wine` | off | Wine/Proton version number. |
| `resolution` | off | Active render resolution. |
| `time` | off | System clock. |
| `time_no_label` | off | System clock without label prefix. |
| `version` | off | MangoHud version number. |
| `arch` | off | CPU architecture string. |
| `gpu_name` | off | GPU model name. |
| `api` | off | Graphics API in use (Vulkan / OpenGL). |
| `vulkan_driver` | off | Vulkan driver name and version. |
| `gamemode` | off | Shows if `gamemode` is active. |
| `throttling_status` | off | Flashes when GPU/CPU is thermally or power throttling. |
| `battery` | off | Battery percentage and power draw (laptops). |
| `network` | off | Network throughput in kb/s. |
| `position=X` | top-left | HUD position. Values: `top-left`, `top-center`, `top-right`, `middle-left`, `middle`, `middle-right`, `bottom-left`, `bottom-center`, `bottom-right`. |
| `font_size=N` | 24 | Font size in points. |
| `round_corners=N` | 0 | Corner radius of the HUD background. |
| `background_alpha=F` | 0.5 | Background opacity (0.0 transparent to 1.0 opaque). |
| `table_columns=N` | auto | Number of columns in the HUD layout. |
| `hud_compact` | off | Compact single-line layout. |
| `horizontal` | off | Horizontal side-by-side layout. |
| `hud_no_margin` | off | Remove outer margins from the HUD. |
| `text_outline` | off | Draw an outline around all text for readability. |
| `text_outline_color` | 000000 | Color of the text outline as hex. |
| `text_outline_thickness=F` | 1.5 | Thickness of the text outline in pixels. |
| `no_display` | off | Start with HUD hidden. Toggle on/off with Shift+F12. |
| `gl_vsync=N` | -1 | OpenGL VSync: -1=adaptive, 0=off, 1=on, N=sync every N frames. Written from state key `opengl_vsync`. |
| `vsync=N` | 3 | Vulkan present mode: 0=FIFO_RELAXED (adaptive), 1=IMMEDIATE (off), 2=MAILBOX, 3=FIFO (on). Written from state key `vulkan_vsync`. |
| `text_color`, `gpu_color`, etc. | various | Six-digit hex color codes without `#`. |
| `gpu_load_color`, `core_load_color` | various | Comma-separated hex triples for low/medium/high load thresholds. |

---

## 11. Proton environment variable reference

These are the variables written into the `gubr-launch` wrapper script and the per-game `.env` files. Sources: [Valve/Proton GitHub](https://github.com/ValveSoftware/Proton), [DXVK GitHub](https://github.com/doitsujin/dxvk), [vkd3d-proton GitHub](https://github.com/HansKristian-Work/vkd3d-proton), [CachyOS gaming guide](https://wiki.cachyos.org/configuration/gaming/).

### Sync Technology

| Variable | Value | Description |
|---|---|---|
| `PROTON_USE_NTSYNC` | `1` | Enable NTSync, a kernel-level thread synchronization mechanism. Requires Linux kernel 6.14 or newer. Faster and lower-overhead than Esync or Fsync. Automatically enables Disable Esync and Disable Fsync when turned on. |
| `PROTON_USE_NTSYNC` | `0` | Explicitly disable NTSync. Use this on Proton versions that enable NTSync by default if you want to force it off. |
| `PROTON_NO_ESYNC` | `1` | Disable Esync (eventfd-based sync). Enable when NTSync is active to avoid conflicts. |
| `PROTON_NO_FSYNC` | `1` | Disable Fsync (futex-based sync). Enable when NTSync is active to avoid conflicts. |

### Wayland & HDR

| Variable | Value | Description |
|---|---|---|
| `PROTON_ENABLE_WAYLAND` | `1` | Use native Wayland rendering instead of XWayland. Requires Proton 9+. Automatically enabled when HDR is turned on. |
| `PROTON_ENABLE_HDR` | `1` | Enable HDR output through Proton. Requires a Wayland compositor with HDR support and an HDR-capable display. Set together with ENABLE_HDR_WSI via the combined "Enable HDR" toggle. |
| `ENABLE_HDR_WSI` | `1` | Enable HDR through the Vulkan WSI (Window System Integration) layer. Works with gamescope and KDE Plasma 6. Set together with PROTON_ENABLE_HDR. |

### Wine & Compatibility

| Variable | Value | Description |
|---|---|---|
| `PROTON_USE_WOW64` | `1` | Run 32-bit game executables without requiring 32-bit Linux userspace libraries. Uses Wine's WOW64 mode. Useful on systems without `multilib`. **Incompatible with PROTON_NVIDIA_LIBS.** |
| `PROTON_USE_XALIA` | `1` | Enable Xalia, a tool that adds gamepad navigation to keyboard/mouse game UIs. |
| `PROTON_USE_XALIA` | `0` | Force-disable Xalia if it causes crashes. **Conflicts with enabling Xalia.** |
| `WINE_LARGE_ADDRESS_AWARE` | `1` | Force Wine to mark all 32-bit executables as Large Address Aware, allowing them to use more than 2 GB of RAM. Usually on by default in recent Proton versions. |
| `PROTON_HEAP_DELAY_FREE` | `1` | Delays freeing allocated memory. Works around use-after-free bugs in some games. |
| `STAGING_SHARED_MEMORY` | `1` | Enable Wine Staging's shared memory optimization. |
| `PROTON_USE_WINED3D` | `1` | Replace DXVK (Vulkan-based) with WineD3D (OpenGL-based) for D3D9/10/11. Useful as a fallback if DXVK causes crashes. **Disables DXVK Async and DXR.** |

### DXVK / VKD3D

| Variable | Value | Description |
|---|---|---|
| `DXVK_ASYNC` | `1` | Enable asynchronous shader compilation in DXVK. Reduces shader-compilation stutter. **Do not combine with WineD3D** (has no effect). |
| `DXVK_FRAME_RATE` | `0` | DXVK's internal frame rate cap. Set to 0 to disable it and let MangoHud or the game control frame rate. |
| `DXVK_HUD` | `fps` | Show DXVK's built-in HUD. Useful for debugging without MangoHud. |
| `DXVK_STATE_CACHE_PATH` | `/tmp` | Directory where DXVK writes its shader state cache. `/tmp` puts it in RAM, avoiding disk writes. Cache is lost on reboot. |
| `VKD3D_CONFIG` | `dxr` | Enable DirectX Raytracing through VKD3D-Proton. DXR is usually auto-enabled when supported; this forces it. **Incompatible with WineD3D.** |
| `VKD3D_FEATURE_LEVEL` | `12_1` | Force a specific Direct3D 12 feature level in VKD3D. Use when a game requires a specific level. |

### NVIDIA

| Variable | Value | Description |
|---|---|---|
| `NVPRESENT_ENABLE_SMOOTH_MOTION` | `1` | Enable NVIDIA Smooth Motion (frame interpolation). |
| `NVPRESENT_QUEUE_FAMILY` | `1` | Workaround to prevent Smooth Motion from interfering with third-party overlays. Enable alongside Smooth Motion if overlays behave incorrectly. |
| `PROTON_ENABLE_NVAPI` | `1` | Enable NVAPI support in Proton. Required for DLSS, Nvidia Reflex, and other Nvidia-specific features. |
| `DXVK_ENABLE_NVAPI` | `1` | Enable NVAPI support in the DXVK translation layer specifically. |
| `__GL_THREADED_OPTIMIZATIONS` | `1` | Enable Nvidia's OpenGL threaded optimization. Can improve performance in OpenGL titles. |
| `__NV_PRIME_RENDER_OFFLOAD` | `1` | Use the discrete Nvidia GPU on Optimus (hybrid) laptops. **Conflicts with DRI_PRIME.** |
| `__VK_LAYER_NV_optimus` | `NVIDIA_only` | Force Vulkan to use the Nvidia GPU on Optimus systems. **Conflicts with DRI_PRIME.** |
| `PROTON_HIDE_NVIDIA_GPU` | `1` | Make the game see the GPU as AMD instead of Nvidia. Fixes crashes in games that require NVAPI but don't use it correctly. |
| `PROTON_NVIDIA_LIBS` | `1` | Enable extra Nvidia library support (proton-cachyos only). **Incompatible with WOW64.** |

### AMD / Mesa

| Variable | Value | Description |
|---|---|---|
| `DRI_PRIME` | `1` | Use the discrete GPU on hybrid AMD/Intel laptops via DRI PRIME. **Conflicts with Nvidia PRIME.** |
| `ENABLE_LAYER_MESA_ANTI_LAG` | `1` | Enable AMD Anti-Lag to reduce input latency. AMD GPUs and Mesa drivers only. |
| `RADV_PERFTEST` | `gpl` | Enable Vulkan Graphics Pipeline Library in the RADV driver. Reduces shader-compilation stutter on AMD. |
| `RADV_DEBUG` | `syncshaders` | Force synchronous shader compilation in RADV. Useful when combined with VKD3D breadcrumb debugging. |
| `mesa_glthread` | `true` | Enable Mesa's OpenGL threading optimization. Reduces CPU overhead for OpenGL games. |

### Misc

| Variable | Value | Description |
|---|---|---|
| `PROTON_LOG` | `1` | Write a detailed Wine/Proton debug log to `~/steam-APPID.log`. Useful for diagnosing crashes. Creates large files. |
| `PROTON_NO_STEAMINPUT` | `1` | Disable Steam Input controller remapping for this game. Use when a game handles its own controller input but Steam Input interferes. |
| `PROTON_FORCE_LARGE_ADDRESS_AWARE` | `1` | Override and force LAA even if the game's executable explicitly opts out. |
| `ZINK` | `1` | Use the Zink driver (Mesa) to translate OpenGL calls to Vulkan. Experimental. Useful for testing or on systems with better Vulkan than OpenGL support. |

---

## 12. External sources and further reading

| Source | URL | What you will find there |
|---|---|---|
| MangoHud GitHub | https://github.com/flightlessmango/MangoHud | Full config key reference, `data/MangoHud.conf` contains every option with comments |
| MangoHud ArchWiki | https://wiki.archlinux.org/title/MangoHud | Installation, per-game configs, global enable, Wine integration |
| Proton GitHub | https://github.com/ValveSoftware/Proton | Complete list of all official Proton environment variables with descriptions |
| DXVK GitHub | https://github.com/doitsujin/dxvk | DXVK config options, `DXVK_ASYNC`, `DXVK_HUD`, state cache |
| vkd3d-proton GitHub | https://github.com/HansKristian-Work/vkd3d-proton | `VKD3D_CONFIG` options, DXR support, feature levels |
| reshade-steam-proton | https://github.com/kevinlekiller/reshade-steam-proton | The `reshade-linux.sh` script used by the ReShade tab |
| Proton Plus | https://github.com/Vysp3r/ProtonPlus | GUI tool for installing custom Proton versions (linked in Proton Manager tab) |
| ProtonUp-Qt | https://github.com/DavidoTek/ProtonUp-Qt | Qt-based Proton version manager (linked in Proton Manager tab) |
| ProtonDB | https://www.protondb.com | Community game compatibility database (linked in Proton-Tweaks tab) |
| GOverlay GitHub | https://github.com/benjamimgois/goverlay | The inspiration for the wrapper-script approach (fgmod) |
| Steam VDF/ACF format | https://developer.valvesoftware.com/wiki/KeyValues | The text format used by `appmanifest_*.acf` and `libraryfolders.vdf` |
| GTK4 Python docs | https://docs.gtk.org/gtk4/ | GTK widget reference |
| libadwaita docs | https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/ | Adw.ActionRow, Adw.PreferencesGroup, Adw.SplitButton, Adw.ApplicationWindow |
| PyGObject docs | https://pygobject.gnome.org/ | Python GObject introspection, signal/callback system |
| CachyOS gaming guide | https://wiki.cachyos.org/configuration/gaming/ | RADV_PERFTEST, AMD Anti-Lag, proton-cachyos specific vars |
| Linux /proc filesystem | https://www.kernel.org/doc/html/latest/filesystems/proc.html | How `/proc/<pid>/environ` and `/proc/<pid>/exe` work (used by the companion autofill) |
| Unreal Engine INI docs | https://dev.epicgames.com/documentation/en-us/unreal-engine/configuration-files-in-unreal-engine | INI file structure, section names, and key references |
