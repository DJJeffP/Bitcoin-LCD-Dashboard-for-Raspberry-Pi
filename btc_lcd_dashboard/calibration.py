# calibration.py
"""
Touchscreen kalibratie, scaling, crosshair.
"""

import os
import json
import time
import evdev
from PIL import Image, ImageDraw, ImageFont

# Zet je standaardwaarden
WIDTH, HEIGHT = 480, 320
FRAMEBUFFER = "/dev/fb1"
CALIBRATION_FILE = "touch_calibration.json"
FONT_SMALL = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def draw_crosshair(x, y, msg=""):
    image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    size = 20
    draw.line([(x-size, y), (x+size, y)], fill=(0,255,0), width=3)
    draw.line([(x, y-size), (x, y+size)], fill=(0,255,0), width=3)
    font = ImageFont.truetype(FONT_SMALL, 24)
    draw.text((WIDTH//2 - 80, HEIGHT-40), msg, fill=(255,255,255), font=font)
    image = image.rotate(180)
    rgb565 = bytearray()
    for pixel in image.getdata():
        r = pixel[0] >> 3
        g = pixel[1] >> 2
        b = pixel[2] >> 3
        value = (r << 11) | (g << 5) | b
        rgb565.append(value & 0xFF)
        rgb565.append((value >> 8) & 0xFF)
    with open(FRAMEBUFFER, 'wb') as f:
        f.write(rgb565)

def calibrate_touch():
    print("[CALIBRATION] Starting touchscreen calibration...")
    points = [
        ("Top Left", 30, 30),
        ("Top Right", WIDTH-31, 30),
        ("Bottom Right", WIDTH-31, HEIGHT-31),
        ("Bottom Left", 30, HEIGHT-31),
        ("Center", WIDTH//2, HEIGHT//2),
    ]
    raw_points = []
    screen_points = []
    device = evdev.InputDevice('/dev/input/event0')

    for name, x, y in points:
        draw_crosshair(x, y, f"Touch the {name} cross")
        print(f"[CALIBRATION] Waiting for touch at {name} ({x},{y})...")
        got_tap = False
        raw_x, raw_y = None, None
        while not got_tap:
            for event in device.read_loop():
                if event.type == evdev.ecodes.EV_ABS:
                    if event.code == evdev.ecodes.ABS_X:
                        raw_x = event.value
                    elif event.code == evdev.ecodes.ABS_Y:
                        raw_y = event.value
                elif event.type == evdev.ecodes.EV_KEY and event.code == evdev.ecodes.BTN_TOUCH and event.value == 0:
                    if raw_x is not None and raw_y is not None:
                        raw_points.append((raw_x, raw_y))
                        screen_points.append((x, y))
                        print(f"[CALIBRATION] Got raw ({raw_x}, {raw_y}) for {name}")
                        got_tap = True
                        break
            if got_tap:
                break

    calibration_data = {
        "screen_points": screen_points,
        "raw_points": raw_points,
    }
    with open(CALIBRATION_FILE, "w") as f:
        json.dump(calibration_data, f, indent=2)
    print("[CALIBRATION] Calibration complete and saved.")
    time.sleep(1)

def load_calibration():
    if not os.path.isfile(CALIBRATION_FILE):
        print("[INFO] No calibration file found, running calibration...")
        calibrate_touch()
    with open(CALIBRATION_FILE, "r") as f:
        return json.load(f)

# Globale cache voor schaaldata
calib = None
def scale_touch(x, y):
    global calib
    if calib is None:
        calib = load_calibration()
    screen_points = calib["screen_points"]
    raw_points = calib["raw_points"]
    (sx0, sy0), (sx1, sy1) = screen_points[0], screen_points[2]
    (rx0, ry0), (rx1, ry1) = raw_points[0], raw_points[2]
    if rx1 == rx0: rx1 += 1
    if ry1 == ry0: ry1 += 1
    pixel_x = int((y - ry0) * (sx1 - sx0) / (ry1 - ry0) + sx0)
    pixel_y = int((x - rx0) * (sy1 - sy0) / (rx1 - rx0) + sy0)
    pixel_x = max(0, min(WIDTH-1, pixel_x))
    pixel_y = max(0, min(HEIGHT-1, pixel_y))
    return pixel_x, pixel_y
