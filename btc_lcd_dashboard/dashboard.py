# dashboard.py
"""
Dashboard met overlays: klok en coin value box als overlay, coin value box altijd gecentreerd onder BTC!
"""

import os
import time
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 480, 320
FRAMEBUFFER = "/dev/fb1"
BG_FOLDER = "backgrounds"
BG_FALLBACK = os.path.join(BG_FOLDER, "btc-bg.png")

# Klok rechtsboven
CLOCK_X = 270
CLOCK_Y = 10
CLOCK_W = 200
CLOCK_H = 55

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
    Tekent statische achtergrond + BTC (naam en prijs).
    Coin value box en klok worden apart ge-overlayed!
    """
    coin_id = coin["id"]
    coin_bg = os.path.join(BG_FOLDER, f"{coin_id}-bg.png")
    if not os.path.isfile(coin_bg):
        coin_bg = BG_FALLBACK
    full_bg = Image.open(coin_bg).convert("RGB").resize((WIDTH, HEIGHT))
    draw = ImageDraw.Draw(full_bg)

    label = "BTC"
    price_text = "$" + (str(btc_price) if btc_price is not None else "N/A")
    right_offset = 60
    btc_color_rgb = btc_color

    # Gebruik textbbox om afmetingen te bepalen (voor de overlay-functie!)
    label_bbox = draw.textbbox((0, 0), label, font=font_main)
    label_w = label_bbox[2] - label_bbox[0]
    label_h = label_bbox[3] - label_bbox[1]
    price_bbox = draw.textbbox((0, 0), price_text, font=font_value)
    price_w = price_bbox[2] - price_bbox[0]
    price_h = price_bbox[3] - price_bbox[1]
    btc_label_y = int(HEIGHT * 0.35) - label_h
    btc_price_y = btc_label_y + label_h + 5

    # Zet deze in global vars (voor overlay):
    global _btc_label_w, _btc_label_y, _btc_price_y, _btc_price_h
    _btc_label_w = label_w
    _btc_label_y = btc_label_y
    _btc_price_y = btc_price_y
    _btc_price_h = price_h

    draw.text(((WIDTH - label_w)//2 + right_offset, btc_label_y), label, font=font_main, fill=btc_color_rgb)
    draw.text(((WIDTH - price_w)//2 + right_offset, btc_price_y), price_text, font=font_value, fill=(255,255,255))

    global _full_bg_cache
    _full_bg_cache = full_bg.copy()

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
    Overlay klok rechtsboven, oranje datum.
    """
    global _full_bg_cache
    if '_full_bg_cache' not in globals():
        return

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

def update_coin_value_area_aligned(coin_symbol, coin_value, coin_color=(255,255,255)):
    """
    Overlay coin value box, exact horizontaal uitgelijnd met BTC-label en -waarde.
    Automatische hoogte, geen afkapping meer.
    """
    global _full_bg_cache, _btc_label_w, _btc_label_y, _btc_price_y, _btc_price_h
    if '_full_bg_cache' not in globals():
        return
    if not all(k in globals() for k in ['_btc_label_w', '_btc_label_y', '_btc_price_y', '_btc_price_h']):
        # fallback naar ruwe waardes als globals er niet zijn
        _btc_label_w = 240
        _btc_label_y = 80
        _btc_price_y = 120
        _btc_price_h = 48

    # Zelfde breedte/offset als BTC-label
    BOX_W = _btc_label_w
    BOX_X = (WIDTH - _btc_label_w)//2 + 60  # 60 = dezelfde right_offset als BTC-label!

    # Dynamische hoogte, altijd genoeg
    symbol_text = coin_symbol.upper()
    value_text = "$" + (str(coin_value) if coin_value is not None else "N/A")
    # Bepaal tekstafmetingen:
    symbol_bbox = font_main.getbbox(symbol_text)
    symbol_h = symbol_bbox[3] - symbol_bbox[1]
    value_bbox = font_value.getbbox(value_text)
    value_h = value_bbox[3] - value_bbox[1]
    # Makkelijk marge toevoegen:
    BOX_H = symbol_h + value_h + 20

    # Y direct onder BTC-prijs
    BOX_Y = _btc_price_y + _btc_price_h + 20
    # Corrigeer als onderkant buiten beeld zou vallen:
    if BOX_Y + BOX_H > HEIGHT:
        BOX_Y = HEIGHT - BOX_H - 10

    # Knip achtergrond
    img = _full_bg_cache.crop((BOX_X, BOX_Y, BOX_X + BOX_W, BOX_Y + BOX_H))
    draw = ImageDraw.Draw(img)

    # Tekst centreren in box:
    symbol_w = font_main.getlength(symbol_text)
    symbol_x = (BOX_W - symbol_w)//2
    symbol_y = 5

    value_w = font_value.getlength(value_text)
    value_x = (BOX_W - value_w)//2
    value_y = symbol_y + symbol_h + 5

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

    fb_x = WIDTH - BOX_X - BOX_W
    fb_y = HEIGHT - BOX_Y - BOX_H
    fb_offset = (fb_y * WIDTH + fb_x) * 2

    with open(FRAMEBUFFER, "r+b") as f:
        for row in range(BOX_H):
            f.seek(fb_offset + row * WIDTH * 2)
            start = row * BOX_W * 2
            end = start + BOX_W * 2
            f.write(rgb565[start:end])
