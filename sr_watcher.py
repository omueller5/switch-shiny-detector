
# SR Watcher – UI version (baseline-preserving update)
# Based on the uploaded working baseline:
# - detection/logging logic kept the same
# - black side bars
# - controls window can be opened/closed anytime
# - controls can be opened with O key or on-screen button
# - debug mode added (off by default)

import cv2
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path
import tkinter as tk

CAMERA_INDEX = 2
TEMPLATE_FILE = "cc-image.jpg"

MIN_MATCH_SCORE = 56.0
MAX_MATCH_SCORE = 58.5
MATCH_CONFIRM_FRAMES = 2
RESET_COOLDOWN_SECONDS = 15

OBS_PATH = r"C:\Program Files\obs-studio\bin\64bit\obs64.exe"
OBS_WAIT_SECONDS = 4

LOG_FOLDER = Path.home() / "Desktop" / "SR Logs"
LOG_FOLDER.mkdir(parents=True, exist_ok=True)

WINDOW_NAME = "SR Watcher"

controls_root = None
controls_host = None
count_enabled_var = None
overlay_enabled_var = None
log_enabled_var = None
debug_enabled_var = None
cooldown_var = None

options_button_rect = None


def resource_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return str(Path(sys._MEIPASS) / relative_path)
    return str(Path(__file__).resolve().parent / relative_path)



def launch_obs():
    try:
        subprocess.Popen(
            [OBS_PATH, "--startvirtualcam", "--minimize-to-tray"],
            cwd=str(Path(OBS_PATH).parent)
        )
        time.sleep(OBS_WAIT_SECONDS)
    except Exception as e:
        print("OBS launch failed:", e)


def get_log_file():
    now = datetime.now()
    return LOG_FOLDER / f"SR {now.month}-{now.day}-{now.year}.txt"


def log_reset():
    log_file = get_log_file()

    if not log_file.exists():
        log_file.write_text("Soft Reset Log\n\n", encoding="utf-8")

    with open(log_file, "a", encoding="utf-8") as f:
        now = datetime.now().strftime("%I:%M:%S %p")
        f.write(f"{now}  +1\n")


def find_text_bbox(gray):
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    points = cv2.findNonZero(thresh)
    if points is None:
        h, w = gray.shape[:2]
        return 0, 0, w, h

    x, y, w, h = cv2.boundingRect(points)
    return x, y, w, h


def load_template():
    template_path = resource_path(TEMPLATE_FILE)
    img = cv2.imread(template_path)
    if img is None:
        raise RuntimeError(f"Missing or unreadable template image: {TEMPLATE_FILE}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    x, y, w, h = find_text_bbox(gray)
    crop = gray[y:y + h, x:x + w]
    return gray, crop, (x, y, w, h)


def crop_live(frame_gray, bbox, size):
    x, y, w, h = bbox
    full_w, full_h = size
    resized = cv2.resize(frame_gray, (full_w, full_h), interpolation=cv2.INTER_AREA)
    return resized[y:y + h, x:x + w]


def score_frame(frame_gray, size, bbox, template_crop):
    live = crop_live(frame_gray, bbox, size)
    diff = cv2.absdiff(live, template_crop)
    return float(diff.mean())


def draw_status_panel(frame, reset_count, remaining, ready, show_overlay):
    if not show_overlay:
        return frame

    panel_x = 20
    panel_y = frame.shape[0] - 120

    count_text = f"RESETS: {reset_count}"
    cv2.rectangle(frame, (panel_x - 10, panel_y - 50), (panel_x + 320, panel_y + 10), (0, 0, 0), -1)
    cv2.putText(frame, count_text, (panel_x, panel_y), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)

    if ready:
        timer_text = "READY"
        timer_color = (0, 255, 0)
    else:
        timer_text = f"{remaining:.1f}s"
        timer_color = (0, 200, 255)

    cv2.rectangle(frame, (panel_x - 10, panel_y + 20), (panel_x + 180, panel_y + 70), (0, 0, 0), -1)
    cv2.putText(frame, timer_text, (panel_x, panel_y + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.9, timer_color, 2)

    return frame


def draw_debug_panel(frame, score, ready, count_enabled, logging_enabled):
    if debug_enabled_var is None or not debug_enabled_var.get():
        return frame

    x = 20
    y = 25
    lines = [
        f"SCORE: {score:.4f}",
        f"READY: {'YES' if ready else 'NO'}",
        f"COUNTING: {'ON' if count_enabled else 'OFF'}",
        f"LOGGING: {'ON' if logging_enabled else 'OFF'}",
    ]

    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.65
    thickness = 2
    line_h = 26
    box_w = 270
    box_h = 18 + line_h * len(lines)

    cv2.rectangle(frame, (x - 10, y - 18), (x - 10 + box_w, y - 18 + box_h), (0, 0, 0), -1)

    for i, line in enumerate(lines):
        cv2.putText(frame, line, (x, y + i * line_h), font, scale, (255, 255, 255), thickness)

    return frame


def draw_options_button(frame):
    global options_button_rect
    h, w = frame.shape[:2]

    btn_w = 140
    btn_h = 42
    x1 = w - btn_w - 20
    y1 = 20
    x2 = w - 20
    y2 = y1 + btn_h

    options_button_rect = (x1, y1, x2, y2)

    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), -1)
    cv2.putText(frame, "OPTIONS", (x1 + 16, y1 + 29), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    return frame


def fit_to_window(frame, win_w, win_h):
    if win_w <= 0 or win_h <= 0:
        return frame

    fh, fw = frame.shape[:2]
    scale = min(win_w / fw, win_h / fh)
    new_w = max(1, int(fw * scale))
    new_h = max(1, int(fh * scale))

    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    canvas = cv2.resize(frame, (win_w, win_h), interpolation=cv2.INTER_NEAREST)
    canvas[:] = (0, 0, 0)

    x = (win_w - new_w) // 2
    y = (win_h - new_h) // 2
    canvas[y:y + new_h, x:x + new_w] = resized
    return canvas


def ensure_controls_window():
    global controls_root, controls_host
    global count_enabled_var, overlay_enabled_var, log_enabled_var, debug_enabled_var, cooldown_var

    if controls_root is not None:
        try:
            if controls_root.winfo_exists():
                controls_root.deiconify()
                controls_root.lift()
                controls_root.focus_force()
                return
        except Exception:
            controls_root = None

    if controls_host is None:
        controls_host = tk.Tk()
        controls_host.withdraw()

    controls_root = tk.Toplevel(controls_host)
    controls_root.title("SR Watcher Controls")
    controls_root.geometry("300x240")
    controls_root.resizable(False, False)

    count_enabled_var = tk.BooleanVar(value=True)
    overlay_enabled_var = tk.BooleanVar(value=True)
    log_enabled_var = tk.BooleanVar(value=True)
    debug_enabled_var = tk.BooleanVar(value=False)
    cooldown_var = tk.StringVar(value=str(int(RESET_COOLDOWN_SECONDS)))

    tk.Label(controls_root, text="SR Watcher Controls", font=("Segoe UI", 11, "bold")).pack(pady=(10, 8))
    tk.Checkbutton(controls_root, text="Enable reset counting", variable=count_enabled_var).pack(anchor="w", padx=14)
    tk.Checkbutton(controls_root, text="Show overlay", variable=overlay_enabled_var).pack(anchor="w", padx=14)
    tk.Checkbutton(controls_root, text="Write TXT log", variable=log_enabled_var).pack(anchor="w", padx=14)
    tk.Checkbutton(controls_root, text="Debug mode", variable=debug_enabled_var).pack(anchor="w", padx=14)

    row = tk.Frame(controls_root)
    row.pack(anchor="w", padx=14, pady=(12, 0))
    tk.Label(row, text="Cooldown (seconds):").pack(side="left")
    tk.Entry(row, textvariable=cooldown_var, width=8).pack(side="left", padx=(8, 0))

    help_text = tk.Label(
        controls_root,
        text="Press O or click OPTIONS in the video window.\nClosing this panel does not stop SR Watcher.",
        justify="left",
        fg="#444"
    )
    help_text.pack(anchor="w", padx=14, pady=(12, 0))


def update_controls_window():
    global controls_root
    if controls_root is None:
        return
    try:
        controls_root.update()
    except tk.TclError:
        controls_root = None


def get_count_enabled():
    return True if count_enabled_var is None else count_enabled_var.get()


def get_overlay_enabled():
    return True if overlay_enabled_var is None else overlay_enabled_var.get()


def get_log_enabled():
    return True if log_enabled_var is None else log_enabled_var.get()


def get_cooldown_seconds():
    if cooldown_var is None:
        return RESET_COOLDOWN_SECONDS
    try:
        return max(0.0, float(cooldown_var.get()))
    except Exception:
        return RESET_COOLDOWN_SECONDS


def on_mouse(event, x, y, flags, param):
    if event != cv2.EVENT_LBUTTONDOWN:
        return
    if options_button_rect is None:
        return
    x1, y1, x2, y2 = options_button_rect
    if x1 <= x <= x2 and y1 <= y <= y2:
        ensure_controls_window()


def main():
    launch_obs()

    template_gray, template_crop, bbox = load_template()
    h, w = template_gray.shape[:2]

    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    if not cap.isOpened():
        raise RuntimeError("Could not open OBS camera")

    match_streak = 0
    reset_count = 0
    last_reset_time = 0.0

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, 1280, 720)
    cv2.setMouseCallback(WINDOW_NAME, on_mouse)

    ensure_controls_window()

    print("SR Watcher started")
    print(f"Match range: {MIN_MATCH_SCORE} to {MAX_MATCH_SCORE}")
    print("Press O to open controls")
    print("Press ESC to exit")

    while True:
        update_controls_window()

        ret, frame = cap.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        score = score_frame(gray, (w, h), bbox, template_crop)

        now = time.time()
        cooldown_seconds = get_cooldown_seconds()
        elapsed = now - last_reset_time
        ready = elapsed >= cooldown_seconds
        remaining = max(0.0, cooldown_seconds - elapsed)

        print(f"match score: {score:.4f}", end="\r", flush=True)

        count_enabled = get_count_enabled()
        overlay_enabled = get_overlay_enabled()
        logging_enabled = get_log_enabled()

        if count_enabled and MIN_MATCH_SCORE <= score <= MAX_MATCH_SCORE and ready:
            match_streak += 1
        else:
            match_streak = 0

        if match_streak >= MATCH_CONFIRM_FRAMES:
            reset_count += 1
            if logging_enabled:
                log_reset()
            last_reset_time = now
            match_streak = 0
            print(f"\nRESET DETECTED -> Total: {reset_count} (score={score:.4f})")

        display = frame.copy()
        if overlay_enabled:
            display = draw_status_panel(display, reset_count, remaining, ready, True)
        display = draw_debug_panel(display, score, ready, count_enabled, logging_enabled)
        display = draw_options_button(display)

        try:
            _, _, win_w, win_h = cv2.getWindowImageRect(WINDOW_NAME)
        except Exception:
            win_w, win_h = display.shape[1], display.shape[0]

        display = fit_to_window(display, max(1, win_w), max(1, win_h))
        cv2.imshow(WINDOW_NAME, display)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            break
        elif key in (ord('o'), ord('O')):
            ensure_controls_window()

    cap.release()
    cv2.destroyAllWindows()

    if controls_root is not None:
        try:
            controls_root.destroy()
        except Exception:
            pass
    if controls_host is not None:
        try:
            controls_host.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    main()
