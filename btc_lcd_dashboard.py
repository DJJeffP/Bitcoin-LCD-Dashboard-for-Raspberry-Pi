import time
import json
import os
import threading
import requests
import evdev
from PIL import Image, ImageDraw, ImageFont

DEBUG = False  # Set to True for crosshair and debug output

# ==== LCD / Touch Config ====
FRAMEBUFFER = "/dev/fb1"
WIDTH, HEIGHT = 480, 320
TOUCH_DEVICE = '/dev/input/event0'
CALIBRATION_FILE = "touch_calibration.json"

# ==== UI regions (pixels) ====
CLOCK_X = WIDTH - 160
CLOCK_Y = 16
CLOCK_W = 150
CLOCK_H = 60

COIN_X = 170
COIN_Y = 135
COIN_W = 240
COIN_H = 55

# ==== Fonts ====
FONT_BIG = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SMALL = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
font_main = ImageFont.truetype(FONT_BIG, 36)
font_value = ImageFont.truetype(FONT_BIG, 48)
font_time = ImageFont.truetype(FONT_BIG, 28)
font_date = ImageFont.truetype(FONT_SMALL, 20)

# ==== UI MODE ====
ui_mode = {'dashboard': True}

def clear_framebuffer():
    with open(FRAMEBUFFER, 'wb') as f:
        f.write(bytearray([0x00, 0x00] * WIDTH * HEIGHT))

# ==== Calibration ====
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

def draw_debug_crosshair(x, y, msg=""):
    image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    size = 18
    draw.line([(x-size, y), (x+size, y)], fill=(0,255,0), width=3)
    draw.line([(x, y-size), (x, y+size)], fill=(0,255,0), width=3)
    if msg:
        font = ImageFont.truetype(FONT_SMALL, 24)
        draw.text((10, HEIGHT-35), msg, fill=(255,255,0), font=font)
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
    device = evdev.InputDevice(TOUCH_DEVICE)

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

def is_in_clock_area(x, y):
    return x >= 428

# ==== Config ====
CONFIG_FILE = "coins.json"
BG_FOLDER = "backgrounds"
BG_FALLBACK = os.path.join(BG_FOLDER, "btc-bg.png")
ROTATE_SECS = 20
PRICE_UPDATE_SECS = 60

def load_coins(config_file=CONFIG_FILE):
    with open(config_file, "r") as f:
        cfg = json.load(f)
    coins = [coin for coin in cfg.get("coins", [])]
    return coins

# === Price Caching ===
price_cache = {}
price_cache_lock = threading.Lock()

def price_updater(coins):
    while True:
        ids = [coin.get("coingecko_id", coin.get("id")) for coin in coins]
        ids_param = ",".join(ids)
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_param}&vs_currencies=usd"
            r = requests.get(url, timeout=8)
            prices = r.json()
            for coin in coins:
                coingecko_id = coin.get("coingecko_id", coin.get("id"))
                price = prices.get(coingecko_id, {}).get("usd")
                if price is not None:
                    with price_cache_lock:
                        price_cache[coingecko_id] = float(price)
                    if DEBUG:
                        print(f"[INFO] Updated {coin['symbol']} price: {price}")
                else:
                    try:
                        url_single = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd"
                        r_single = requests.get(url_single, timeout=8)
                        single_price = r_single.json().get(coingecko_id, {}).get("usd")
                        if single_price is not None:
                            with price_cache_lock:
                                price_cache[coingecko_id] = float(single_price)
                            if DEBUG:
                                print(f"[FALLBACK] Updated {coin['symbol']} price (single): {single_price}")
                        else:
                            binance_symbol = coin.get("binance_symbol")
                            if binance_symbol:
                                binance_url = f"https://api.binance.com/api/v3/ticker/price?symbol={binance_symbol}"
                                r_bin = requests.get(binance_url, timeout=8)
                                if r_bin.ok:
                                    price_bin = float(r_bin.json().get("price", 0))
                                    if price_bin > 0:
                                        with price_cache_lock:
                                            price_cache[coingecko_id] = price_bin
                                        if DEBUG:
                                            print(f"[BINANCE] Updated {coin['symbol']} price: {price_bin}")
                                    else:
                                        print(f"[WARNING] {coin['symbol']} not found at Binance ({binance_symbol}): {r_bin.text}")
                                else:
                                    print(f"[WARNING] {coin['symbol']} Binance API error: {r_bin.text}")
                            else:
                                print(f"[WARNING] {coin['symbol']} not found in any API (ID: {coingecko_id})")
                    except Exception as e2:
                        print(f"[ERROR] Fallback failed for {coingecko_id}: {e2}")
        except Exception as e:
            print(f"[ERROR] API call failed: {e}")
        time.sleep(PRICE_UPDATE_SECS)

def get_cached_price(coin):
    coingecko_id = coin.get("coingecko_id", coin.get("id"))
    with price_cache_lock:
        return price_cache.get(coingecko_id)

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
    image = Image.open(coin_bg).convert("RGB").resize((WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    t = time.localtime()
    now_str = time.strftime("%H:%M:%S", t)
    date_str = time.strftime("%a %d %b %Y", t)
    time_w, time_h = draw.textbbox((0, 0), now_str, font=font_time)[2:]
    date_w, date_h = draw.textbbox((0, 0), date_str, font=font_date)[2:]
    draw.text((WIDTH - time_w - 20, 16), now_str, font=font_time, fill=(255,255,255))
    draw.text((WIDTH - date_w - 20, 16 + time_h + 2), date_str, font=font_date, fill=btc_color)
    label = "BTC"
    price_text = "$" + (str(btc_price) if btc_price is not None else "N/A")
    label_w, label_h = draw.textbbox((0, 0), label, font=font_main)[2:]
    price_w, price_h = draw.textbbox((0, 0), price_text, font=font_value)[2:]
    right_offset = 60
    btc_label_y = int(HEIGHT * 0.35) - label_h
    btc_price_y = btc_label_y + label_h + 5
    draw.text(((WIDTH - label_w)//2 + right_offset, btc_label_y), label, font=font_main, fill=btc_color)
    draw.text(((WIDTH - price_w)//2 + right_offset, btc_price_y), price_text, font=font_value, fill=(255,255,255))
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

# --- [Insert your full setup screen, handle_setup_touch, setup_touch_listener, etc. code here] ---
# (Use the latest versions from previous answers—keyboard above SAVE, getbbox, scroll, etc.)

def main():
    global calib
    calib = load_calibration()
    clear_framebuffer()
    coins = load_coins()
    btc_coin = next(c for c in coins if c["id"] == "btc")
    btc_color = hex_to_rgb(btc_coin["color"])
    t_price = threading.Thread(target=price_updater, args=(coins,), daemon=True)
    t_price.start()
    t_touch = threading.Thread(target=double_tap_detector, args=(switch_to_setup,), daemon=True)
    t_touch.start()
    last_rot_time = 0
    coin_index = 0
    last_clock_str = ""
    last_coin_val_str = ""
    while True:
        if ui_mode['dashboard']:
            now = time.localtime()
            now_str = time.strftime("%H:%M:%S", now)
            date_str = time.strftime("%a %d %b %Y", now)
            btc_price = get_cached_price(btc_coin)
            show_coin = coins[coin_index]
            show_coin_price = get_cached_price(show_coin) if show_coin["id"] != "btc" else None
            coin_label = show_coin["symbol"]
            coin_val_str = "$" + (str(show_coin_price) if show_coin_price is not None else "N/A")
            redraw_full = False
            if now - last_rot_time >= ROTATE_SECS:
                coin_index = (coin_index + 1) % len(coins)
                last_rot_time = now
                redraw_full = True
            if redraw_full:
                draw_dashboard(btc_price, btc_color, show_coin, show_coin_price)
                last_coin_val_str = coin_val_str
                last_clock_str = now_str
            if now_str != last_clock_str:
                update_clock_area()
                last_clock_str = now_str
            if coin_val_str != last_coin_val_str:
                update_coin_value_area(coin_val_str)
                last_coin_val_str = coin_val_str
            time.sleep(0.1)
        else:
            setup_touch_listener(coins)
            time.sleep(0.1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting dashboard... cleaning LCD screen.")
        clear_framebuffer()
        time.sleep(0.5)
        print("LCD is now blank. Goodbye!")
    except Exception as e:
        import traceback
        print("Error:", e)
        traceback.print_exc()
        clear_framebuffer()
        time.sleep(1)
