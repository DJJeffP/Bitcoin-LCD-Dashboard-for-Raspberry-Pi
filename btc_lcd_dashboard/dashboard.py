# dashboard.py
"""
Dashboard met snelle overlays: alleen klok en coin value box worden geüpdatet als overlay!
Achtergrond blijft altijd in originele orientatie, rotatie alleen direct voor framebuffer.
"""

import os
import time
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 480, 320
FRAMEBUFFER = "/dev/fb1"
BG_FOLDER = "backgrounds"
BG_FALLBACK = os.path.join(BG_FOLDER, "btc-bg.png")

# Klok rechtsboven, evt. X naar links als je wilt
CLOCK_X = 270
CLOCK_Y = 10
CLOCK_W = 200
CLOCK_H = 55

# Coin value box rechtsonder
COIN_BOX_X = 240
COIN_BOX_Y = 230
COIN_BOX_W = 210
COIN_BOX_H = 70

# Fonts
FONT_BIG = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SMALL = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
font_main = ImageFont.truetype(FONT_BIG, 36)
font_value = ImageFont.truetype(FONT_BIG, 48)
font_time = ImageFont.truetype(FONT_BIG, 28)
font_date = ImageFont.truetype(FONT_SMALL, 20)

def hex_to_rgb(hex_color, fallback=(247,147,26)):
    try:
        h = hex_color.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0,2,4))
    except:
        return fallback

def draw_dashboard(btc_price, btc_color, coin, coin_price):
    """
    Tekent alleen de statische achtergrond, BTC naam/waarde, géén overlay coin box en geen klok!
    """
    coin_id = coin["id"]
    coin_bg = os.path.join(BG_FOLDER, f"{coin_id}-bg.png")
    if not os.path.isfile(coin_bg):
        coin_bg = BG_FALLBACK
    full_bg = Image.open(coin_bg).convert("RGB").resize((WIDTH, HEIGHT))
    draw = ImageDraw.Draw(full_bg)

    # BTC label en prijs (midden)
    label = "BTC"
    price_text = "$" + (str(btc_price) if btc_price is not None else "N/A")
    right_offset = 60
    btc_color_rgb = btc_color
    label_w, label_h = draw.textbbox((0, 0), label, font=font_main)[2:]
    price_w, price_h = draw.textbbox((0, 0), price_text, font=font_value)[2:]
    btc_label_y = int(HEIGHT * 0.35) - label_h
    btc_price_y = btc_label_y + label_h + 5
    draw.text(((WIDTH - label_w)//2 + right_offset, btc_label_y), label, font=font_main, fill=btc_color_rgb)
    draw.text(((WIDTH - price_w)//2 + right_offset, btc_price_y), price_text, font=font_value, fill=(255,255,255))

    # Bewaar bg voor overlays
    global _full_bg_cache
    _full_bg_cache = full_bg.copy()

    # Volledig scherm roteren en schrijven
    img_rot = full_bg.rotate(180)
    rgb565 = bytearray()
    for pixel in img_rot.getdata():
        r = pixel[0] >> 3
        g = pixel[1] >> 2
        b = pixel[2] >> 3
        value = (r << 11) | (g << 5) | b
        rgb565.append(value & 0xFF)
        rgb565.append((value >> 8) & 0xFF)
    with open(FRAMEBUFFER, 'wb') as f:
        f.write(rgb565)

def update_clock_area(btc_color=(247,147,26)):
    """
    Overlay de klok rechtsboven als losse block met oranje datum.
    """
    global _full_bg_cache
    if '_full_bg_cache' not in globals():
        return

    # Copy uit originele bg
    img = _full_bg_cache.crop((CLOCK_X, CLOCK_Y, CLOCK_X + CLOCK_W, CLOCK_Y + CLOCK_H))
    draw = ImageDraw.Draw(img)
    t = time.localtime()
    now_str = time.strftime("%H:%M:%S", t)
    date_str = time.strftime("%a %d %b %Y", t)
    time_color = (255,255,255)
    date_color = btc_color
    draw.text((10, 0), now_str, font=font_time, fill=time_color)
    draw.text((10, 30), date_str, font=font_date, fill=date_color)

    img_rot = img.rotate(180)
    rgb565 = bytearray()
    for pixel in img_rot.getdata():
        r = pixel[0] >> 3
        g = pixel[1] >> 2
        b = pixel[2] >> 3
        val = (r << 11) | (g << 5) | b
        rgb565.append(val & 0xFF)
        rgb565.append((val >> 8) & 0xFF)

    fb_x = WIDTH - CLOCK_X - CLOCK_W
    fb_y = HEIGHT - CLOCK_Y - CLOCK_H
    fb_offset = (fb_y * WIDTH + fb_x) * 2

    with open(FRAMEBUFFER, "r+b") as f:
        for row in range(CLOCK_H):
            f.seek(fb_offset + row * WIDTH * 2)
            start = row * CLOCK_W * 2
            end = start + CLOCK_W * 2
            f.write(rgb565[start:end])

def update_coin_value_area(coin_symbol, coin_value, coin_color=(255,255,255)):
    """
    Overlay coin value box rechts onderin met naam in kleur en waarde in wit.
    """
    global _full_bg_cache
    if '_full_bg_cache' not in globals():
        return

    img = _full_bg_cache.crop((COIN_BOX_X, COIN_BOX_Y, COIN_BOX_X + COIN_BOX_W, COIN_BOX_Y + COIN_BOX_H))
    draw = ImageDraw.Draw(img)

    symbol_text = coin_symbol.upper()
    value_text = "$" + (str(coin_value) if coin_value is not None else "N/A")

    symbol_w, symbol_h = draw.textbbox((0,0), symbol_text, font=font_main)[2:]
    symbol_x = (COIN_BOX_W - symbol_w)//2
    symbol_y = 0

    value_w, value_h = draw.textbbox((0,0), value_text, font=font_value)[2:]
    value_x = (COIN_BOX_W - value_w)//2
    value_y = symbol_y + symbol_h + 4

    draw.text((symbol_x, symbol_y), symbol_text, font=font_main, fill=coin_color)
    draw.text((value_x, value_y), value_text, font=font_value, fill=(255,255,255))

    img_rot = img.rotate(180)
    rgb565 = bytearray()
    for pixel in img_rot.getdata():
        r = pixel[0] >> 3
        g = pixel[1] >> 2
        b = pixel[2] >> 3
        val = (r << 11) | (g << 5) | b
        rgb565.append(val & 0xFF)
        rgb565.append((val >> 8) & 0xFF)

    fb_x = WIDTH - COIN_BOX_X - COIN_BOX_W
    fb_y = HEIGHT - COIN_BOX_Y - COIN_BOX_H
    fb_offset = (fb_y * WIDTH + fb_x) * 2

    with open(FRAMEBUFFER, "r+b") as f:
        for row in range(COIN_BOX_H):
            f.seek(fb_offset + row * WIDTH * 2)
            start = row * COIN_BOX_W * 2
            end = start + COIN_BOX_W * 2
            f.write(rgb565[start:end])
