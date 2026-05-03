# VR-Head-Tracking-GUI
A configuration manager and launcher for the ofisare/VRCompanion VR head-tracking scripts.
Features

Three configurable profiles in one interface

Mouse Emulation (head movement → mouse cursor)
Joystick Emulation (head movement → virtual gamepad)
6DOF Head Tracking Mod (UDP stream to OpenTrack-compatible games, e.g. itsloopyo/resident-evil-requiem-headtracking)


Live config editing with sliders, toggles, and inputs

Sensitivity, deadzone, output scale, max angle
Per-axis gains (Yaw / Pitch / Roll / X / Y / Z) for 6DOF
IP address and port for UDP streaming
Recenter delay
Curve options (linear / non-linear, with disable toggle)


One-click Start / Stop for each profile

Launches FreePIE.Console.exe directly (no terminal windows)
Reliable process tracking — Stop kills exactly what Start spawned


Global hotkeys to toggle tracking on/off

Per-section hotkey assignment with click-to-capture
Works system-wide, even when GUI is minimized or hidden (perfect for VR)
Supports modifiers (Ctrl/Shift/Alt), function keys, numpad, punctuation, and more
Bindings persist in hotkeys.json


Three UI themes, switchable on the fly

Color (default — red/blue/purple accents)
Dark (flat black with blue hover accents)
Light (white/grey with cyan hover accents)
Optional color.png / dark.png / light.png banner images for the header


Two layout modes

Vertical (sections stacked) — default
Horizontal (sections side-by-side)


Quality-of-life touches

System tray icon with minimize-to-tray (close button still quits)
Auto-elevates to admin (required by FreePIE)
USB-style audible feedback on tracking start / stop
Resizable window, geometry + theme + layout persisted across launches



Requirements

Windows 10/11
Python 3.8+
VRCompanion installed with FreePIE.Console.exe accessible

Run the included Install_Requirements.bat once — it auto-installs Python (if missing) and the two required pip packages (pystray, Pillow).

<img width="1326" height="935" alt="2 (1)" src="https://github.com/user-attachments/assets/3811696e-da89-4495-a4c8-672a4a4cc644" />
<img width="1341" height="932" alt="2 (2)" src="https://github.com/user-attachments/assets/4ab2596a-5da3-40d5-957d-ee8598494044" />
<img width="1343" height="932" alt="2 (3)" src="https://github.com/user-attachments/assets/d274ef6b-4101-4798-a990-0b576faf6a75" />


1- run Install_Requirements.bat to install python and requirements
2- install free pie and vr companion https://github.com/Ofisare/VRCompanion
3-copy the contents of the pack to the vr companion directory
4- install 6dof mods for games https://github.com/itsloopyo?tab=repositories
5- run VR_Head-Tracking_GUI.pyw , setup settings and setup hotkeys to start tracking
