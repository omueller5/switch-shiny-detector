
import ctypes
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

APP_NAME = "SR Watcher"

CAMERA_INDEX = 2
WINDOW_NAME = APP_NAME
TEMPLATE_IMAGE = "cc-image.jpg"

DESKTOP_PATH = Path.home() / "Desktop"
BASE_FOLDER = DESKTOP_PATH / "SR Logs"

AUTO_LAUNCH_OBS = True
OBS_EXE_PATH = r"C:\Program Files\obs-studio\bin\64bit\obs64.exe"
OBS_LAUNCH_WAIT_SECONDS = 4.0

HASH_DISTANCE_THRESHOLD = 4
HASH_SIZE = 8

ARM_NONMATCH_FRAMES = 15
MATCH_CONFIRM_FRAMES = 3

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
FRAME_FPS = 30

ARM_FLASH_DURATION_SECONDS = 0.6
MATCH_FLASH_DURATION_SECONDS = 0.18

USE_TRUE_FULLSCREEN = False

COLOR_ARM_FLASH = (120, 220, 120)
COLOR_MATCH_FLASH = (120, 220, 220)

COUNTER_BG_COLOR = (0, 0, 0)
COUNTER_TEXT_COLOR = (255, 255, 255)
COUNTER_BORDER_COLOR = (255, 255, 255)

user32 = ctypes.windll.user32
VK_ESCAPE = 0x1B


def escape_pressed():
    return bool(user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000)


def resource_path(relative_path: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).resolve().parent / relative_path


def get_today_strings():
    now = datetime.now()
    file_date = f"{now.month}-{now.day}-{now.year}"
    header_date = now.strftime("%m-%d-%Y")
    return file_date, header_date


def get_daily_log_path():
    BASE_FOLDER.mkdir(parents=True, exist_ok=True)
    file_date, header_date = get_today_strings()
    log_file = BASE_FOLDER / f"SR {file_date}.txt"
    return log_file, header_date


def launch_obs_with_virtual_camera():
    if not AUTO_LAUNCH_OBS:
        return

    obs_path = Path(OBS_EXE_PATH)
    if not obs_path.exists():
        print(f"OBS launch -> not found: {obs_path}")
        return

    try:
        subprocess.Popen(
            [str(obs_path), "--startvirtualcam", "--minimize-to-tray"],
            cwd=str(obs_path.parent)
        )
        print("OBS launched with virtual camera")
        time.sleep(OBS_LAUNCH_WAIT_SECONDS)
    except Exception as e:
        print(f"OBS launch failed: {e}")


def ensure_log_file_exists():
    log_file, _ = get_daily_log_path()
    if not log_file.exists():
        log_file.write_text(
            "Soft Reset Encounter Log\n"
            "========================\n"
            "Total Increments: 0\n\n",
            encoding="utf-8"
        )


def read_log_state():
    log_file, _ = get_daily_log_path()
    ensure_log_file_exists()

    text = log_file.read_text(encoding="utf-8")
    lines = text.splitlines()

    total = 0
    for line in lines:
        if line.startswith("Total Increments:"):
            try:
                total = int(line.split(":", 1)[1].strip())
            except Exception:
                total = 0
            break

    return lines, total


def write_increment_to_log():
    log_file, header_date = get_daily_log_path()
    lines, total = read_log_state()

    total += 1
    today_header = f"[{header_date}]"
    timestamp = datetime.now().strftime("%I:%M:%S %p")

    total_updated = False
    for i, line in enumerate(lines):
        if line.startswith("Total Increments:"):
            lines[i] = f"Total Increments: {total}"
            total_updated = True
            break

    if not total_updated:
        lines.insert(2, f"Total Increments: {total}")

    if today_header not in lines:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(today_header)

    day_index = lines.index(today_header)
    insert_at = day_index + 1
    while insert_at < len(lines) and not (lines[insert_at].startswith("[") and lines[insert_at].endswith("]")):
        insert_at += 1

    lines.insert(insert_at, f"  {timestamp}  +1")
    log_file.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    return total, log_file


def average_hash(image_bgr, hash_size=8):
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (hash_size, hash_size), interpolation=cv2.INTER_AREA)
    avg = resized.mean()
    return (resized > avg).astype(np.uint8)


def hamming_distance(hash_a, hash_b):
    return int(np.count_nonzero(hash_a != hash_b))


def load_template_hash():
    path = resource_path(TEMPLATE_IMAGE)
    if not path.exists():
        raise RuntimeError(f"Could not find template image: {path}")

    template = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if template is None:
        raise RuntimeError(f"Could not load template image: {path}")

    return average_hash(template, HASH_SIZE)


def configure_capture(cap):
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, FRAME_FPS)


def setup_window(actual_w, actual_h):
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)

    if USE_TRUE_FULLSCREEN:
        cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    else:
        cv2.resizeWindow(WINDOW_NAME, screen_w, screen_h)
        cv2.moveWindow(WINDOW_NAME, 0, 0)
        try:
            cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)
        except Exception:
            pass


def draw_flash_indicator(frame, text, color):
    cv2.circle(frame, (28, 28), 12, color, -1)
    cv2.putText(
        frame,
        text,
        (50, 34),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        color,
        2,
        cv2.LINE_AA
    )
    return frame


def draw_live_counter(frame, total_count):
    label = f"RESETS: {total_count}"

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.25
    thickness = 3

    (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)

    x = 20
    y = frame.shape[0] - 30

    pad_x = 18
    pad_y = 16

    box_x1 = x - pad_x
    box_y1 = y - text_h - pad_y
    box_x2 = x + text_w + pad_x
    box_y2 = y + baseline + pad_y // 2

    cv2.rectangle(frame, (box_x1, box_y1), (box_x2, box_y2), COUNTER_BG_COLOR, -1)
    cv2.rectangle(frame, (box_x1, box_y1), (box_x2, box_y2), COUNTER_BORDER_COLOR, 2)

    cv2.putText(
        frame,
        label,
        (x, y),
        font,
        font_scale,
        COUNTER_TEXT_COLOR,
        thickness,
        cv2.LINE_AA
    )

    return frame


def main():
    ensure_log_file_exists()
    launch_obs_with_virtual_camera()
    template_hash = load_template_hash()

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera index {CAMERA_INDEX}")

    configure_capture(cap)
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS)

    setup_window(actual_w, actual_h)

    last_esc_state = False

    armed = False
    nonmatch_streak = 0
    match_streak = 0
    waiting_for_leave = False

    arm_flash_until = 0.0
    match_flash_until = 0.0

    _, live_total = read_log_state()

    print(f"{APP_NAME} started")
    print(f"Capture requested: {FRAME_WIDTH}x{FRAME_HEIGHT} @ {FRAME_FPS} fps")
    print(f"Capture actual: {actual_w}x{actual_h} @ {actual_fps:.2f} fps")
    print("Waiting to arm...")
    print("ESC exits")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Capture lost -> retrying...")
            cap.release()
            time.sleep(1.5)
            cap = cv2.VideoCapture(CAMERA_INDEX)
            configure_capture(cap)
            continue

        frame_hash = average_hash(frame, HASH_SIZE)
        distance = hamming_distance(template_hash, frame_hash)
        is_match = distance <= HASH_DISTANCE_THRESHOLD

        if not armed:
            if is_match:
                nonmatch_streak = 0
            else:
                nonmatch_streak += 1
                if nonmatch_streak >= ARM_NONMATCH_FRAMES:
                    armed = True
                    arm_flash_until = time.time() + ARM_FLASH_DURATION_SECONDS
                    print("Detector armed -> ready for next reset")
        else:
            if is_match:
                match_streak += 1
            else:
                match_streak = 0
                waiting_for_leave = False

            if (
                is_match
                and not waiting_for_leave
                and match_streak >= MATCH_CONFIRM_FRAMES
            ):
                live_total, log_file = write_increment_to_log()
                waiting_for_leave = True
                match_flash_until = time.time() + MATCH_FLASH_DURATION_SECONDS
                print(f"Reset detected -> +1 (Total {live_total})")
                print(f"Logged to {log_file}")

        display_frame = frame.copy()
        display_frame = draw_live_counter(display_frame, live_total)

        now = time.time()
        if now < arm_flash_until:
            display_frame = draw_flash_indicator(display_frame, "ARMED", COLOR_ARM_FLASH)
        elif now < match_flash_until:
            display_frame = draw_flash_indicator(display_frame, "CC MATCH", COLOR_MATCH_FLASH)

        cv2.imshow(WINDOW_NAME, display_frame)

        esc_now = escape_pressed()
        if esc_now and not last_esc_state:
            break
        last_esc_state = esc_now

        cv2.waitKey(1)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
