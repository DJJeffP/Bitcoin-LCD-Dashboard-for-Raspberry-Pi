# dashboard.py
"""
Dashboard-drawing met efficiënte klok-update via correcte orientatie en rotatie.
"""

import os
import time
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 480, 320
FRAMEBUFFER = "/dev/fb1"
BG_FOLDER = "backgrounds"
BG_FALLBACK = os.path.join(BG_FOLDER, "btc-bg.png")

# Klok regio (in originele orientatie)
CLOCK_X = 315   # Rechtsboven
CLOCK_Y = 10
CLOCK_W = 155
CLOCK_H = 55

# Coin value regio (boven BTC prijs)
COIN_X = 60
COIN_Y = 20
COIN_W = 240
COIN_H = 55

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
    Teken volledige dashboard: achtergrond, BTC, andere coin info, klok wordt apart geüpdatet.
    Werkt intern altijd in 0° orientatie. Rotatie gebeurt pas direct voor framebuffer.
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

    # Andere coin centraal onderin
    if coin["id"] != "btc":
        c_label = coin["symbol"]
        c_color = hex_to_rgb(coin["color"])
        c_price = "$" + (str(coin_price) if coin_price is not None else "N/A")
        c_label_w, c_label_h = draw.textbbox((0, 0), c_label, font=font_main)[2:]
        c_price_w, c_price_h = draw.textbbox((0, 0), c_price, font=font_value)[2:]
        y_offset = int(HEIGHT * 0.75)
        c_label_y = y_offset - c_label_h
        c_price_y = c_label_y + c_label_h + 5
        draw.text(((WIDTH - c_label_w)//2 + right_offset, c_label_y), c_label, font=font_main, fill=c_color)
        draw.text(((WIDTH - c_price_w)//2 + right_offset, c_price_y), c_price, font=font_value, fill=(255,255,255))

    # Bewaar full_bg voor klok-update (globaal, altijd in 0° orientatie)
    global _full_bg_cache
    _full_bg_cache = full_bg.copy()

    # Volledige scherm rotatie (180 graden, zoals hardware verwacht)
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
    Snijdt klokgebied uit cached achtergrond (in 0° orientatie), tekent klok en datum erop,
    roteert het blokje, en schrijft het naar de juiste plek in framebuffer.
    """
    global _full_bg_cache
    if '_full_bg_cache' not in globals():
        return  # Geen achtergrond beschikbaar

    # 1. Snijd klokgebied uit (0° orientatie)
    img = _full_bg_cache.crop((CLOCK_X, CLOCK_Y, CLOCK_X + CLOCK_W, CLOCK_Y + CLOCK_H))
    draw = ImageDraw.Draw(img)
    t = time.localtime()
    now_str = time.strftime("%H:%M:%S", t)
    date_str = time.strftime("%a %d %b %Y", t)

    # Teken tijd en datum
    time_color = (255,255,255)
    date_color = btc_color  # BTC-oranje!
    draw.text((10, 0), now_str, font=font_time, fill=time_color)
    draw.text((10, 30), date_str, font=font_date, fill=date_color)

    # 2. Roteer het blokje 180° (net als het hele scherm)
    img_rot = img.rotate(180)

    # 3. Zet om naar RGB565
    rgb565 = bytearray()
    for pixel in img_rot.getdata():
        r = pixel[0] >> 3
        g = pixel[1] >> 2
        b = pixel[2] >> 3
        val = (r << 11) | (g << 5) | b
        rgb565.append(val & 0xFF)
        rgb565.append((val >> 8) & 0xFF)

    # 4. Bereken framebuffer offset voor *geroteerde* klokpositie!
    fb_x = WIDTH - CLOCK_X - CLOCK_W
    fb_y = HEIGHT - CLOCK_Y - CLOCK_H
    fb_offset = (fb_y * WIDTH + fb_x) * 2

    # 5. Schrijf pixelblokken rij voor rij naar framebuffer
    with open(FRAMEBUFFER, "r+b") as f:
        for row in range(CLOCK_H):
            f.seek(fb_offset + row * WIDTH * 2)
            start = row * CLOCK_W * 2
            end = start + CLOCK_W * 2
            f.write(rgb565[start:end])

def update_coin_value_area(value_str, coin_color=(255,255,255)):
    """
    Snijdt coin value gebied uit cached achtergrond (in 0° orientatie), tekent de prijs erop,
    roteert het blokje, en schrijft het naar de juiste plek in framebuffer.
    """
    global _full_bg_cache
    if '_full_bg_cache' not in globals():
        return  # Geen achtergrond beschikbaar

    img = _full_bg_cache.crop((COIN_X, COIN_Y, COIN_X + COIN_W, COIN_Y + COIN_H))
    draw = ImageDraw.Draw(img)

    w, h = draw.textbbox((0, 0), value_str, font=font_value)[2:]
    # Tekst centreren in het coin value gebied
    draw.text(((COIN_W - w)//2, (COIN_H - h)//2), value_str, font=font_value, fill=coin_color)

    img_rot = img.rotate(180)

    rgb565 = bytearray()
    for pixel in img_rot.getdata():
        r = pixel[0] >> 3
        g = pixel[1] >> 2
        b = pixel[2] >> 3
        val = (r << 11) | (g << 5) | b
        rgb565.append(val & 0xFF)
        rgb565.append((val >> 8) & 0xFF)

    fb_x = WIDTH - COIN_X - COIN_W
    fb_y = HEIGHT - COIN_Y - COIN_H
    fb_offset = (fb_y * WIDTH + fb_x) * 2

    with open(FRAMEBUFFER, "r+b") as f:
        for row in range(COIN_H):
            f.seek(fb_offset + row * WIDTH * 2)
            start = row * COIN_W * 2
            end = start + COIN_W * 2
            f.write(rgb565[start:end])
