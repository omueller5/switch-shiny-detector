# SR Watcher

SR Watcher is a lightweight reset logger for real-hardware shiny hunting.

It watches your capture feed through OBS Virtual Camera, detects the copyright screen, logs each reset to a text file, and shows a live reset counter on screen.

This was built mainly for Pokémon FireRed and LeafGreen soft resets, but the basic setup can be adapted for other games if needed.

---

# What It Does

SR Watcher:

- launches OBS
- starts the OBS Virtual Camera
- opens a live preview window
- watches for a reference image of the copyright screen
- logs a `+1` reset each time that screen appears
- shows a live reset counter overlay in the preview window
- prevents double counting from the same screen appearance

---

# Features

- Automatic soft reset detection
- Live `RESETS: X` overlay in the preview window
- Daily reset logs saved to your Desktop
- One `SR Logs` folder with one file per day
- Auto-launches OBS with Virtual Camera
- Works with real hardware and a capture card
- Subtle on-screen indicators for armed state and copyright-screen match
- Fast-launching executable build

---

# Requirements

You need:

- Python 3.11
- OBS Studio
- OBS Virtual Camera
- a capture card
- Python packages:
  - `opencv-python`
  - `numpy`
  - `pyinstaller` (only needed if building the EXE)

---

# Install Requirements

Install all dependencies with:

```
python -m pip install -r requirements.txt
```

---

# How It Works

SR Watcher compares the live video feed to `cc-image.jpg`.

When the copyright screen is detected:

- the live reset counter increases by 1
- the reset is written to the current day’s log file
- the preview flashes a subtle indicator
- the script waits for the screen to disappear before allowing another count

This prevents the same reset from being counted multiple times.

---

# OBS Behavior

When launched, SR Watcher attempts to:

- start OBS
- start the OBS Virtual Camera
- minimize OBS
- begin watching the capture feed

---

# Logs

Logs are saved to your Desktop in:

```
Desktop\SR Logs
```

SR Watcher creates **one log file per day**.

Example files:

```
SR 3-15-2026.txt
SR 3-16-2026.txt
SR 3-17-2026.txt
```

---

# Example Log Format

```
Soft Reset Encounter Log
========================
Total Increments: 43

[03-15-2026]
  07:14:02 PM  +1
  07:16:41 PM  +1
  07:19:08 PM  +1
```

---

# Running the Python Script

From the project folder run:

```
python sr_watcher.py
```

When running:

- OBS should launch automatically
- the preview window opens
- the live reset counter appears in the bottom corner
- press `ESC` to close the program

---

# Building the Executable

```
python -m PyInstaller --windowed --noupx --icon game.ico --name "SR Watcher" --add-data "cc-image.jpg;." sr_watcher.py
```

---

# Built EXE Output

After building, PyInstaller creates a `dist` folder.

Your executable will be located at:

```
dist\SR Watcher\SR Watcher.exe
```

---

# Controls

- `ESC` = exit the program

---

# Future Plans

A future version may include the ability to **directly increment encounters inside the Shiny Tracker application**, allowing resets detected by SR Watcher to automatically update the active hunt.
