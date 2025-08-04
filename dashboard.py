# --- BOOKMARK: Altcoin overlay-only versie, BTC in bg, 2024-08-05 ---
# Deze versie werkt als de "gouden basis" voor altcoin overlays!

import os
import time
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 480, 320
FRAMEBUFFER = "/dev/fb1"
BG_FOLDER = "backgrounds"
BG_FALLBACK = os.path.join(BG_FOLDER, "btc-bg.png")
textbox_offset = 60

CLOCK_X = 270
CLOCK_Y = 10
CLOCK_W = 200
CLOCK_H = 55

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
    coin_id = coin["id"]
    coin_bg = os.path.join(BG_FOLDER, f"{coin_id}-bg.png")
    if not os.path.isfile(coin_bg):
        coin_bg = BG_FALLBACK
    full_bg = Image.open(coin_bg).convert("RGB").resize((WIDTH, HEIGHT))
    draw = ImageDraw.Draw(full_bg)

    label = "BTC"
    price_text = "$" + (str(btc_price) if btc_price is not None else "N/A")
    right_offset = textbox_offset
    btc_color_rgb = btc_color

    label_bbox = draw.textbbox((0, 0), label, font=font_main)
    label_w = label_bbox[2] - label_bbox[0]
    label_h = label_bbox[3] - label_bbox[1]
    price_bbox = draw.textbbox((0, 0), price_text, font=font_value)
    price_w = price_bbox[2] - price_bbox[0]
    price_h = price_bbox[3] - price_bbox[1]
    btc_label_y = int(HEIGHT * 0.35) - label_h
    btc_price_y = btc_label_y + label_h + 5

    global _btc_label_y, _btc_price_y, _btc_price_h
    _btc_label_y = btc_label_y
    _btc_price_y = btc_price_y
    _btc_price_h = price_h

    # BTC-label en prijs worden direct op de achtergrond getekend!
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

def update_coin_value_area_variable(coin_symbol, coin_value, coin_color=(255,255,255), right_offset=60):
    global _full_bg_cache, _btc_price_y, _btc_price_h, _prev_coin_box
    if '_full_bg_cache' not in globals():
        return
    if '_btc_price_y' not in globals() or '_btc_price_h' not in globals():
        _btc_price_y = int(HEIGHT * 0.35) + 5
        _btc_price_h = 48

    symbol_text = coin_symbol.upper()
    value_text = "$" + (str(coin_value) if coin_value is not None else "N/A")

    symbol_bbox = font_main.getbbox(symbol_text)
    symbol_w = symbol_bbox[2] - symbol_bbox[0]
    symbol_h = symbol_bbox[3] - symbol_bbox[1]
    value_bbox = font_value.getbbox(value_text)
    value_w = value_bbox[2] - value_bbox[0]
    value_h = value_bbox[3] - value_bbox[1]

    box_w = max(symbol_w, value_w) + 40
    box_h = symbol_h + value_h + 25
    box_x = (WIDTH - box_w)//2 + right_offset
    box_y = _btc_price_y + _btc_price_h + 20

    # UNION met vorige box voor anti-ghosting
    if '_prev_coin_box' in globals() and _prev_coin_box:
        prev_x, prev_y, prev_w, prev_h = _prev_coin_box
        min_x = min(box_x, prev_x)
        min_y = min(box_y, prev_y)
        max_x = max(box_x + box_w, prev_x + prev_w)
        max_y = max(box_y + box_h, prev_y + prev_h)
        box_x, box_y = min_x, min_y
        box_w, box_h = max_x - min_x, max_y - min_y

    # Sla nieuwe box op voor de volgende iteratie
    _prev_coin_box = (box_x, box_y, box_w, box_h)

    # Knip uit bg en teken tekst
    img = _full_bg_cache.crop((box_x, box_y, box_x + box_w, box_y + box_h))
    draw = ImageDraw.Draw(img)

    # Tekst centreren
    symbol_x = (box_w - symbol_w)//2
    symbol_y = 7
    value_x = (box_w - value_w)//2
    value_y = symbol_y + symbol_h + 8

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

    fb_x = WIDTH - box_x - box_w
    fb_y = HEIGHT - box_y - box_h
    fb_offset = (fb_y * WIDTH + fb_x) * 2

    with open(FRAMEBUFFER, "r+b") as f:
        for row in range(box_h):
            f.seek(fb_offset + row * WIDTH * 2)
            start = row * box_w * 2
            end = start + box_w * 2
            f.write(rgb565[start:end])

