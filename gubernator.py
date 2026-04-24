#!/usr/bin/env python3
"""
Gubernator – One command, full control
Arch Linux / GTK4 + libadwaita

Dependencies:
  sudo pacman -S python-gobject gtk4 libadwaita vulkan-tools
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
import subprocess, signal, os, json, shlex

# ── Paths ─────────────────────────────────────────────────────────────────────
CONFIG_DIR     = Path.home() / ".config" / "MangoHud"
CONFIG_FILE    = CONFIG_DIR / "MangoHud.conf"
GUBERNATOR_DIR   = Path.home() / ".config" / "gubernator"
WRAPPER_SCRIPT = GUBERNATOR_DIR / "gubr-launch"
SETTINGS_FILE  = GUBERNATOR_DIR / "settings.json"
GAMES_DIR      = GUBERNATOR_DIR / "games"          # per-game settings / wrappers
STEAM_COMMAND  = f"{WRAPPER_SCRIPT} %command%"

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
    ("PROTON_ENABLE_HDR=1","Proton HDR","HDR via Proton. Requires Wayland + HDR display",[]),
    ("ENABLE_HDR_WSI=1","HDR WSI","Vulkan WSI HDR layer (gamescope / KDE 6)",[]),
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
    """Return sorted list of (appid, name) tuples for all installed Steam games."""
    games = []
    seen  = set()
    for steamapps in _steam_library_dirs():
        for acf in steamapps.glob("appmanifest_*.acf"):
            try:
                content = acf.read_text(errors="replace")
                appid   = _acf_value(content, "appid")
                name    = _acf_value(content, "name")
                if appid and name and appid not in seen:
                    seen.add(appid)
                    games.append((appid, name))
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

def write_wrapper(proton_active: set, custom_vars: str):
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
    active_vars = _env_vars(proton_active, custom_vars)
    if active_vars:
        lines.append("# Global Proton tweaks")
        for var, val in active_vars:
            lines.append(f'export {var}="{val}"')
        lines.append("")
    lines += [
        "# Per-game Proton overrides (sourced when custom settings are enabled)",
        f'GAME_ENV="{GAMES_DIR}/${{SteamAppId}}.env"',
        'if [ -n "$SteamAppId" ] && [ -f "$GAME_ENV" ]; then',
        '    set -a; source "$GAME_ENV"; set +a',
        "fi",
        "",
        "# Auto-launch companion if configured for this game",
        f'_GC_COMPANION="{GAMES_DIR}/${{SteamAppId}}-companion.sh"',
        'if [ -n "$SteamAppId" ] && [ -f "$_GC_COMPANION" ]; then',
        '    "$@" &',
        '    _GC_GAME_PID=$!',
        "    _GC_DELAY=$(grep -m1 \"COMPANION_DELAY=\" \"$_GC_COMPANION\" 2>/dev/null | tr -dc '0-9')",
        '    sleep "${_GC_DELAY:-5}"',
        '    bash "$_GC_COMPANION" &',
        '    _GC_COMPANION_PID=$!',
        '    wait "$_GC_GAME_PID"',
        '    kill -TERM "$_GC_COMPANION_PID" 2>/dev/null',
        'else',
        '    exec "$@"',
        'fi',
        "",
    ]
    WRAPPER_SCRIPT.write_text("\n".join(lines))
    WRAPPER_SCRIPT.chmod(0o755)

def write_game_env(appid: str, proton_active: set, custom_vars: str,
                   global_active: set = None, global_custom_vars: str = ""):
    """Write per-game Proton tweaks to <appid>.env, sourced by the global wrapper.

    Variables that global sets but this game leaves unchecked are written as
    `unset VAR` so the global export doesn't bleed through.
    """
    GAMES_DIR.mkdir(parents=True, exist_ok=True)
    active_vars = _env_vars(proton_active, custom_vars)
    per_game_var_names = {var for var, _ in active_vars}

    # Any var exported globally but absent in per-game settings must be unset
    global_vars = _env_vars(global_active or set(), global_custom_vars)
    to_unset = sorted({var for var, _ in global_vars if var not in per_game_var_names})

    lines = [f"# Gubernator per-game env for AppID {appid} – auto-generated", ""]
    for var, val in active_vars:
        lines.append(f'export {var}="{val}"')
    if to_unset:
        if active_vars:
            lines.append("")
        lines.append("# Disable global tweaks not active for this game")
        for var in to_unset:
            lines.append(f"unset {var}")
    if not active_vars and not to_unset:
        lines.append("# No custom Proton tweaks for this game")
    (GAMES_DIR / f"{appid}.env").write_text("\n".join(lines) + "\n")


def write_companion_script(appid: str, exec_cmd: str, env_vars: str):
    """Generate per-game companion launcher script used by the global wrapper."""
    GAMES_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["#!/usr/bin/env bash", f"# gubernator companion for AppID {appid} – auto-generated", ""]
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


# ── Sidebar game row widget ───────────────────────────────────────────────────

class GameRow(Gtk.ListBoxRow):
    """A ListBoxRow representing either "Global / Default" (appid=None) or a Steam game."""

    def __init__(self, appid, name):
        super().__init__()
        self.appid     = appid
        self.game_name = name

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
        self._current_tab   = 0              # remember active tab across rebuilds

        # ── Initial settings load ─────────────────────────────────────────────
        self.s             = load_settings()
        self.proton_active = set(self.s.get("proton_active", []))
        self.proton_custom = self.s.get("proton_custom", "")
        self.companion_exec     = ""
        self.companion_env      = ""
        self.companion_autowrap = False

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
        self.preview_btn = Gtk.Button(label="▶  Preview (vkcube)")
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

        # ── Filter state (created before rows are appended so _filter_games works) ──
        self._hide_proton_cb    = Gtk.CheckButton(label="Proton-versions")
        self._hide_slr_cb       = Gtk.CheckButton(label="Steam Linux Runtime")
        self._hide_steamworks_cb = Gtk.CheckButton(label="Steamworks")
        for cb in (self._hide_proton_cb, self._hide_slr_cb, self._hide_steamworks_cb):
            cb.set_active(True)
            cb.connect("toggled", lambda _: self._game_list.invalidate_filter())

        # ── Filter popover ────────────────────────────────────────────────────
        fp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                         margin_start=10, margin_end=10, margin_top=10, margin_bottom=10)
        fp_head = Gtk.Label(label="Hide entries")
        fp_head.set_xalign(0); fp_head.add_css_class("heading")
        fp_box.append(fp_head)
        fp_box.append(Gtk.Separator())
        for cb in (self._hide_proton_cb, self._hide_slr_cb, self._hide_steamworks_cb):
            fp_box.append(cb)
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
        for appid, name in read_steam_games():
            self._game_list.append(GameRow(appid, name))

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

        # Hide-filter rules
        for keyword, attr in self._HIDE_RULES:
            cb = getattr(self, attr, None)
            if cb and cb.get_active() and keyword in name_lower:
                return False

        # Search query
        query = self._search_entry.get_text().strip().lower()
        if not query:
            return True
        return query in name_lower or query in row.appid

    def _on_search_changed(self, _):
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
            self.use_custom    = True
            self.companion_exec     = ""
            self.companion_env      = ""
            self.companion_autowrap = False
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
            self.companion_exec     = (game_data or {}).get("companion_exec", "")
            self.companion_env      = (game_data or {}).get("companion_env", "")
            self.companion_autowrap = bool((game_data or {}).get("companion_autowrap", False))

        self._build_right_panel()

    # ── Right panel ───────────────────────────────────────────────────────────

    def _build_right_panel(self):
        """Clear and reconstruct the right side (title + toggle + notebook)."""
        # Remove all existing children
        child = self._right_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._right_box.remove(child)
            child = nxt

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
        nb = Gtk.Notebook(vexpand=True)
        nb.set_margin_start(8)
        nb.set_margin_end(8)
        nb.set_margin_bottom(8)
        nb.append_page(self._page_mango(),      Gtk.Label(label="MangoHud"))
        nb.append_page(self._page_proton(),     Gtk.Label(label="Proton-Tweaks"))
        nb.append_page(self._page_companion(),  Gtk.Label(label="Custom App"))

        # Dim all tabs when a game has no custom settings (showing global read-only)
        nb.set_sensitive((self.selected_appid is None) or self.use_custom)
        nb.set_current_page(self._current_tab)
        nb.connect("switch-page", lambda *a: setattr(self, "_current_tab", a[2]))
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
        else:
            save_game_settings(self.selected_appid, {"use_custom": False})
            self.s             = load_settings()
            self.proton_active = set(self.s.get("proton_active", []))
            self.proton_custom = self.s.get("proton_custom", "")
            self.companion_exec = ""
            self.companion_env  = ""

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

    def _on_companion_autowrap_changed(self, sw, _):
        self.companion_autowrap = sw.get_active()
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

    def _toggle_vkcube(self, btn):
        if self._vkcube_proc and self._vkcube_proc.poll() is None:
            try: os.killpg(os.getpgid(self._vkcube_proc.pid), signal.SIGTERM)
            except: self._vkcube_proc.terminate()
            self._vkcube_proc = None
            self.preview_btn.set_label("▶  Preview (vkcube)")
            self._set_status("Preview closed")
        else:
            env = os.environ.copy()
            env["MANGOHUD"]="1"; env["MANGOHUD_CONFIGFILE"]=str(CONFIG_FILE)
            try:
                self._vkcube_proc = subprocess.Popen(["vkcube"],env=env,
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,preexec_fn=os.setsid)
                self.preview_btn.set_label("■  Stop Preview")
                self._set_status("vkcube running with MangoHud")
                GLib.timeout_add(1000, self._poll_vkcube)
            except FileNotFoundError:
                self._set_status("vkcube not found – install vulkan-tools")

    def _poll_vkcube(self):
        if self._vkcube_proc and self._vkcube_proc.poll() is not None:
            self._vkcube_proc = None
            self.preview_btn.set_label("▶  Preview (vkcube)")
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
            save_settings(self.s)
            write_conf(mango_text)
            write_wrapper(self.proton_active, self.proton_custom)
            script_path = WRAPPER_SCRIPT
        elif self.use_custom:
            # Per-game – write game-specific JSON, MangoHud conf, and env file
            game_state = dict(self.s)
            game_state["use_custom"]          = True
            game_state["companion_exec"]      = self.companion_exec
            game_state["companion_env"]       = self.companion_env
            game_state["companion_autowrap"]  = self.companion_autowrap
            save_game_settings(self.selected_appid, game_state)
            GAMES_DIR.mkdir(parents=True, exist_ok=True)
            (GAMES_DIR / f"{self.selected_appid}.conf").write_text(mango_text)
            _gs = load_settings()
            write_game_env(
                self.selected_appid, self.proton_active, self.proton_custom,
                set(_gs.get("proton_active", [])), _gs.get("proton_custom", ""),
            )
            companion_script = GAMES_DIR / f"{self.selected_appid}-companion.sh"
            if companion_script.exists():
                companion_script.unlink()
            script_path = WRAPPER_SCRIPT
        else:
            # Game with custom disabled – show global conf as preview only
            mango_text  = build_conf(load_settings())
            script_path = WRAPPER_SCRIPT

        self.conf_preview.set_label(mango_text)
        if script_path.exists():
            self.script_preview.set_label(script_path.read_text())
        self._set_status("✓ saved")

    def _copy_cmd(self, cmd):
        self.get_display().get_clipboard().set(cmd)
        self._set_status("Command copied!")

    def _set_status(self, msg):
        self.status_lbl.set_label(msg)
        GLib.timeout_add(2500, lambda: self.status_lbl.set_label("") or False)


if __name__ == "__main__":
    Gubernator().run()
