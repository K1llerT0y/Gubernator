#!/usr/bin/env python3
"""
Gubernator – One command, full control
Linux / GTK4 + libadwaita

Dependencies:
  ./install.sh
"""

"""
LICENSE

Gubernator – One command, full control
Copyright (C) 2026  K1llerT0y

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import gi, re
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, GLib, Pango
from pathlib import Path
import subprocess, signal, os, json, shlex, shutil, random
import threading, urllib.request, urllib.parse, datetime

# ── Paths ─────────────────────────────────────────────────────────────────────
CONFIG_DIR     = Path.home() / ".config" / "MangoHud"
CONFIG_FILE    = CONFIG_DIR / "MangoHud.conf"
GUBERNATOR_DIR   = Path.home() / ".config" / "gubernator"
WRAPPER_SCRIPT = GUBERNATOR_DIR / "gubr-launch"
SETTINGS_FILE  = GUBERNATOR_DIR / "settings.json"
GAMES_DIR           = GUBERNATOR_DIR / "games"          # per-game settings / wrappers
HIDDEN_APPIDS_FILE  = GUBERNATOR_DIR / "hidden_appids.json"
STEAM_COMMAND  = f"{WRAPPER_SCRIPT} %command%"

_LOGO_PATH = next(
    (str(p) for p in [
        Path(__file__).parent / "icong.svg",
        Path.home() / ".local/share/icons/hicolor/scalable/apps/io.gubernator.svg",
    ] if p.exists()),
    None,
)

# ── Proton Version Manager ─────────────────────────────────────────────────────
COMPAT_DIR   = Path.home() / ".steam" / "root" / "compatibilitytools.d"
MANAGED_FILE = GUBERNATOR_DIR / "proton_managed.json"

PROTON_PLUS_FLATPAK  = "com.github.DavidoTek.ProtonPlus"
PROTONUP_QT_FLATPAK  = "net.davidotek.pupgui2"
APPIMAGE_DIRS        = [Path.home() / ".local/share/AppImage", Path.home() / "Applications"]
PROTONDB_URL         = "https://www.protondb.com/"
PROTON_PLUS_URL      = "https://github.com/DavidoTek/ProtonPlus/releases"
PROTONUP_QT_URL      = "https://github.com/DavidoTek/ProtonUp-Qt/releases"

ALL_PROTON_LABELS = [
    "Proton-GE", "Proton-CachyOS", "DW-Proton", "Proton-EM", "Proton-GE-RTSP",
    "Proton-Tkg", "Luxtorpeda", "Roberta", "Boxtron",
]

# ── Per-game tweak database (PCGamingWiki-sourced, keyed by Steam AppID) ─────

_LABEL_PATTERNS = {
    "Proton-GE":      ["ge-proton", "proton-ge"],
    "Proton-CachyOS": ["proton-cachyos", "cachyos-proton", "cachyos"],
    "DW-Proton":      ["dw-proton", "dwproton"],
    "Proton-EM":      ["proton-em"],
    "Proton-GE-RTSP": ["ge-rtsp", "proton-ge-rtsp"],
    "Proton-Tkg":     ["proton-tkg", "tkg"],
    "Luxtorpeda":     ["luxtorpeda"],
    "Roberta":        ["roberta"],
    "Boxtron":        ["boxtron"],
}

# ── Default state ─────────────────────────────────────────────────────────────
DEFAULT_STATE = {
    # Performance
    "fps":               True,
    "fps_text":          True,   # show label next to fps
    "fps_only":          False,
    "frame_count":       False,
    "frame_count_text":  True,
    "show_frametime":    True,
    "show_framegraph":   True,
    "frametime_text":    True,
    "fps_color_change":  False,
    "fps_sampling_period": 500,
    # GPU
    "gpu_stats":         True,
    "gpu_stats_text":    True,
    "gpu_temp":          True,
    "gpu_temp_text":     True,
    "gpu_junction_temp": False,
    "gpu_core_clock":    False,
    "gpu_mem_clock":     False,
    "gpu_mem_temp":      False,
    "gpu_power":         False,
    "gpu_power_limit":   False,
    "gpu_fan":           False,
    "gpu_voltage":       False,
    "gpu_load_change":   False,
    "gpu_efficiency":    False,
    "vram":              True,
    "vram_text":         True,
    "proc_vram":         True,
    "proc_vram_text":    True,
    # CPU
    "cpu_stats":         True,
    "cpu_stats_text":    True,
    "cpu_temp":          True,
    "cpu_temp_text":     True,
    "cpu_power":         False,
    "cpu_mhz":           False,
    "core_load":         False,
    "core_load_change":  False,
    "core_bars":         False,
    "cpu_efficiency":    False,
    "ram":               True,
    "ram_text":          True,
    "procmem":           True,
    "procmem_text":      True,
    "swap":              False,
    # IO
    "io_read":           False,
    "io_write":          False,
    # Misc
    "media_player":      True,
    "wine":              False,
    "resolution":        False,
    "time":              False,
    "time_no_label":     False,
    "version":           False,
    "arch":              False,
    "gpu_name":          False,
    "api":               False,
    "vulkan_driver":     False,
    "gamemode":          False,
    "throttling_status": False,
    "battery":           False,
    "network":           False,
    # Display
    "hud_compact":       False,
    "horizontal":        False,
    "hud_no_margin":     False,
    "text_outline":      False,
    "no_display":        False,
    # Colors
    "text_color":           "ffffff",
    "background_color":     "020202",
    "gpu_color":            "39f900",
    "cpu_color":            "2ea3f2",
    "vram_color":           "e01b24",
    "ram_color":            "f8e45c",
    "media_player_color":   "d600ff",
    "fps_color_1":          "b22222",
    "fps_color_2":          "fdfd09",
    "fps_color_3":          "39f900",
    "engine_color":         "813d9c",
    "frametime_color":      "00ff00",
    "wine_color":           "eb5b5b",
    "gpu_load_color":       "39f900,fdfd09,b22222",
    "core_load_color":      "39f900,fdfd09,b22222",
    "battery_color":        "ff9078",
    "io_color":             "a491d3",
    "network_color":        "e07b85",
    "text_outline_color":   "000000",
    # Sliders
    "font_size":            20,
    "round_corners":        8,
    "background_alpha":     0.5,
    "table_columns":        1,
    "text_outline_thickness": 1.5,
    # Position / VSync
    "position":          "top-right",
    "fps_limit":         0,
    "gpu_index":         -1,
    "opengl_vsync":      "-1",
    "vulkan_vsync":      "3",
}

# ── Color labels ──────────────────────────────────────────────────────────────
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
# Multi-stop colors stored as CSV strings – shown as text entries
MULTI_COLOR_KEYS = {"gpu_load_color","core_load_color"}

# ── HUD position grid ─────────────────────────────────────────────────────────
POSITIONS = [
    ("top-left",0,0),("top-center",0,1),("top-right",0,2),
    ("middle-left",1,0),("middle",1,1),("middle-right",1,2),
    ("bottom-left",2,0),("bottom-center",2,1),("bottom-right",2,2),
]
POS_ARROWS = {
    "top-left":"↖","top-center":"↑","top-right":"↗",
    "middle-left":"←","middle":"·","middle-right":"→",
    "bottom-left":"↙","bottom-center":"↓","bottom-right":"↘",
}
FPS_PRESETS = [0,60,120,144,165,240]
OPENGL_VSYNC = [("-1","Adaptive sync"),("0","Off"),("1","On"),("n","Sync to refresh rate")]
VULKAN_VSYNC  = [("0","Adaptive VSync (FIFO_RELAXED_KHR)"),("1","Off (IMMEDIATE_KHR)"),("2","Mailbox (VSync with uncapped FPS) (MAILBOX_KHR)"),("3","On FIFO_KHR")]

# ── Proton tweak definitions ──────────────────────────────────────────────────
# (key, title, subtitle, conflicts_with_list)
PROTON_SYNC = [
    ("PROTON_USE_NTSYNC=1","NTSync","Kernel 6.14+ required. Newer, faster kernel-level sync.",["PROTON_USE_NTSYNC=0"]),
    ("PROTON_NO_ESYNC=1","Disable Esync","Disable eventfd sync – DISABLE when using NTSync",[]),
    ("PROTON_NO_FSYNC=1","Disable Fsync","Disable futex sync – DISABLE when using NTSync",[]),
    ("PROTON_USE_NTSYNC=0","Disable NTSync","some proton-versions has NTSync enabled by default",["PROTON_USE_NTSYNC=1"]),
]
PROTON_WAYLAND_HDR = [
    ("PROTON_ENABLE_WAYLAND=1","Proton Wayland","Native Wayland rendering (Proton 9+)",[]),
]
PROTON_WINE = [
    ("PROTON_USE_WOW64=1","WOW64 Mode","Run 32-bit games without 32-bit userspace. Incompatible with PROTON_NVIDIA_LIBS",["PROTON_NVIDIA_LIBS=1"]),
    ("PROTON_USE_XALIA=1","Enable Xalia","Gamepad UI for keyboard/mouse interfaces",[]),
    ("PROTON_USE_XALIA=0","Disable Xalia","Force-disable Xalia if causing crashes",["PROTON_USE_XALIA=1"]),
    ("WINE_LARGE_ADDRESS_AWARE=1","Large Address Aware","Force LAA for 32-bit games (>2GB RAM). Usually on by default",[]),
    ("PROTON_HEAP_DELAY_FREE=1","Heap Delay Free","Delay freeing memory – fixes use-after-free bugs",[]),
    ("STAGING_SHARED_MEMORY=1","Staging Shared Memory","Wine Staging shared memory optimisation",[]),
    ("PROTON_USE_WINED3D=1","WineD3D instead of DXVK","OpenGL fallback for D3D9/10/11",["DXVK_ASYNC=1","VKD3D_CONFIG=dxr"]),
]
PROTON_DXVK = [
    ("DXVK_ASYNC=1","DXVK Async","Async shader compilation – reduces stutter. Do not use with WineD3D",["PROTON_USE_WINED3D=1"]),
    ("DXVK_FRAME_RATE=0","DXVK Frame Rate Limit","Set to 0 to disable DXVK's internal limiter",[]),
    ("DXVK_HUD=fps","DXVK HUD","Show DXVK's built-in HUD (fps). Use instead of MangoHud for debugging",[]),
    ("DXVK_STATE_CACHE_PATH=/tmp","DXVK Cache → /tmp","Store shader cache in RAM",[]),
    ("VKD3D_CONFIG=dxr","DXR Raytracing","Enable DXR via VKD3D",["PROTON_USE_WINED3D=1"]),
    ("VKD3D_FEATURE_LEVEL=12_1","DX12 Feature 12_1","Force VKD3D feature level",[]),
]
PROTON_NVIDIA = [
    ("NVPRESENT_ENABLE_SMOOTH_MOTION=1","Smooth Motion","Enable NVIDIA Smooth Motion",[]),
    ("NVPRESENT_QUEUE_FAMILY=1","SM prone to cause issues with third party overlays","In order to avoid this enable this",[]),
    ("PROTON_ENABLE_NVAPI=1","Enable NVAPI","Enable Nvidia NVAPI support (DLSS, Reflex etc.)",[]),
    ("DXVK_ENABLE_NVAPI=1","DXVK NVAPI","Enable NVAPI in DXVK layer",[]),
    ("DXVK_NVAPI_VKREFLEX=1","Enable Nvidia Reflex","Enable Reflex in native Vulkan games",[]),
    ("__GL_THREADED_OPTIMIZATIONS=1","GL Threaded Optimizations","Nvidia OpenGL threaded opts",[]),
    ("__NV_PRIME_RENDER_OFFLOAD=1","PRIME Render Offload","Use discrete Nvidia GPU on Optimus laptops",["DRI_PRIME=1"]),
    ("__VK_LAYER_NV_optimus=NVIDIA_only","Force Nvidia Vulkan","Force Nvidia GPU for Vulkan on Optimus",["DRI_PRIME=1"]),
    ("PROTON_HIDE_NVIDIA_GPU=1","Hide Nvidia GPU","Report as AMD – fixes nvapi-dependent crashes",[]),
    ("PROTON_NVIDIA_LIBS=1","Nvidia Libs (CachyOS)","Extra Nvidia libs (proton-cachyos only). Incompatible with WOW64",["PROTON_USE_WOW64=1"]),
]
PROTON_AMD = [
    ("DRI_PRIME=1","DRI PRIME","Use discrete AMD GPU on hybrid laptops",["__NV_PRIME_RENDER_OFFLOAD=1","__VK_LAYER_NV_optimus=NVIDIA_only"]),
    ("ENABLE_LAYER_MESA_ANTI_LAG=1","AMD Anti-Lag","Reduce input latency (AMD only)",[]),
    ("RADV_PERFTEST=gpl","RADV GPL","Enable Vulkan Graphics Pipeline Library (reduces stutter on RADV)",[]),
    ("RADV_DEBUG=syncshaders","RADV Sync Shaders","Synchronous shader compilation for debugging breadcrumbs",[]),
    ("mesa_glthread=true","Mesa GL Thread","OpenGL multi-threading for Mesa",[]),
]
PROTON_MISC = [
    ("PROTON_LOG=1","Proton Logging","Write debug log to ~/steam-APPID.log",[]),
    ("PROTON_NO_STEAMINPUT=1","Disable Steam Input","Disable Steam controller remapping",[]),
    ("PROTON_FORCE_LARGE_ADDRESS_AWARE=1","Force LAA (override)","Override LAA flag even if game disables it",[]),
    ("ZINK=1","Zink (OpenGL→Vulkan)","Use Zink to translate OpenGL to Vulkan (Mesa)",[]),
]

ALL_PROTON_SECTIONS = [
    ("Sync Technology", PROTON_SYNC),
    ("Wayland & HDR", PROTON_WAYLAND_HDR),
    ("Wine & Compatibility", PROTON_WINE),
    ("DXVK / VKD3D", PROTON_DXVK),
    ("NVIDIA", PROTON_NVIDIA),
    ("AMD / Mesa", PROTON_AMD),
    ("Misc", PROTON_MISC),
]

# Build a flat conflict map: key → set of keys it conflicts with
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


# ── GTK helpers ───────────────────────────────────────────────────────────────

def hex_to_rgba(h: str) -> Gdk.RGBA:
    h = h.strip().lstrip("#").ljust(6,"0")[:6]
    rgba = Gdk.RGBA()
    rgba.red   = int(h[0:2],16)/255
    rgba.green = int(h[2:4],16)/255
    rgba.blue  = int(h[4:6],16)/255
    rgba.alpha = 1.0
    return rgba

def rgba_to_hex(r: Gdk.RGBA) -> str:
    return "{:02x}{:02x}{:02x}".format(int(r.red*255),int(r.green*255),int(r.blue*255))

def detect_gpus():
    """Enumerate PCI GPUs from sysfs."""
    gpus = []
    pci = Path("/sys/bus/pci/devices")
    if not pci.exists(): return gpus
    for dev in sorted(pci.iterdir()):
        try:
            cls = (dev/"class").read_text().strip()
        except: continue
        if not cls.startswith("0x03"): continue
        parts = []
        try:
            v = (dev/"vendor").read_text().strip()
            parts.append({"0x10de":"NVIDIA","0x1002":"AMD","0x8086":"Intel"}.get(v,v))
        except: pass
        for f in ["label","device"]:
            fp = dev/f
            if fp.exists():
                try: parts.append(fp.read_text().strip()); break
                except: pass
        gpus.append((len(gpus)," ".join(parts) or dev.name))
    return gpus

def sec_lbl(text):
    """Section heading label."""
    l = Gtk.Label(label=text)
    l.set_xalign(0); l.add_css_class("heading")
    l.set_margin_top(12); l.set_margin_bottom(4)
    return l

def adw_toggle(title, subtitle, active, cb, color_btn=None):
    """Adw.ActionRow with a Switch (and optional color button) on the right."""
    row = Adw.ActionRow(title=title, subtitle=subtitle)
    if color_btn is not None:
        row.add_suffix(color_btn)
    sw  = Gtk.Switch(valign=Gtk.Align.CENTER, active=active)
    sw.connect("notify::active", cb)
    row.add_suffix(sw); row.set_activatable_widget(sw)
    return row, sw


# ── Global persistence ────────────────────────────────────────────────────────

def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            saved = json.loads(SETTINGS_FILE.read_text())
            state = dict(DEFAULT_STATE)
            state.update(saved)
            return state
        except: pass
    return dict(DEFAULT_STATE)

def save_settings(state: dict):
    GUBERNATOR_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(state, indent=2))


# ── Per-game persistence ──────────────────────────────────────────────────────

def load_game_settings(appid: str):
    """Return the saved dict for this appid, or None if not yet saved."""
    path = GAMES_DIR / f"{appid}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except: pass
    return None

def save_game_settings(appid: str, state: dict):
    GAMES_DIR.mkdir(parents=True, exist_ok=True)
    (GAMES_DIR / f"{appid}.json").write_text(json.dumps(state, indent=2))

def load_hidden_appids() -> set:
    if HIDDEN_APPIDS_FILE.exists():
        try:
            return set(json.loads(HIDDEN_APPIDS_FILE.read_text()))
        except: pass
    return set()

def save_hidden_appids(appids: set):
    GUBERNATOR_DIR.mkdir(parents=True, exist_ok=True)
    HIDDEN_APPIDS_FILE.write_text(json.dumps(sorted(appids), indent=2))


# ── Steam library / game discovery ───────────────────────────────────────────

def _acf_value(content: str, key: str) -> str:
    """Extract a single quoted value from a Valve KeyValues (VDF/ACF) file."""
    m = re.search(r'"' + re.escape(key) + r'"\s+"([^"]*)"', content, re.IGNORECASE)
    return m.group(1) if m else ""

def _steam_library_dirs() -> list:
    """
    Parse libraryfolders.vdf to collect all Steam library steamapps directories.
    Always includes the default ~/.steam/steam/steamapps path.
    """
    dirs = []
    default = Path.home() / ".steam" / "steam" / "steamapps"
    if default.exists():
        dirs.append(default)

    vdf_path = default / "libraryfolders.vdf"
    if vdf_path.exists():
        try:
            content = vdf_path.read_text(errors="replace")
            for m in re.finditer(r'"path"\s+"([^"]+)"', content):
                extra = Path(m.group(1)) / "steamapps"
                if extra.exists() and extra not in dirs:
                    dirs.append(extra)
        except: pass

    return dirs

def read_steam_games() -> list:
    """Return sorted list of (appid, name, install_path) tuples for all installed Steam games."""
    games = []
    seen  = set()
    for steamapps in _steam_library_dirs():
        for acf in steamapps.glob("appmanifest_*.acf"):
            try:
                content    = acf.read_text(errors="replace")
                appid      = _acf_value(content, "appid")
                name       = _acf_value(content, "name")
                installdir = _acf_value(content, "installdir")
                if appid and name and appid not in seen:
                    seen.add(appid)
                    install_path = str(steamapps / "common" / installdir) if installdir else ""
                    games.append((appid, name, install_path))
            except: pass
    return sorted(games, key=lambda x: x[1].lower())


# ── Wrapper script generation ─────────────────────────────────────────────────

def _env_vars(proton_active: set, custom_vars: str) -> list:
    """Return list of (var, val) tuples from active Proton keys + custom lines."""
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

def write_wrapper(proton_active: set, custom_vars: str, mangohud_disabled: bool = False):
    """
    Write the single smart global wrapper used for ALL games.
    At runtime it reads $SteamAppId (set by Steam) and automatically
    selects the per-game MangoHud conf and Proton env when available.
    """
    GUBERNATOR_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "#!/usr/bin/env bash",
        "# Gubernator launcher – auto-generated",
        "# One command for all games: gubr-launch %command%",
        "",
    ]
    active_vars = _env_vars(proton_active, custom_vars)
    if active_vars:
        lines.append("# Global Proton tweaks")
        for var, val in active_vars:
            lines.append(f'export {var}="{val}"')
        lines.append("")
    lines += [
        "# Per-game Proton overrides (sourced when custom settings are enabled)",
        "# Per-game env can also export MANGOHUD=0 to disable MangoHud for this game",
        f'GAME_ENV="{GAMES_DIR}/${{SteamAppId}}.env"',
        'if [ -n "$SteamAppId" ] && [ -f "$GAME_ENV" ]; then',
        '    set -a; source "$GAME_ENV"; set +a',
        "fi",
        "",
        "# MangoHud – enabled by default; per-game env or nomangohud file can disable",
        f'GAME_CONF="{GAMES_DIR}/${{SteamAppId}}.conf"',
        'if [ -n "$SteamAppId" ] && [ -f "$GAME_CONF" ]; then',
        '    export MANGOHUD_CONFIGFILE="$GAME_CONF"',
        "else",
        f'    export MANGOHUD_CONFIGFILE="{CONFIG_FILE}"',
        "fi",
        *(["export MANGOHUD=0"] if mangohud_disabled else [
            f'if [ -n "$SteamAppId" ] && [ -f "{GAMES_DIR}/${{SteamAppId}}-nomangohud" ]; then',
            "    export MANGOHUD=0",
            'elif [ "${MANGOHUD:-1}" != "0" ]; then',
            "    export MANGOHUD=1",
            "fi",
        ]),
        "",
        "# Per-game extra launch arguments (e.g. RE Engine fix)",
        f'_GC_ARGS_FILE="{GAMES_DIR}/${{SteamAppId}}-launch-args.txt"',
        "_GC_EXTRA_ARGS=()",
        'if [ -n "$SteamAppId" ] && [ -f "$_GC_ARGS_FILE" ]; then',
        '    while IFS= read -r _arg; do',
        '        [ -n "$_arg" ] && _GC_EXTRA_ARGS+=("$_arg")',
        '    done < "$_GC_ARGS_FILE"',
        'fi',
        "",
        "# Per-game Game-tab tweaks launch arguments",
        f'_GC_TWEAKS_FILE="{GAMES_DIR}/${{SteamAppId}}-tweaks-args.txt"',
        'if [ -n "$SteamAppId" ] && [ -f "$_GC_TWEAKS_FILE" ]; then',
        '    while IFS= read -r _arg; do',
        '        [ -n "$_arg" ] && _GC_EXTRA_ARGS+=("$_arg")',
        '    done < "$_GC_TWEAKS_FILE"',
        'fi',
        "",
        "# Auto-launch companion if configured for this game",
        f'_GC_COMPANION="{GAMES_DIR}/${{SteamAppId}}-companion.sh"',
        'if [ -n "$SteamAppId" ] && [ -f "$_GC_COMPANION" ]; then',
        '    "$@" "${_GC_EXTRA_ARGS[@]}" &',
        '    _GC_GAME_PID=$!',
        "    _GC_DELAY=$(grep -m1 \"COMPANION_DELAY=\" \"$_GC_COMPANION\" 2>/dev/null | tr -dc '0-9')",
        '    sleep "${_GC_DELAY:-5}"',
        '    bash "$_GC_COMPANION" &',
        '    _GC_COMPANION_PID=$!',
        '    wait "$_GC_GAME_PID"',
        '    kill -TERM "$_GC_COMPANION_PID" 2>/dev/null',
        'else',
        '    exec "$@" "${_GC_EXTRA_ARGS[@]}"',
        'fi',
        "",
    ]
    WRAPPER_SCRIPT.write_text("\n".join(lines))
    WRAPPER_SCRIPT.chmod(0o755)

def write_game_env(appid: str, proton_active: set, custom_vars: str,
                   global_active: set = None, global_custom_vars: str = "",
                   mangohud_disabled: bool = False):
    """Write per-game Proton tweaks to <appid>.env, sourced by the global wrapper.

    Variables that global sets but this game leaves unchecked are written as
    `unset VAR` so the global export doesn't bleed through.
    Set mangohud_disabled=True to export MANGOHUD=0, which the wrapper reads
    after the Proton vars to disable MangoHud injection for this game.
    """
    GAMES_DIR.mkdir(parents=True, exist_ok=True)
    active_vars = _env_vars(proton_active, custom_vars)
    per_game_var_names = {var for var, _ in active_vars}

    # Any var exported globally but absent in per-game settings must be unset
    global_vars = _env_vars(global_active or set(), global_custom_vars)
    to_unset = sorted({var for var, _ in global_vars if var not in per_game_var_names})

    lines = [f"# Gubernator per-game env for AppID {appid} – auto-generated", ""]
    if mangohud_disabled:
        lines.append("export MANGOHUD=0")
        lines.append("")
    for var, val in active_vars:
        lines.append(f'export {var}="{val}"')
    if to_unset:
        if active_vars:
            lines.append("")
        lines.append("# Disable global tweaks not active for this game")
        for var in to_unset:
            lines.append(f"unset {var}")
    if not mangohud_disabled and not active_vars and not to_unset:
        lines.append("# No custom Proton tweaks for this game")
    (GAMES_DIR / f"{appid}.env").write_text("\n".join(lines) + "\n")


def write_companion_script(appid: str, exec_cmd: str, env_vars: str, delay: int = 30):
    """Generate per-game companion launcher script used by the global wrapper."""
    GAMES_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "#!/usr/bin/env bash",
        f"# gubernator companion for AppID {appid} – auto-generated",
        f"COMPANION_DELAY={max(0, int(delay))}",
        "",
    ]
    for line in env_vars.strip().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            var, val = line.split("=", 1)
            lines.append(f'export {var.strip()}="{val.strip()}"')
    lines.append("")
    try:
        parts = shlex.split(exec_cmd.strip())
        lines.append("exec " + " ".join(shlex.quote(p) for p in parts))
    except ValueError:
        lines.append(f"exec {exec_cmd.strip()}")
    lines.append("")
    path = GAMES_DIR / f"{appid}-companion.sh"
    path.write_text("\n".join(lines))
    path.chmod(0o755)


# ── MangoHud config builder ───────────────────────────────────────────────────

def build_conf(s: dict) -> str:
    def tog(k): return s.get(k, False)
    def val(k): return s.get(k, DEFAULT_STATE.get(k))
    lines = ["# MangoHud Config – Gubernator", ""]

    # ── Performance ──
    lines.append("# Performance")
    if tog("fps_only"):
        lines += ["fps_only", "legacy_layout=0"]
    else:
        lines.append("fps=1" if tog("fps") else "fps=0")
        if not tog("fps_text") and tog("fps"):
            lines.append("fps_text=")
        if tog("show_frametime"):  lines.append("frametime=1")
        else:                      lines.append("frametime=0")
        if tog("show_framegraph"): lines.append("frame_timing=1")
        else:                      lines.append("frame_timing=0")
        if tog("frame_count"):     lines.append("frame_count")
        if tog("fps_color_change"):lines.append("fps_color_change")
        lines.append(f"fps_sampling_period={int(val('fps_sampling_period'))}")
    fps_limit = val("fps_limit")
    if fps_limit and int(fps_limit) > 0:
        lines.append(f"fps_limit={int(fps_limit)}")
    lines.append("")

    # ── GPU ──
    lines.append("# GPU")
    lines.append("gpu_stats=1" if tog("gpu_stats") else "gpu_stats=0")
    if tog("gpu_temp"):         lines.append("gpu_temp")
    if tog("gpu_junction_temp"):lines.append("gpu_junction_temp")
    if tog("gpu_core_clock"):   lines.append("gpu_core_clock")
    if tog("gpu_mem_clock"):    lines.append("gpu_mem_clock")
    if tog("gpu_mem_temp"):     lines.append("gpu_mem_temp")
    if tog("gpu_power"):        lines.append("gpu_power")
    if tog("gpu_power_limit"):  lines.append("gpu_power_limit")
    if tog("gpu_fan"):          lines.append("gpu_fan")
    if tog("gpu_voltage"):      lines.append("gpu_voltage")
    if tog("gpu_load_change"):  lines.append("gpu_load_change")
    if tog("gpu_efficiency"):   lines.append("gpu_efficiency")
    if tog("vram"):             lines.append("vram")
    if tog("proc_vram"):        lines.append("proc_vram")
    gpu_index = val("gpu_index")
    if gpu_index is not None and int(gpu_index) >= 0:
        lines.append(f"gpu_list={int(gpu_index)}")
    lines.append("")

    # ── CPU ──
    lines.append("# CPU")
    lines.append("cpu_stats=1" if tog("cpu_stats") else "cpu_stats=0")
    if tog("cpu_temp"):         lines.append("cpu_temp")
    if tog("cpu_power"):        lines.append("cpu_power")
    if tog("cpu_mhz"):          lines.append("cpu_mhz")
    if tog("core_load"):        lines.append("core_load")
    if tog("core_load_change"): lines.append("core_load_change")
    if tog("core_bars"):        lines.append("core_bars")
    if tog("cpu_efficiency"):   lines.append("cpu_efficiency")
    if tog("ram"):              lines.append("ram")
    if tog("procmem"):          lines.append("procmem")
    if tog("swap"):             lines.append("swap")
    lines.append("")

    # ── IO ──
    if tog("io_read") or tog("io_write"):
        lines.append("# IO")
        if tog("io_read"):  lines.append("io_read")
        if tog("io_write"): lines.append("io_write")
        lines.append("")

    # ── Misc ──
    lines.append("# Misc")
    if tog("media_player"):    lines.append("media_player")
    if tog("wine"):            lines.append("wine")
    if tog("resolution"):      lines.append("resolution")
    if tog("time"):
        if tog("time_no_label"): lines.append("time_no_label")
        else:                    lines.append("time")
    if tog("version"):         lines.append("version")
    if tog("arch"):            lines.append("arch")
    if tog("gpu_name"):        lines.append("gpu_name")
    if tog("api"):             lines.append("api")
    if tog("vulkan_driver"):   lines.append("vulkan_driver")
    if tog("gamemode"):        lines.append("gamemode")
    if tog("throttling_status"): lines.append("throttling_status")
    if tog("battery"):         lines.append("battery")
    if tog("network"):         lines.append("network")
    lines.append("")

    # ── Display ──
    lines.append("# Display")
    lines.append(f"position={val('position')}")
    lines.append(f"font_size={int(val('font_size'))}")
    lines.append(f"round_corners={int(val('round_corners'))}")
    lines.append(f"background_alpha={float(val('background_alpha')):.2f}")
    tc = int(val("table_columns"))
    if tc > 1: lines.append(f"table_columns={tc}")
    if tog("hud_compact"):   lines.append("hud_compact")
    if tog("horizontal"):    lines.append("horizontal")
    if tog("hud_no_margin"): lines.append("hud_no_margin")
    if tog("no_display"):    lines.append("no_display")
    if tog("text_outline"):
        lines.append("text_outline")
        lines.append(f"text_outline_color={val('text_outline_color')}")
        lines.append(f"text_outline_thickness={float(val('text_outline_thickness')):.1f}")
    lines.append("")

    # ── Colors ──
    lines.append("# Colors")
    simple_color_keys = [k for k,_ in COLOR_KEYS if k not in MULTI_COLOR_KEYS and k != "text_outline_color"]
    for k in simple_color_keys:
        lines.append(f"{k}={val(k)}")
    for k in MULTI_COLOR_KEYS:
        lines.append(f"{k}={val(k)}")
    lines.append("")

    lines.append("# Colors")
    simple_color_keys = [k for k,_ in COLOR_KEY if k not in MULTI_COLOR_KEYS and k != "text_outline_color"]
    for k in simple_color_keys:
        lines.append(f"{k}={val(k)}")
    for k in MULTI_COLOR_KEYS:
        lines.append(f"{k}={val(k)}")
    lines.append("")

    # ── VSync ──
    lines.append("# VSync")
    lines.append(f"gl_vsync={val('opengl_vsync')}")
    lines.append(f"vsync={val('vulkan_vsync')}")
    lines.append("")

    # Collapse consecutive blank lines
    out, prev_blank = [], False
    for l in lines:
        blank = (l.strip()=="")
        if blank and prev_blank: continue
        out.append(l); prev_blank = blank
    return "\n".join(out)+"\n"

def write_conf(text):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(text)


# ── Proton Version Manager ─────────────────────────────────

def _version_belongs_to_label(dir_name: str, label: str) -> bool:
    lower = dir_name.lower()
    return any(p in lower for p in _LABEL_PATTERNS.get(label, []))

def get_installed_proton_versions() -> list:
    if not COMPAT_DIR.exists():
        return []
    return sorted(
        d.name for d in COMPAT_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )

def find_external_tool(flatpak_id: str, appimage_names: list[str], exe_names: list[str]) -> tuple[bool, list]:
    """Return (found, launch_cmd). Checks Flatpak, then PATH, then AppImage dirs."""
    try:
        r = subprocess.run(["flatpak", "info", flatpak_id], capture_output=True)
        if r.returncode == 0:
            return True, ["flatpak", "run", flatpak_id]
    except FileNotFoundError:
        pass
    for exe in exe_names:
        path = shutil.which(exe)
        if path:
            return True, [path]
    for d in APPIMAGE_DIRS:
        if d.is_dir():
            for name in appimage_names:
                matches = list(d.glob(f"*{name}*.AppImage"))
                if not matches:
                    matches = list(d.glob(f"*{name.lower()}*.appimage"))
                if matches:
                    return True, [str(matches[0])]
    return False, []

# ── Engine Detection & Config ──────────────────────────────────────────────────

def detect_engine(install_dir: str) -> str:
    p = Path(install_dir)
    if not p.exists():                          return "unknown"
    if (p / "natives").is_dir():                return "re_engine"
    if list(p.glob("re_chunk_*.pak")):          return "re_engine"
    if (p / "Engine" / "Binaries").is_dir():    return "unreal"
    if (p / "Content" / "Paks").is_dir():       return "unreal"
    if (p / "UnityPlayer.dll").exists():        return "unity"
    if (p / "UnityPlayer.so").exists():         return "unity"
    if list(p.glob("*.pck")):                   return "godot"
    if (p / "REDprelauncher.exe").exists():     return "red_engine"
    if (p / "r4data").is_dir():                 return "red_engine"
    if (p / "hl2.exe").exists():                return "source"
    if next(p.glob("*/GameInfo.txt"), None):    return "source"
    if next(p.glob("*/gameinfo.gi"),  None):    return "source"
    if next(p.glob("Data/*.esm"),     None):    return "creation"
    if next(p.glob("Data/*.bsa"),     None):    return "creation"
    if (p / "data.win").exists():               return "gamemaker"
    if (p / "game.unx").exists():               return "gamemaker"
    if (p / "Game.rgss3a").exists():            return "rpgmaker"
    if (p / "Game.rgss2a").exists():            return "rpgmaker"
    if (p / "www" / "data").is_dir():           return "rpgmaker"
    if (p / "engine.pak").exists():             return "cry_engine"
    if (p / "system.cfg").exists():             return "cry_engine"
    if (p / "Bin64").is_dir():                  return "cry_engine"
    if (p / "bin" / "win_x64").is_dir():        return "cry_engine"
    if (p / "Engine").is_dir():                 return "cry_engine"
    if (p / "engine").is_dir():                 return "cry_engine"
    if list(p.glob("*.pk4")) or list(p.glob("**/*.pk4")): return "id_tech"
    if list(p.glob("*.pk3")) or list(p.glob("**/*.pk3")): return "id_tech"
    if (p / "database.bp").exists():            return "decima"
    if list(p.glob("**/*.core")):               return "decima"
    if list(p.glob("**/*.fdata")):              return "katana"
    if next(p.glob("**/*.asr"), None) or next(p.glob("**/*.asr.*"), None): return "asura"
    return "unknown"


def find_unreal_config_dir(appid: str) -> "Path | None":
    for steamapps in _steam_library_dirs():
        pfx_user = steamapps / "compatdata" / appid / "pfx/drive_c/users/steamuser"
        if not pfx_user.exists():
            continue
        # Primary: AppData/Local/[Game]/Saved/Config/WindowsClient/
        local = pfx_user / "AppData/Local"
        if local.exists():
            for d in local.iterdir():
                for config_dir in ["WindowsClient", "WindowsNoEditor", "Windows"]:
                    candidate = d / "Saved" / "Config" / config_dir
                    if candidate.is_dir():
                        return candidate
        # Fallback: My Documents/My Games/[Game]/Config/WindowNoEditor
        for docs_dir in ["Documents/My Games", "My Documents/My Games"]:
            mydocs = pfx_user / docs_dir
            if mydocs.exists():
                for d in mydocs.iterdir():
                    for config_dir in ["WindowsClient", "WindowsNoEditor", "Windows"]:
                        candidate = d / "Config" / config_dir
                        if candidate.is_dir():
                            return candidate
        # Fallback: Saved Games/[folder]/[folder]/Saved/Config/WindowsNoEditor/
        saved_games = pfx_user / "Saved Games"
        if saved_games.exists():
            for d1 in saved_games.iterdir():
                if not d1.is_dir():
                    continue
                for d2 in d1.iterdir():
                    if not d2.is_dir():
                        continue
                    candidate = d2 / "Saved" / "Config" / "WindowsNoEditor"
                    if candidate.is_dir():
                        return candidate
    return None


def read_unreal_ini(ini_path: "Path", section: str) -> dict:
    import configparser
    cfg = configparser.ConfigParser(strict=False)
    cfg.optionxform = str
    if ini_path.exists():
        cfg.read(str(ini_path))
    sl = section.lower()
    for s in cfg.sections():
        if s.lower() == sl:
            return dict(cfg[s])
    return {}


def write_unreal_ini(ini_path: "Path", section: str, values: dict):
    import configparser
    cfg = configparser.ConfigParser(strict=False)
    cfg.optionxform = str
    if ini_path.exists():
        cfg.read(str(ini_path))
    target = section
    sl = section.lower()
    for s in cfg.sections():
        if s.lower() == sl:
            target = s
            break
    if target not in cfg:
        cfg[target] = {}
    cfg[target].update(values)
    ini_path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(ini_path), "w") as f:
        cfg.write(f)


def save_re_engine_args(appid: str, wine_detection_enabled: bool):
    GAMES_DIR.mkdir(parents=True, exist_ok=True)
    path = GAMES_DIR / f"{appid}-launch-args.txt"
    if not wine_detection_enabled:
        path.write_text("/WineDetectionEnabled:False\n")
    else:
        path.unlink(missing_ok=True)


def save_game_tweak_args(appid: str, args: list):
    GAMES_DIR.mkdir(parents=True, exist_ok=True)
    path = GAMES_DIR / f"{appid}-tweaks-args.txt"
    if args:
        path.write_text("\n".join(args) + "\n")
    else:
        path.unlink(missing_ok=True)


_PCGW_UA = "Gubernator/1.0 (Linux game config tool)"

def _pcgw_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": _PCGW_UA})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

# In-memory cache: populated once per session so revisiting a game never re-fetches.
_TWEAKS_SESSION_CACHE: dict = {}  # appid → {"launch_args": [...], "file_ops": [...]}

_RESOLUTION_KEYWORDS = frozenset({
    "width", "height", "resx", "resy", "xres", "yres",
    "screenwidth", "screenheight", "screen-width", "screen-height",
    "displaywidth", "displayheight", "resolution",
})
_RESOLUTION_SHORT = frozenset({"-x", "-y", "-w", "-h", "/x", "/y", "/w", "/h"})

_FPS_KEYWORDS = frozenset({
    "fps", "maxfps", "minfps", "fpscap", "fpsmax", "fpsmin", "fpsclamp",
    "maxframerate", "minframerate", "framelimit", "framerate",
    "maxfps_vsync_off", "maxfps_vsync_on",
})

def _is_resolution_arg(arg: str) -> bool:
    """Return True if the arg's first token is a resolution-related flag."""
    first = arg.split()[0]
    bare = first.lstrip("-+/").lower()
    if '=' in bare:
        bare = bare.split('=', 1)[0]
    return bare in _RESOLUTION_KEYWORDS or first.split('=', 1)[0] in _RESOLUTION_SHORT

def _is_fps_arg(arg: str) -> bool:
    """Return True if the arg's first token is an FPS / frame-rate flag."""
    token = arg.split()[0].lstrip("-+/").lower()
    return token in _FPS_KEYWORDS

_SCREEN_KEYWORDS = frozenset({
    "fullscreen", "windowed", "borderless", "noborder", "window",
    "exclusive", "monitor", "nofullscreen", "nowindow",
    "fullwindow", "exclusive-fullscreen",
})

def _is_screen_arg(arg: str) -> bool:
    """Return True if the arg's first token is a screen/window-mode flag."""
    token = arg.split()[0].lstrip("-+/").lower()
    if '=' in token:
        token = token.split('=', 1)[0]
    return token in _SCREEN_KEYWORDS or any(kw in token for kw in _SCREEN_KEYWORDS)

def _parse_pcgw_screen_resolution_html(html: str) -> list:
    """Scan <code> and <b> elements for screen/window/resolution CLI args.

    Formats covered:
      Format 2: <code>-arg</code>  anywhere on the page
      Format 3: <b>-arg</b>        anywhere on the page
    (Format 1 — template-infotable-monospace — and Format 4 — <li><code> inside <td> —
     are handled upstream by _parse_pcgw_args_html, feeding into all_screen_args.)

    Tokens with '=' (e.g. -resx=1920) are normalised to '-resx=' so the user
    can supply their own value in the UI.
    """
    args = []
    seen = set()

    def _try_add(token: str, ctx: str):
        # Normalise -flag=value → -flag=
        if '=' in token:
            token = token.split('=', 1)[0] + '='
        if not re.match(r'^[-+/]', token):
            return
        if _is_numeric_token(token.rstrip('=')):
            return
        if not re.search(r'[a-zA-Z_]', token):
            return
        if not (_is_resolution_arg(token) or _is_screen_arg(token)):
            return
        if token in seen:
            return
        seen.add(token)
        args.append({
            "arg":   token,
            "label": token,
            "desc":  ctx[:150].strip() or f"Screen/resolution argument: {token}",
        })

    # Formats 2 + 3: <code> and <b> elements anywhere on the page
    for m in re.finditer(r'<(?:code|b)[^>]*>\s*([^<]+?)\s*</(?:code|b)>', html):
        start = max(0, m.start() - 250)
        ctx = re.sub(r'\s+', ' ', _html_strip(html[start:m.end()])).strip()[-120:]
        for token in m.group(1).split():
            _try_add(token, ctx)

    return args

_WIDESCREEN_LABELS = [
    "Widescreen resolution",
    "4K Ultra HD",
    "Ultrawide",
    "Multi-monitor",
]

_STATUS_MAP = [
    (("table-yes",    "template-true"),    "Supported",     "success"),
    (("table-no",     "template-false"),   "Not supported", "error"),
    (("table-hackable","template-hackable"),"Hackable",     "warning"),
    (("table-limited", "template-limited"),"Limited",       "warning"),
    (("table-na",     "template-na"),      "N/A",           "dim-label"),
    (("table-unknown","template-unknown"), "Unknown",       "dim-label"),
]

def _parse_pcgw_widescreen_html(html: str) -> list:
    """Extract widescreen / 4K / ultrawide support rows from the PCGW Video settings table."""
    results = []
    seen = set()
    target_lower = {lbl.lower(): lbl for lbl in _WIDESCREEN_LABELS}

    for row_m in re.finditer(r'<tr[^>]*>([\s\S]+?)</tr>', html):
        cells = re.findall(r'<td([^>]*)>([\s\S]+?)</td>', row_m.group(1))
        if len(cells) < 2:
            continue

        label_text = _html_strip(cells[0][1]).strip()
        matched = next((canonical for key, canonical in target_lower.items()
                        if key in label_text.lower()), None)
        if not matched or matched in seen:
            continue

        attr1  = cells[1][0].lower()
        status = _html_strip(cells[1][1]).strip() or "Unknown"
        css    = "dim-label"
        for keys, s, c in _STATUS_MAP:
            if any(k in attr1 for k in keys):
                status, css = s, c
                break

        note = _html_strip(cells[2][1]).strip()[:200] if len(cells) >= 3 else ""

        seen.add(matched)
        results.append({"label": matched, "status": status, "css": css, "note": note})

    return results


def _html_strip(s: str) -> str:
    text = re.sub(r'<[^>]+>', '', s)
    for ent, ch in (('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'),
                    ('&#91;', '['), ('&#93;', ']'), ('&ndash;', '–'),
                    ('&mdash;', '—'), ('&nbsp;', ' ')):
        text = text.replace(ent, ch)
    return re.sub(r'\[\d+\]', '', text).strip()


def _is_numeric_token(s: str) -> bool:
    """Return True if s is a pure sign+digits value like '-1', '+0' — a parameter, not a flag."""
    return bool(re.match(r'^[-+/]\d+$', s))


def _fmt4_extract(cell_html: str, args: list, seen: set) -> None:
    """Format 4 helper: extract CLI args from <li><code>-flag=val -flag</code></li> inside cell_html.

    For tokens with '=' (e.g. -resx=1920), the value is stripped and only '-resx=' is stored,
    so the user can supply their own value in the UI.
    """
    for li_m in re.finditer(r'<li[^>]*>([\s\S]+?)</li>', cell_html):
        for code_m in re.finditer(r'<code[^>]*>([\s\S]+?)</code>', li_m.group(1)):
            code_text = _html_strip(code_m.group(1)).strip()
            desc = code_text.strip('.,').strip()
            for raw_tok in code_text.split():
                if not re.match(r'^[-+/]', raw_tok):
                    continue
                # Normalise -flag=value → -flag=  (user fills in value)
                if '=' in raw_tok:
                    token = raw_tok.split('=', 1)[0] + '='
                else:
                    token = raw_tok
                base = token.lstrip('-+/').rstrip('=')
                if not base or not re.search(r'[a-zA-Z_]', base):
                    continue
                if _is_numeric_token(token.rstrip('=')):
                    continue
                if token in seen:
                    continue
                seen.add(token)
                args.append({
                    "arg":   token,
                    "label": token,
                    "desc":  desc if len(desc) > 3 else f"Launch argument: {token}",
                })


def _parse_pcgw_args_html(html: str) -> list:
    """Extract command-line arguments from any PCGamingWiki rendered HTML section.

    PCGamingWiki uses four table formats for CLI args:
      Format 1: <td class="template-infotable-monospace">-arg</td>  (standard table)
      Format 2: <td><code>-arg</code></td>                          (wikitable + code)
      Format 3: <td><b>-arg</b></td>                                (wikitable + bold)
      Format 4: <td><ol><li>-arg ...</li></ol></td>                 (fixbox/wikitable list,
                  e.g. h3 → table → tbody → tr → td → ol → li)

    Compound args like '+connect_lobby -1' are supported in two ways:
      • Single cell:  the full string is kept as one toggle entry.
      • Two rows:     when a numeric-only row (e.g. '-1') immediately follows a named
                      flag, the two are merged into one compound entry.
    """
    args = []
    seen = set()

    for row_m in re.finditer(r'<tr[^>]*>([\s\S]+?)</tr>', html):
        cells = re.findall(r'<td([^>]*)>([\s\S]+?)</td>', row_m.group(1))
        if len(cells) < 2:
            # Format 4 only: single-cell rows with <ol/ul><li><code>-arg=val</code></li>
            if len(cells) == 1:
                _fmt4_extract(cells[0][1], args, seen)
            continue
        attr0, raw0 = cells[0]
        _, raw1 = cells[1]

        # Determine argument from first cell using Formats 1–3
        arg = None
        if 'template-infotable-monospace' in attr0:
            arg = _html_strip(raw0)
        else:
            m = re.search(r'<(?:code|b)>\s*([-+/][^<\s][^<]*?)\s*</(?:code|b)>', raw0)
            if m:
                arg = m.group(1).strip()

        # Format 4 on multi-cell rows: scan ALL cells for <li><code> when Formats 1–3 found nothing
        if not arg or not re.match(r'^[-+/]', arg):
            for _, raw_cell in cells:
                _fmt4_extract(raw_cell, args, seen)
            continue

        first_token = arg.split()[0]

        # Pure-numeric token (e.g. '-1') — it's a parameter value, not a standalone flag.
        # If the previous entry was a simple named flag, merge to form a compound arg.
        if _is_numeric_token(first_token):
            if args and ' ' not in args[-1]["arg"]:
                prev = args[-1]
                compound = f"{prev['arg']} {arg}"
                if compound not in seen:
                    seen.discard(prev["arg"])
                    seen.add(compound)
                    args[-1] = dict(prev, arg=compound, label=compound)
            continue

        # Skip tokens that have no alphabetic characters at all (catches malformed entries)
        if not re.search(r'[a-zA-Z_]', first_token):
            continue

        if arg in seen:
            continue

        desc = _html_strip(raw1).strip('.,').strip()
        seen.add(arg)
        args.append({
            "arg":   arg,
            "label": arg,
            "desc":  desc if len(desc) > 3 else f"Launch argument: {arg}",
        })
    return args


def _parse_pcgw_fixbox_inline_args(html: str) -> list:
    """Extract CLI flags embedded inside fixbox titles as <code> elements.

    Example: a fixbox title like
      "Bypass launcher with <code>--launcher-skip -skipStartScreen -modded</code> parameters"
    yields three separate arg entries, each using the full title as description.
    Only tokens starting with '-' or '+' are kept; value-tokens (pure digits,
    words, etc.) are skipped so that '-width 1920' yields only '-width'.
    """
    args = []
    for fixbox_m in re.finditer(r'<table[^>]*\bfixbox\b[^>]*>([\s\S]+?)</table>', html):
        title_m = re.search(
            r'<th[^>]*fixbox-title[^>]*>([\s\S]+?)</th>',
            fixbox_m.group(1),
        )
        if not title_m:
            continue
        title_html = title_m.group(1)
        desc = re.sub(r'\s+', ' ', _html_strip(title_html)).strip()
        for code_m in re.finditer(r'<code[^>]*>\s*([^<]+?)\s*</code>', title_html):
            for token in code_m.group(1).split():
                if re.match(r'^[-+]', token) and not _is_numeric_token(token) and re.search(r'[a-zA-Z_]', token):
                    args.append({"arg": token, "label": token, "desc": desc})
    return args


def _parse_pcgw_fixbox_files(html: str) -> list:
    """Extract file-deletion operations from PCGamingWiki fixbox tables.

    Only fixboxes whose title or body mention 'delete' or 'remove' and
    contain a <code> element with the <path-to-game> placeholder are returned.
    The placeholder is stripped and the remaining relative path is used as the
    glob pattern passed to Path.glob() at deletion time.
    """
    file_ops = []
    for fixbox_m in re.finditer(r'<table[^>]*\bfixbox\b[^>]*>([\s\S]+?)</table>', html):
        content = fixbox_m.group(1)

        # Title
        title_m = re.search(r'<th[^>]*fixbox-title[^>]*>([\s\S]+?)</th>', content)
        if not title_m:
            continue
        title = _html_strip(title_m.group(1)).strip()

        # Only handle deletion fixboxes
        combined = (title + content).lower()
        if 'delete' not in combined and 'remove' not in combined:
            continue

        # Extract file paths that include the <path-to-game> placeholder
        paths = []
        for code_m in re.finditer(r'<code[^>]*>([\s\S]+?)</code>', content):
            raw = code_m.group(1)
            if 'path-to-game' not in raw.lower():
                continue
            text = _html_strip(raw)
            # text looks like: <path-to-game>\Relative\Path\file.ext
            parts = re.split(r'<path-to-game>', text, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) < 2:
                continue
            rel = parts[1].strip('\\/').replace('\\', '/')
            if rel and rel not in paths:
                paths.append(rel)

        if not paths:
            continue

        file_ops.append({
            "label":   title,
            "desc":    f"Deletes: {paths[0]}",
            "globs":   paths,
            "confirm": title + "\n\nThis will permanently delete:\n" + "\n".join(paths),
        })
    return file_ops


def save_nomangohud(appid: str, disabled: bool):
    GAMES_DIR.mkdir(parents=True, exist_ok=True)
    path = GAMES_DIR / f"{appid}-nomangohud"
    if disabled:
        path.touch()
    else:
        path.unlink(missing_ok=True)


# ── Save Path Discovery ────────────────────────────────────────────────────────

def find_save_paths(appid: str, engine: str, name: str = "") -> dict:
    result: dict = {"native": None, "proton": None}
    if engine != "unreal":
        return result
    for base in [Path.home() / ".config/Epic",
                 Path.home() / ".local/share/Epic"]:
        if not base.exists():
            continue
        c = base / name / "SaveGames"
        if c.is_dir():
            result["native"] = c
            break
    for steamapps in _steam_library_dirs():
        pfx_user = steamapps / "compatdata" / appid / "pfx/drive_c/users/steamuser"
        if not pfx_user.exists():
            continue
        # Primary: AppData/Local/[Game]/Saved/SaveGames/
        local = pfx_user / "AppData/Local"
        if local.exists():
            for d in local.iterdir():
                c = d / "Saved" / "SaveGames"
                if c.is_dir():
                    result["proton"] = c
                    break
        # Fallback: My Documents/My Games/[Game]/SaveGames/
        if not result["proton"]:
            mydocs = pfx_user / "My Documents/My Games"
            if mydocs.exists():
                for d in mydocs.iterdir():
                    c = d / "SaveGames"
                    if c.is_dir():
                        result["proton"] = c
                        break
        # Fallback: Saved Games/[folder]/[folder]/Saved/SaveGames/
        if not result["proton"]:
            saved_games = pfx_user / "Saved Games"
            if saved_games.exists():
                for d1 in saved_games.iterdir():
                    if not d1.is_dir():
                        continue
                    for d2 in d1.iterdir():
                        if not d2.is_dir():
                            continue
                        c = d2 / "Saved" / "SaveGames"
                        if c.is_dir():
                            result["proton"] = c
                            break
                    if result["proton"]:
                        break
    return result


def find_save_paths_redengine(appid: str) -> dict:
    """CD Projekt Red: Saved Games/CD Projekt Red/"""
    result: dict = {"proton": None}
    for steamapps in _steam_library_dirs():
        pfx_user = steamapps / "compatdata" / appid / "pfx/drive_c/users/steamuser"
        path = pfx_user / "Saved Games" / "CD Projekt Red"
        if path.is_dir():
            result["proton"] = path
            break
    return result


def find_save_paths_creation(appid: str) -> dict:
    """Bethesda: My Documents/My Games/[Game]/Saves/"""
    result: dict = {"proton": None}
    for steamapps in _steam_library_dirs():
        pfx_user = steamapps / "compatdata" / appid / "pfx/drive_c/users/steamuser"
        mygames = pfx_user / "My Documents" / "My Games"
        if not mygames.is_dir():
            continue
        for d in mygames.iterdir():
            if not d.is_dir():
                continue
            saves = d / "Saves"
            if saves.is_dir():
                result["proton"] = saves
                break
        if not result["proton"] and mygames.is_dir():
            result["proton"] = mygames
        break
    return result


def find_save_paths_appdata(appid: str) -> dict:
    """Generic AppData scan for GameMaker / RPG Maker."""
    result: dict = {"local": None, "roaming": None}
    for steamapps in _steam_library_dirs():
        pfx_user = steamapps / "compatdata" / appid / "pfx/drive_c/users/steamuser"
        local   = pfx_user / "AppData" / "Local"
        roaming = pfx_user / "AppData" / "Roaming"
        if local.is_dir():
            result["local"] = local
        if roaming.is_dir():
            result["roaming"] = roaming
        break
    return result


def find_save_paths_cryengine(appid: str) -> dict:
    """CryEngine: scan Documents/My Games, AppData/Local, AppData/LocalLow, AppData/Roaming."""
    result: dict = {"my_games": None, "local": None, "local_low": None, "roaming": None}
    for steamapps in _steam_library_dirs():
        pfx_user = steamapps / "compatdata" / appid / "pfx/drive_c/users/steamuser"
        if not pfx_user.exists():
            continue
        my_games = pfx_user / "My Documents" / "My Games"
        if my_games.is_dir():
            result["my_games"] = my_games
        local = pfx_user / "AppData" / "Local"
        if local.is_dir():
            result["local"] = local
        local_low = pfx_user / "AppData" / "LocalLow"
        if local_low.is_dir():
            result["local_low"] = local_low
        roaming = pfx_user / "AppData" / "Roaming"
        if roaming.is_dir():
            result["roaming"] = roaming
        break
    return result


def find_decima_config(appid: str) -> "Path | None":
    """Scan Documents/[gamename]/[id_folder]/ for game_settings.cfg."""
    for steamapps in _steam_library_dirs():
        pfx_user = steamapps / "compatdata" / appid / "pfx/drive_c/users/steamuser"
        for docs in [pfx_user / "Documents", pfx_user / "My Documents"]:
            if not docs.is_dir():
                continue
            for game_dir in docs.iterdir():
                if not game_dir.is_dir():
                    continue
                for id_dir in game_dir.iterdir():
                    if not id_dir.is_dir():
                        continue
                    cfg = id_dir / "game_settings.cfg"
                    if cfg.exists():
                        return cfg
    return None


_APPDATA_SYSTEM_DIRS = frozenset({
    "microsoft", "temp", "programs", "windows", "packages",
    "microsoftedge", "nuget", "history", "d3dscache", "nvidia corporation",
    "windscale",
})

def find_asura_paths(appid: str) -> dict:
    """Asura Engine: config = AppData/Local/[gamename], saves = .../PC_ProfileSaves/[id]/"""
    result: dict = {"config": None, "saves": None}
    for steamapps in _steam_library_dirs():
        pfx_user = steamapps / "compatdata" / appid / "pfx/drive_c/users/steamuser"
        local = pfx_user / "AppData" / "Local"
        if not local.is_dir():
            continue
        for game_dir in local.iterdir():
            if not game_dir.is_dir():
                continue
            if game_dir.name.lower() in _APPDATA_SYSTEM_DIRS:
                continue
            result["config"] = game_dir
            saves_base = game_dir / "PC_ProfileSaves"
            if saves_base.is_dir():
                for id_dir in saves_base.iterdir():
                    if id_dir.is_dir():
                        result["saves"] = id_dir
                        break
            return result
    return result


def find_katana_config(appid: str) -> dict:
    """Check AppData/Local/KoeiTecmo for graphics_option.json; fall back to game.ini in install dir."""
    result: dict = {"graphics": None, "ini": None}
    for steamapps in _steam_library_dirs():
        pfx_user = steamapps / "compatdata" / appid / "pfx/drive_c/users/steamuser"
        base = pfx_user / "AppData" / "Local" / "KoeiTecmo"
        if base.is_dir():
            for game_dir in base.iterdir():
                if not game_dir.is_dir():
                    continue
                candidate = game_dir / "Savedata" / "graphics_option.json"
                if candidate.exists():
                    result["graphics"] = candidate
                    return result
        acf = steamapps / f"appmanifest_{appid}.acf"
        if not acf.exists():
            continue
        try:
            idir = _acf_value(acf.read_text(errors="replace"), "installdir")
            for ini in (steamapps / "common" / idir).rglob("game.ini"):
                result["ini"] = ini
                return result
        except Exception:
            pass
    return result


_KATANA_FPS_KEYS = ("fps", "fps_limit", "frame_rate", "max_fps", "framerate")


def read_katana_fps(json_path: "Path") -> "tuple[str|None, object]":
    """Return (key, raw_value) for the first recognized FPS key, or (None, None)."""
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        for key in _KATANA_FPS_KEYS:
            if key in data:
                return key, data[key]
    except Exception:
        pass
    return None, None


def write_katana_fps(json_path: "Path", key: str, value: int, as_string: bool):
    """Write FPS back, preserving original string/int type."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    data[key] = str(value) if as_string else value
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def copy_saves(source: "Path", dest: "Path"):
    dest.mkdir(parents=True, exist_ok=True)
    for f in source.rglob("*"):
        if f.is_file():
            rel = f.relative_to(source)
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest / rel)


def export_saves_zip(source: "Path", zip_path: "Path"):
    import zipfile
    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        for f in source.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(source))


def import_saves_zip(zip_path: "Path", dest: "Path"):
    import zipfile
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(str(zip_path), "r") as zf:
        zf.extractall(str(dest))


def load_managed() -> dict:
    if MANAGED_FILE.exists():
        try:
            return json.loads(MANAGED_FILE.read_text())
        except Exception:
            pass
    return {"auto_installed": []}

# ── Sidebar game row widget ───────────────────────────────────────────────────


class GameRow(Gtk.ListBoxRow):
    """A ListBoxRow representing either "Global / Default" (appid=None) or a Steam game."""

    def __init__(self, appid, name, engine="unknown"):
        super().__init__()
        self.appid     = appid
        self.game_name = name
        self.engine    = engine

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2,
                      margin_start=8, margin_end=8, margin_top=6, margin_bottom=6)

        name_lbl = Gtk.Label(label=name)
        name_lbl.set_xalign(0)
        name_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        name_lbl.set_max_width_chars(30)
        box.append(name_lbl)

        sub_text = "Global Settings" if appid is None else f"AppID: {appid}"
        sub_lbl  = Gtk.Label(label=sub_text)
        sub_lbl.set_xalign(0)
        sub_lbl.add_css_class("dim-label")
        sub_lbl.add_css_class("caption")
        box.append(sub_lbl)

        self.set_child(box)


# ── Application ───────────────────────────────────────────────────────────────

class Gubernator(Adw.Application):
    def __init__(self):
        super().__init__(application_id="io.gubernator")
        self.connect("activate", lambda app: MainWindow(application=app).present())


SAVE_CHANCE = 0.05
SAVE_MSGS = [
    "done. go touch grass.",
    "saved (nobody asked)",
    "ur mom?",
]

def _save_label() -> str:
    if SAVE_MSGS and random.random() < SAVE_CHANCE:
        return random.choice(SAVE_MSGS)
    return "✓ saved"


# ── Main Window ───────────────────────────────────────────────────────────────

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Gubernator")
        self.set_default_size(1100, 900)

        # ── Selection state (must be initialised before any UI is built) ──────
        self.selected_appid = None            # None = Global / Default
        self.selected_name  = "Global / Default"
        self.use_custom     = True            # always True for Global
        self._current_tab_name   = "MangoHud"  # remember active tab by name across rebuilds
        self._current_nb         = None  # live notebook widget
        self._nb_switch_handler  = None  # switch-page signal id

        # ── Initial settings load ─────────────────────────────────────────────
        self.s             = load_settings()
        self.proton_active = set(self.s.get("proton_active", []))
        self.proton_custom = self.s.get("proton_custom", "")
        self.companion_exec      = ""
        self.companion_env       = ""
        self.companion_autowrap  = False
        self.companion_autostart = False
        self.companion_delay     = 30
        self.mangohud_disabled   = self.s.get("mangohud_disabled", False)

        # ── Engine / Saves state ──────────────────────────────────────────────
        self._selected_install_dir = ""
        self._engine_detected      = "unknown"

        # ── Widget reference dicts (reset each time the right panel rebuilds) ─
        self._vkcube_proc      = None
        self._companion_proc   = None
        self._companion_launch_btn = None
        self._pos_btns         = {}
        self._fps_preset_btns  = {}
        self._proton_switches  = {}
        self._proton_callbacks = {}   # key → actual cb closure for handler block/unblock
        self._conflict_rows    = {}

        # ── Header bar ────────────────────────────────────────────────────────
        hdr = Adw.HeaderBar()
        # Remove window icon from headerbar decoration while keeping taskbar icon
        _gs = Gtk.Settings.get_default()
        _layout = (_gs.get_property("gtk-decoration-layout") or ":close")
        _left, _, _right = _layout.partition(":")
        _left  = ",".join(p for p in _left.split(",")  if p.strip() != "icon")
        _right = ",".join(p for p in _right.split(",") if p.strip() != "icon")
        hdr.set_decoration_layout(f"{_left}:{_right}")

        self._vkcube_img = Gtk.Image(pixel_size=20)
        if _LOGO_PATH:
            self._vkcube_img.set_from_file(_LOGO_PATH)
        else:
            self._vkcube_img.set_from_icon_name("io.gubernator")
        self._vkcube_lbl = Gtk.Label(label="Preview (vkcube)")
        _btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        _btn_box.append(self._vkcube_img)
        _btn_box.append(self._vkcube_lbl)
        self.preview_btn = Gtk.Button()
        self.preview_btn.set_child(_btn_box)
        self.preview_btn.set_tooltip_text(
            "Preview uses Global / Default settings only")
        self.preview_btn.connect("clicked", self._toggle_vkcube)
        hdr.pack_start(self.preview_btn)

        # ── Preview popover (script + MangoHud config) ────────────────────────
        pop_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4,
                          margin_start=12, margin_end=12,
                          margin_top=8, margin_bottom=12)
        pop_box.set_size_request(600, -1)

        # Steam command display at the top
        cmd_head = Gtk.Label(label="Steam Launch Command")
        cmd_head.set_xalign(0); cmd_head.add_css_class("heading")
        cmd_head.set_margin_bottom(2)
        pop_box.append(cmd_head)
        cmd_display = Gtk.Label(label=str(STEAM_COMMAND))
        cmd_display.set_xalign(0); cmd_display.add_css_class("monospace")
        cmd_display.set_selectable(True); cmd_display.set_margin_bottom(8)
        pop_box.append(cmd_display)

        # Launcher script preview
        scr_head = Gtk.Label(label="Launcher Script")
        scr_head.set_xalign(0); scr_head.add_css_class("heading")
        scr_head.set_margin_bottom(2)
        pop_box.append(scr_head)
        self.script_preview = Gtk.Label(label="")
        self.script_preview.set_xalign(0); self.script_preview.add_css_class("monospace")
        self.script_preview.set_selectable(True)
        scr1 = Gtk.ScrolledWindow()
        scr1.set_min_content_height(140); scr1.set_max_content_height(180)
        scr1.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scr1.set_child(self.script_preview)
        fr1 = Gtk.Frame(); fr1.set_child(scr1); fr1.set_margin_bottom(8)
        pop_box.append(fr1)

        # MangoHud config preview
        conf_head = Gtk.Label(label="MangoHud Config")
        conf_head.set_xalign(0); conf_head.add_css_class("heading")
        conf_head.set_margin_bottom(2)
        pop_box.append(conf_head)
        self.conf_preview = Gtk.Label(label="")
        self.conf_preview.set_xalign(0); self.conf_preview.add_css_class("monospace")
        self.conf_preview.set_selectable(True)
        scr2 = Gtk.ScrolledWindow()
        scr2.set_min_content_height(260); scr2.set_max_content_height(400)
        scr2.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scr2.set_child(self.conf_preview)
        fr2 = Gtk.Frame(); fr2.set_child(scr2)
        pop_box.append(fr2)

        popover = Gtk.Popover()
        popover.set_child(pop_box)

        # SplitButton: left part copies command, arrow opens the preview popover
        self._cmd_btn = Adw.SplitButton(label="Copy Steam Command")
        self._cmd_btn.add_css_class("steam-cmd")
        self._cmd_btn.set_popover(popover)
        self._cmd_btn.connect("clicked", lambda _: self._copy_cmd(str(STEAM_COMMAND)))

        # Steam-blue styling for the split button
        _css = Gtk.CssProvider()
        _css.load_from_data(b"""
            splitbutton.steam-cmd > button {
                background: #1b9cf2;
                color: #ffffff;
                border-radius: 6px 0 0 6px;
                box-shadow: 0 1px 3px rgba(0,0,0,.45);
            }
            splitbutton.steam-cmd > button:hover  { background: #3db5ff; }
            splitbutton.steam-cmd > button:active { background: #0f80d4; }
            splitbutton.steam-cmd separator       { background: rgba(255,255,255,.3); min-width: 1px; }
            splitbutton.steam-cmd > menubutton > button {
                background: #1270b0;
                color: #ffffff;
                border-radius: 0 6px 6px 0;
                box-shadow: 0 1px 3px rgba(0,0,0,.45);
            }
            splitbutton.steam-cmd > menubutton > button:hover  { background: #1888d4; }
            splitbutton.steam-cmd > menubutton > button:active { background: #0d5c96; }
        """)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), _css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        save_btn = Gtk.Button(label="Save & Apply")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", lambda b: self._do_write())
        self.status_lbl = Gtk.Label(label="")
        self.status_lbl.add_css_class("dim-label")
        self.status_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self.status_lbl.set_max_width_chars(40)

        # Left side: vkcube preview · copy+dropdown steam command
        hdr.pack_start(self._cmd_btn)
        # Right side (pack_end = right-to-left): save → status
        hdr.pack_end(save_btn)
        hdr.pack_end(self.status_lbl)

        # ── Two-panel layout ──────────────────────────────────────────────────
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, vexpand=True)
        paned.set_position(260)
        paned.set_shrink_start_child(False)
        paned.set_shrink_end_child(False)

        # Right panel container created first so it exists when sidebar fires
        # the initial row-selected signal during construction.
        self._right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True)
        self._build_right_panel()

        sidebar = self._build_sidebar()
        paned.set_start_child(sidebar)
        paned.set_end_child(self._right_box)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.append(hdr)
        root.append(paned)
        self.set_content(root)
        self.connect("close-request", self._on_close)


        self._do_write()

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        """Left panel: search field + filter button + scrollable game list."""
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar.set_size_request(250, -1)

        self._hidden_appids = load_hidden_appids()
        games_data = read_steam_games()

        # ── Filter state (created before rows are appended so _filter_games works) ──
        self._hide_proton_cb     = Gtk.CheckButton(label="Proton-versions")
        self._hide_slr_cb        = Gtk.CheckButton(label="Steam Linux Runtime")
        self._hide_steamworks_cb = Gtk.CheckButton(label="Steamworks")
        for cb in (self._hide_proton_cb, self._hide_slr_cb, self._hide_steamworks_cb):
            cb.set_active(True)
            cb.connect("toggled", lambda _: self._game_list.invalidate_filter())

        self._engine_search_cb = Gtk.CheckButton(label="Search by engine")
        self._engine_search_cb.set_active(False)
        self._engine_search_cb.connect("toggled", lambda _: self._game_list.invalidate_filter())

        # ── Filter popover ────────────────────────────────────────────────────
        fp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                         margin_start=10, margin_end=10, margin_top=10, margin_bottom=10)
        fp_box.set_size_request(270, -1)

        def _fp_head(text):
            lbl = Gtk.Label(label=text)
            lbl.set_xalign(0)
            lbl.add_css_class("heading")
            return lbl

        fp_box.append(_fp_head("Auto-hide"))
        fp_box.append(Gtk.Separator())
        for cb in (self._hide_proton_cb, self._hide_slr_cb, self._hide_steamworks_cb):
            fp_box.append(cb)

        fp_box.append(Gtk.Separator())
        fp_box.append(_fp_head("Engine Search"))
        fp_box.append(self._engine_search_cb)
        eng_hint = Gtk.Label(label="e.g. unreal, re_engine, godot …")
        eng_hint.set_xalign(0)
        eng_hint.add_css_class("caption")
        eng_hint.add_css_class("dim-label")
        fp_box.append(eng_hint)

        fp_box.append(Gtk.Separator())
        fp_box.append(_fp_head("Custom Hidden"))

        self._hide_search_entry = Gtk.SearchEntry()
        self._hide_search_entry.set_placeholder_text("Find game to hide…")
        self._hide_search_entry.connect(
            "search-changed", lambda _: self._hidden_list.invalidate_filter())
        fp_box.append(self._hide_search_entry)

        hide_scroll = Gtk.ScrolledWindow()
        hide_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        hide_scroll.set_min_content_height(60)
        hide_scroll.set_max_content_height(200)
        self._hidden_list = Gtk.ListBox()
        self._hidden_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._hidden_list.set_filter_func(self._filter_hidden_list)
        self._fill_hidden_checks(games_data)
        hide_scroll.set_child(self._hidden_list)
        fp_box.append(hide_scroll)

        filter_pop = Gtk.Popover()
        filter_pop.set_child(fp_box)

        # ── Search row: entry + filter button ─────────────────────────────────
        search_row = Gtk.Box(spacing=4,
                             margin_start=8, margin_end=8,
                             margin_top=8, margin_bottom=4)
        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text("Search games…")
        self._search_entry.set_hexpand(True)
        self._search_entry.connect("search-changed", self._on_search_changed)
        search_row.append(self._search_entry)

        filter_btn = Gtk.MenuButton()
        filter_btn.set_icon_name("funnel-symbolic")
        filter_btn.set_popover(filter_pop)
        filter_btn.set_tooltip_text("Filter entries")
        filter_btn.set_valign(Gtk.Align.CENTER)
        search_row.append(filter_btn)

        rescan_btn = Gtk.Button()
        rescan_btn.set_icon_name("view-refresh-symbolic")
        rescan_btn.set_tooltip_text("Rescan Steam library")
        rescan_btn.set_valign(Gtk.Align.CENTER)
        rescan_btn.connect("clicked", lambda _: self._rescan_games())
        search_row.append(rescan_btn)

        sidebar.append(search_row)
        sidebar.append(Gtk.Separator())

        # ── Scrollable game list ───────────────────────────────────────────────
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._game_list = Gtk.ListBox()
        self._game_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._game_list.add_css_class("navigation-sidebar")
        self._game_list.set_filter_func(self._filter_games)
        self._game_list.connect("row-selected", self._on_game_selected)

        # "Global / Default" is always the first entry
        self._game_list.append(GameRow(None, "Global / Default"))
        for appid, name, install_path in games_data:
            engine = detect_engine(install_path) if install_path else "unknown"
            self._game_list.append(GameRow(appid, name, engine))

        scroll.set_child(self._game_list)
        sidebar.append(scroll)

        # Pre-select Global; _switch_to detects same appid and skips a rebuild
        self._game_list.select_row(self._game_list.get_row_at_index(0))
        return sidebar

    # Hide-filter keywords mapped to their CheckButton
    _HIDE_RULES = [
        ("proton",              "_hide_proton_cb"),
        ("steam linux runtime", "_hide_slr_cb"),
        ("steamworks",          "_hide_steamworks_cb"),
    ]

    def _filter_games(self, row):
        """Apply hide-filters and search query; Global is always visible."""
        if not isinstance(row, GameRow):
            return True
        if row.appid is None:
            return True

        name_lower = row.game_name.lower()

        # Auto-hide rules
        for keyword, attr in self._HIDE_RULES:
            cb = getattr(self, attr, None)
            if cb and cb.get_active() and keyword in name_lower:
                return False

        # Custom hidden entries (saved)
        if row.appid in self._hidden_appids:
            return False

        # Search query
        query = self._search_entry.get_text().strip().lower()
        if not query:
            return True

        # Engine search mode (not saved, off by default)
        if self._engine_search_cb.get_active():
            return query in row.engine.lower()

        return query in name_lower or query in row.appid

    def _on_search_changed(self, _):
        self._game_list.invalidate_filter()

    def _fill_hidden_checks(self, games_data):
        """Rebuild the hidden-entries list in the filter popover."""
        while (child := self._hidden_list.get_first_child()):
            self._hidden_list.remove(child)
        for appid, name, _ in games_data:
            list_row = Gtk.ListBoxRow()
            list_row._appid = appid
            list_row._name  = name.lower()
            cb = Gtk.CheckButton(label=name)
            cb.set_margin_start(4); cb.set_margin_end(4)
            cb.set_margin_top(2);   cb.set_margin_bottom(2)
            cb.set_active(appid in self._hidden_appids)
            def _on_toggle(b, aid=appid):
                if b.get_active():
                    self._hidden_appids.add(aid)
                else:
                    self._hidden_appids.discard(aid)
                save_hidden_appids(self._hidden_appids)
                self._game_list.invalidate_filter()
                self._hidden_list.invalidate_filter()
            cb.connect("toggled", _on_toggle)
            list_row.set_child(cb)
            self._hidden_list.append(list_row)

    def _filter_hidden_list(self, row):
        """Show hidden games when search is empty; matching games when typing."""
        if not hasattr(row, '_appid'):
            return True
        query = self._hide_search_entry.get_text().strip().lower()
        if not query:
            return row._appid in self._hidden_appids
        return query in row._name

    def _rescan_games(self):
        """Remove all game rows and re-read the Steam library."""
        row = self._game_list.get_row_at_index(1)
        while row is not None:
            self._game_list.remove(row)
            row = self._game_list.get_row_at_index(1)
        games_data = read_steam_games()
        self._fill_hidden_checks(games_data)
        for appid, name, install_path in games_data:
            engine = detect_engine(install_path) if install_path else "unknown"
            self._game_list.append(GameRow(appid, name, engine))
        self._game_list.invalidate_filter()

    def _on_game_selected(self, _, row):
        if not isinstance(row, GameRow):
            return
        self._switch_to(row.appid, row.game_name)

    def _switch_to(self, appid, name):
        """Load settings for the selected entry and rebuild the right panel."""
        if appid == self.selected_appid:
            return   # same entry – nothing to do

        self.selected_appid = appid
        self.selected_name  = name

        if appid is None:
            # Global / Default
            self.s             = load_settings()
            self.proton_active = set(self.s.get("proton_active", []))
            self.proton_custom = self.s.get("proton_custom", "")
            self.use_custom      = True
            self.companion_exec      = ""
            self.companion_env       = ""
            self.companion_autowrap  = False
            self.companion_autostart = False
            self.companion_delay     = 30
            self.mangohud_disabled   = self.s.get("mangohud_disabled", False)
            self._selected_install_dir = ""
            self._engine_detected      = "unknown"
        else:
            # Individual game
            game_data = load_game_settings(appid)
            if game_data:
                self.use_custom = game_data.get("use_custom", False)
                if self.use_custom:
                    state = dict(DEFAULT_STATE)
                    state.update({k: v for k, v in game_data.items() if k != "use_custom"})
                    self.s = state
                else:
                    self.s = load_settings()   # show global settings as reference
            else:
                self.use_custom = False
                self.s = load_settings()
            self.proton_active = set(self.s.get("proton_active", []))
            self.proton_custom = self.s.get("proton_custom", "")
            self.companion_exec      = (game_data or {}).get("companion_exec", "")
            self.companion_env       = (game_data or {}).get("companion_env", "")
            self.companion_autowrap  = bool((game_data or {}).get("companion_autowrap", False))
            self.companion_autostart = bool((game_data or {}).get("companion_autostart", False))
            self.companion_delay     = int((game_data or {}).get("companion_delay", 30))
            self.mangohud_disabled  = (GAMES_DIR / f"{appid}-nomangohud").exists()
            # Resolve install directory from ACF
            self._selected_install_dir = ""
            for steamapps in _steam_library_dirs():
                acf = steamapps / f"appmanifest_{appid}.acf"
                if acf.exists():
                    raw  = acf.read_text(errors="replace")
                    idir = _acf_value(raw, "installdir")
                    if idir:
                        self._selected_install_dir = str(steamapps / "common" / idir)
                    break
            self._engine_detected = detect_engine(self._selected_install_dir)

        self._build_right_panel()

    # ── Right panel ───────────────────────────────────────────────────────────

    def _build_right_panel(self):
        """Clear and reconstruct the right side (title + toggle + notebook)."""
        # Disconnect the old switch-page handler BEFORE removing the notebook so
        # it can never fire after this point and corrupt _current_tab.
        if self._current_nb is not None and self._nb_switch_handler is not None:
            try:
                self._current_nb.disconnect(self._nb_switch_handler)
            except Exception:
                pass
        self._current_nb        = None
        self._nb_switch_handler = None

        saved_tab_name = self._current_tab_name

        # Remove all existing children
        child = self._right_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._right_box.remove(child)
            child = nxt

        self._current_tab_name = saved_tab_name  # safety restore after any GLib signals

        # Reset per-rebuild widget reference dicts
        self._pos_btns         = {}
        self._fps_preset_btns  = {}
        self._proton_switches  = {}
        self._proton_callbacks = {}
        self._conflict_rows    = {}

        # ── Game / profile title ──────────────────────────────────────────────
        title_lbl = Gtk.Label(label=self.selected_name)
        title_lbl.add_css_class("title-2")
        title_lbl.set_xalign(0)
        title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        title_lbl.set_margin_start(16)
        title_lbl.set_margin_end(16)
        title_lbl.set_margin_top(12)
        title_lbl.set_margin_bottom(4)
        self._right_box.append(title_lbl)

        # ── "Custom Settings" toggle (games only) ─────────────────────────────
        if self.selected_appid is not None:
            custom_pg = Adw.PreferencesGroup()
            custom_pg.set_margin_start(8)
            custom_pg.set_margin_end(8)
            custom_pg.set_margin_bottom(4)
            custom_row = Adw.ActionRow(
                title="Custom Settings",
                subtitle="Use individual settings"
            )
            self._custom_sw = Gtk.Switch(valign=Gtk.Align.CENTER, active=self.use_custom)
            self._custom_sw.connect("notify::active", self._on_custom_toggle)
            custom_row.add_suffix(self._custom_sw)
            custom_row.set_activatable_widget(self._custom_sw)
            custom_pg.add(custom_row)
            self._right_box.append(custom_pg)

        # ── Tabs ──────────────────────────────────────────────────────────────
        def _lbl(text, bold=False):
            l = Gtk.Label()
            l.set_markup(f"<b>{text}</b>" if bold else text)
            return l

        nb = Gtk.Notebook(vexpand=True)
        nb.set_margin_start(8)
        nb.set_margin_end(8)
        nb.set_margin_bottom(8)
        is_global  = self.selected_appid is None
        editable   = is_global or self.use_custom
        # (name, page, bold_label, sensitive)
        tab_pages = [
            ("MangoHud",      self._page_mango(),     is_global, editable),
            ("Proton-Tweaks", self._page_proton(),    is_global, editable),
            ("Game",          self._page_game(),      False,     True),
            ("Engine",        self._page_engine(),    False,     True),
            ("Saves",         self._page_saves(),     False,     True),
            ("Reshade",       self._page_reshade(),   is_global, editable),
            ("Custom App",    self._page_companion(), False,     editable),
        ]
        if is_global:
            tab_pages.insert(2, ("Proton Manager", self._page_versions(), True, True))
        tab_names = [name for name, *_ in tab_pages]
        for name, page, bold, sensitive in tab_pages:
            page.set_sensitive(sensitive)
            nb.append_page(page, _lbl(name, bold=bold))
        restore_idx = tab_names.index(self._current_tab_name) if self._current_tab_name in tab_names else 0
        nb.set_current_page(restore_idx)
        self._nb_switch_handler = nb.connect(
            "switch-page",
            lambda __, _, idx, tn=tab_names: setattr(self, "_current_tab_name", tn[idx]),
        )
        self._current_nb = nb
        self._right_box.append(nb)

    def _on_custom_toggle(self, sw, _):
        """Enable or disable per-game custom settings."""
        new_val = sw.get_active()
        if new_val == self.use_custom:
            return
        self.use_custom = new_val

        if new_val:
            # Load existing game settings, or copy from global as starting point
            game_data = load_game_settings(self.selected_appid)
            if game_data and len(game_data) > 1:
                state = dict(DEFAULT_STATE)
                state.update({k: v for k, v in game_data.items() if k != "use_custom"})
                self.s = state
                self.companion_exec = game_data.get("companion_exec", "")
                self.companion_env  = game_data.get("companion_env", "")
            else:
                self.s = dict(load_settings())
                self.companion_exec = ""
                self.companion_env  = ""
            self.proton_active = set(self.s.get("proton_active", []))
            self.proton_custom = self.s.get("proton_custom", "")
            self._do_write()
        else:
            save_game_settings(self.selected_appid, {"use_custom": False})
            self.s             = load_settings()
            self.proton_active = set(self.s.get("proton_active", []))
            self.proton_custom = self.s.get("proton_custom", "")
            self.companion_exec = ""
            self.companion_env  = ""
            self._do_write()

        GLib.idle_add(self._build_right_panel)

    # ── State helpers ─────────────────────────────────────────────────────────
    def _tog(self, k): return bool(self.s.get(k, DEFAULT_STATE.get(k, False)))
    def _val(self, k): return self.s.get(k, DEFAULT_STATE.get(k))
    def _set(self, k, v): self.s[k] = v; self._do_write()

    # ── Toggle row with optional color picker ─────────────────────────────────
    def _make_full_row(self, title, subtitle, tog_key, color_key=None):
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        suffix_box = Gtk.Box(spacing=8, valign=Gtk.Align.CENTER)

        if color_key:
            cbtn = Gtk.ColorButton()
            cbtn.set_rgba(hex_to_rgba(str(self._val(color_key))))
            cbtn.set_valign(Gtk.Align.CENTER)
            cbtn.connect("color-set", lambda b,k=color_key: self._set(k, rgba_to_hex(b.get_rgba())))
            suffix_box.append(cbtn)

        sw = Gtk.Switch(valign=Gtk.Align.CENTER, active=self._tog(tog_key))
        sw.connect("notify::active", lambda sw,_,k=tog_key: self._set(k, sw.get_active()))
        suffix_box.append(sw)
        row.add_suffix(suffix_box)
        row.set_activatable_widget(sw)
        return row

    # ── MangoHud tab ──────────────────────────────────────────────────────────
    def _page_mango(self):
        scroll = Gtk.ScrolledWindow(vexpand=True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin_start=12, margin_end=12)
        scroll.set_child(box)

        # ── Performance ──
        box.append(sec_lbl("Performance"))
        pg = Adw.PreferencesGroup(); box.append(pg)

        fps_only_row, _ = adw_toggle("FPS Only","Show only FPS counter, hide all text labels",
            self._tog("fps_only"), lambda sw,_: self._set("fps_only", sw.get_active()))
        pg.add(fps_only_row)

        pg.add(self._make_full_row("FPS","Frames per second","fps","engine_color"))
        pg.add(self._make_full_row("Frametime Number","Show ms value per frame","show_frametime"))
        pg.add(self._make_full_row("Frametime Graph","Show frame-timing bar graph","show_framegraph","frametime_color"))
        pg.add(self._make_full_row("Frame Count","Total frame counter","frame_count"))

        fcc_suffix = Gtk.Box(spacing=4, valign=Gtk.Align.CENTER)
        fcc_sw = Gtk.Switch(valign=Gtk.Align.CENTER, active=self._tog("fps_color_change"))
        fcc_sw.connect("notify::active", lambda sw,_: self._set("fps_color_change", sw.get_active()))
        fcc_suffix.append(fcc_sw)
        fcc_row = Adw.ActionRow(title="FPS Color Change", subtitle="Color FPS based on thresholds (good/medium/bad)")
        fcc_row.add_suffix(fcc_suffix); fcc_row.set_activatable_widget(fcc_sw)
        pg.add(fcc_row)

        # FPS Limit row with preset buttons + custom entry
        fps_row = Adw.ActionRow(title="FPS Limit", subtitle="Off = unlimited")
        fps_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER)
        preset_box = Gtk.Box(spacing=4)
        for p in FPS_PRESETS:
            lbl = "Off" if p==0 else str(p)
            btn = Gtk.Button(label=lbl); btn.set_size_request(44,-1)
            if p == self._val("fps_limit"): btn.add_css_class("suggested-action")
            btn.connect("clicked", self._mkfps(p))
            preset_box.append(btn); self._fps_preset_btns[p] = btn
        fps_vbox.append(preset_box)
        mb = Gtk.Box(spacing=6)
        ll = Gtk.Label(label="Custom:"); ll.add_css_class("dim-label")
        self.fps_entry = Gtk.Entry(); self.fps_entry.set_width_chars(6)
        self.fps_entry.set_input_purpose(Gtk.InputPurpose.DIGITS)
        self.fps_entry.set_placeholder_text("e.g. 72")
        cur = self._val("fps_limit")
        if cur and int(cur) > 0 and int(cur) not in FPS_PRESETS:
            self.fps_entry.set_text(str(int(cur)))
        self.fps_entry.connect("changed", self._on_fps_entry)
        mb.append(ll); mb.append(self.fps_entry)
        fps_vbox.append(mb); fps_row.add_suffix(fps_vbox); pg.add(fps_row)

        # ── GPU ──
        box.append(sec_lbl("GPU"))
        gg = Adw.PreferencesGroup(); box.append(gg)
        gg.add(self._make_full_row("GPU Usage","% load","gpu_stats","gpu_color"))
        gg.add(self._make_full_row("GPU Temperature","°C","gpu_temp"))
        gg.add(self._make_full_row("Junction Temp","Hotspot (AMD)","gpu_junction_temp"))
        gg.add(self._make_full_row("GPU Core Clock","MHz","gpu_core_clock"))
        gg.add(self._make_full_row("GPU Mem Clock","MHz - needs vram","gpu_mem_clock"))
        gg.add(self._make_full_row("GPU Mem Temp","°C - needs vram","gpu_mem_temp"))
        gg.add(self._make_full_row("GPU Power","Watt draw","gpu_power"))
        gg.add(self._make_full_row("GPU Power Limit","Show power limit","gpu_power_limit"))
        gg.add(self._make_full_row("GPU Fan","RPM","gpu_fan"))
        gg.add(self._make_full_row("GPU Voltage","mV (AMD only)","gpu_voltage"))
        gg.add(self._make_full_row("GPU Load Color Change","Color based on load","gpu_load_change"))
        gg.add(self._make_full_row("GPU Efficiency","Frames per joule","gpu_efficiency"))
        gg.add(self._make_full_row("VRAM Total","Total video memory","vram"))
        gg.add(self._make_full_row("VRAM (Process)","Only this game's VRAM","proc_vram"))

        # GPU selector (only shown when multiple GPUs are detected)
        gpus = detect_gpus()
        if len(gpus) > 1:
            gpu_row = Adw.ActionRow(title="GPU Device", subtitle="Select GPU to monitor")
            gpu_combo = Gtk.ComboBoxText()
            gpu_combo.append("-1","All / Default")
            for idx,name in gpus:
                gpu_combo.append(str(idx),f"GPU {idx}: {name}")
            gpu_combo.set_active_id(str(self._val("gpu_index")))
            if not gpu_combo.get_active_id(): gpu_combo.set_active_id("-1")
            gpu_combo.set_valign(Gtk.Align.CENTER)
            gpu_combo.connect("changed", lambda c: self._set("gpu_index", int(c.get_active_id() or -1)))
            gpu_row.add_suffix(gpu_combo); gg.add(gpu_row)

        # ── CPU ──
        box.append(sec_lbl("CPU"))
        cg = Adw.PreferencesGroup(); box.append(cg)
        cg.add(self._make_full_row("CPU Usage","% total load","cpu_stats","cpu_color"))
        cg.add(self._make_full_row("CPU Temperature","°C","cpu_temp"))
        cg.add(self._make_full_row("CPU Power","Watt draw","cpu_power"))
        cg.add(self._make_full_row("CPU MHz","Clock speed","cpu_mhz"))
        cg.add(self._make_full_row("Core Load","Per-core %","core_load"))
        cg.add(self._make_full_row("Core Bars","Visual bar per-core - needs Core Load (same color as Frame Graph)","core_bars"))
        cg.add(self._make_full_row("Core Load Color Change","Color pre-core by load","core_load_change"))
        cg.add(self._make_full_row("CPU Efficiency","Frames per joule","cpu_efficiency"))
        cg.add(self._make_full_row("RAM Total","System memory","ram"))
        cg.add(self._make_full_row("RAM (Process)","Only this game's RAM","procmem"))
        cg.add(self._make_full_row("Swap","Swap usage","swap"))

        # ── IO ──
        box.append(sec_lbl("IO"))
        ig = Adw.PreferencesGroup(); box.append(ig)
        ig.add(self._make_full_row("IO Read","Disk read MB/s","io_read"))
        ig.add(self._make_full_row("IO Write","Disk write MB/s","io_write"))

        # ── Misc ──
        box.append(sec_lbl("Misc"))
        mg = Adw.PreferencesGroup(); box.append(mg)
        for k,t,s,ck in [
            ("media_player","Media Player","Spotify / browser (MPRIS) – needs playerctl","media_player_color"),
            ("wine","Wine / Proton","Version number","wine_color"),
            ("battery","Battery","Battery % and watts","battery_color"),
            ("network","Network","Network throughput kb/s","network_color"),
        ]:
            cbtn = Gtk.ColorButton()
            cbtn.set_rgba(hex_to_rgba(str(self._val(ck)))); cbtn.set_valign(Gtk.Align.CENTER)
            cbtn.connect("color-set", lambda b,kk=ck: self._set(kk, rgba_to_hex(b.get_rgba())))
            r,_ = adw_toggle(t,s,self._tog(k),lambda sw,_,kk=k: self._set(kk,sw.get_active()), cbtn)
            mg.add(r)

        mg.add(self._make_full_row("Resolution","Active render resolution","resolution"))
        mg.add(self._make_full_row("Clock","System time","time"))
        mg.add(self._make_full_row("MangoHud Version","Show MangoHud version","version"))
        mg.add(self._make_full_row("Architecture","CPU arch (x86_64 etc)","arch"))
        mg.add(self._make_full_row("GPU Name","GPU model name","gpu_name"))
        mg.add(self._make_full_row("Gamemode","Show if Gamemode is active","gamemode"))
        mg.add(self._make_full_row("Throttling Status","Show if GPU/CPU is throttling","throttling_status"))
        mg.add(self._make_full_row("Graphics API","Vulkan / OpenGL","api"))

        # ── Display ──
        box.append(sec_lbl("Display"))
        dg = Adw.PreferencesGroup(); box.append(dg)
        for sk,t,lo,hi,step in [
            ("font_size","Font Size",12,36,1),
            ("round_corners","Corner Radius",0,20,1),
            ("background_alpha","Background Alpha",0,1,0.05),
            ("text_outline_thickness","Outline Thickness",0.5,3,0.5),
        ]:
            row = Adw.ActionRow(title=t)
            sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,lo,hi,step)
            sc.set_value(float(self._val(sk))); sc.set_size_request(200,-1)
            sc.set_valign(Gtk.Align.CENTER); sc.set_draw_value(True)
            sc.connect("value-changed", lambda sc,kk=sk: self._set(kk, sc.get_value()))
            row.add_suffix(sc); dg.add(row)

        cols_row = Adw.ActionRow(title="Table Columns", subtitle="1–4 overlay columns")
        spin = Gtk.SpinButton.new_with_range(1,4,1)
        spin.set_value(int(self._val("table_columns"))); spin.set_valign(Gtk.Align.CENTER)
        spin.connect("value-changed", lambda s: self._set("table_columns", int(s.get_value())))
        cols_row.add_suffix(spin); dg.add(cols_row)

        for k,t,s in [
            ("hud_compact","Compact HUD","Minimal layout"),
            ("horizontal","Horizontal HUD","Side-by-side layout"),
            ("hud_no_margin","No Margin","Remove margins"),
            ("text_outline","Text Outline","Outline around text"),
            ("no_display","Hidden by Default","Start hidden (toggle with Shift+F12)"),
        ]:
            r,_ = adw_toggle(t,s,self._tog(k),lambda sw,_,kk=k: self._set(kk,sw.get_active()))
            dg.add(r)

        # HUD position 3×3 grid
        pos_row = Adw.ActionRow(title="Position")
        grid = Gtk.Grid(row_spacing=4, column_spacing=4, valign=Gtk.Align.CENTER)
        for pos,r,c in POSITIONS:
            btn = Gtk.Button(label=POS_ARROWS[pos])
            btn.set_size_request(40,34); btn.set_tooltip_text(pos)
            if pos == self._val("position"): btn.add_css_class("suggested-action")
            btn.connect("clicked", self._mkpos(pos))
            grid.attach(btn,c,r,1,1); self._pos_btns[pos]=btn
        pos_row.add_suffix(grid); dg.add(pos_row)

        # ── VSync ──
        box.append(sec_lbl("VSync"))
        vg = Adw.PreferencesGroup(); box.append(vg)
        ogl_row = Adw.ActionRow(title="OpenGL VSync", subtitle="-1 Adaptive · 0 Off · 1 On · n=Sync/n")
        oc = Gtk.ComboBoxText()
        for v,l in OPENGL_VSYNC: oc.append(v,l)
        oc.set_active_id(str(self._val("opengl_vsync")))
        if not oc.get_active_id(): oc.set_active_id("-1")
        oc.set_valign(Gtk.Align.CENTER)
        oc.connect("changed", lambda c: self._set("opengl_vsync", c.get_active_id() or "-1"))
        ogl_row.add_suffix(oc); vg.add(ogl_row)

        vk_row = Adw.ActionRow(title="Vulkan VSync", subtitle="0 Adaptive · 1 Off · 2 Mailbox · 3 On")
        vc = Gtk.ComboBoxText()
        for v,l in VULKAN_VSYNC: vc.append(v,l)
        vc.set_active_id(str(self._val("vulkan_vsync")))
        if not vc.get_active_id(): vc.set_active_id("3")
        vc.set_valign(Gtk.Align.CENTER)
        vc.connect("changed", lambda c: self._set("vulkan_vsync", c.get_active_id() or "3"))
        vk_row.add_suffix(vc); vg.add(vk_row)

        # ── Colors (collapsible) ──
        box.append(sec_lbl("Colors"))
        exp = Gtk.Expander(label="Show / hide color settings"); exp.set_margin_bottom(8)
        ci = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        cg2 = Adw.PreferencesGroup(); ci.append(cg2); exp.set_child(ci); box.append(exp)
        for c_key, c_label in COLOR_KEY:
            row = Adw.ActionRow(title=c_label)
            if c_key in MULTI_COLOR_KEYS:
                entry = Gtk.Entry(); entry.set_width_chars(24)
                entry.set_text(str(self._val(c_key)))
                entry.set_valign(Gtk.Align.CENTER)
                entry.connect("changed", lambda e,k=c_key: self._set(k, e.get_text()))
                row.add_suffix(entry)
            else:
                cbtn = Gtk.ColorButton()
                cbtn.set_rgba(hex_to_rgba(str(self._val(c_key))))
                cbtn.set_valign(Gtk.Align.CENTER)
                cbtn.connect("color-set", lambda b,k=c_key: self._set(k, rgba_to_hex(b.get_rgba())))
                row.add_suffix(cbtn)
            cg2.add(row)

        # ── Extra raw config lines ──
        box.append(sec_lbl("Extra Config Lines"))
        hint = Gtk.Label(label="Raw MangoHud config lines, one per line.")
        hint.set_xalign(0); hint.add_css_class("dim-label"); hint.set_margin_bottom(4)
        box.append(hint)
        self._extra_buf = Gtk.TextBuffer()
        self._extra_buf.set_text(self.s.get("mango_extra",""))
        self._extra_buf.connect("changed", lambda b: self._set("mango_extra", self._get_buf(b)))
        tv = Gtk.TextView(buffer=self._extra_buf, monospace=True); tv.set_size_request(-1,80)
        tv.set_left_margin(6); tv.set_right_margin(6); tv.set_top_margin(6); tv.set_bottom_margin(6)
        fr = Gtk.Frame(); fr.set_child(tv); fr.set_margin_bottom(16); box.append(fr)
        return scroll

    # ── Proton-Tweaks tab ─────────────────────────────────────────────────────
    def _page_proton(self):
        scroll = Gtk.ScrolledWindow(vexpand=True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin_start=12, margin_end=12)
        scroll.set_child(box)

        protondb_url = (
            f"https://www.protondb.com/app/{self.selected_appid}"
            if self.selected_appid else
            PROTONDB_URL
        )
        box.append(sec_lbl("ProtonDB"))
        db_grp = Adw.PreferencesGroup()
        db_row = Adw.ActionRow(title="ProtonDB", subtitle="Community game compatibility database")
        db_btn = Gtk.Button(label="Open ProtonDB for this game" if self.selected_appid else "Open in Browser")
        db_btn.set_valign(Gtk.Align.CENTER)
        db_btn.connect("clicked", lambda _, url=protondb_url: subprocess.Popen(["xdg-open", url]))
        db_row.add_suffix(db_btn)
        db_grp.add(db_row)
        box.append(db_grp)

        for section_title, entries in ALL_PROTON_SECTIONS:
            box.append(sec_lbl(section_title))
            grp = Adw.PreferencesGroup(); box.append(grp)
            for key, title, subtitle, conflicts in entries:
                row = Adw.ActionRow(title=title, subtitle=subtitle)
                sw = Gtk.Switch(valign=Gtk.Align.CENTER, active=key in self.proton_active)
                cb = self._mkproton(key, conflicts)
                sw.connect("notify::active", cb)
                row.add_suffix(sw); row.set_activatable_widget(sw)
                grp.add(row)
                self._proton_switches[key]  = sw
                self._proton_callbacks[key] = cb   # store exact closure for block/unblock
                self._conflict_rows[key]    = row

            if section_title == "Wayland & HDR":
                # Combined HDR row (PROTON_ENABLE_HDR=1 + ENABLE_HDR_WSI=1); auto-enables Wayland
                hdr_active = (
                    "PROTON_ENABLE_HDR=1" in self.proton_active or
                    "ENABLE_HDR_WSI=1"    in self.proton_active
                )
                hdr_row = Adw.ActionRow(
                    title="Enable HDR",
                    subtitle="HDR via Proton + Vulkan WSI layer. Automatically enables Wayland.")
                hdr_sw = Gtk.Switch(valign=Gtk.Align.CENTER, active=hdr_active)
                def _on_hdr(sw, _):
                    on = sw.get_active()
                    if on:
                        self.proton_active.add("PROTON_ENABLE_HDR=1")
                        self.proton_active.add("ENABLE_HDR_WSI=1")
                        self.proton_active.add("PROTON_ENABLE_WAYLAND=1")
                        wl_sw = self._proton_switches.get("PROTON_ENABLE_WAYLAND=1")
                        if wl_sw and not wl_sw.get_active():
                            h = self._proton_callbacks.get("PROTON_ENABLE_WAYLAND=1")
                            if h: wl_sw.handler_block_by_func(h)
                            wl_sw.set_active(True)
                            if h: wl_sw.handler_unblock_by_func(h)
                    else:
                        self.proton_active.discard("PROTON_ENABLE_HDR=1")
                        self.proton_active.discard("ENABLE_HDR_WSI=1")
                    self.s["proton_active"] = list(self.proton_active)
                    self._do_write()
                hdr_sw.connect("notify::active", _on_hdr)
                hdr_row.add_suffix(hdr_sw)
                hdr_row.set_activatable_widget(hdr_sw)
                grp.add(hdr_row)

                # When Wayland is turned off, auto-disable HDR
                wl_sw = self._proton_switches.get("PROTON_ENABLE_WAYLAND=1")
                if wl_sw:
                    def _on_wayland_for_hdr(sw, _, *, _hs=hdr_sw):
                        if not sw.get_active() and _hs.get_active():
                            _hs.set_active(False)
                    wl_sw.connect("notify::active", _on_wayland_for_hdr)

                # Disable MangoHud – shown for all profiles (global and per-game)
                is_global = self.selected_appid is None
                mango_sub = ("Disable MangoHud for all games (useful when the game won't start on XWayland/X11)"
                             if is_global else
                             "Disable MangoHud for this game (useful when running the game won't start on XWayland/X11)")
                mango_row = Adw.SwitchRow(title="Disable MangoHud", subtitle=mango_sub)
                mango_row.set_active(self.mangohud_disabled)
                def _on_mangohud_toggle(row, _):
                    self.mangohud_disabled = row.get_active()
                    self._do_write()
                mango_row.connect("notify::active", _on_mangohud_toggle)
                grp.add(mango_row)

        # Custom env vars text area
        box.append(sec_lbl("Custom Environment Variables"))
        hint = Gtk.Label(label="One variable per line: VAR=value")
        hint.set_xalign(0); hint.add_css_class("dim-label"); hint.set_margin_bottom(4)
        box.append(hint)
        self._proton_buf = Gtk.TextBuffer()
        self._proton_buf.set_text(self.proton_custom)
        self._proton_buf.connect("changed", self._on_proton_custom)
        tv2 = Gtk.TextView(buffer=self._proton_buf, monospace=True); tv2.set_size_request(-1,100)
        tv2.set_left_margin(6); tv2.set_right_margin(6); tv2.set_top_margin(6); tv2.set_bottom_margin(6)
        fr2 = Gtk.Frame(); fr2.set_child(tv2); fr2.set_margin_bottom(16); box.append(fr2)
        return scroll

    # ── Proton Versions tab ───────────────────────────────────────────────────

    def _page_versions(self):
        outer = Gtk.ScrolledWindow(vexpand=True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                      margin_start=12, margin_end=12, spacing=0)
        outer.set_child(box)

        # ── External Proton Tools ─────────────────────────────────────────────
        ext_grp = Adw.PreferencesGroup(title="External Proton Tools")
        ext_grp.set_margin_top(10)
        ext_grp.set_margin_bottom(12)

        def _make_tool_row(title, subtitle, flatpak_id, appimage_names, exe_names, github_url):
            found, launch_cmd = find_external_tool(flatpak_id, appimage_names, exe_names)
            row = Adw.ActionRow(title=title, subtitle=subtitle)
            if found:
                btn = Gtk.Button(label="Open")
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect("clicked", lambda _, cmd=launch_cmd: subprocess.Popen(cmd))
            else:
                btn = Gtk.Button(label="Get on GitHub")
                btn.add_css_class("suggested-action")
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect("clicked", lambda _, u=github_url: subprocess.Popen(["xdg-open", u]))
            row.add_suffix(btn)
            return row

        ext_grp.add(_make_tool_row(
            "Proton Plus",
            "Manage custom Proton/Wine versions",
            PROTON_PLUS_FLATPAK, ["ProtonPlus"], ["protonplus"], PROTON_PLUS_URL,
        ))
        ext_grp.add(_make_tool_row(
            "ProtonUp-Qt",
            "Qt-based Proton/Wine version manager",
            PROTONUP_QT_FLATPAK, ["ProtonUp-Qt", "pupgui2"], ["protonup-qt", "pupgui2"], PROTONUP_QT_URL,
        ))

        box.append(ext_grp)
        box.append(Gtk.Separator(margin_bottom=8))

        # ── Installed Proton Versions ─────────────────────────────────────────
        hdr = Gtk.Box(spacing=8, margin_top=8, margin_bottom=6)
        lbl = Gtk.Label(label="Installed Proton Versions")
        lbl.add_css_class("heading"); lbl.set_hexpand(True); lbl.set_xalign(0)
        hdr.append(lbl)
        ref_btn = Gtk.Button(label="⟳ Refresh")
        ref_btn.connect("clicked", lambda _: self._refresh_versions_page())
        hdr.append(ref_btn)
        box.append(hdr)

        def _ver(dir_name: str) -> str:
            """Read the 'version' file inside a compatibilitytools.d directory."""
            try:
                return (COMPAT_DIR / dir_name / "version").read_text().strip()
            except Exception:
                return ""

        installed     = get_installed_proton_versions()
        managed       = load_managed()
        any_installed = False
        categorized   = set()

        for label in ALL_PROTON_LABELS:
            # Any dir with "latest" in its name that matches this family
            latest_list = [d for d in installed
                           if "latest" in d.lower() and _version_belongs_to_label(d, label)]
            # Always include the gubernator-managed dir if present
            managed_name = f"{label}-Latest"
            if (COMPAT_DIR / managed_name).is_dir() and managed_name not in latest_list:
                latest_list.insert(0, managed_name)

            versioned = [d for d in installed
                         if "latest" not in d.lower()
                         and _version_belongs_to_label(d, label)]

            categorized.update(latest_list)
            categorized.update(versioned)

            if not latest_list and not versioned:
                continue
            any_installed = True

            exp = Gtk.Expander(label=label)
            exp.set_expanded(False)
            exp.set_margin_bottom(6)
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                            spacing=2, margin_start=8, margin_top=4)
            exp.set_child(inner)
            grp = Adw.PreferencesGroup()

            for dir_name in latest_list:
                ver = _ver(dir_name)
                if not ver:
                    entry = managed.get(label)
                    ver   = entry.get("latest_tag", "") if isinstance(entry, dict) else ""
                sub = f"Version: {ver}" if ver else dir_name
                row = Adw.ActionRow(title=f"{label} Latest", subtitle=sub)
                grp.add(row)

            for name in versioned:
                ver = _ver(name)
                row = Adw.ActionRow(title=name, subtitle=f"Version: {ver}" if ver else "")
                grp.add(row)

            inner.append(grp)
            box.append(exp)

        # Other — dirs that don't match any known family
        other = [d for d in installed if d not in categorized]
        if other:
            any_installed = True
            exp = Gtk.Expander(label="Other")
            exp.set_expanded(True)
            exp.set_margin_bottom(6)
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                            spacing=2, margin_start=8, margin_top=4)
            exp.set_child(inner)
            grp = Adw.PreferencesGroup()
            for name in other:
                ver = _ver(name)
                row = Adw.ActionRow(title=name, subtitle=f"Version: {ver}" if ver else "")
                grp.add(row)
            inner.append(grp)
            box.append(exp)

        if not any_installed:
            hint = Gtk.Label(label="No Proton versions installed in compatibilitytools.d.")
            hint.add_css_class("dim-label")
            hint.set_margin_top(16)
            box.append(hint)

        # ── Credits ───────────────────────────────────────────────────────────
        box.append(Gtk.Separator(margin_top=12, margin_bottom=4))
        credits_grp = Adw.PreferencesGroup(title="Credits")
        credits_grp.set_margin_bottom(12)

        pp_row = Adw.ActionRow(
            title="Proton Plus by Vysp3r",
            subtitle="github.com/Vysp3r/ProtonPlus",
        )
        pp_btn = Gtk.Button(label="Open GitHub", valign=Gtk.Align.CENTER)
        pp_btn.connect(
            "clicked",
            lambda _: subprocess.Popen(["xdg-open", "https://github.com/Vysp3r/ProtonPlus"]),
        )
        pp_row.add_suffix(pp_btn)
        credits_grp.add(pp_row)

        pq_row = Adw.ActionRow(
            title="ProtonUp-Qt by DavidoTek",
            subtitle="github.com/DavidoTek/ProtonUp-Qt",
        )
        pq_btn = Gtk.Button(label="Open GitHub", valign=Gtk.Align.CENTER)
        pq_btn.connect(
            "clicked",
            lambda _: subprocess.Popen(["xdg-open", "https://github.com/DavidoTek/ProtonUp-Qt"]),
        )
        pq_row.add_suffix(pq_btn)
        credits_grp.add(pq_row)

        box.append(credits_grp)

        return outer

    # ── Reshade tab ───────────────────────────────────────────────────────────

    """
    ReShade Script License — kevinlekiller/reshade-steam-proton
    
    The installer launched by this tab uses reshade-linux.sh by kevinlekiller.
    Source: https://github.com/kevinlekiller/reshade-steam-proton
    """

    def _page_reshade(self):
        is_global = self.selected_appid is None

        outer = Gtk.ScrolledWindow(vexpand=True)
        prefs = Adw.PreferencesPage()
        outer.set_child(prefs)

        # ── Installation (active in Global, grayed in per-game) ───────────────
        install_grp = Adw.PreferencesGroup(
            title="ReShade Installation",
            description="Download reshade-linux.sh and run the interactive installer",
        )
        install_row = Adw.ActionRow(
            title="Install / Update ReShade",
            subtitle="Opens a terminal, downloads reshade-linux.sh to ~/ and runs it",
        )
        install_btn = Gtk.Button(label="Install", valign=Gtk.Align.CENTER)
        install_btn.add_css_class("suggested-action")
        install_btn.set_sensitive(is_global)
        install_btn.connect("clicked", lambda _: self._reshade_run_install())
        install_row.add_suffix(install_btn)
        install_grp.add(install_row)
        prefs.add(install_grp)

        if is_global:
            hint_grp = Adw.PreferencesGroup(
                title="Game Configuration",
                description="Select a game from the sidebar to configure ReShade for it",
            )
            hint_row = Adw.ActionRow(
                title="Available per game only",
                subtitle="Open ReShade, executable path, and WINEDLLOVERRIDES are set per game",
            )
            hint_row.set_sensitive(False)
            hint_grp.add(hint_row)
            prefs.add(hint_grp)
        else:
            # ── Open ReShade ──────────────────────────────────────────────────
            open_grp = Adw.PreferencesGroup(title="Launch ReShade Installer")
            open_row = Adw.ActionRow(
                title="Open ReShade",
                subtitle="Runs ~/reshade-linux.sh in a terminal for this game",
            )
            open_btn = Gtk.Button(label="Open", valign=Gtk.Align.CENTER)
            open_btn.connect("clicked", lambda _: self._reshade_run_script())
            open_row.add_suffix(open_btn)
            open_grp.add(open_row)
            prefs.add(open_grp)

            # ── Game Executable ───────────────────────────────────────────────
            exe_path, folder_path = self._find_reshade_exe()
            exe_grp = Adw.PreferencesGroup(
                title="Game Executable",
                description="Paste this path when the ReShade installer asks for the game .exe",
            )
            if exe_path:
                exe_row = Adw.ActionRow(
                    title="Detected executable",
                    subtitle=str(exe_path),
                )
                copy_exe_btn = Gtk.Button(label="Copy Path", valign=Gtk.Align.CENTER)
                copy_exe_btn.add_css_class("flat")
                copy_exe_btn.connect(
                    "clicked",
                    lambda _, p=str(exe_path): Gdk.Display.get_default().get_clipboard().set(p),
                )
                exe_row.add_suffix(copy_exe_btn)
                exe_grp.add(exe_row)
            else:
                exe_grp.add(Adw.ActionRow(
                    title="Executable not detected",
                    subtitle="Use 'Open Game Folder' to navigate manually",
                ))

            fp = folder_path or (
                Path(self._selected_install_dir) if self._selected_install_dir else None
            )
            folder_row = Adw.ActionRow(
                title="Game folder",
                subtitle=str(fp) if fp else "Not found",
            )
            if fp and fp.exists():
                open_folder_btn = Gtk.Button(label="Open Folder", valign=Gtk.Align.CENTER)
                open_folder_btn.add_css_class("flat")
                open_folder_btn.connect(
                    "clicked", lambda _, p=str(fp): subprocess.Popen(["xdg-open", p])
                )
                folder_row.add_suffix(open_folder_btn)
            exe_grp.add(folder_row)
            prefs.add(exe_grp)

            # ── WINEDLLOVERRIDES ──────────────────────────────────────────────
            dll_grp = Adw.PreferencesGroup(title="WINEDLLOVERRIDES")

            warn_row = Adw.ActionRow(
                title="Select the option shown by the ReShade installer",
                subtitle=(
                    "If your option is not listed, use the Custom field below. "
                    "The selected value is automatically applied to Proton custom vars."
                ),
            )
            warn_row.set_sensitive(False)
            dll_grp.add(warn_row)

            PRESETS = [
                ("DirectX 9",                  "d3d9=n"),
                ("DirectX 9 (alt)",            "d3d9=n,b;dxgi=n,b"),
                ("DirectX 10/11/12 (default)", "dxgi=n,b"),
                ("DirectX 11",                 "d3d11=n,b"),
                ("DirectX 11 (alt)",           "d3d11=n,b;dxgi=n,b"),
                ("DirectX 12",                 "d3d12=n,b"),
                ("DirectX 12 (alt)",           "d3d12=n,b;dxgi=n,b"),
                ("Other",                      "d3dcompiler_47=n;dxgi=n,b"),
                ("OpenGL",                     "opengl32=n,b"),
            ]
            preset_values = [v for _, v in PRESETS]

            game_data = load_game_settings(self.selected_appid) or {}
            saved_dll = game_data.get("reshade_winedll", "")
            is_custom = bool(saved_dll) and saved_dll not in preset_values

            none_row = Adw.ActionRow(
                title="None (disabled)",
                subtitle="Remove WINEDLLOVERRIDES from the launch script",
            )
            none_btn = Gtk.CheckButton(valign=Gtk.Align.CENTER)
            none_btn.set_active(saved_dll == "")
            def _on_none(b, _):
                if b.get_active():
                    self._clear_reshade_winedll()
            none_btn.connect("notify::active", _on_none)
            none_row.add_prefix(none_btn)
            none_row.set_activatable_widget(none_btn)
            dll_grp.add(none_row)

            group_btn = none_btn
            for label, value in PRESETS:
                row = Adw.ActionRow(title=label, subtitle=f'WINEDLLOVERRIDES="{value}"')
                btn = Gtk.CheckButton(valign=Gtk.Align.CENTER)
                if group_btn is None:
                    group_btn = btn
                else:
                    btn.set_group(group_btn)
                btn.set_active(saved_dll == value)

                def _on_preset(b, _, v=value):
                    if b.get_active():
                        self._apply_reshade_winedll(v)
                btn.connect("notify::active", _on_preset)
                row.add_prefix(btn)
                row.set_activatable_widget(btn)
                dll_grp.add(row)

            custom_radio_row = Adw.ActionRow(
                title="Custom",
                subtitle="Enter a value not listed above",
            )
            custom_btn = Gtk.CheckButton(valign=Gtk.Align.CENTER)
            custom_btn.set_group(group_btn)
            custom_btn.set_active(is_custom)
            custom_radio_row.add_prefix(custom_btn)
            custom_radio_row.set_activatable_widget(custom_btn)
            dll_grp.add(custom_radio_row)

            custom_entry_row = Adw.EntryRow(title="Custom WINEDLLOVERRIDES")
            custom_entry_row.set_show_apply_button(True)
            custom_entry_row.set_text(saved_dll if is_custom else "")
            custom_entry_row.set_sensitive(is_custom)

            def _on_custom_radio(b, _):
                custom_entry_row.set_sensitive(b.get_active())
            custom_btn.connect("notify::active", _on_custom_radio)

            def _on_custom_entry(row):
                val = row.get_text().strip()
                if val and custom_btn.get_active():
                    self._apply_reshade_winedll(val)
            custom_entry_row.connect("apply", _on_custom_entry)
            dll_grp.add(custom_entry_row)

            prefs.add(dll_grp)

        # ── Credits ───────────────────────────────────────────────────────────
        credits_grp = Adw.PreferencesGroup(title="Credits")
        credits_row = Adw.ActionRow(
            title="Script by kevinlekiller",
            subtitle="reshade-steam-proton · github.com/kevinlekiller/reshade-steam-proton",
        )
        github_btn = Gtk.Button(label="Open GitHub", valign=Gtk.Align.CENTER)
        github_btn.connect(
            "clicked",
            lambda _: subprocess.Popen(
                ["xdg-open", "https://github.com/kevinlekiller/reshade-steam-proton"]
            ),
        )
        credits_row.add_suffix(github_btn)
        credits_grp.add(credits_row)
        prefs.add(credits_grp)

        return outer

    def _find_reshade_exe(self):
        if not self._selected_install_dir:
            return None, None
        p = Path(self._selected_install_dir)
        if not p.exists():
            return None, None

        if self._engine_detected == "unreal":
            for exe in sorted(p.rglob("*-Win64-Shipping.exe")):
                return exe, exe.parent
            for exe in sorted(p.rglob("*64.exe")):
                if "launcher" not in exe.name.lower():
                    return exe, exe.parent
            folder_lower = p.name.lower()
            for exe in sorted(p.rglob("*.exe")):
                if "launcher" not in exe.name.lower() and exe.stem.lower() == folder_lower:
                    return exe, exe.parent
            return None, p

        if self._engine_detected == "red_engine":
            # Primary: bin/x64/<GameName>.exe (Cyberpunk 2077 pattern)
            bin_x64 = p / "bin" / "x64"
            if bin_x64.is_dir():
                for exe in sorted(bin_x64.glob("*.exe")):
                    if "launcher" not in exe.name.lower():
                        return exe, exe.parent
            # Fallback: bin/game.exe
            fallback = p / "bin" / "game.exe"
            if fallback.exists():
                return fallback, fallback.parent
            return None, p

        return None, p

    def _reshade_run_install(self):
        url = "https://raw.githubusercontent.com/kevinlekiller/reshade-steam-proton/main/reshade-linux.sh"
        cmd = (
            f'curl -sL "{url}" -o ~/reshade-linux.sh && '
            f'chmod +x ~/reshade-linux.sh && ~/reshade-linux.sh; '
            f'echo; echo "Press Enter to close..."; read _'
        )
        self._open_terminal(cmd)

    def _reshade_run_script(self):
        script = Path.home() / "reshade-linux.sh"
        if not script.exists():
            dlg = Adw.MessageDialog(
                heading="ReShade not installed",
                body=(
                    "~/reshade-linux.sh not found.\n"
                    "Use 'Install / Update ReShade' in Global / Default first."
                ),
            )
            dlg.add_response("ok", "OK")
            dlg.present(self)
            return
        cmd = "~/reshade-linux.sh; echo; echo 'Press Enter to close...'; read _"
        self._open_terminal(cmd)

    def _open_terminal(self, cmd: str):
        candidates = [
            ["gnome-terminal", "--", "bash", "-c", cmd],
            ["konsole", "-e", "bash", "-c", cmd],
            ["xfce4-terminal", "-e", f"bash -c {cmd!r}"],
            ["kitty", "bash", "-c", cmd],
            ["alacritty", "-e", "bash", "-c", cmd],
            ["foot", "bash", "-c", cmd],
            ["xterm", "-e", f"bash -c {cmd!r}"],
        ]
        for args in candidates:
            try:
                subprocess.Popen(args)
                return
            except FileNotFoundError:
                continue
        dlg = Adw.MessageDialog(
            heading="No terminal found",
            body="Could not find a terminal emulator. Run this command manually:\n\n" + cmd,
        )
        dlg.add_response("ok", "OK")
        dlg.present(self)

    def _apply_reshade_winedll(self, value: str):
        if not self.selected_appid:
            return
        new_line = f'export WINEDLLOVERRIDES="{value}"'
        lines = [
            ln for ln in self.proton_custom.splitlines()
            if not ln.strip().startswith("export WINEDLLOVERRIDES=")
            and not ln.strip().startswith("WINEDLLOVERRIDES=")
        ]
        lines.append(new_line)
        self.proton_custom = "\n".join(lines)
        self.s["proton_custom"] = self.proton_custom
        self._do_write()
        # Save after _do_write so it isn't overwritten by _do_write's save_game_settings call
        game_data = load_game_settings(self.selected_appid) or {}
        game_data["reshade_winedll"] = value
        save_game_settings(self.selected_appid, game_data)

    def _clear_reshade_winedll(self):
        if not self.selected_appid:
            return
        lines = [
            ln for ln in self.proton_custom.splitlines()
            if not ln.strip().startswith("export WINEDLLOVERRIDES=")
            and not ln.strip().startswith("WINEDLLOVERRIDES=")
        ]
        self.proton_custom = "\n".join(lines)
        self.s["proton_custom"] = self.proton_custom
        self._do_write()
        # Save after _do_write so it isn't overwritten
        game_data = load_game_settings(self.selected_appid) or {}
        game_data.pop("reshade_winedll", None)
        save_game_settings(self.selected_appid, game_data)

    def _refresh_versions_page(self):
        GLib.idle_add(self._build_right_panel)

    # ── Engine tab ────────────────────────────────────────────────────────────

    def _page_engine(self):
        page = Adw.PreferencesPage()
        self._engine_group = Adw.PreferencesGroup()
        page.add(self._engine_group)
        self._fill_engine_content()
        return page

    def _fill_engine_content(self):
        grp = self._engine_group
        # Clear existing rows
        child = grp.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            try:
                grp.remove(child)
            except Exception:
                pass
            child = nxt

        if self.selected_appid is None:
            row = Adw.ActionRow(title="Engine Config",
                                subtitle="Select a game from the list")
            grp.add(row)
            return

        engine = self._engine_detected
        ENGINE_NAMES = {
            "unreal":     "Unreal Engine",
            "re_engine":  "RE Engine",
            "unity":      "Unity",
            "godot":      "Godot",
            "unknown":    "Unknown",
            "red_engine": "REDengine (CD Projekt Red)",
            "source":     "Source / Source 2",
            "creation":   "Creation Engine",
            "gamemaker":  "GameMaker",
            "rpgmaker":   "RPG Maker",
            "cry_engine": "CryEngine",
            "id_tech":    "id Tech",
            "decima":     "Decima",
            "katana":     "Katana Engine",
            "asura":      "Asura Engine",
        }
        engine_lbl = ENGINE_NAMES.get(engine, engine.title())

        badge_row = Adw.ActionRow(title="Detected Engine", subtitle=engine_lbl)
        grp.set_title(engine_lbl + " Config")
        grp.add(badge_row)

        if engine == "unreal":
            cfg_dir = find_unreal_config_dir(self.selected_appid)
            path_str = str(cfg_dir) if cfg_dir else "Not found — launch the game at least once"
            path_row = Adw.ActionRow(title="Config directory", subtitle=path_str)
            if cfg_dir:
                open_btn = Gtk.Button(label="Open Folder", valign=Gtk.Align.CENTER)
                open_btn.add_css_class("flat")
                open_btn.connect("clicked",
                    lambda _, p=cfg_dir: subprocess.Popen(["xdg-open", str(p)]))
                path_row.add_suffix(open_btn)
            grp.add(path_row)

            if cfg_dir:
                input_ini  = cfg_dir / "Input.ini"
                engine_ini = cfg_dir / "Engine.ini"
                inp_vals = read_unreal_ini(input_ini,  "/Script/Engine.InputSettings")
                eng_vals = read_unreal_ini(engine_ini, "SystemSettings")

                smooth_row = Adw.SwitchRow(
                    title="Disable Mouse Smoothing",
                    subtitle="bEnableMouseSmoothing + bViewAccelerationEnabled in Input.ini")
                smooth_row.set_active(
                    inp_vals.get("bEnableMouseSmoothing", "True").strip() != "True")
                smooth_row.connect("notify::active", lambda row, _,
                        ir=input_ini: (
                    write_unreal_ini(ir, "/Script/Engine.InputSettings", {
                        "bEnableMouseSmoothing":    "False" if row.get_active() else "True",
                        "bViewAccelerationEnabled": "False" if row.get_active() else "True",
                    }),
                    self.s.update({"ue_mouse_smoothing_disabled": row.get_active()}),
                    self._do_write(),
                ))
                grp.add(smooth_row)

                blur_val = eng_vals.get("r.MotionBlur.Max", "1").strip()
                blur_row = Adw.SwitchRow(
                    title="Disable Motion Blur",
                    subtitle="r.MotionBlur.Max / Quality in Engine.ini")
                blur_row.set_active(blur_val == "0")
                blur_row.connect("notify::active", lambda row, _,
                        er=engine_ini: (
                    write_unreal_ini(er, "SystemSettings", {
                        "r.MotionBlur.Max":            "0" if row.get_active() else "1",
                        "r.MotionBlurQuality":         "0" if row.get_active() else "3",
                        "r.DefaultFeature.MotionBlur": "0" if row.get_active() else "1",
                    }),
                    self.s.update({"ue_motion_blur_disabled": row.get_active()}),
                    self._do_write(),
                ))
                grp.add(blur_row)



        elif engine == "re_engine":
            args_path = GAMES_DIR / f"{self.selected_appid}-launch-args.txt"
            wine_enabled = not (args_path.exists() and
                                "/WineDetectionEnabled:False" in args_path.read_text())
            wine_row = Adw.SwitchRow(
                title="Wine Detection",
                subtitle="Disable to use Ray Tracing (/WineDetectionEnabled:False)")
            wine_row.set_active(wine_enabled)
            grp.add(wine_row)

            save_btn = Gtk.Button(label="Save", halign=Gtk.Align.END,
                                  margin_top=8, margin_bottom=4)
            save_btn.add_css_class("suggested-action")
            save_btn.connect("clicked",
                lambda _, wr=wine_row: self._on_save_engine_config_re(wr))
            grp.add(save_btn)

        elif engine == "katana":
            katana = find_katana_config(self.selected_appid)
            json_path = katana["graphics"]
            ini_path  = katana["ini"]
            if json_path:
                path_row = Adw.ActionRow(
                    title="Graphics config",
                    subtitle=str(json_path),
                )
                open_btn = Gtk.Button(label="Open Folder", valign=Gtk.Align.CENTER)
                open_btn.add_css_class("flat")
                open_btn.connect(
                    "clicked",
                    lambda _, p=json_path.parent: subprocess.Popen(["xdg-open", str(p)]),
                )
                path_row.add_suffix(open_btn)
                grp.add(path_row)

                fps_key, fps_val = read_katana_fps(json_path)
                if fps_key is not None:
                    is_str = isinstance(fps_val, str)
                    fps_row = Adw.EntryRow(title=f"FPS limit  ({fps_key})")
                    fps_row.set_show_apply_button(True)
                    fps_row.set_text(str(fps_val))
                    fps_row.connect(
                        "apply",
                        lambda row, p=json_path, k=fps_key, s=is_str:
                            self._on_save_katana_fps(row, p, k, s),
                    )
                    grp.add(fps_row)
                else:
                    grp.add(Adw.ActionRow(
                        title="FPS key not found",
                        subtitle="No recognized FPS key in graphics_option.json",
                    ))
            else:
                grp.add(Adw.ActionRow(
                    title="Config not found",
                    subtitle="Launch the game at least once to generate "
                             "KoeiTecmo/[Game]/Savedata/graphics_option.json",
                ))
            if ini_path:
                ini_row = Adw.ActionRow(
                    title="game.ini",
                    subtitle=str(ini_path),
                )
                ini_open_btn = Gtk.Button(label="Open Folder", valign=Gtk.Align.CENTER)
                ini_open_btn.add_css_class("flat")
                ini_open_btn.connect(
                    "clicked",
                    lambda _, p=ini_path.parent: subprocess.Popen(["xdg-open", str(p)]),
                )
                ini_row.add_suffix(ini_open_btn)
                grp.add(ini_row)

        elif engine == "asura":
            asura = find_asura_paths(self.selected_appid)
            cfg = asura["config"]
            if cfg:
                row = Adw.ActionRow(title="Config Folder", subtitle=str(cfg))
                btn = Gtk.Button(label="Open Folder", valign=Gtk.Align.CENTER)
                btn.add_css_class("flat")
                btn.connect("clicked", lambda _, p=cfg: subprocess.Popen(["xdg-open", str(p)]))
                row.add_suffix(btn)
                grp.add(row)
            else:
                grp.add(Adw.ActionRow(
                    title="Config not found",
                    subtitle="Launch the game at least once to generate AppData/Local/[Game]",
                ))

        elif engine == "decima":
            cfg_path = find_decima_config(self.selected_appid)
            if cfg_path:
                path_row = Adw.ActionRow(
                    title="game_settings.cfg",
                    subtitle=str(cfg_path),
                )
                open_btn = Gtk.Button(label="Open Folder", valign=Gtk.Align.CENTER)
                open_btn.add_css_class("flat")
                open_btn.connect(
                    "clicked",
                    lambda _, p=cfg_path.parent: subprocess.Popen(["xdg-open", str(p)]),
                )
                path_row.add_suffix(open_btn)
                grp.add(path_row)
            else:
                grp.add(Adw.ActionRow(
                    title="Config not found",
                    subtitle="Launch the game at least once to generate game_settings.cfg",
                ))

        else:
            info_row = Adw.ActionRow(
                title="No config available",
                subtitle=f"{engine_lbl} engine configs are not yet supported")
            grp.add(info_row)

    def _refresh_engine_page(self):
        self._fill_engine_content()
     

    def _on_save_engine_config_re(self, wine_row):
        try:
            save_re_engine_args(self.selected_appid, wine_row.get_active())
            # Regenerate wrapper from global settings — do NOT go through _do_write()
            # because that would overwrite the per-game Proton env and add unset calls
            # for global tweaks (Wayland, HDR, …) that the user wants to keep active.
            gs = load_settings()
            write_wrapper(set(gs.get("proton_active", [])), gs.get("proton_custom", ""), mangohud_disabled=gs.get("mangohud_disabled", False))
            if WRAPPER_SCRIPT.exists():
                self.script_preview.set_label(WRAPPER_SCRIPT.read_text())
            self._set_status("RE Engine config saved")
        except Exception as e:
            dlg = Adw.MessageDialog(transient_for=self, heading="Gubr open",
                                    body=f"Could not save RE Engine config:\n{e}")
            dlg.add_response("ok", "OK")
            dlg.present()

    def _on_save_katana_fps(self, entry_row, json_path, key, as_string):
        val_str = entry_row.get_text().strip()
        try:
            val = int(val_str)
        except ValueError:
            dlg = Adw.MessageDialog(
                transient_for=self,
                heading="Invalid value",
                body="Please enter a whole number for the FPS limit.",
            )
            dlg.add_response("ok", "OK")
            dlg.present()
            return
        try:
            write_katana_fps(json_path, key, val, as_string)
            self._set_status(f"FPS limit set to {val}")
        except Exception as e:
            dlg = Adw.MessageDialog(
                transient_for=self,
                heading="Could not save config",
                body=str(e),
            )
            dlg.add_response("ok", "OK")
            dlg.present()

    # ── Saves tab ─────────────────────────────────────────────────────────────

    def _page_saves(self):
        page = Adw.PreferencesPage()
        self._saves_native_grp  = Adw.PreferencesGroup(title="Native Linux Saves")
        self._saves_proton_grp  = Adw.PreferencesGroup(title="Proton Saves")
        self._saves_migrate_grp = Adw.PreferencesGroup(title="Migration")
        self._saves_backup_grp  = Adw.PreferencesGroup(title="Backup")
        page.add(self._saves_native_grp)
        page.add(self._saves_proton_grp)
        page.add(self._saves_migrate_grp)
        page.add(self._saves_backup_grp)
        self._fill_saves_content()
        return page

    def _fill_saves_content(self):
        def _clear(grp):
            child = grp.get_first_child()
            while child:
                nxt = child.get_next_sibling()
                try:
                    grp.remove(child)
                except Exception:
                    pass
                child = nxt

        for g in (self._saves_native_grp, self._saves_proton_grp,
                  self._saves_migrate_grp, self._saves_backup_grp):
            _clear(g)

        if self.selected_appid is None:
            self._saves_native_grp.set_title("Saves")
            row = Adw.ActionRow(title="Save Migration",
                                subtitle="Select a game from the list")
            self._saves_native_grp.add(row)
            self._saves_proton_grp.set_visible(False)
            self._saves_migrate_grp.set_visible(False)
            self._saves_backup_grp.set_visible(False)
            return

        # ── Per-game overrides ────────────────────────────────────────────────
        CLOUD_ONLY_GAMES = {
            "594650":   "Hunt: Showdown 1896",
            "730":      "CS2",
            "570":      "Dota 2",
            "440":      "Team Fortress 2",
            "221100":   "DayZ",
            "252490":   "Rust",
            "2767030":  "Marvel Rivals",
            "1172470":  "Apex Legends",
            "1085660":  "Destiny 2",
            "230410":   "Warframe",
            "238960":   "Path of Exile",
            "2694490":  "Path of Exile 2",
        }
        if self.selected_appid in CLOUD_ONLY_GAMES:
            self._saves_native_grp.set_title("Saves")
            self._saves_native_grp.set_visible(True)
            self._saves_native_grp.add(Adw.ActionRow(
                title="Steam Cloud Saves only",
                subtitle=f"{CLOUD_ONLY_GAMES[self.selected_appid]} does not store save files locally — "
                         "all progress is managed by Steam Cloud.",
            ))
            self._saves_proton_grp.set_visible(False)
            self._saves_migrate_grp.set_visible(False)
            self._saves_backup_grp.set_visible(False)
            return

        engine = self._engine_detected

        def _open_btn(path):
            btn = Gtk.Button(label="Open Folder", valign=Gtk.Align.CENTER)
            btn.add_css_class("flat")
            btn.connect("clicked", lambda _, p=path: subprocess.Popen(["xdg-open", str(p)]))
            return btn

        def _show_not_supported(msg):
            self._saves_native_grp.set_title("Saves")
            self._saves_native_grp.set_visible(True)
            self._saves_native_grp.add(Adw.ActionRow(title="Not available", subtitle=msg))
            self._saves_proton_grp.set_visible(False)
            self._saves_migrate_grp.set_visible(False)
            self._saves_backup_grp.set_visible(False)

        def _show_proton_only(path, group_title):
            self._saves_native_grp.set_visible(False)
            self._saves_proton_grp.set_title(group_title)
            self._saves_proton_grp.set_visible(True)
            row = Adw.ActionRow(
                title="Save location",
                subtitle=str(path) if path else "Not found yet — launch the game once")
            if path:
                row.add_suffix(_open_btn(path))
            self._saves_proton_grp.add(row)
            self._saves_migrate_grp.set_visible(False)
            if path:
                self._saves_backup_grp.set_visible(True)
                exp_btn = Gtk.Button(label="Export as ZIP", halign=Gtk.Align.CENTER,
                                     margin_top=4, margin_bottom=4)
                exp_btn.add_css_class("suggested-action")
                exp_btn.connect("clicked", lambda _, s=path: self._on_export_saves(s))
                self._saves_backup_grp.add(exp_btn)
                imp_btn = Gtk.Button(label="Import ZIP", halign=Gtk.Align.CENTER,
                                     margin_bottom=4)
                imp_btn.connect("clicked", lambda _, d=path: self._on_import_saves(d))
                self._saves_backup_grp.add(imp_btn)
            else:
                self._saves_backup_grp.set_visible(False)

        def _show_appdata(locs):
            self._saves_native_grp.set_visible(False)
            self._saves_proton_grp.set_title("Proton Saves (AppData)")
            self._saves_proton_grp.set_visible(True)
            for label, path in [("AppData/Local", locs["local"]),
                                 ("AppData/Roaming", locs["roaming"])]:
                row = Adw.ActionRow(title=label,
                                    subtitle=str(path) if path else "Not found")
                if path:
                    row.add_suffix(_open_btn(path))
                self._saves_proton_grp.add(row)
            self._saves_migrate_grp.set_visible(False)
            self._saves_backup_grp.set_visible(False)

        if engine == "unreal":
            self._saves_native_grp.set_title("Native Linux Saves")
            self._saves_proton_grp.set_visible(True)
            self._saves_backup_grp.set_visible(True)
            paths = find_save_paths(self.selected_appid, engine, self.selected_name)
            native_path = paths["native"]
            proton_path = paths["proton"]

            # Native card
            nat_row = Adw.ActionRow(
                title="Save location",
                subtitle=str(native_path) if native_path else "Not found")
            if native_path:
                nat_row.add_suffix(_open_btn(native_path))
            self._saves_native_grp.add(nat_row)

            # Proton card
            pro_row = Adw.ActionRow(
                title="Save location",
                subtitle=str(proton_path) if proton_path else "Not found yet — launch the game once")
            if proton_path:
                pro_row.add_suffix(_open_btn(proton_path))
            self._saves_proton_grp.add(pro_row)

            # Migration (only when both exist)
            if native_path and proton_path:
                self._saves_migrate_grp.set_visible(True)
                n2p_btn = Gtk.Button(
                    label="Copy Native → Proton", halign=Gtk.Align.CENTER,
                    margin_top=4, margin_bottom=4)
                n2p_btn.add_css_class("destructive-action")
                n2p_btn.connect("clicked",
                    lambda _, s=native_path, d=proton_path:
                        self._confirm_copy_saves(s, d, "Copy Native → Proton?"))
                self._saves_migrate_grp.add(n2p_btn)

                p2n_btn = Gtk.Button(
                    label="Copy Proton → Native", halign=Gtk.Align.CENTER,
                    margin_bottom=4)
                p2n_btn.add_css_class("destructive-action")
                p2n_btn.connect("clicked",
                    lambda _, s=proton_path, d=native_path:
                        self._confirm_copy_saves(s, d, "Copy Proton → Native?"))
                self._saves_migrate_grp.add(p2n_btn)
            else:
                self._saves_migrate_grp.set_visible(False)

            # Backup
            export_src = native_path or proton_path
            if export_src:
                exp_btn = Gtk.Button(
                    label="Export as ZIP", halign=Gtk.Align.CENTER,
                    margin_top=4, margin_bottom=4)
                exp_btn.add_css_class("suggested-action")
                exp_btn.connect("clicked",
                    lambda _, s=export_src: self._on_export_saves(s))
                self._saves_backup_grp.add(exp_btn)

            imp_dest = proton_path or native_path
            if imp_dest:
                imp_btn = Gtk.Button(
                    label="Import ZIP", halign=Gtk.Align.CENTER,
                    margin_bottom=4)
                imp_btn.connect("clicked",
                    lambda _, d=imp_dest: self._on_import_saves(d))
                self._saves_backup_grp.add(imp_btn)

        elif engine == "red_engine":
            paths = find_save_paths_redengine(self.selected_appid)
            _show_proton_only(paths["proton"], "Proton Saves (CD Projekt Red)")

        elif engine == "creation":
            paths = find_save_paths_creation(self.selected_appid)
            _show_proton_only(paths["proton"], "Proton Saves (My Documents/My Games)")

        elif engine in ("gamemaker", "rpgmaker"):
            locs = find_save_paths_appdata(self.selected_appid)
            _show_appdata(locs)

        elif engine == "cry_engine":
            locs = find_save_paths_cryengine(self.selected_appid)
            self._saves_native_grp.set_visible(False)
            self._saves_proton_grp.set_title("Proton Saves (CryEngine)")
            self._saves_proton_grp.set_visible(True)
            for label, path in [
                ("Documents/My Games", locs["my_games"]),
                ("AppData/Local",      locs["local"]),
                ("AppData/LocalLow",   locs["local_low"]),
                ("AppData/Roaming",    locs["roaming"]),
            ]:
                row = Adw.ActionRow(title=label,
                                    subtitle=str(path) if path else "Not found")
                if path:
                    row.add_suffix(_open_btn(path))
                self._saves_proton_grp.add(row)
            self._saves_migrate_grp.set_visible(False)
            self._saves_backup_grp.set_visible(False)

        elif engine == "asura":
            asura = find_asura_paths(self.selected_appid)
            _show_proton_only(asura["saves"], "Proton Saves (Asura Engine)")

        elif engine == "source":
            _show_not_supported("Source / Source 2 save paths are not supported yet")

        else:
            _show_not_supported("Save path detection is not supported for this engine type")

    def _refresh_saves_page(self):
        self._fill_saves_content()

    def _confirm_copy_saves(self, source, dest, title):
        dlg = Adw.MessageDialog(
            transient_for=self,
            heading="Gubr open",
            body=f"{title}\nDestination will be overwritten.")
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("copy",   "Copy")
        dlg.set_response_appearance("copy", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        dlg.connect("response",
            lambda _, r, s=source, d=dest:
                self._do_copy_saves(s, d) if r == "copy" else None)
        dlg.present()

    def _do_copy_saves(self, source, dest):
        try:
            copy_saves(source, dest)
            self._set_status(f"Saves copied to {dest}")
        except Exception as e:
            dlg = Adw.MessageDialog(transient_for=self, heading="Gubr open",
                                    body=f"Copy failed:\n{e}")
            dlg.add_response("ok", "OK")
            dlg.present()

    def _on_export_saves(self, source):
        fc = Gtk.FileChooserNative(
            title="Export Saves as ZIP",
            transient_for=self,
            action=Gtk.FileChooserAction.SAVE)
        safe_name = self.selected_name.replace(" ", "_") if self.selected_name else "game"
        fc.set_current_name(f"{safe_name}_saves_backup.zip")
        fc.connect("response", lambda dlg, resp, s=source:
            self._do_export_saves(s, Path(dlg.get_file().get_path()))
            if resp == Gtk.ResponseType.ACCEPT else None)
        fc.show()

    def _do_export_saves(self, source, zip_path):
        try:
            export_saves_zip(source, zip_path)
            self._set_status(f"Saves exported to {zip_path.name}")
        except Exception as e:
            dlg = Adw.MessageDialog(transient_for=self, heading="Gubr open",
                                    body=f"Export failed:\n{e}")
            dlg.add_response("ok", "OK")
            dlg.present()

    def _on_import_saves(self, dest):
        fc = Gtk.FileChooserNative(
            title="Import Saves from ZIP",
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN)
        f = Gtk.FileFilter()
        f.set_name("ZIP archives")
        f.add_pattern("*.zip")
        fc.add_filter(f)
        fc.connect("response", lambda dlg, resp, d=dest:
            self._do_import_saves(Path(dlg.get_file().get_path()), d)
            if resp == Gtk.ResponseType.ACCEPT else None)
        fc.show()

    def _do_import_saves(self, zip_path, dest):
        try:
            import_saves_zip(zip_path, dest)
            self._set_status(f"Saves imported from {zip_path.name}")
        except Exception as e:
            dlg = Adw.MessageDialog(transient_for=self, heading="Gubr open",
                                    body=f"Import failed:\n{e}")
            dlg.add_response("ok", "OK")
            dlg.present()

    # ── Companion tab ─────────────────────────────────────────────────────────

    def _page_companion(self):
        scroll = Gtk.ScrolledWindow(vexpand=True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin_start=12, margin_end=12)
        scroll.set_child(box)

        if self.selected_appid is None:
            info = Gtk.Label(
                label="Custom app settings are per-game only.\n"
                      "Select a game from the sidebar to configure."
            )
            info.set_xalign(0)
            info.add_css_class("dim-label")
            info.set_margin_top(16)
            box.append(info)
            return scroll

        # ── Launch control ─────────────────────────────────────────────────────
        box.append(sec_lbl("Custom App"))
        en_grp = Adw.PreferencesGroup()
        en_grp.set_description(
            "Manually launch an extra Windows program inside the same Wine prefix "
            "as the game. Use Auto-fill to match the running game's wine binary."
        )
        box.append(en_grp)

        running = self._companion_proc and self._companion_proc.poll() is None
        launch_row = Adw.ActionRow(
            title="Manual Launch",
            subtitle="Start or stop the app right now, without launching the game"
        )
        self._companion_launch_btn = Gtk.Button(
            label="■  Kill App" if running else "▶  Launch App",
            valign=Gtk.Align.CENTER
        )
        if running:
            self._companion_launch_btn.add_css_class("destructive-action")
        else:
            self._companion_launch_btn.add_css_class("suggested-action")
        self._companion_launch_btn.connect("clicked", self._toggle_companion)
        launch_row.add_suffix(self._companion_launch_btn)
        en_grp.add(launch_row)

        # Autostart row: label + delay entry on the same row
        autostart_cfg_row = Adw.ActionRow(
            title="Autostart Delay",
            subtitle="Seconds to wait after the game starts before launching the app"
        )
        autostart_sw_row = Adw.SwitchRow(
            title="Enable Autostart",
            subtitle="Launch the app automatically when the game starts (game starts first, then the app after the delay)"
        )
        autostart_sw_row.set_active(self.companion_autostart)
        autostart_sw_row.connect("notify::active", self._on_companion_autostart_changed)
        en_grp.add(autostart_sw_row)
        delay_box = Gtk.Box(spacing=4, valign=Gtk.Align.CENTER)
        delay_entry = Gtk.Entry(width_chars=4)
        delay_entry.set_text(str(self.companion_delay))
        delay_entry.set_input_purpose(Gtk.InputPurpose.DIGITS)
        delay_entry.connect("changed", self._on_companion_delay_changed)
        delay_lbl = Gtk.Label(label="sec")
        delay_lbl.add_css_class("dim-label")
        delay_box.append(delay_entry)
        delay_box.append(delay_lbl)
        autostart_cfg_row.add_suffix(delay_box)
        en_grp.add(autostart_cfg_row)


        autowrap_row = Adw.SwitchRow(
            title="Crash Popup",
            subtitle="Show a popup with exit code and output when the app exits unexpectedly."
        )
        autowrap_row.set_active(self.companion_autowrap)
        autowrap_row.connect("notify::active", self._on_companion_autowrap_changed)
        en_grp.add(autowrap_row)

        # ── Command entry ──────────────────────────────────────────────────────
        box.append(sec_lbl("Executable / Command"))
        cmd_grp = Adw.PreferencesGroup()
        cmd_grp.set_description(
            "Full command to launch the app, e.g.:  wine /home/user/Aurora/Aurora.exe\n"
            "For .exe files, 'wine ' is prepended automatically when using the file picker."
        )
        box.append(cmd_grp)

        cmd_row = Adw.ActionRow(title="Command")
        cmd_box = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)

        self._companion_entry = Gtk.Entry()
        self._companion_entry.set_text(self.companion_exec)
        self._companion_entry.set_hexpand(True)
        self._companion_entry.set_width_chars(42)
        self._companion_entry.set_placeholder_text("wine /path/to/companion.exe")
        self._companion_entry.connect("changed", self._on_companion_exec_changed)
        cmd_box.append(self._companion_entry)

        browse_btn = Gtk.Button(icon_name="document-open-symbolic")
        browse_btn.set_valign(Gtk.Align.CENTER)
        browse_btn.set_tooltip_text("Browse for executable…")
        browse_btn.connect("clicked", self._on_companion_browse)
        cmd_box.append(browse_btn)

        cmd_row.add_suffix(cmd_box)
        cmd_grp.add(cmd_row)

        # ── Companion env vars ─────────────────────────────────────────────────
        env_hdr = Gtk.Box(spacing=8, margin_top=12, margin_bottom=4)
        env_lbl = Gtk.Label(label="App-only Environment Variables")
        env_lbl.add_css_class("heading")
        env_lbl.set_hexpand(True)
        env_lbl.set_xalign(0)
        env_hdr.append(env_lbl)

        autofill_btn = Gtk.Button(label="Auto-fill Proton Prefix")
        autofill_btn.set_valign(Gtk.Align.CENTER)
        autofill_btn.set_tooltip_text(
            "Detects this game's Steam Proton prefix and Proton wine binary,\n"
            "then fills WINEPREFIX and updates the command automatically."
        )
        autofill_btn.connect("clicked", self._on_companion_autofill)
        env_hdr.append(autofill_btn)
        box.append(env_hdr)

        hint = Gtk.Label(
            label="One variable per line: VAR=value\n"
                  "These vars apply ONLY to this app, NOT to the game."
        )
        hint.set_xalign(0)
        hint.add_css_class("dim-label")
        hint.set_margin_bottom(4)
        box.append(hint)

        self._companion_buf = Gtk.TextBuffer()
        self._companion_buf.set_text(self.companion_env)
        self._companion_buf.connect("changed", self._on_companion_env_changed)
        tv = Gtk.TextView(buffer=self._companion_buf, monospace=True)
        tv.set_size_request(-1, 120)
        tv.set_left_margin(6); tv.set_right_margin(6); tv.set_top_margin(6); tv.set_bottom_margin(6)
        fr = Gtk.Frame()
        fr.set_child(tv)
        fr.set_margin_bottom(16)
        box.append(fr)

        return scroll

    # ── Game tab ──────────────────────────────────────────────────────────────

    def _page_game(self):
        scroll = Gtk.ScrolledWindow(vexpand=True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin_start=12, margin_end=12)
        scroll.set_child(box)

        is_global = self.selected_appid is None
        editable  = not is_global and self.use_custom
        install   = self._selected_install_dir if not is_global else ""

        # ── Installation ──────────────────────────────────────────────────────
        box.append(sec_lbl("Installation"))

        loc_grp = Adw.PreferencesGroup()
        box.append(loc_grp)

        if is_global:
            info = Gtk.Label(label="Game information is per-game only.\nSelect a game from the sidebar to view.")
            info.set_xalign(0)
            info.add_css_class("dim-label")
            info.set_margin_top(8)
            box.append(info)
            return scroll

        # Install path row
        path_row = Adw.ActionRow(
            title="Install Path",
            subtitle=install if install else "Not found",
        )
        open_btn = Gtk.Button(label="Open Folder", valign=Gtk.Align.CENTER)
        open_btn.set_sensitive(bool(install))
        open_btn.connect("clicked", lambda _: subprocess.Popen(["xdg-open", install]))
        path_row.add_suffix(open_btn)
        loc_grp.add(path_row)

        # PCGamingWiki row
        pcgw_row = Adw.ActionRow(
            title="PCGamingWiki",
            subtitle="Open the game's page on PCGamingWiki",
        )
        pcgw_btn = Gtk.Button(label="Open Page", valign=Gtk.Align.CENTER)
        pcgw_btn.connect("clicked", lambda btn: self._open_pcgw_page(btn))
        pcgw_row.add_suffix(pcgw_btn)
        loc_grp.add(pcgw_row)

        # PCGamingWiki API data row
        _cache_path_g = GAMES_DIR / f"{self.selected_appid}-tweaks-cache.json"
        try:
            _cache_date_str = json.loads(_cache_path_g.read_text()).get("last_checked", "never")
        except Exception:
            _cache_date_str = "never"
        api_row = Adw.ActionRow(
            title="Game Tweaks Data",
            subtitle=f"Last fetched: {_cache_date_str}",
        )
        fetch_api_btn = Gtk.Button(label="Fetch API", valign=Gtk.Align.CENTER)
        api_row.add_suffix(fetch_api_btn)
        loc_grp.add(api_row)

        # ── Game Tweaks ───────────────────────────────────────────────────────
        box.append(sec_lbl("Game Tweaks"))

        if not editable:
            hint = Gtk.Label(label="Enable Custom Settings to use game-specific tweaks.")
            hint.set_xalign(0)
            hint.add_css_class("dim-label")
            hint.set_margin_top(4)
            hint.set_margin_bottom(8)
            box.append(hint)

        # Placeholder populated asynchronously by the PCGamingWiki fetch
        tweaks_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.append(tweaks_box)

        def _show_loading():
            child = tweaks_box.get_first_child()
            while child:
                nxt = child.get_next_sibling()
                tweaks_box.remove(child)
                child = nxt
            lbl = Gtk.Label(label="Loading tweaks from PCGamingWiki…")
            lbl.set_xalign(0)
            lbl.add_css_class("dim-label")
            lbl.set_margin_top(4)
            tweaks_box.append(lbl)

        _show_loading()

        def _force_fetch_clicked(_btn):
            _TWEAKS_SESSION_CACHE.pop(self.selected_appid, None)
            fetch_api_btn.set_sensitive(False)
            _show_loading()
            threading.Thread(
                target=self._fetch_and_update_tweaks,
                args=(self.selected_appid, install, tweaks_box, editable, True, fetch_api_btn, api_row),
                daemon=True,
            ).start()

        fetch_api_btn.connect("clicked", _force_fetch_clicked)

        threading.Thread(
            target=self._fetch_and_update_tweaks,
            args=(self.selected_appid, install, tweaks_box, editable, False, fetch_api_btn, api_row),
            daemon=True,
        ).start()

        return scroll

    def _fetch_and_update_tweaks(self, appid, install_dir, tweaks_box, editable,
                                  force=False, fetch_btn=None, api_row=None):
        """Background thread: fetch PCGamingWiki data, then schedule a UI rebuild."""
        today = datetime.date.today()

        # Session cache: if we already fetched this game during this run, reuse it.
        if not force and appid in _TWEAKS_SESSION_CACHE:
            hit = _TWEAKS_SESSION_CACHE[appid]
            GLib.idle_add(
                self._rebuild_tweaks_ui,
                appid, tweaks_box, hit["launch_args"], hit["file_ops"], install_dir, editable,
                fetch_btn, api_row, hit.get("screen_args", []), hit.get("widescreen_info", []),
            )
            return

        cache_path = GAMES_DIR / f"{appid}-tweaks-cache.json"

        # Load file cache so we can show options even if the API fails
        cached_args:           list = []
        cached_file_ops:       list = []
        cached_screen_args:    list = []
        cached_widescreen_info: list = []
        last_checked = None
        try:
            cached = json.loads(cache_path.read_text())
            cached_args            = cached.get("launch_args",     [])
            cached_file_ops        = cached.get("file_ops",        [])
            cached_screen_args     = cached.get("screen_args",     [])
            cached_widescreen_info = cached.get("widescreen_info", [])
            lc = cached.get("last_checked")
            if lc:
                last_checked = datetime.date.fromisoformat(lc)
        except Exception:
            pass

        # Use cached data if it was already checked today and this is not a forced refresh
        _has_cache = bool(cached_args or cached_file_ops or cached_screen_args or cached_widescreen_info)
        if not force and last_checked == today and _has_cache:
            _TWEAKS_SESSION_CACHE[appid] = {
                "launch_args": cached_args, "file_ops": cached_file_ops,
                "screen_args": cached_screen_args, "widescreen_info": cached_widescreen_info,
            }
            GLib.idle_add(
                self._rebuild_tweaks_ui,
                appid, tweaks_box, cached_args, cached_file_ops, install_dir, editable,
                fetch_btn, api_row, cached_screen_args, cached_widescreen_info,
            )
            return

        # Step 1: resolve page name by Steam AppID
        page_name = None
        try:
            data = _pcgw_get(
                "https://www.pcgamingwiki.com/w/api.php?action=cargoquery"
                f"&tables=Infobox_game&fields=_pageName%3Dpage"
                f"&where=Steam_AppID+HOLDS+%22{appid}%22&format=json&limit=1"
            )
            results = data.get("cargoquery", [])
            if results:
                page_name = results[0]["title"]["page"]
        except Exception:
            pass

        all_args:           list = []
        all_file_ops:       list = []
        all_screen_args:    list = []
        all_widescreen_info: list = []
        fetched_ok = False

        if page_name:
            try:
                # Step 2: fetch the full page HTML in a single call
                hdata = _pcgw_get(
                    "https://www.pcgamingwiki.com/w/api.php?action=parse"
                    f"&page={urllib.parse.quote(page_name)}&prop=text&format=json"
                )
                html = hdata.get("parse", {}).get("text", {}).get("*", "")

                # CLI arg tables — all 3 PCGW formats (infotable-monospace, code, bold)
                all_args = _parse_pcgw_args_html(html)

                # Fixbox inline args (e.g. Cyberpunk Essential improvements)
                existing = {a["arg"] for a in all_args}
                for a in _parse_pcgw_fixbox_inline_args(html):
                    if a["arg"] not in existing:
                        all_args.append(a)
                        existing.add(a["arg"])

                # Move resolution/screen args out of all_args → all_screen_args so that
                # all 3 table formats feed the "Screen & Resolution" section, not "Game Tweaks"
                _other_args = []
                for a in all_args:
                    if _is_resolution_arg(a["arg"]) or _is_screen_arg(a["arg"]):
                        all_screen_args.append(a)
                    else:
                        _other_args.append(a)
                all_args = _other_args

                # File-deletion fixboxes (whole page, all sections)
                all_file_ops = _parse_pcgw_fixbox_files(html)

                # Screen/resolution args from notes, Video settings table and fixbox bodies
                # — adds any not yet found by the table parsers above
                existing_screen = {a["arg"].split()[0] for a in all_screen_args}
                for a in _parse_pcgw_screen_resolution_html(html):
                    if a["arg"].split()[0] not in existing_screen:
                        all_screen_args.append(a)
                        existing_screen.add(a["arg"].split()[0])

                # Widescreen / 4K / ultrawide support status from the Video settings table
                all_widescreen_info = _parse_pcgw_widescreen_html(html)

                fetched_ok = True
            except Exception:
                pass

        if fetched_ok and (all_args or all_file_ops or all_screen_args or all_widescreen_info):
            new_content = {
                "launch_args": all_args, "file_ops": all_file_ops,
                "screen_args": all_screen_args, "widescreen_info": all_widescreen_info,
            }
            old_content = {
                "launch_args": cached_args, "file_ops": cached_file_ops,
                "screen_args": cached_screen_args, "widescreen_info": cached_widescreen_info,
            }
            try:
                GAMES_DIR.mkdir(parents=True, exist_ok=True)
                if new_content != old_content:
                    cache_path.write_text(
                        json.dumps({**new_content, "last_checked": today.isoformat()}, indent=2)
                    )
                else:
                    try:
                        existing = json.loads(cache_path.read_text())
                    except Exception:
                        existing = dict(new_content)
                    existing["last_checked"] = today.isoformat()
                    cache_path.write_text(json.dumps(existing, indent=2))
            except Exception:
                pass
            _TWEAKS_SESSION_CACHE[appid] = new_content
        elif cached_args or cached_file_ops or cached_screen_args or cached_widescreen_info:
            # API returned nothing useful — fall back to file cache, do not update it
            all_args            = cached_args
            all_file_ops        = cached_file_ops
            all_screen_args     = cached_screen_args
            all_widescreen_info = cached_widescreen_info
            _TWEAKS_SESSION_CACHE[appid] = {
                "launch_args": all_args, "file_ops": all_file_ops,
                "screen_args": all_screen_args, "widescreen_info": all_widescreen_info,
            }

        GLib.idle_add(
            self._rebuild_tweaks_ui,
            appid, tweaks_box, all_args, all_file_ops, install_dir, editable,
            fetch_btn, api_row, all_screen_args, all_widescreen_info,
        )

    def _finalize_tweaks_widgets(self, fetch_btn, api_row, appid):
        """Re-enable the Fetch API button and update the last-fetched date label."""
        if fetch_btn is not None:
            fetch_btn.set_sensitive(True)
        if api_row is not None:
            _cp = GAMES_DIR / f"{appid}-tweaks-cache.json"
            try:
                _lc = json.loads(_cp.read_text()).get("last_checked", "")
                if _lc:
                    api_row.set_subtitle(f"Last fetched: {_lc}")
            except Exception:
                pass

    def _rebuild_tweaks_ui(self, appid, tweaks_box, launch_args, file_ops, install_dir, editable, fetch_btn=None, api_row=None, screen_args=None, widescreen_info=None):
        """Main-thread callback: replace the loading label with actual tweak widgets."""
        # Guard: widget removed (user switched game before fetch completed)
        if tweaks_box.get_parent() is None:
            return False
        if self.selected_appid != appid:
            return False

        # Clear placeholder
        child = tweaks_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            tweaks_box.remove(child)
            child = nxt

        if not launch_args and not file_ops and not screen_args and not widescreen_info:
            no_tweaks = Gtk.Label(label="No command-line tweaks are documented for this game on PCGamingWiki.")
            no_tweaks.set_xalign(0)
            no_tweaks.add_css_class("dim-label")
            no_tweaks.set_margin_top(4)
            tweaks_box.append(no_tweaks)
            self._finalize_tweaks_widgets(fetch_btn, api_row, appid)
            return False

        # Launch argument toggles
        if launch_args:
            args_grp = Adw.PreferencesGroup()
            args_grp.set_description("Selected arguments are appended to the game launch command.")
            args_grp.set_sensitive(editable)
            tweaks_box.append(args_grp)

            active_args = self.s.get("game_tweak_args", [])
            # Build a lookup: base flag → stored value (e.g. "-width" → "1920")
            stored_vals: dict = {}
            for stored in active_args:
                parts = stored.split(None, 1)
                if len(parts) == 2:
                    stored_vals[parts[0]] = parts[1]

            for entry in launch_args:
                flag = entry["arg"].split()[0]  # first token, e.g. "-width"

                if _is_resolution_arg(entry["arg"]) or _is_fps_arg(entry["arg"]):
                    # Resolution arg: ActionRow with an inline text entry for the value
                    row = Adw.ActionRow(title=entry["label"], subtitle=entry["desc"])
                    txt = Gtk.Entry(valign=Gtk.Align.CENTER, width_chars=6,
                                    placeholder_text="value")
                    txt.set_text(stored_vals.get(flag, ""))
                    txt.set_input_purpose(Gtk.InputPurpose.DIGITS)

                    def _on_res_changed(e, f=flag):
                        val = e.get_text().strip()
                        cur = [a for a in self.s.get("game_tweak_args", [])
                               if a.split()[0] != f]
                        if val:
                            cur.append(f"{f} {val}")
                        self._set("game_tweak_args", sorted(cur))

                    txt.connect("changed", _on_res_changed)
                    row.add_suffix(txt)
                else:
                    # Boolean toggle arg: SwitchRow
                    row = Adw.SwitchRow(title=entry["label"], subtitle=entry["desc"])
                    row.set_active(entry["arg"] in active_args)

                    def _on_arg_toggled(sw, _, arg=entry["arg"]):
                        cur = list(self.s.get("game_tweak_args", []))
                        if sw.get_active():
                            if arg not in cur:
                                cur.append(arg)
                        else:
                            cur = [a for a in cur if a != arg]
                        self._set("game_tweak_args", sorted(cur))

                    row.connect("notify::active", _on_arg_toggled)

                args_grp.add(row)

        # File operation buttons
        if file_ops:
            ops_grp = Adw.PreferencesGroup()
            ops_grp.set_sensitive(editable)
            tweaks_box.append(ops_grp)

            for op in file_ops:
                op_row = Adw.ActionRow(title=op["label"], subtitle=op["desc"])
                del_btn = Gtk.Button(label="Delete Files", valign=Gtk.Align.CENTER)
                del_btn.add_css_class("destructive-action")
                del_btn.connect("clicked", lambda _, o=op, d=install_dir: self._on_delete_game_files(o, d))
                op_row.add_suffix(del_btn)
                ops_grp.add(op_row)

        # Screen & Resolution options
        if screen_args:
            screen_grp = Adw.PreferencesGroup()
            screen_grp.set_title("Screen & Resolution")
            screen_grp.set_description("Screen mode and resolution arguments appended to the launch command.")
            screen_grp.set_sensitive(editable)
            tweaks_box.append(screen_grp)

            active_args  = self.s.get("game_tweak_args", [])
            stored_vals2: dict = {}
            for stored in active_args:
                if '=' in stored.lstrip('-+/'):
                    # -flag=value format (e.g. "-resx=1920")
                    idx = stored.index('=')
                    stored_vals2[stored[:idx + 1]] = stored[idx + 1:]
                else:
                    parts = stored.split(None, 1)
                    if len(parts) == 2:
                        stored_vals2[parts[0]] = parts[1]

            for entry in screen_args:
                flag = entry["arg"].split()[0]
                if _is_resolution_arg(entry["arg"]):
                    row = Adw.ActionRow(title=entry["label"], subtitle=entry["desc"])
                    txt = Gtk.Entry(valign=Gtk.Align.CENTER, width_chars=6, placeholder_text="value")
                    txt.set_text(stored_vals2.get(flag, ""))
                    txt.set_input_purpose(Gtk.InputPurpose.DIGITS)

                    def _on_screen_res_changed(e, f=flag):
                        val = e.get_text().strip()
                        if f.endswith('='):
                            # -flag=value: filter by prefix, append without space
                            cur = [a for a in self.s.get("game_tweak_args", [])
                                   if not a.startswith(f)]
                            if val:
                                cur.append(f"{f}{val}")
                        else:
                            # -flag value: filter by first token, append with space
                            cur = [a for a in self.s.get("game_tweak_args", [])
                                   if a.split()[0] != f]
                            if val:
                                cur.append(f"{f} {val}")
                        self._set("game_tweak_args", sorted(cur))

                    txt.connect("changed", _on_screen_res_changed)
                    row.add_suffix(txt)
                else:
                    row = Adw.SwitchRow(title=entry["label"], subtitle=entry["desc"])
                    row.set_active(entry["arg"] in active_args)

                    def _on_screen_toggled(sw, _, arg=entry["arg"]):
                        cur = list(self.s.get("game_tweak_args", []))
                        if sw.get_active():
                            if arg not in cur:
                                cur.append(arg)
                        else:
                            cur = [a for a in cur if a != arg]
                        self._set("game_tweak_args", sorted(cur))

                    row.connect("notify::active", _on_screen_toggled)
                screen_grp.add(row)

        # Widescreen resolution info (read-only status rows)
        if widescreen_info:
            ws_grp = Adw.PreferencesGroup()
            ws_grp.set_title("Widescreen Resolution")
            ws_grp.set_description("Resolution support status sourced from PCGamingWiki.")
            tweaks_box.append(ws_grp)

            for entry in widescreen_info:
                row = Adw.ActionRow(
                    title=entry["label"],
                    subtitle=entry.get("note", "") or "",
                )
                status_lbl = Gtk.Label(label=entry["status"], valign=Gtk.Align.CENTER)
                status_lbl.add_css_class(entry["css"])
                row.add_suffix(status_lbl)
                ws_grp.add(row)

        self._finalize_tweaks_widgets(fetch_btn, api_row, appid)
        return False

    def _open_pcgw_page(self, btn):
        btn.set_sensitive(False)
        btn.set_label("Loading…")
        appid = self.selected_appid
        name  = self.selected_name

        def fetch():
            try:
                data = _pcgw_get(
                    "https://www.pcgamingwiki.com/w/api.php?action=cargoquery"
                    f"&tables=Infobox_game&fields=_pageName%3Dpage"
                    f"&where=Steam_AppID+HOLDS+%22{appid}%22&format=json&limit=1"
                )
                results = data.get("cargoquery", [])
                if results:
                    page = results[0]["title"]["page"]
                    url = "https://www.pcgamingwiki.com/wiki/" + urllib.parse.quote(page.replace(" ", "_"))
                else:
                    url = "https://www.pcgamingwiki.com/w/index.php?search=" + urllib.parse.quote(name)
            except Exception:
                url = "https://www.pcgamingwiki.com/w/index.php?search=" + urllib.parse.quote(name)

            def _open():
                subprocess.Popen(["xdg-open", url])
                btn.set_label("Open Page")
                btn.set_sensitive(True)
            GLib.idle_add(_open)

        threading.Thread(target=fetch, daemon=True).start()

    def _on_delete_game_files(self, op, install_dir):
        def confirm_cb(_, response):
            if response != "delete":
                return
            deleted = 0
            for pattern in op.get("globs", []):
                for f in Path(install_dir).glob(pattern):
                    try:
                        f.unlink()
                        deleted += 1
                    except Exception:
                        pass
            self._set_status(f"Deleted {deleted} file(s).")

        dlg = Adw.MessageDialog(
            transient_for=self,
            heading="Delete Files",
            body=op["confirm"],
        )
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("delete", "Delete")
        dlg.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        dlg.connect("response", confirm_cb)
        dlg.present()

    def _on_companion_autowrap_changed(self, sw, _):
        self.companion_autowrap = sw.get_active()
        self._do_write()

    def _on_companion_autostart_changed(self, sw, _):
        self.companion_autostart = sw.get_active()
        self._do_write()

    def _on_companion_delay_changed(self, entry):
        text = entry.get_text().strip()
        try:
            self.companion_delay = max(0, int(text)) if text else 30
        except ValueError:
            self.companion_delay = 30
        self._do_write()

    def _on_companion_exec_changed(self, entry):
        self.companion_exec = entry.get_text()
        self._do_write()

    def _on_companion_env_changed(self, buf):
        self.companion_env = self._get_buf(buf)
        self._do_write()

    def _on_companion_browse(self, _):
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Custom App Executable")
        dialog.open(self, None, self._companion_browse_done)

    def _companion_browse_done(self, dialog, result):
        try:
            f = dialog.open_finish(result)
            if f:
                path = f.get_path()
                cmd = f"wine {shlex.quote(path)}" if path.lower().endswith(".exe") else shlex.quote(path)
                self._companion_entry.set_text(cmd)
        except Exception:
            pass

    def _find_running_proton_wine(self, prefix: Path):
        """Scan /proc for a wine process already using *prefix*.
        Returns (wine_binary_path, label, env_dict) or (None, "", None).
        env_dict is the full environment of the matched process — use it as the
        base when launching a companion so it joins the existing wineserver."""
        prefix_str = str(prefix.resolve()).rstrip("/")
        for pid_dir in Path("/proc").iterdir():
            if not pid_dir.name.isdigit():
                continue
            try:
                env_raw = (pid_dir / "environ").read_bytes()
                raw_env = {}
                for part in env_raw.split(b"\x00"):
                    if b"=" in part:
                        k, v = part.split(b"=", 1)
                        raw_env[k] = v
                wp = raw_env.get(b"WINEPREFIX", b"").decode(errors="replace").rstrip("/")
                if not wp:
                    continue
                if str(Path(wp).resolve()).rstrip("/") != prefix_str:
                    continue
                exe = Path(os.readlink(f"/proc/{pid_dir.name}/exe"))
                if "wine" not in exe.name.lower():
                    continue
                wine = exe.parent / "wine"
                if wine.exists():
                    try:
                        label = exe.parent.parent.parent.name
                    except Exception:
                        label = exe.parent.name
                    env_dict = {
                        k.decode(errors="replace"): v.decode(errors="replace")
                        for k, v in raw_env.items()
                    }
                    return wine.resolve(), label, env_dict
            except (PermissionError, FileNotFoundError, ValueError, OSError):
                continue
        return None, "", None

    def _on_companion_autofill(self, _):
        appid = self.selected_appid
        if not appid:
            return

        # Search ALL Steam library dirs (reads libraryfolders.vdf)
        prefix = None
        for steamapps in _steam_library_dirs():
            candidate = steamapps / "compatdata" / appid / "pfx"
            if candidate.exists():
                prefix = candidate
                break

        if not prefix:
            self._set_status(
                f"No Proton prefix found for AppID {appid} – "
                "make sure the game was launched at least once"
            )
            return

        prefix = prefix.resolve()

        # Prefer the wine binary from the RUNNING game (guarantees version match).
        # Fall back to newest installed Proton when no game is active.
        wine_bin, wine_label, _ = self._find_running_proton_wine(prefix)
        if wine_bin:
            wine_label = f"{wine_label} (running – version matched)"
        else:
            steam_roots = {sa.parent for sa in _steam_library_dirs()}
            for root in steam_roots:
                for search in (root / "compatibilitytools.d", root / "steamapps" / "common"):
                    if not search.exists():
                        continue
                    candidates = sorted(
                        [d for d in search.iterdir()
                         if (d / "files" / "bin" / "wine").exists()],
                        reverse=True,
                    )
                    if candidates:
                        wine_bin  = (candidates[0] / "files" / "bin" / "wine").resolve()
                        wine_label = candidates[0].name + " (game not running)"
                        break
                if wine_bin:
                    break

        # Update env textarea: replace/add WINEPREFIX
        existing_lines = [
            l for l in self.companion_env.strip().splitlines()
            if not l.strip().startswith("WINEPREFIX=")
        ]
        existing_lines.append(f"WINEPREFIX={prefix}")
        self._companion_buf.set_text("\n".join(existing_lines))

        # Update command: replace leading "wine " with Proton's wine binary (quoted if path has spaces)
        if wine_bin:
            wine_str = f'"{wine_bin}"' if " " in str(wine_bin) else str(wine_bin)
            current_cmd = self._companion_entry.get_text().strip()
            if current_cmd.startswith("wine "):
                self._companion_entry.set_text(f"{wine_str} {current_cmd[5:]}")
            elif not current_cmd:
                pass  # leave empty, user hasn't set a command yet

        msg = f"Prefix: …/compatdata/{appid}/pfx"
        if wine_bin:
            msg += f"  |  Wine: {wine_label}"
        else:
            msg += "  |  No Proton wine found – update command manually"
        self._set_status(msg)

    def _toggle_companion(self, _):
        if self._companion_proc and self._companion_proc.poll() is None:
            try:
                os.killpg(os.getpgid(self._companion_proc.pid), signal.SIGTERM)
            except Exception:
                self._companion_proc.terminate()
            self._companion_proc = None
            self._update_companion_btn()
            self._set_status("Custom app stopped")
        else:
            cmd = self.companion_exec.strip()
            if not cmd:
                self._set_status("No command set – enter a command first")
                return

            try:
                parts = shlex.split(cmd)
            except ValueError as e:
                self._set_status(f"Bad command syntax: {e}")
                return
            if not parts:
                self._set_status("No command set – enter a command first")
                return

            # Parse companion_env to extract vars and WINEPREFIX
            companion_vars = {}
            prefix = None
            for line in self.companion_env.strip().splitlines():
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    var, val = line.split("=", 1)
                    companion_vars[var.strip()] = val.strip()
                    if var.strip() == "WINEPREFIX":
                        prefix = Path(val.strip())

            # Match the running game's exact wine binary so Aurora connects to
            # the existing wineserver (version mismatch causes a silent hang).
            wine_info = ""
            live_wine = None
            game_env = None
            if prefix:
                live_wine, label, game_env = self._find_running_proton_wine(prefix)
                if live_wine and "wine" in Path(parts[0]).name.lower():
                    parts[0] = str(live_wine)
                    wine_info = f" – {label} matched"
                elif not live_wine:
                    wine_info = " – game not running, version unmatched"

            # Use game's Proton env (has DXVK LD_LIBRARY_PATH) but strip LD_PRELOAD:
            # Steam overlay .so files crash wine launched outside Pressure Vessel.
            if game_env:
                env = {k: v for k, v in game_env.items() if k != "LD_PRELOAD"}
            else:
                env = os.environ.copy()
            env.update(companion_vars)

            try:
                self._companion_proc = subprocess.Popen(
                    parts, shell=False, env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    preexec_fn=os.setsid
                )
                self._update_companion_btn()
                self._set_status(f"Custom app launched{wine_info}")
                GLib.timeout_add(1000, self._poll_companion)
            except Exception as e:
                self._set_status(f"Launch failed: {e}")

    def _poll_companion(self):
        if self._companion_proc and self._companion_proc.poll() is not None:
            rc = self._companion_proc.returncode
            try:
                out = self._companion_proc.stdout.read(4096).decode(errors="replace").strip()
            except Exception:
                out = ""
            self._companion_proc = None
            self._update_companion_btn()
            if rc is not None and rc < 0:
                try:
                    sig_name = signal.Signals(-rc).name
                except (ValueError, AttributeError):
                    sig_name = str(-rc)
                self._set_status(f"Custom app killed by signal {sig_name}")
            elif self.companion_autowrap and (out or rc != 0):
                self._show_companion_crash(out, rc)
            else:
                self._set_status(f"Custom app exited (code {rc})")
            return False
        return self._companion_proc is not None

    def _show_companion_crash(self, text, rc):
        heading = "Custom App Crashed" if rc != 0 else "Custom App Output"
        body = f"Exit code: {rc}"
        if text:
            body += f"\n\n{text[:1200]}"
        dialog = Adw.MessageDialog(transient_for=self, heading=heading)
        dialog.set_body(body)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present()

    def _update_companion_btn(self):
        btn = self._companion_launch_btn
        if btn is None:
            return
        running = self._companion_proc and self._companion_proc.poll() is None
        btn.set_label("■  Kill App" if running else "▶  Launch App")
        if running:
            btn.remove_css_class("suggested-action")
            btn.add_css_class("destructive-action")
        else:
            btn.remove_css_class("destructive-action")
            btn.add_css_class("suggested-action")

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _mkpos(self, pos):
        """Factory: return a clicked-callback for a HUD position button."""
        def cb(btn):
            self.s["position"] = pos
            for p,b in self._pos_btns.items():
                if p==pos: b.add_css_class("suggested-action")
                else:      b.remove_css_class("suggested-action")
            self._do_write()
        return cb

    def _mkfps(self, preset):
        """Factory: return a clicked-callback for an FPS preset button."""
        def cb(btn):
            self.s["fps_limit"] = preset
            for p,b in self._fps_preset_btns.items():
                if p==preset: b.add_css_class("suggested-action")
                else:         b.remove_css_class("suggested-action")
            self.fps_entry.set_text("")
            self._do_write()
        return cb

    def _on_fps_entry(self, entry):
        txt = entry.get_text().strip()
        if txt.isdigit():
            self.s["fps_limit"] = int(txt)
            for b in self._fps_preset_btns.values(): b.remove_css_class("suggested-action")
            self._do_write()

    def _mkproton(self, key, conflicts):
        """Factory: return a notify::active callback for a Proton tweak switch."""
        def cb(sw, _):
            active = sw.get_active()
            if active:
                # Block activation if a conflicting key is already active
                blocking = [c for c in CONFLICT_MAP.get(key,[]) if c in self.proton_active]
                if blocking:
                    sw.handler_block_by_func(cb)
                    sw.set_active(False)
                    sw.handler_unblock_by_func(cb)
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
                        s2 = self._proton_switches.get(auto)
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
                        s2 = self._proton_switches.get(auto)
                        cb2 = self._proton_callbacks.get(auto)
                        if s2 and cb2:
                            s2.handler_block_by_func(cb2)
                            s2.set_active(False)
                            s2.handler_unblock_by_func(cb2)
            self._do_write()
        return cb

    def _on_proton_custom(self, buf):
        self.proton_custom = self._get_buf(buf)
        self._do_write()

    # ── vkcube preview ────────────────────────────────────────────────────────

    def _set_vkcube_btn_state(self, running: bool):
        if running:
            self._vkcube_img.set_from_icon_name("media-playback-stop-symbolic")
            self._vkcube_lbl.set_label("Stop Preview")
        else:
            if _LOGO_PATH:
                self._vkcube_img.set_from_file(_LOGO_PATH)
            else:
                self._vkcube_img.set_from_icon_name("io.gubernator")
            self._vkcube_lbl.set_label("Preview (vkcube)")

    def _toggle_vkcube(self, btn):
        if self._vkcube_proc and self._vkcube_proc.poll() is None:
            try: os.killpg(os.getpgid(self._vkcube_proc.pid), signal.SIGTERM)
            except: self._vkcube_proc.terminate()
            self._vkcube_proc = None
            self._set_vkcube_btn_state(False)
            self._set_status("Preview closed")
        else:
            env = os.environ.copy()
            env["MANGOHUD"]="1"; env["MANGOHUD_CONFIGFILE"]=str(CONFIG_FILE)
            try:
                self._vkcube_proc = subprocess.Popen(["vkcube"],env=env,
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,preexec_fn=os.setsid)
                self._set_vkcube_btn_state(True)
                self._set_status("vkcube running with MangoHud")
                GLib.timeout_add(1000, self._poll_vkcube)
            except FileNotFoundError:
                self._set_status("vkcube not found – install vulkan-tools")

    def _poll_vkcube(self):
        if self._vkcube_proc and self._vkcube_proc.poll() is not None:
            self._vkcube_proc = None
            self._set_vkcube_btn_state(False)
            return False
        return self._vkcube_proc is not None

    def _on_close(self, _):
        if self._vkcube_proc and self._vkcube_proc.poll() is None:
            try: os.killpg(os.getpgid(self._vkcube_proc.pid), signal.SIGTERM)
            except: self._vkcube_proc.terminate()
        if self._companion_proc and self._companion_proc.poll() is None:
            try: os.killpg(os.getpgid(self._companion_proc.pid), signal.SIGTERM)
            except: self._companion_proc.terminate()
        return False

    # ── Save & apply ──────────────────────────────────────────────────────────

    def _get_buf(self, buf):
        return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)

    def _do_write(self):
        """Persist the current state and update config files / previews."""
        self.s["proton_active"] = list(self.proton_active)
        self.s["proton_custom"] = self.proton_custom
        mango_text = build_conf(self.s)

        if self.selected_appid is None:
            # Global – write MangoHud.conf and the shared wrapper script
            self.s["mangohud_disabled"] = self.mangohud_disabled
            save_settings(self.s)
            write_conf(mango_text)
            write_wrapper(self.proton_active, self.proton_custom, mangohud_disabled=self.mangohud_disabled)
            script_path = WRAPPER_SCRIPT
        elif self.use_custom:
            # Per-game – write game-specific JSON, MangoHud conf, and env file
            game_state = dict(self.s)
            game_state["use_custom"]           = True
            game_state["companion_exec"]       = self.companion_exec
            game_state["companion_env"]        = self.companion_env
            game_state["companion_autowrap"]   = self.companion_autowrap
            game_state["companion_autostart"]  = self.companion_autostart
            game_state["companion_delay"]      = self.companion_delay
            save_game_settings(self.selected_appid, game_state)
            GAMES_DIR.mkdir(parents=True, exist_ok=True)
            (GAMES_DIR / f"{self.selected_appid}.conf").write_text(mango_text)
            _gs = load_settings()
            write_game_env(
                self.selected_appid, self.proton_active, self.proton_custom,
                set(_gs.get("proton_active", [])), _gs.get("proton_custom", ""),
                mangohud_disabled=self.mangohud_disabled,
            )
            save_nomangohud(self.selected_appid, self.mangohud_disabled)
            save_game_tweak_args(self.selected_appid, self.s.get("game_tweak_args", []))
            companion_script = GAMES_DIR / f"{self.selected_appid}-companion.sh"
            if self.companion_autostart and self.companion_exec.strip():
                write_companion_script(
                    self.selected_appid, self.companion_exec,
                    self.companion_env, self.companion_delay,
                )
            elif companion_script.exists():
                companion_script.unlink()
            script_path = WRAPPER_SCRIPT
        else:
            # Game with custom disabled – show global conf as preview only
            mango_text  = build_conf(load_settings())
            script_path = WRAPPER_SCRIPT

        self.conf_preview.set_label(mango_text)
        if script_path.exists():
            self.script_preview.set_label(script_path.read_text())
        self._set_status(_save_label())

    def _copy_cmd(self, cmd):
        self.get_display().get_clipboard().set(cmd)
        self._set_status("Command copied!")

    def _set_status(self, msg):
        self.status_lbl.set_label(msg)
        GLib.timeout_add(2500, lambda: self.status_lbl.set_label("") or False)




if __name__ == "__main__":
    Gubernator().run()
