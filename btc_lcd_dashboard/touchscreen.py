# touchscreen.py
"""
Touchscreen event handling & double-tap detectie.
"""

import evdev
import time

# Importeer scale_touch vanuit calibration
from calibration import scale_touch

TOUCH_DEVICE = '/dev/input/event0'

def is_in_clock_area(x, y, width=480):
    """Check of een coördinaat in het klokgebied valt (rechtsboven)."""
    return x >= width - 52  # 480-428 = 52px breed klokgebied

def double_tap_detector(trigger_callback, width=480):
    """
    Detecteert double-tap op het klokgebied en roept de callback aan.
    """
    device = evdev.InputDevice(TOUCH_DEVICE)
    last_tap_time = 0
    DOUBLE_TAP_MAX_INTERVAL = 0.4  # seconden
    raw_x, raw_y = 0, 0
    for event in device.read_loop():
        if event.type == evdev.ecodes.EV_ABS:
            if event.code == evdev.ecodes.ABS_X:
                raw_x = event.value
            elif event.code == evdev.ecodes.ABS_Y:
                raw_y = event.value
        elif event.type == evdev.ecodes.EV_KEY and event.code == evdev.ecodes.BTN_TOUCH and event.value == 1:
            x, y = scale_touch(raw_x, raw_y)
            now = time.time()
            if is_in_clock_area(x, y, width):
                if last_tap_time and (now - last_tap_time < DOUBLE_TAP_MAX_INTERVAL):
                    print("[TOUCH] Double tap detected in clock area!")
                    trigger_callback()
                    last_tap_time = 0
                else:
                    last_tap_time = now

def touch_event_reader(callback):
    """
    Algemeen event-reader. Roept de callback aan bij elke 'finger up' met geschaalde x, y.
    """
    device = evdev.InputDevice(TOUCH_DEVICE)
    raw_x, raw_y = 0, 0
    finger_down = False
    for event in device.read_loop():
        if event.type == evdev.ecodes.EV_ABS:
            if event.code == evdev.ecodes.ABS_X:
                raw_x = event.value
            elif event.code == evdev.ecodes.ABS_Y:
                raw_y = event.value
        elif event.type == evdev.ecodes.EV_KEY and event.code == evdev.ecodes.BTN_TOUCH:
            if event.value == 1:
                finger_down = True
            elif event.value == 0 and finger_down:
                finger_down = False
                x, y = scale_touch(raw_x, raw_y)
                callback(x, y)
