import time
import json
import os
import requests
from PIL import Image, ImageDraw, ImageFont

FRAMEBUFFER = "/dev/fb1"
WIDTH, HEIGHT = 480, 320

# Configuratie
CONFIG_FILE = "coins.json"
BG_FOLDER = "backgrounds"
BG_FALLBACK = os.path.join(BG_FOLDER, "btc-bg.png")
ROTATE_SECS = 20

# Fonts
FONT_BIG = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SMALL = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
font_main = ImageFont.truetype(FONT_BIG, 36)
font_value = ImageFont.truetype(FONT_BIG, 48)
font_time = ImageFont.truetype(FONT_BIG, 28)
font_date = ImageFont.truetype(FONT_SMALL, 20)

def load_coins(config_file=CONFIG_FILE):
    with open(config_file, "r") as f:
        cfg = json.load(f)
    # Alleen coins met 'show': true
    coins = [coin for coin in cfg.get("coins", []) if coin.get("show", True)]
    return coins

def get_price(coin):
    coingecko_id = coin.get("coingecko_id", coin.get("id"))
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd"
        r = requests.get(url, timeout=6)
        price = r.json()[coingecko_id]["usd"]
        return float(price)
    except Exception:
        return None

def hex_to_rgb(hex_color, fallback=(247,147,26)):
    # "#FF6600" -> (255,102,0)
    try:
        h = hex_color.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0,2,4))
    except:
        return fallback

def clear_framebuffer():
    with open(FRAMEBUFFER, 'wb') as f:
        f.write(bytearray([0x00, 0x00] * WIDTH * HEIGHT))

def draw_dashboard(btc_price, btc_color, coin, coin_price):
    # BTC background (of fallback)
    coin_id = coin["id"]
    coin_bg = os.path.join(BG_FOLDER, f"{coin_id}-bg.png")
    if not os.path.isfile(coin_bg):
        coin_bg = BG_FALLBACK
    image = Image.open(coin_bg).convert("RGB").resize((WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)

    # ---- Tijd en datum rechtsboven ----
    t = time.localtime()
    now_str = time.strftime("%H:%M:%S", t)
    date_str = time.strftime("%a %d %b %Y", t)
    time_w, time_h = draw.textbbox((0, 0), now_str, font=font_time)[2:]
    date_w, date_h = draw.textbbox((0, 0), date_str, font=font_date)[2:]
    draw.text((WIDTH - time_w - 20, 16), now_str, font=font_time, fill=(255,255,255))
    draw.text((WIDTH - date_w - 20, 16 + time_h + 2), date_str, font=font_date, fill=btc_color)

    # ---- BTC altijd zichtbaar als hoofdcoin (iets hoger in beeld) ----
    label = "BTC"
    price_text = "$" + (f"{btc_price:,.2f}" if btc_price is not None else "N/A")
    label_w, label_h = draw.textbbox((0, 0), label, font=font_main)[2:]
    price_w, price_h = draw.textbbox((0, 0), price_text, font=font_value)[2:]

    # BTC staat hoger in beeld en naar rechts voor ruimte
    right_offset = 60
    btc_label_y = int(HEIGHT * 0.35) - label_h
    btc_price_y = btc_label_y + label_h + 5
    draw.text(((WIDTH - label_w)//2 + right_offset, btc_label_y), label, font=font_main, fill=btc_color)
    draw.text(((WIDTH - price_w)//2 + right_offset, btc_price_y), price_text, font=font_value, fill=(255,255,255))

    # ---- Andere coin centraal onderin beeld (rotating) ----
    # Alleen tonen als niet BTC
    if coin["id"] != "btc":
        c_label = coin["symbol"]
        c_color = hex_to_rgb(coin["color"])
        c_price = "$" + (f"{coin_price:,.2f}" if coin_price is not None else "N/A")
        c_label_w, c_label_h = draw.textbbox((0, 0), c_label, font=font_main)[2:]
        c_price_w, c_price_h = draw.textbbox((0, 0), c_price, font=font_value)[2:]
        # Centraal iets onder BTC
        y_offset = int(HEIGHT * 0.75)
        c_label_y = y_offset - c_label_h
        c_price_y = c_label_y + c_label_h + 5
        draw.text(((WIDTH - c_label_w)//2 + right_offset, c_label_y), c_label, font=font_main, fill=c_color)
        draw.text(((WIDTH - c_price_w)//2 + right_offset, c_price_y), c_price, font=font_value, fill=(255,255,255))

    # ---- Rotatie voor LCD ----
    image = image.rotate(180)

    # ---- RGB565 little endian ----
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

def main():
    clear_framebuffer()
    coins = load_coins()
    btc_coin = next(c for c in coins if c["id"] == "btc")
    btc_color = hex_to_rgb(btc_coin["color"])
    btc_price = get_price(btc_coin)
    last_rot_time = 0
    coin_index = 0

    while True:
        now = time.time()
        # Elke 20 sec: andere coin
        if now - last_rot_time >= ROTATE_SECS:
            coin_index = (coin_index + 1) % len(coins)
            last_rot_time = now
        show_coin = coins[coin_index]
        # BTC altijd tonen als hoofdcoin (bovenin), maar roteren de ondercoin (behalve als het btc is, dan alleen BTC)
        show_coin_price = get_price(show_coin) if show_coin["id"] != "btc" else None
        btc_price = get_price(btc_coin)
        draw_dashboard(btc_price, btc_color, show_coin, show_coin_price)
        time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting dashboard... cleaning LCD screen.")
        clear_framebuffer()
        time.sleep(0.5)
        print("LCD is now blank. Goodbye!")
    except Exception as e:
        print("Error:", e)
        clear_framebuffer()
        time.sleep(1)
