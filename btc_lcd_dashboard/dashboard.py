# dashboard.py
"""
Dashboard-drawing: volledig scherm en partiële updates (clock/coin value).
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Schermparameters
WIDTH, HEIGHT = 480, 320
FRAMEBUFFER = "/dev/fb1"
BG_FOLDER = "backgrounds"
BG_FALLBACK = os.path.join(BG_FOLDER, "btc-bg.png")

# UI-gebieden voor snelle updates
CLOCK_X = WIDTH - 160
CLOCK_Y = 16
CLOCK_W = 150
CLOCK_H = 60

COIN_X = 170
COIN_Y = 135
COIN_W = 240
COIN_H = 55

# Fonts
FONT_BIG = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SMALL = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
font_main = ImageFont.truetype(FONT_BIG, 36)
font_value = ImageFont.truetype(FONT_BIG, 48)
font_time = ImageFont.truetype(FONT_BIG, 28)
font_date = ImageFont.truetype(FONT_SMALL, 20)

def draw_dashboard(btc_price, btc_color, coin, coin_price):
    """
    Tekent het volledige dashboard en schrijft dit naar het framebuffer.
    """
    coin_id = coin["id"]
    coin_bg = os.path.join(BG_FOLDER, f"{coin_id}-bg.png")
    if not os.path.isfile(coin_bg):
        coin_bg = BG_FALLBACK
    image = Image.open(coin_bg).convert("RGB").resize((WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    # Tijd & datum
    t = time.localtime()
    now_str = time.strftime("%H:%M:%S", t)
    date_str = time.strftime("%a %d %b %Y", t)
    time_w, time_h = draw.textbbox((0, 0), now_str, font=font_time)[2:]
    date_w, date_h = draw.textbbox((0, 0), date_str, font=font_date)[2:]
    draw.text((WIDTH - time_w - 20, 16), now_str, font=font_time, fill=(255,255,255))
    draw.text((WIDTH - date_w - 20, 16 + time_h + 2), date_str, font=font_date, fill=btc_color)
    # BTC (altijd bovenin)
    label = "BTC"
    price_text = "$" + (str(btc_price) if btc_price is not None else "N/A")
    label_w, label_h = draw.textbbox((0, 0), label, font=font_main)[2:]
    price_w, price_h = draw.textbbox((0, 0), price_text, font=font_value)[2:]
    right_offset = 60
    btc_label_y = int(HEIGHT * 0.35) - label_h
    btc_price_y = btc_label_y + label_h + 5
    draw.text(((WIDTH - label_w)//2 + right_offset, btc_label_y), label, font=font_main, fill=btc_color)
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
    # Rotatie voor LCD
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

def update_clock_area():
    """
    Schrijft alleen het klok/date-gebied bij op het scherm.
    """
    import time
    t = time.localtime()
    now_str = time.strftime("%H:%M:%S", t)
    date_str = time.strftime("%a %d %b %Y", t)
    img = Image.new("RGB", (CLOCK_W, CLOCK_H), (40, 40, 40))
    draw = ImageDraw.Draw(img)
    draw.text((10, 0), now_str, font=font_time, fill=(255,255,255))
    draw.text((10, 30), date_str, font=font_date, fill=(255,255,255))
    img = img.rotate(180)
    rgb565 = bytearray()
    for pixel in img.getdata():
        r = pixel[0] >> 3
        g = pixel[1] >> 2
        b = pixel[2] >> 3
        value = (r << 11) | (g << 5) | b
        rgb565.append(value & 0xFF)
        rgb565.append((value >> 8) & 0xFF)
    fb_offset = (CLOCK_Y * WIDTH + CLOCK_X) * 2
    with open(FRAMEBUFFER, "r+b") as f:
        for row in range(CLOCK_H):
            f.seek(fb_offset + row * WIDTH * 2)
            start = row * CLOCK_W * 2
            end = start + CLOCK_W * 2
            f.write(rgb565[start:end])

def update_coin_value_area(value_str, coin_color=(255,255,255)):
    """
    Schrijft alleen het coin-value gebied bij.
    """
    img = Image.new("RGB", (COIN_W, COIN_H), (0,0,0))
    draw = ImageDraw.Draw(img)
    w, h = draw.textbbox((0,0), value_str, font=font_value)[2:]
    draw.text(((COIN_W - w)//2, (COIN_H - h)//2), value_str, font=font_value, fill=coin_color)
    img = img.rotate(180)
    rgb565 = bytearray()
    for pixel in img.getdata():
        r = pixel[0] >> 3
        g = pixel[1] >> 2
        b = pixel[2] >> 3
        value = (r << 11) | (g << 5) | b
        rgb565.append(value & 0xFF)
        rgb565.append((value >> 8) & 0xFF)
    fb_offset = (COIN_Y * WIDTH + COIN_X) * 2
    with open(FRAMEBUFFER, "r+b") as f:
        for row in range(COIN_H):
            f.seek(fb_offset + row * WIDTH * 2)
            start = row * COIN_W * 2
            end = start + COIN_W * 2
            f.write(rgb565[start:end])

# Importeer deze helper uit utils of kopieer hierheen
def hex_to_rgb(hex_color, fallback=(247,147,26)):
    try:
        h = hex_color.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0,2,4))
    except:
        return fallback
