# Gubernator – Developer & User Documentation

**Version:** 1.0  
**Platform:** Arch Linux (GTK4 + libadwaita)  
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
   - 5.11 [write_game_env and write_companion_script](#511-write_game_env-and-write_companion_script)
   - 5.12 [build_conf – the MangoHud config generator](#512-build_conf--the-mangohud-config-generator)
   - 5.13 [GameRow – the sidebar game widget](#513-gamerow--the-sidebar-game-widget)
   - 5.14 [The GTK application – Gubernator and MainWindow](#514-the-gtk-application--gubernator-and-mainwindow)
   - 5.15 [The sidebar](#515-the-sidebar)
   - 5.16 [UI pages](#516-ui-pages)
   - 5.17 [Callbacks and the write cycle](#517-callbacks-and-the-write-cycle)
   - 5.18 [The vkcube live preview](#518-the-vkcube-live-preview)
   - 5.19 [The conflict protection system](#519-the-conflict-protection-system)
   - 5.20 [The companion app tab](#520-the-companion-app-tab)
6. [Data flow diagram](#6-data-flow-diagram)
7. [How to add a new MangoHud option](#7-how-to-add-a-new-mangohud-option)
8. [How to add a new Proton tweak](#8-how-to-add-a-new-proton-tweak)
9. [MangoHud config key reference](#9-mangohud-config-key-reference)
10. [Proton environment variable reference](#10-proton-environment-variable-reference)
11. [External sources and further reading](#11-external-sources-and-further-reading)

---

## 1. What is Gubernator?

Gubernator is a desktop GUI application for Linux that lets you configure two things without ever opening a text editor:

- **MangoHud** – a performance overlay that shows FPS, temperatures, GPU/CPU load, RAM usage and more on top of games. It reads a plain-text config file (`MangoHud.conf`) every time a setting changes.
- **Proton environment variables** – shell variables that modify how Proton (Valve's Windows compatibility layer for Steam) behaves. Things like enabling NTSync, HDR, Wayland rendering, DXVK options, NVIDIA/AMD-specific tweaks and so on.

The key design goal is that you **paste one line into Steam once per game** and then you never touch Steam settings again. All subsequent changes in Gubernator take effect immediately because Gubernator rewrites the config files on disk every time you flip a toggle.

A second design goal is **per-game customisation**: each game in your Steam library can have its own MangoHud layout, its own Proton tweaks, and even its own companion Windows app (e.g. an overlay, a trainer, or an achievement tool) that starts and stops alongside the game automatically.

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

The script also handles an optional **companion app** (e.g. a Windows overlay or trainer): if a companion script exists for the current game, it launches the game as a background process, waits a configurable delay, starts the companion, and then waits for the game to exit before killing the companion cleanly.

This approach is inspired by [GOverlay's fgmod launcher](https://github.com/benjamimgois/goverlay), which uses the same wrapper-script technique.

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
│   └── MangoHud.conf                 ← Global MangoHud config (read by MangoHud live)
└── gubernator/
    ├── settings.json                 ← Global GUI settings
    ├── gubr-launch               ← Smart bash launcher script (chmod +x)
    └── games/
        ├── 123456.json               ← Per-game settings for AppID 123456
        ├── 123456.conf               ← Per-game MangoHud config for AppID 123456
        ├── 123456.env                ← Per-game Proton env vars for AppID 123456
        └── 123456-companion.sh       ← Companion launcher script for AppID 123456
```

| File | Purpose |
|---|---|
| `MangoHud.conf` | Read by MangoHud overlay at game launch. Generated by `build_conf()`. |
| `settings.json` | Saves every global toggle, slider, color and Proton setting so they survive app restarts. |
| `gubr-launch` | Smart bash script that selects per-game or global configs at runtime and launches the game with MangoHud. |
| `games/<appid>.json` | Per-game settings including MangoHud options, Proton tweaks, and companion app config. |
| `games/<appid>.conf` | Per-game MangoHud config, used instead of the global one when Steam launches this game. |
| `games/<appid>.env` | Per-game Proton env vars, sourced by the global wrapper. Also contains `unset` commands for global vars that should not apply to this game. |
| `games/<appid>-companion.sh` | Auto-generated launcher for the companion app. Created on demand, deleted when companion config is cleared. |

---

## 5. Code walkthrough – section by section

### 5.1 Imports

```python
import gi, re
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, GLib, Pango
from pathlib import Path
import subprocess, signal, os, json, shlex
```

`gi` is the Python GObject Introspection library. It gives Python access to any GObject-based C library installed on the system. `gi.require_version()` must be called before any imports from `gi.repository` to lock in the correct version. The five imported modules are:

- `Gtk` – the core widget library (buttons, labels, switches, windows)
- `Adw` – libadwaita extensions (ActionRow, PreferencesGroup, SplitButton, ApplicationWindow)
- `Gdk` – lower-level display/color types (used for `Gdk.RGBA` and clipboard access)
- `GLib` – system utilities used by GTK (used here for `GLib.timeout_add()` and `GLib.idle_add()`)
- `Pango` – text layout library (used for `Pango.EllipsizeMode.END` to truncate long game names in the sidebar)

`re` is Python's regular expression module, used to parse Valve's VDF/ACF file format when reading the Steam library. `subprocess` launches vkcube and companion apps. `signal` and `os` are used to kill those processes cleanly when needed. `json` handles persistence. `pathlib.Path` is used for all file operations. `shlex` safely splits shell command strings into argument lists (used for the companion app launcher).

### 5.2 Path constants

```python
CONFIG_DIR     = Path.home() / ".config" / "MangoHud"
CONFIG_FILE    = CONFIG_DIR / "MangoHud.conf"
GUBERNATOR_DIR = Path.home() / ".config" / "gubernator"
WRAPPER_SCRIPT = GUBERNATOR_DIR / "gubr-launch"
SETTINGS_FILE  = GUBERNATOR_DIR / "settings.json"
GAMES_DIR      = GUBERNATOR_DIR / "games"          # per-game settings / wrappers
STEAM_COMMAND  = f"{WRAPPER_SCRIPT} %command%"
```

All file paths are defined as module-level constants so they can be changed in one place. `Path.home()` returns the current user's home directory (e.g. `/home/alice`). The `/` operator on `Path` objects joins path segments, equivalent to `os.path.join`.

`GAMES_DIR` is the directory that holds all per-game files. It is created on demand (never upfront) by whichever function first needs to write into it.

`STEAM_COMMAND` is the string you paste into Steam → Game Properties → Launch Options. `%command%` is Steam's placeholder for the actual game executable and its arguments.

### 5.3 DEFAULT_STATE – the single source of truth

`DEFAULT_STATE` is a flat Python dictionary that holds the default value for every setting Gubernator manages. There is exactly one entry per setting. The types used are:

- `bool` – for toggles (on/off switches)
- `str` – for colors (6-character hex without `#`, e.g. `"e3673e"`), positions, dropdown selections
- `int` / `float` – for sliders and number inputs

This dict serves three purposes:

1. **Initial state** when no `settings.json` exists yet
2. **Fallback** when `settings.json` is missing a key (e.g. after adding a new option to a newer version)
3. **Type reference** so the rest of the code knows what kind of value to expect

`load_settings()` merges saved data on top of `DEFAULT_STATE`, so old settings files remain compatible when new keys are added.

Some keys end in `_text`. These control whether MangoHud shows a text label next to a metric (e.g. `fps_text=` suppresses the "FPS" label while keeping the number). They are currently stored in state but not yet exposed in the UI as separate controls.

The VSync keys are named `opengl_vsync` and `vulkan_vsync` in the state dict, but they are written to `MangoHud.conf` as `gl_vsync` and `vsync` respectively, because those are the actual MangoHud config key names.

A special key `mango_extra` (defaulting to an empty string) holds raw MangoHud config lines that the user can type directly. These are appended verbatim to the generated config, allowing any MangoHud option that Gubernator doesn't have a UI control for.

### 5.4 Color definitions

```python
COLOR_KEYS = [
    ("gpu_color",           "GPU"),
    ("cpu_color",           "CPU"),
    ("media_player_color",  "Media Player"),
    ("fps_color_1",         "FPS good"),
    ("fps_color_2",         "FPS medium"),
    ("fps_color_3",         "FPS bad"),
    ("engine_color",        "Engine"),
    ("frametime_color",     "Frametime"),
    ("wine_color",          "Wine / Proton"),
    ("battery_color",       "Battery"),
    ("network_color",       "Network"),
]
COLOR_KEY = [
    ("text_color",          "Text"),
    ("background_color",    "Background"),
    ("text_outline_color",  "Text Outline"),
    ("ram_color",           "RAM/PRAM"),
    ("vram_color",          "VRAM/PVRAM"),
    ("io_color",            "IO Read/Write"),
]
MULTI_COLOR_KEYS = {"gpu_load_color", "core_load_color"}
```

There are two separate color lists because they are used in different places in the UI:

- **`COLOR_KEYS`** – colors that are visually paired with their feature toggle. For example, the GPU color picker appears in the same row as the "GPU Usage" toggle. `build_conf()` iterates this list to write those values to the config. The UI does not show these in the Colors expander — they appear inline with their feature.
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

This means: the environment variable to export is `DXVK_ASYNC=1`, it is shown in the UI as "DXVK Async", its description says it reduces stutter, and it conflicts with `PROTON_USE_WINED3D=1` (because DXVK Async has no effect if you replaced DXVK with WineD3D).

The `env_var_string` uses `=` to encode both the variable name and its value in a single string. When writing the launcher script, the code splits on the first `=` to separate the variable name from its value.

A few entries have the same variable name but different values, making them mutually exclusive options:

```python
("PROTON_USE_NTSYNC=1", "NTSync", "Enable NTSync …", ["PROTON_USE_NTSYNC=0"]),
("PROTON_USE_NTSYNC=0", "Disable NTSync", "…some Proton versions have NTSync on by default", ["PROTON_USE_NTSYNC=1"]),
```

```python
("PROTON_USE_XALIA=1", "Enable Xalia", "…", []),
("PROTON_USE_XALIA=0", "Disable Xalia", "…", ["PROTON_USE_XALIA=1"]),
```

All sections are collected in `ALL_PROTON_SECTIONS`, which is a list of `(section_title, entries_list)` pairs. This drives the entire Proton-Tweaks tab UI with a single loop.

**The conflict map** is built automatically at module load time:

```python
CONFLICT_MAP = {}
for _, section in ALL_PROTON_SECTIONS:
    for key, _, _, conflicts in section:
        if key not in CONFLICT_MAP:
            CONFLICT_MAP[key] = set()
        for c in conflicts:
            CONFLICT_MAP[key].add(c)
            if c not in CONFLICT_MAP:
                CONFLICT_MAP[c] = set()
            CONFLICT_MAP[c].add(key)
```

This loop makes conflicts bidirectional. If entry A declares B as a conflict, the map will also say B conflicts with A, even if B's own definition doesn't list A. The result is a dictionary where `CONFLICT_MAP["DXVK_ASYNC=1"]` returns the set `{"PROTON_USE_WINED3D=1"}` and vice versa.

This map is queried at runtime in `_mkproton()` every time the user flips a Proton toggle.

### 5.7 Helper functions

**`hex_to_rgba(h)`** converts a 6-character hex string (e.g. `"e3673e"`) to a `Gdk.RGBA` object that GTK's `ColorButton` understands. It strips any `#` prefix, pads short strings to 6 chars, then divides each channel by 255 to get a float in the range 0.0–1.0.

**`rgba_to_hex(r)`** does the reverse: takes a `Gdk.RGBA` and returns a lowercase 6-char hex string for storage in the state dict.

**`detect_gpus()`** enumerates GPUs by reading the Linux kernel's PCI sysfs interface at `/sys/bus/pci/devices/`. It looks for devices where the `class` file starts with `0x03` (the PCI class code for display controllers). For each GPU it reads the `vendor` file to identify NVIDIA (`0x10de`), AMD (`0x1002`), or Intel (`0x8086`), and the `label` or `device` file for a human-readable name. Returns a list of `(index, name)` tuples. If fewer than 2 GPUs are found, the GPU selector dropdown is not shown in the UI.

**`sec_lbl(text)`** creates a styled heading label used above each preferences group in the UI. It left-aligns the text, applies the `"heading"` CSS class (which makes it bold and slightly larger), and adds margins.

**`adw_toggle(title, subtitle, active, cb, color_btn=None)`** is a factory for the most common UI pattern in the app: an `Adw.ActionRow` with a `Gtk.Switch` on the right. The optional `color_btn` parameter allows a `Gtk.ColorButton` to be inserted to the left of the switch in the same row, so the color picker and its toggle stay visually grouped. Returns a `(row, switch)` tuple.

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

`load_settings()` is called when `MainWindow.__init__()` runs and whenever the user switches to the global profile. It reads `settings.json`, starts with a fresh copy of `DEFAULT_STATE`, and then overwrites only the keys that exist in the saved file. This means:

- New keys added in a future version of Gubernator automatically get their default values.
- Corrupted or unreadable JSON files fall back to defaults silently.
- The in-memory state is always complete – no key is ever missing.

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

`load_game_settings()` returns `None` if no JSON file exists for this AppID (meaning the game has never been individually configured).

### 5.9 Steam library and game discovery

```python
def _acf_value(content: str, key: str) -> str:
    m = re.search(r'"' + re.escape(key) + r'"\s+"([^"]*)"', content, re.IGNORECASE)
    return m.group(1) if m else ""
```

Steam stores game metadata in `.acf` files (App Cache Files) using Valve's text-based KeyValues format (VDF). This function extracts a single field value using a regular expression: it looks for the key name between double quotes, followed by whitespace, followed by the value between double quotes.

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

Steam supports multiple library locations (e.g. one SSD and one HDD). `libraryfolders.vdf` lists all of them. `_steam_library_dirs()` reads that file and returns a list of every `steamapps/` directory that actually exists. The default library is always included first.

```python
def read_steam_games() -> list:
    games = []
    seen  = set()
    for steamapps in _steam_library_dirs():
        for acf in steamapps.glob("appmanifest_*.acf"):
            content = acf.read_text(errors="replace")
            appid   = _acf_value(content, "appid")
            name    = _acf_value(content, "name")
            if appid and name and appid not in seen:
                seen.add(appid)
                games.append((appid, name))
    return sorted(games, key=lambda x: x[1].lower())
```

`read_steam_games()` scans all Steam library directories for `.acf` files, extracts the AppID and game name from each, deduplicates (a game can't appear in two libraries at once, but this guards against edge cases), and returns a list of `(appid, name)` tuples sorted alphabetically by name. This list populates the sidebar.

### 5.10 write_wrapper – the smart launcher script

```python
def write_wrapper(proton_active: set, custom_vars: str):
    lines = [
        "#!/usr/bin/env bash",
        "# Gubernator launcher – auto-generated",
        "# One command for all games: gubr-launch %command%",
        "",
        "# Auto-select per-game MangoHud config when custom settings are saved",
        f'GAME_CONF="{GAMES_DIR}/${{SteamAppId}}.conf"',
        'if [ -n "$SteamAppId" ] && [ -f "$GAME_CONF" ]; then',
        '    export MANGOHUD_CONFIGFILE="$GAME_CONF"',
        "else",
        f'    export MANGOHUD_CONFIGFILE="{CONFIG_FILE}"',
        "fi",
        "export MANGOHUD=1",
        "",
    ]
    # ... global Proton tweaks ...
    lines += [
        f'GAME_ENV="{GAMES_DIR}/${{SteamAppId}}.env"',
        'if [ -n "$SteamAppId" ] && [ -f "$GAME_ENV" ]; then',
        '    set -a; source "$GAME_ENV"; set +a',
        "fi",
        "",
        # ... companion logic ...
        'exec "$@"',
    ]
    WRAPPER_SCRIPT.write_text("\n".join(lines))
    WRAPPER_SCRIPT.chmod(0o755)
```

This generates a bash script that is smarter than it might look. The key is that `$SteamAppId` is an environment variable that Steam sets automatically when launching any game. The script uses it at runtime to select the right files:

1. **MangoHud config selection**: if a per-game `.conf` exists for the current AppID, use it; otherwise fall back to the global `MangoHud.conf`.
2. **Global Proton tweaks**: the variables from the Global/Default settings are exported unconditionally.
3. **Per-game Proton overrides**: if a per-game `.env` file exists, it is sourced with `set -a` (auto-export mode) so all variables in it are automatically exported. The `.env` file may also contain `unset VAR` commands to cancel global tweaks that shouldn't apply to this game.
4. **Companion launch**: if a companion script exists for the current AppID, the game is launched as a background process (`"$@" &`), the companion starts after a delay, and the wrapper waits for the game to exit before terminating the companion.
5. **Normal launch**: if no companion is configured, `exec "$@"` replaces the shell process with the game. This is important for Steam to correctly detect when the game starts and stops.

`WRAPPER_SCRIPT.chmod(0o755)` makes the file executable. Without this, Steam cannot run it.

The `_env_vars()` helper extracts `(var, val)` pairs from both the active Proton set and the custom variables text field:

```python
def _env_vars(proton_active: set, custom_vars: str) -> list:
    result = []
    for key in proton_active:
        if "=" in key:
            var, val = key.split("=", 1)
            result.append((var, val))
    for line in custom_vars.strip().splitlines():
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            var, val = line.split("=", 1)
            result.append((var.strip(), val.strip()))
    return result
```

Note that `split("=", 1)` limits the split to one occurrence, which handles values that contain `=` themselves (e.g. `"VKD3D_CONFIG=dxr"`).

### 5.11 write_game_env and write_companion_script

**`write_game_env(appid, proton_active, custom_vars, global_active, global_custom_vars)`**

This function generates the per-game `.env` file that the global wrapper sources for a specific game. The tricky part is that a global Proton tweak might be active (e.g. `DXVK_ASYNC=1`) but this particular game should not use it. Simply not including that variable in the per-game file would not help, because the global wrapper already exported it before sourcing the per-game file.

The solution is to write explicit `unset VAR` commands for any variable that is active globally but not active for this game:

```python
global_vars = _env_vars(global_active or set(), global_custom_vars)
to_unset = sorted({var for var, _ in global_vars if var not in per_game_var_names})
# ...
for var in to_unset:
    lines.append(f"unset {var}")
```

This guarantees that per-game settings completely override the global Proton configuration, both for additions and removals.

**`write_companion_script(appid, exec_cmd, env_vars)`**

Generates the per-game `<appid>-companion.sh` script. This script is sourced by the global wrapper when the game starts. It:
1. Exports companion-specific environment variables.
2. Runs the companion executable using `exec` (with `shlex.quote()` for safe quoting of paths with spaces).

This script is created only when the user saves companion settings. The global wrapper checks for its existence at runtime; if the file is absent, it falls through to the normal `exec "$@"` path.

### 5.12 build_conf – the MangoHud config generator

`build_conf(s: dict)` takes the full state dict and produces the complete text of `MangoHud.conf` as a string. It uses two inner helper functions:

```python
def tog(k): return s.get(k, False)
def val(k): return s.get(k, DEFAULT_STATE.get(k))
```

`tog()` returns `True`/`False` for boolean keys. `val()` returns the raw value for any key, falling back to the default.

**Important MangoHud behaviour** you need to understand to read this code correctly:

Some MangoHud options are *enabled by default* in MangoHud itself (fps, gpu_stats, cpu_stats). If your config file simply omits them, they still appear in the overlay. To actually turn them off, you must write `fps=0`, `gpu_stats=0`, `cpu_stats=0` explicitly. Gubernator handles this:

```python
lines.append("fps=1" if tog("fps") else "fps=0")
lines.append("gpu_stats=1" if tog("gpu_stats") else "gpu_stats=0")
lines.append("cpu_stats=1" if tog("cpu_stats") else "cpu_stats=0")
```

For options that are *off by default*, you only write the key when the toggle is on:

```python
if tog("gpu_temp"): lines.append("gpu_temp")
```

**Frametime vs frame_timing**: MangoHud has two separate options:
- `frametime` (or `frametime=1`) – shows the millisecond value as a number
- `frame_timing=1` – shows the bar graph

These are controlled independently in Gubernator via `show_frametime` and `show_framegraph` in the state dict.

**fps_only mode**: When enabled, Gubernator writes `fps_only` and `legacy_layout=0` to the config. This activates MangoHud's special compact FPS-only display mode and skips writing all other metrics.

**Colors**: All color values (stored as 6-char hex strings in the state dict) are written directly as MangoHud config keys. Both `COLOR_KEYS` and `COLOR_KEY` are iterated in two separate passes (each preceded by a `# Colors` comment). Multi-stop colors (`gpu_load_color`, `core_load_color`) are comma-separated values that MangoHud uses for low/medium/high color thresholds.

**Text outline**: When enabled, two additional keys are written alongside the `text_outline` key:
```python
if tog("text_outline"):
    lines.append("text_outline")
    lines.append(f"text_outline_color={val('text_outline_color')}")
    lines.append(f"text_outline_thickness={float(val('text_outline_thickness')):.1f}")
```

**VSync**: The state dict uses `opengl_vsync` and `vulkan_vsync` as key names, but `build_conf()` writes them using MangoHud's actual key names `gl_vsync` and `vsync`:

```python
lines.append(f"gl_vsync={val('opengl_vsync')}")
lines.append(f"vsync={val('vulkan_vsync')}")
```

**Extra raw config lines**: The `mango_extra` key holds a raw multi-line string. Any non-empty lines from it are appended directly to the generated config, allowing advanced users to add any MangoHud option that doesn't have a UI control.

The function ends by collapsing consecutive blank lines to keep the output file clean even when many optional sections are disabled.

### 5.13 GameRow – the sidebar game widget

```python
class GameRow(Gtk.ListBoxRow):
    def __init__(self, appid, name):
        super().__init__()
        self.appid     = appid
        self.game_name = name
        # builds a two-line label: game name (truncated) + "AppID: 123456" or "Global Settings"
```

`GameRow` is a custom `Gtk.ListBoxRow` subclass that represents one entry in the sidebar list. Each row displays the game name on the first line (truncated with an ellipsis if too long, using `Pango.EllipsizeMode.END`) and a dimmed subtitle on the second line.

The special "Global / Default" row has `appid=None`. All per-game rows have their Steam AppID as a string. The `appid` attribute is read by the selection callback to know which game was chosen.

### 5.14 The GTK application – Gubernator and MainWindow

```python
class Gubernator(Adw.Application):
    def __init__(self):
        super().__init__(application_id="io.gubernator")
        self.connect("activate", lambda app: MainWindow(application=app).present())
```

`Gubernator` is a thin wrapper around `Adw.Application`. The `application_id` is a reverse-domain string that uniquely identifies the app on the system (used by D-Bus, the desktop environment, and `.desktop` files). The `activate` signal fires when the app is started. It creates the main window and calls `.present()` to show it.

`MainWindow` uses a **two-panel layout**: a fixed-width sidebar on the left and a flexible right panel. The sidebar lists all Steam games; the right panel shows the settings for whichever game is selected. When the user selects a different game, only the right panel is rebuilt — the sidebar stays in place.

**Key instance variables:**

```python
self.s                  # full state dict – all settings live here
self.selected_appid     # None = Global, otherwise a Steam AppID string
self.selected_name      # display name of the currently selected game
self.use_custom         # True if this game has per-game settings enabled
self._current_tab       # integer, remembers the active tab across rebuilds

self.proton_active      # set of active Proton env var strings
self.proton_custom      # contents of the custom vars text area
self.companion_exec     # companion app command string
self.companion_env      # companion env vars (raw text)
self.companion_autowrap # bool, show crash popup on unexpected exit

self._vkcube_proc       # subprocess.Popen handle for vkcube
self._companion_proc    # subprocess.Popen handle for companion app

# Widget reference dicts – reset each time the right panel rebuilds:
self._pos_btns          # position_name → Gtk.Button
self._fps_preset_btns   # preset_value → Gtk.Button
self._proton_switches   # env_var_string → Gtk.Switch
self._proton_callbacks  # env_var_string → callback closure (needed for handler_block_by_func)
self._conflict_rows     # env_var_string → Adw.ActionRow
```

**Why `_proton_callbacks` was added**: The conflict protection system uses `handler_block_by_func(cb)` to temporarily disconnect a callback. This requires a reference to the exact same function object that was passed to `sw.connect()`. Since `_mkproton()` returns a new closure each time, the closure reference must be stored in `_proton_callbacks` so it can be retrieved later. Storing only the switch widget in `_proton_switches` would not be enough.

**Three state helpers:**

```python
def _tog(self, k): return bool(self.s.get(k, DEFAULT_STATE.get(k, False)))
def _val(self, k): return self.s.get(k, DEFAULT_STATE.get(k))
def _set(self, k, v): self.s[k] = v; self._do_write()
```

These are called throughout the UI-building code. `_set()` both updates the state and immediately triggers a full write to disk and MangoHud config file.

**Header bar**: The header bar contains:
- **vkcube preview button** (left) – launches or stops the live preview
- **Copy Steam Command** (left) – an `Adw.SplitButton`. Clicking the left part copies the launch command to the clipboard. Clicking the right arrow opens a popover that shows the live content of the launcher script and MangoHud config.
- **Status label** (right) – shows brief feedback messages like "✓ saved" or error descriptions. Messages are cleared after 2.5 seconds via `GLib.timeout_add`.
- **Save & Apply button** (right) – an explicit save trigger (though `_do_write()` also runs on every individual toggle change).

### 5.15 The sidebar

```python
def _build_sidebar(self):
    # search entry + filter button + scrollable game list
```

The sidebar has three parts:

**Filter popover** – a `Gtk.MenuButton` with a funnel icon opens a small popover with three checkboxes. These hide entries whose names contain specific keywords:
- "Proton" – hides Proton version entries (e.g. "Proton 9.0")
- "Steam Linux Runtime" – hides the SLR compatibility tool entries
- "Steamworks" – hides Steamworks-related entries

The filter is implemented as a `Gtk.ListBox` filter function (`set_filter_func`). When any checkbox changes, `invalidate_filter()` re-runs the filter over the entire list.

**Search entry** – a `Gtk.SearchEntry` that filters the list by both game name and AppID. The filter function checks the query against `row.game_name.lower()` and `row.appid`.

**Game list** – a `Gtk.ListBox` in single-selection mode. The first entry is always "Global / Default" (appid=None). All installed Steam games follow, sorted alphabetically. Selecting a row fires `_on_game_selected()`, which calls `_switch_to()`.

**`_switch_to(appid, name)`** loads the correct settings and rebuilds the right panel. If the user clicks the same entry that's already selected, the function returns immediately without rebuilding anything. For per-game entries it calls `load_game_settings()` and, if `use_custom` is false, loads global settings as a read-only reference.

When a game with `use_custom=False` is selected, the entire right panel (notebook + tabs) is visually dimmed with `nb.set_sensitive(False)` to signal that changes would have no effect.

### 5.16 UI pages

The right panel contains a `Gtk.Notebook` with three tabs. The notebook is rebuilt completely each time `_build_right_panel()` is called. The active tab index is stored in `self._current_tab` and restored after each rebuild so the user doesn't lose their place when switching games.

For per-game entries, a "Custom Settings" toggle appears above the notebook. When it is off, the notebook is shown read-only (showing global settings as a preview). When it is turned on, the current global settings are copied as a starting point and become independently editable.

**`_page_mango()`** builds the MangoHud tab. It uses two row constructors:

- `adw_toggle(title, subtitle, active, cb, color_btn)` – for rows where the color button needs to be placed separately from the toggle logic
- `_make_full_row(title, subtitle, tog_key, color_key=None)` – creates an on/off row with an optional color picker. This is the standard row factory for most MangoHud metrics.

The tab contains these groups:
- **Performance** – FPS, frametime, frame graph, frame count, FPS color change, FPS limit (preset buttons + custom entry)
- **GPU** – GPU usage, temperatures, clocks, power, fan, VRAM, GPU selector dropdown (only shown with multiple GPUs)
- **CPU** – CPU usage, temperature, power, MHz, per-core metrics, RAM, swap
- **IO** – disk read/write throughput
- **Misc** – media player, wine, battery, network, resolution, clock, version info
- **Display** – sliders for font size, corner radius, background alpha, outline thickness; spinbox for table columns; toggles for compact/horizontal/no-margin/outline/hidden modes; 3×3 position grid
- **VSync** – separate dropdowns for OpenGL and Vulkan present modes
- **Colors** – collapsible expander showing `COLOR_KEY` colors (text, background, outline, RAM, VRAM, IO)
- **Extra Config Lines** – a monospace text area for raw MangoHud config lines

**`_page_proton()`** builds the Proton-Tweaks tab. It iterates over `ALL_PROTON_SECTIONS` and for each entry creates a toggle row with conflict protection. It also adds a text area at the bottom for custom environment variables (lines in `VAR=value` format).

**`_page_companion()`** builds the Custom App tab. It is only available for per-game entries. When "Global / Default" is selected, the tab shows an info message instead. Details are in [section 5.20](#520-the-companion-app-tab).

### 5.17 Callbacks and the write cycle

GTK uses a signal/callback pattern. When the user interacts with a widget, GTK fires a signal and calls any connected Python functions.

**For toggles:**

```python
sw.connect("notify::active", lambda sw, _, k=key: self._set(k, sw.get_active()))
```

`"notify::active"` fires whenever the switch value changes. The lambda captures `key` with a default argument to avoid the Python closure trap (where all lambdas in a loop would otherwise share the last value of `key`). `self._set()` updates state and triggers a write.

**For sliders:**

```python
sc.connect("value-changed", lambda sc, kk=sk: self._set(kk, sc.get_value()))
```

Same pattern. `sc.get_value()` returns the current slider position as a float.

**For color buttons:**

```python
cbtn.connect("color-set", lambda b, k=c_key: self._set(k, rgba_to_hex(b.get_rgba())))
```

`"color-set"` fires when the user confirms a color selection. `b.get_rgba()` returns the chosen color as a `Gdk.RGBA`, which `rgba_to_hex()` converts to a hex string for storage.

**The `_do_write()` method** is the central write function. It behaves differently depending on which profile is selected:

```python
def _do_write(self):
    self.s["proton_active"] = list(self.proton_active)
    self.s["proton_custom"] = self.proton_custom
    mango_text = build_conf(self.s)

    if self.selected_appid is None:
        # Global – write MangoHud.conf and the shared wrapper script
        save_settings(self.s)
        write_conf(mango_text)
        write_wrapper(self.proton_active, self.proton_custom)
    elif self.use_custom:
        # Per-game – write game JSON, per-game MangoHud conf, and per-game env file
        save_game_settings(self.selected_appid, game_state)
        (GAMES_DIR / f"{self.selected_appid}.conf").write_text(mango_text)
        write_game_env(self.selected_appid, ...)
    else:
        # Game with custom disabled – show global conf as preview only
        mango_text = build_conf(load_settings())

    self.conf_preview.set_label(mango_text)
    if script_path.exists():
        self.script_preview.set_label(script_path.read_text())
    self._set_status("✓ saved")
```

For global settings, the wrapper script is regenerated on every write because the user might have changed which global Proton tweaks are active. For per-game settings, only the per-game files change; the wrapper script itself does not need to be rewritten (it reads `$SteamAppId` at runtime).

### 5.18 The vkcube live preview

```python
def _toggle_vkcube(self, btn):
    if self._vkcube_proc and self._vkcube_proc.poll() is None:
        # vkcube is running – kill it
        os.killpg(os.getpgid(self._vkcube_proc.pid), signal.SIGTERM)
        self._vkcube_proc = None
    else:
        # launch vkcube
        env = os.environ.copy()
        env["MANGOHUD"] = "1"
        env["MANGOHUD_CONFIGFILE"] = str(CONFIG_FILE)
        self._vkcube_proc = subprocess.Popen(
            ["vkcube"], env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid,
        )
        GLib.timeout_add(1000, self._poll_vkcube)
```

`vkcube` is a spinning Vulkan demo cube from the `vulkan-tools` package. It is used here purely as a Vulkan application that MangoHud can hook into, so you can see your overlay settings live without launching a game.

Key implementation details:

- `os.environ.copy()` creates a fresh copy of the current environment so we can add variables without polluting the parent process.
- `preexec_fn=os.setsid` creates a new process session for vkcube. This means `os.killpg(os.getpgid(pid), signal.SIGTERM)` can kill vkcube and all its child processes cleanly.
- `stdout=subprocess.DEVNULL` and `stderr=subprocess.DEVNULL` discard vkcube's output so it doesn't pollute the terminal.
- `subprocess.Popen.poll()` returns `None` if the process is still running, or an exit code if it has finished.
- `GLib.timeout_add(1000, self._poll_vkcube)` schedules `_poll_vkcube` to be called by GTK's main loop every 1000 milliseconds. If vkcube was closed by the user (clicking the X on its window), this detects it and resets the button label. `_poll_vkcube` returns `False` to stop the timer, or `True` to keep it running.

If `vkcube` is not installed, the `FileNotFoundError` is caught and a status message is shown instead of crashing.

The preview always uses the **global** `MangoHud.conf`, not a per-game one. This is intentional — vkcube is not a real game and has no AppID, so only the global config applies.

### 5.19 The conflict protection system

The `_mkproton()` method returns a callback function (a closure) that handles toggling a Proton option:

```python
def _mkproton(self, key, conflicts):
    def cb(sw, _):
        active = sw.get_active()
        if active:
            blocking = [c for c in CONFLICT_MAP.get(key, []) if c in self.proton_active]
            if blocking:
                # Revert the switch
                sw.handler_block_by_func(cb)
                sw.set_active(False)
                sw.handler_unblock_by_func(cb)
                # Flash conflicting rows red
                for c in blocking:
                    row = self._conflict_rows.get(c)
                    if row:
                        row.add_css_class("error")
                        GLib.timeout_add(1500, lambda r=row: r.remove_css_class("error") or False)
                self._set_status(f"Conflict: disable {', '.join(blocking)} first")
                return
            self.proton_active.add(key)
            # NTSync on → auto-activate "Disable Esync" and "Disable Fsync"
            if key == "PROTON_USE_NTSYNC=1":
                for auto in ["PROTON_NO_ESYNC=1", "PROTON_NO_FSYNC=1"]:
                    self.proton_active.add(auto)
                    s2  = self._proton_switches.get(auto)
                    cb2 = self._proton_callbacks.get(auto)
                    if s2 and cb2:
                        s2.handler_block_by_func(cb2)
                        s2.set_active(True)
                        s2.handler_unblock_by_func(cb2)
        else:
            self.proton_active.discard(key)
            # NTSync off → auto-deactivate "Disable Esync" and "Disable Fsync"
            if key == "PROTON_USE_NTSYNC=1":
                for auto in ["PROTON_NO_ESYNC=1", "PROTON_NO_FSYNC=1"]:
                    self.proton_active.discard(auto)
                    s2  = self._proton_switches.get(auto)
                    cb2 = self._proton_callbacks.get(auto)
                    if s2 and cb2:
                        s2.handler_block_by_func(cb2)
                        s2.set_active(False)
                        s2.handler_unblock_by_func(cb2)
        self._do_write()
    return cb
```

When the user enables a switch, the code looks up all conflicting keys in `CONFLICT_MAP` and checks if any of them are currently active. If a conflict is found:

1. `sw.handler_block_by_func(cb)` temporarily disconnects the callback so setting the switch programmatically doesn't trigger another callback invocation (infinite recursion).
2. `sw.set_active(False)` reverts the switch to off.
3. `sw.handler_unblock_by_func(cb)` reconnects the callback.
4. The conflicting row gets the `"error"` CSS class, which libadwaita renders as a red highlight.
5. `GLib.timeout_add(1500, ...)` removes the red highlight after 1.5 seconds.
6. A status message appears in the header bar.

**NTSync special case**: When NTSync (`PROTON_USE_NTSYNC=1`) is enabled, Gubernator also automatically enables "Disable Esync" and "Disable Fsync". When NTSync is disabled, those two are automatically turned off. This is because NTSync replaces both and running all three simultaneously would cause undefined behaviour. The same `handler_block_by_func` / `set_active` / `handler_unblock_by_func` pattern is used to update the companion switches without triggering their own callbacks.

Note that `handler_block_by_func` requires the **exact same closure object** that was passed to `connect()`. This is why each callback is stored in `self._proton_callbacks[key]` at build time and retrieved from there when needed for the NTSync automation.

### 5.20 The companion app tab

The "Custom App" tab (`_page_companion()`) is a per-game-only feature that lets you launch a companion Windows program (e.g. a game overlay, a trainer, a stats tool) inside the same Wine prefix as the game, with it starting and stopping automatically.

**How it works end-to-end:**

When the user saves a companion configuration, `_do_write()` calls `write_companion_script()` which generates a `<appid>-companion.sh` file in `GAMES_DIR`. The global wrapper script (`gubr-launch`) checks for this file at runtime. If it exists, instead of `exec "$@"` it does:

```bash
"$@" &                    # start the game in the background
_GC_GAME_PID=$!           # save its PID
sleep "${_GC_DELAY:-5}"   # wait for the game to initialize
bash "$_GC_COMPANION" &   # start the companion
wait "$_GC_GAME_PID"      # wait for the game to exit
kill -TERM "$_GC_COMPANION_PID"   # stop the companion
```

The delay defaults to 5 seconds but can be customised by adding a `COMPANION_DELAY=N` line in the companion script.

**The "Auto-fill Proton Prefix" button (`_on_companion_autofill()`):**

This button detects the correct Wine environment for the selected game automatically. It does two things:

1. Finds the game's Proton prefix at `~/.steam/steam/steamapps/compatdata/<appid>/pfx` (searching all Steam library paths). It writes `WINEPREFIX=<path>` into the companion's env vars text area.

2. Finds the right `wine` binary. It first scans `/proc` for a `wine` process that is already using the correct prefix (via `_find_running_proton_wine()`). If the game is running, this gives an exact version match. If the game is not running, it falls back to the newest Proton installation it can find.

**`_find_running_proton_wine(prefix)`** reads `/proc/<pid>/environ` for every running process, looking for one that has `WINEPREFIX` set to the target prefix and whose executable path contains "wine". This works because Steam sets `WINEPREFIX` in the environment of every process it launches inside a Proton prefix. Reading `/proc` requires no special privileges as long as you own the processes.

**Manual launch (`_toggle_companion()`):**

The "Launch App" button lets you start the companion without launching the game first. This is useful for testing. When launched manually, Gubernator tries to match the running game's Proton wine binary (using `_find_running_proton_wine()`) so the companion joins the existing wineserver rather than starting a new one (a version mismatch would cause a silent hang). It strips `LD_PRELOAD` from the inherited environment because the Steam overlay `.so` files it contains will crash a wine process launched outside Pressure Vessel (Steam's sandbox container).

**Crash popup (`companion_autowrap`):**

When enabled, a `_show_companion_crash()` dialog appears if the companion exits unexpectedly (non-zero exit code or any output). It shows the exit code and up to 1200 characters of the companion's stdout/stderr output (captured via `subprocess.PIPE`). This is useful for diagnosing wine errors without needing a terminal.

---

## 6. Data flow diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                  MainWindow (GTK)                                │
│                                                                  │
│  Sidebar          Right Panel                                    │
│  (game list)      ┌──────────────────────────────────────────┐  │
│                   │ [Custom Settings toggle – games only]     │  │
│  Select game  ──► │                                           │  │
│  → _switch_to()   │  MangoHud Tab   Proton Tab   Companion    │  │
│                   │  toggles        toggles       Tab         │  │
│                   │  sliders        (+ conflict   exec/env    │  │
│                   │  color pickers   protection)  autofill    │  │
│                   └──────────┬───────────┬──────────┘         │  │
│                              │           │                     │  │
│                              ▼           ▼                     │  │
│                         _set(key,v) / _mkproton()              │  │
│                              │                                  │  │
│                         _do_write()                             │  │
│                              │                                  │  │
└──────────────────────────────┼──────────────────────────────────┘
                               │
              ┌────────────────┼──────────────────────┐
              │                │                       │
    [Global selected]   [Per-game + use_custom=True]   [Per-game + use_custom=False]
              │                │                            │
   save_settings()    save_game_settings()          read global for preview only
   write_conf()       write game .conf              (no files written)
   write_wrapper()    write_game_env()
              │                │
              ▼                ▼
       MangoHud.conf    games/<appid>.conf
       gubr-launch  games/<appid>.env
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

Find the appropriate section (GPU, CPU, Misc, etc.) and add the line:

```python
if tog("my_new_option"): lines.append("my_new_option")
```

If it is an option that is enabled by default in MangoHud and must be explicitly disabled, use:

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

If the new option has a color that should appear inline with its toggle, also add the color key to `COLOR_KEYS` so `build_conf()` writes it. If the color belongs in the standalone Colors expander instead, add it to `COLOR_KEY`.

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

The format is strictly `(env_var_string, title, subtitle, conflicts_list)`. Use `[]` for the conflicts list if there are none.

**Step 2 – Done.**

Because the Proton-Tweaks page is built by iterating `ALL_PROTON_SECTIONS`, the new entry automatically appears as a row in the UI with correct conflict checking. The conflict map is also rebuilt automatically at module load time.

If you need a new conflict that is bidirectional (both options should block each other), you only need to declare it in one direction – the conflict map builder makes it symmetric.

**Adding a mutually exclusive pair** (like Enable/Disable Xalia): declare both entries, each listing the other as a conflict:

```python
("MY_VAR=on",  "Enable Feature", "Enable …",  ["MY_VAR=off"]),
("MY_VAR=off", "Disable Feature", "Disable …", ["MY_VAR=on"]),
```

---

## 9. MangoHud config key reference

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

## 10. Proton environment variable reference

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
| `PROTON_ENABLE_WAYLAND` | `1` | Use native Wayland rendering instead of XWayland. Requires Proton 9+. |
| `PROTON_ENABLE_HDR` | `1` | Enable HDR output through Proton. Requires a Wayland compositor with HDR support and an HDR-capable display. |
| `ENABLE_HDR_WSI` | `1` | Enable HDR through the Vulkan WSI (Window System Integration) layer. Works with gamescope and KDE Plasma 6. |

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

## 11. External sources and further reading

| Source | URL | What you will find there |
|---|---|---|
| MangoHud GitHub | https://github.com/flightlessmango/MangoHud | Full config key reference, `data/MangoHud.conf` contains every option with comments |
| MangoHud ArchWiki | https://wiki.archlinux.org/title/MangoHud | Installation, per-game configs, global enable, Wine integration |
| Proton GitHub | https://github.com/ValveSoftware/Proton | Complete list of all official Proton environment variables with descriptions |
| DXVK GitHub | https://github.com/doitsujin/dxvk | DXVK config options, `DXVK_ASYNC`, `DXVK_HUD`, state cache |
| vkd3d-proton GitHub | https://github.com/HansKristian-Work/vkd3d-proton | `VKD3D_CONFIG` options, DXR support, feature levels |
| GOverlay GitHub | https://github.com/benjamimgois/goverlay | The inspiration for the wrapper-script approach (fgmod) |
| Steam VDF/ACF format | https://developer.valvesoftware.com/wiki/KeyValues | The text format used by `appmanifest_*.acf` and `libraryfolders.vdf` |
| GTK4 Python docs | https://docs.gtk.org/gtk4/ | GTK widget reference |
| libadwaita docs | https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/ | Adw.ActionRow, Adw.PreferencesGroup, Adw.SplitButton, Adw.ApplicationWindow |
| PyGObject docs | https://pygobject.gnome.org/ | Python GObject introspection, signal/callback system |
| CachyOS gaming guide | https://wiki.cachyos.org/configuration/gaming/ | RADV_PERFTEST, AMD Anti-Lag, proton-cachyos specific vars |
| GamingOnLinux | https://www.gamingonlinux.com | MangoHud release news, GOverlay updates |
| Steam Deck MangoHud presets | https://dbeley.ovh/en/post/2023/03/23/the-mangohud-presets-used-by-the-steam-deck/ | Real-world config examples from Valve's own presets |
| Linux /proc filesystem | https://www.kernel.org/doc/html/latest/filesystems/proc.html | How `/proc/<pid>/environ` and `/proc/<pid>/exe` work (used by the companion autofill) |
