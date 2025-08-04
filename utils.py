# utils.py
"""
Algemene helper-functies en utilities die in meerdere modules gebruikt worden.
"""

import os
import time

def hex_to_rgb(hex_color, fallback=(247,147,26)):
    """
    Zet een hexadecimale kleur (#AABBCC) om naar een (R,G,B) tuple.
    """
    try:
        h = hex_color.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0,2,4))
    except:
        return fallback

def clear_framebuffer(framebuffer="/dev/fb1", width=480, height=320):
    """
    Maakt het framebuffer-scherm zwart/clean.
    """
    with open(framebuffer, 'wb') as f:
        f.write(bytearray([0x00, 0x00] * width * height))

def get_now_and_struct():
    """
    Geeft zowel tijd in seconden (float) als time.struct_time voor formatering.
    """
    now = time.time()
    t_struct = time.localtime(now)
    return now, t_struct
