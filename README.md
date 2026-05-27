# Gubernator
> One command, full control

![License](https://img.shields.io/badge/license-GPL%20v3-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey)

Gubernator is a game configurator for Linux. It manages MangoHud and Proton settings global or on a per-game basis, integrates custom applications into the game's Proton prefix and Wine server with isolated environment variables, it lets you manage all kind of stuff and all through a single Steam launch command.

---

- [Gubernator](#gubernator)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [Steam launch command](#steam-launch-command)
  - [CheatHappens Aurora](#cheathappens-aurora)
- [Project structure](#project-structure)
- [Images](#images)
  - [MangoHud](#mangohud)
  - [Proton-Tweaks](#proton-tweaks)
  - [Proton Manager](#proton-manager)
  - [Custom app](#custom-app)
  - [Engine](#engine)
  - [Reshade](#reshade)
  - [Saves](#saves)
  - [Filter](#filter)
  - [Steam Launch Command](#steam-launch-command)
- [Credits](#credits)
- [License](#license)
- [Etymology](#etymology)

---

## Features

- Global MangoHud and Proton settings
- Per-game MangoHud configuration
  - change MangoHud settings while the game is running
- Per-game Proton settings
- Applys settings automatic
- Filter to hide Steam Proton and Linux Runtimes
  - you can add custom fiter to hide Software (e.g. Blender, Lossless Scaling)
- Proton Manager
  - list of all installed custom Proton versions and shortcut to open Proton Plus and ProtonUp-Qt
- Custom app integration into game Proton prefix (e.g. CheatHappens Aurora)
  - Isolated Wine environment variables for the custom app that do not affect the game process
- Engine
  - shows the Engine for the game and adds useful settings (not for all engines)
- Reshade
- Saves lets you backup your save or migrate from Linux native to Proton
- Single Steam launch command for all games
> there are a lot more settings that you can't see in the [images](#images)
---

## Installation

Open the Therminal in the folder.

```
  chmod +x install.sh
  ./install.sh
```
---

## Usage

Open the UI from the app menu or search for gubr or Gubernator
- Make your settings
- add the copied launch command into steam launch options

Save & Apply button is for those ones who want to click it (like me)
> if you add a custom app like CheatHappens Aurora, you need to launch the game first



## Steam launch command
paste the copied command in the steam launch options

## CheatHappens Aurora
1. activate per-game custom settings
2. select Aurora.exe (Portable version)
3. launch the game
4. click on Auto-fill Proton Prefix
5. launch Aurora (custom app) search for the game and activate the trainer

### things i noticed
if you start Aurora first, the game won't start until you close Aurora

when you start Aurora without the game to make settings or so and Aurora is a white or black window, then start the game and Aurora should be fixed (~for me it fixt the black/white after a system reboot~ UPDATE: it is random in which games you can use Auroras UI without a running game)

if the GAME CRASHES after you activate the trainer its likely that the game runs on DXVK, fix for this is simply to deactivate the overlay in the trainer settings (after that it workt for me)

if Aurora downloads an update and fails to restart itself, open Aurora directly from where you saved it (not through the tool) and apply the update that way

---

## Project structure

Read [GUBERNATOR_DOCS.md](/GUBERNATOR_DOCS.md) for details

---
> [!NOTE]
> images are from version 1 and 2

## Images
### MangoHud
![V1](/img/gubr1.png)
### Proton-Tweaks
![V2](/img/gubr2-2.png)
### Proton Manager
![V2](/img/gubr6.png)
### Custom app
![V1](/img/gubr3.png)
### Engine
![V2](/img/gubr7.png)
![V2](/img/gubr9.png)
### Reshade
![V2](/img/gubr8.png)
### Saves
![V2](/img/gubr5.png)
### Filter
![V2](/img/gubr10.png)
### Steam Launch Command
![V1](/img/gubr4.png)

---

## Credits
[MangoHud](https://github.com/flightlessmango/MangoHud) MangoHud configs\
[fgmod](https://github.com/FakeMichau/fgmod) one command for all games\
[GOverlay](https://github.com/benjamimgois/goverlay) for the idea\
[Proton-GE](https://github.com/GloriousEggroll/proton-ge-custom) additional Proton configs\
[Proton Valve](https://github.com/ValveSoftware/Proton) Proton configs\
[CachyOS Wiki](https://wiki.cachyos.org/configuration/general_system_tweaks/) for nvidia Smooth Motion\
[vkd3d-proton](https://github.com/HansKristian-Work/vkd3d-proton) vkD3D configs\
[DXVK](https://github.com/doitsujin/dxvk) DXVK configs\
[kevinlekiller](https://github.com/kevinlekiller/reshade-steam-proton) Reshade Script\
[Vysp3r](https://github.com/Vysp3r/ProtonPlus) Proton Plus\
[DavidoTek](https://github.com/DavidoTek/ProtonUp-Qt) ProtonUp-Qt

more credits/sources are in [GUBERNATOR_DOCS.md](/GUBERNATOR_DOCS.md)

---

## License

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

---

## Etymology

The name *Gubernator* comes from the Latin *gubernare* (to steer), itself borrowed from the Greek *κυβερνάτης* (kybernátes) — the helmsman of a ship. Not the captain, not the crew, but the one who actively holds the course while everything else runs. The same Greek root gave us the word *cybernetics*.
