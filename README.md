# SR Watcher v2

SR Watcher is an automated shiny detection tool for static Pokémon encounters on real hardware, using a capture card feed and computer vision to detect shiny Pokémon and stop an automated hunt script running on a Raspberry Pi. It can be used for any static shiny encounter — it was developed and tested on a static Moltres hunt in Pokémon FireRed and LeafGreen on Nintendo Switch.

---

## What It Does

SR Watcher v2:

* Auto-launches OBS and starts the Virtual Camera
* Watches the capture card feed for a known battle screen
* When a battle is detected, compares the Pokémon sprite region against a saved reference image of the normal form
* If the live sprite differs enough from the reference, it flags a shiny detection
* Plays a sound alert when a shiny is detected
* SSHes into a connected Raspberry Pi to stop the automated hunt script
* Enters a sleep state after detection to prevent false re-triggers
* Can be re-armed at any time via the R key or the Options panel
* Closes automatically if OBS fails to launch

---

## What Changed from v1

v2 is a significant rewrite focused on automation rather than logging:

* Reset counting and cooldown timer have been removed — these are now handled by the Pi hunt script
* Shiny detection has been added using OpenCV image comparison
* OBS launch now exits the program if OBS is not found rather than continuing silently
* Pi SSH integration added to stop the hunt script on shiny detection
* Detection is now gated by battle screen recognition to prevent false positives on other screens
* Re-arm system added so the watcher can resume after a shiny alert without restarting

---

## Requirements

* Python 3.11
* OBS Studio installed at the default path
* OBS Virtual Camera
* A capture card
* A Raspberry Pi running the hunt script (see Pi Setup below)
* Python packages:
  * `opencv-python`
  * `numpy`
  * `pygame`
  * `pyinstaller` (only needed for building the EXE)

---

## Install Requirements

```
python -m pip install -r requirements.txt
```

---

## Reference Images

SR Watcher v2 requires two reference images in the project folder:

**battle-screen.jpg**
A screenshot of the full battle screen taken through OBS Virtual Camera. This is used to confirm the game is in a battle before running shiny detection. Crop out any OBS UI elements — just the game feed.

**normal-moltres.jpg** (or equivalent for your target Pokémon — name it whatever you like and update the filename in the config)
A screenshot of the Pokémon sprite region taken through OBS Virtual Camera during a normal (non-shiny) encounter. This is what the watcher compares against to detect a shiny. One reference image is needed per Pokémon you hunt.

Both images must be taken through your actual capture card feed — not raw sprites or emulator screenshots — so the colors and compression match what the watcher sees at runtime.

---

## Crop Region Configuration

The Moltres sprite crop region is configured at the top of `sr_watcher.py`:

```python
MOLTRES_CROP_X1 = 696
MOLTRES_CROP_Y1 = 64
MOLTRES_CROP_X2 = 1213
MOLTRES_CROP_Y2 = 376
```

These values are based on a 1280x726 output frame with the game feed centered. If your capture resolution or game position differs, update these coordinates to match the sprite region in your feed.

---

## Shiny Detection Threshold

The shiny detection threshold controls how different the live sprite needs to be from the reference before triggering an alert:

```python
SHINY_DETECTION_THRESHOLD = 55.0
```

To tune this value:
1. Enable debug mode from the Options panel
2. Get into a normal (non-shiny) encounter with your target Pokémon
3. Note the score shown in the debug panel
4. Set the threshold to roughly 10 points above that score

This value will differ for every Pokémon and every capture setup, so always tune it with debug mode before relying on it for a real hunt. The Moltres value of 55 is specific to the FRLG setup this was tested on.

---

## Pi Setup

SR Watcher v2 integrates with a Raspberry Pi Zero 2 W running an automated hunt script. The Pi emulates a wired Nintendo Switch Pro Controller over USB using [raspberry-switch-control](https://github.com/omakoto/raspberry-switch-control), which handles all button input to the Switch. When a shiny is detected, SR Watcher SSHes into the Pi over your local network and kills the hunt script automatically, stopping the automation so you can take over and catch the Pokémon.

Configure the Pi connection at the top of `sr_watcher.py`:

```python
PI_HOST = "yourusername@yourpi.local"
PI_SCRIPT_NAME = "your_hunt_script.py"
```

The Pi must be accessible over your local network via SSH. Windows 11 includes SSH by default. No password configuration is needed if your network allows it — if a password is required, consider setting up SSH key authentication.

The Pi hunt script (`moltres_hunt.py`) handles:
* Automated button input via USB controller emulation using raspberry-switch-control
* Navigating through title and recap screens after each reset
* Entering the static encounter
* Soft resetting after the shiny check window
* Logging reset counts to `resets.txt`

---

## Running the Script

```
python sr_watcher.py
```

OBS will launch automatically. Once the Virtual Camera is ready the watcher window will open and begin watching the feed.

---

## Controls

* `O` — open the Options panel
* `R` — re-arm shiny detection after an alert
* `ESC` — exit SR Watcher

---

## Options Panel

* **Show overlay** — toggles the status indicator at the bottom of the window
* **Debug mode** — shows live detection scores for tuning thresholds
* **Re-arm button** — same as pressing R

---

## Building the Executable

```
python -m PyInstaller --windowed --noupx --icon game.ico --name "SR Watcher" --add-data "cc-image.jpg;." --add-data "battle-screen.jpg;." --add-data "normal-moltres.jpg;." --add-data "shiny_pla.mp3;." sr_watcher.py
```

The finished build will be at:

```
dist\SR Watcher\SR Watcher.exe
```

Copy the entire `SR Watcher` folder to any Windows machine. No Python installation required.

---

## Logs

Reset logs are written by the Pi hunt script, not SR Watcher v2. Logs are saved to:

```
resets.txt
```

on the Raspberry Pi in the home directory.
