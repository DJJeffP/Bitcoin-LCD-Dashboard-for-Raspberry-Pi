import time
import json
import os
import threading
import requests
import evdev
from PIL import Image, ImageDraw, ImageFont

# ==== LCD / Touch Config ====
FRAMEBUFFER = "/dev/fb1"
WIDTH, HEIGHT = 480, 320
TOUCH_DEVICE = '/dev/input/event0'

def scale_touch(x, y):
    # Map raw touch to screen pixel coordinates (your calibration)
    pixel_x = int(x * 480 / 3592)
    pixel_y = int(y * 320 / 3732)
    return pixel_x, pixel_y

def is_in_clock_area(x, y):
    # Top-right: x >= 428 (your "clock area")
    return x >= 428

# ==== Config ====
CONFIG_FILE = "coins.json"
BG_FOLDER = "backgrounds"
BG_FALLBACK = os.path.join(BG_FOLDER, "btc-bg.png")
ROTATE_SECS = 20
PRICE_UPDATE_SECS = 60  # Cache verversen

# ==== Fonts ====
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
                    print(f"[INFO] Updated {coin['symbol']} price: {price}")
                else:
                    # Fallback: probeer single request CoinGecko
                    try:
                        url_single = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd"
                        r_single = requests.get(url_single, timeout=8)
                        single_price = r_single.json().get(coingecko_id, {}).get("usd")
                        if single_price is not None:
                            with price_cache_lock:
                                price_cache[coingecko_id] = float(single_price)
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

def clear_framebuffer():
    with open(FRAMEBUFFER, 'wb') as f:
        f.write(bytearray([0x00, 0x00] * WIDTH * HEIGHT))

# ==== UI MODE ====
ui_mode = {'dashboard': True}  # Shared between threads

# ==== Dashboard Drawing ====
def draw_dashboard(btc_price, btc_color, coin, coin_price):
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
    price_text = "$" + (str(btc_price) if btc_price is not None else "N/A")
    label_w, label_h = draw.textbbox((0, 0), label, font=font_main)[2:]
    price_w, price_h = draw.textbbox((0, 0), price_text, font=font_value)[2:]
    right_offset = 60
    btc_label_y = int(HEIGHT * 0.35) - label_h
    btc_price_y = btc_label_y + label_h + 5
    draw.text(((WIDTH - label_w)//2 + right_offset, btc_label_y), label, font=font_main, fill=btc_color)
    draw.text(((WIDTH - price_w)//2 + right_offset, btc_price_y), price_text, font=font_value, fill=(255,255,255))

    # ---- Andere coin centraal onderin beeld (rotating) ----
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

# ==== SETUP/SEARCH SCREEN (SIMPLE) ====
def draw_setup_screen():
    image = Image.new("RGB", (WIDTH, HEIGHT), (30,30,60))
    draw = ImageDraw.Draw(image)
    # Title bar
    draw.rectangle([0, 0, WIDTH, 55], fill=(50,50,90))
    font = ImageFont.truetype(FONT_BIG, 28)
    draw.text((20, 10), "SETUP / COIN SEARCH", fill=(255,255,255), font=font)
    # Save button
    draw.rectangle([WIDTH-160, HEIGHT-70, WIDTH-20, HEIGHT-20], fill=(60,130,60))
    draw.text((WIDTH-150, HEIGHT-58), "SAVE", fill=(255,255,255), font=font)
    # You can add: search bar, keyboard, toggles etc. here!
    # ---- Rotatie voor LCD ----
    image = image.rotate(180)
    # Write to framebuffer
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

def handle_setup_touch(x, y):
    # Remember, screen is rotated, but touch is not!
    # SAVE button: right-bottom corner: WIDTH-160, HEIGHT-70, WIDTH-20, HEIGHT-20
    if WIDTH-160 <= x <= WIDTH-20 and HEIGHT-70 <= y <= HEIGHT-20:
        print("[SETUP] SAVE button touched! Returning to dashboard.")
        switch_to_dashboard()

def setup_touch_listener():
    device = evdev.InputDevice(TOUCH_DEVICE)
    raw_x, raw_y = 0, 0
    for event in device.read_loop():
        if ui_mode['dashboard']:
            break  # Exit listener if user left setup mode
        if event.type == evdev.ecodes.EV_ABS:
            if event.code == evdev.ecodes.ABS_X:
                raw_x = event.value
            elif event.code == evdev.ecodes.ABS_Y:
                raw_y = event.value
        elif event.type == evdev.ecodes.EV_KEY and event.code == evdev.ecodes.BTN_TOUCH and event.value == 1:
            x, y = scale_touch(raw_x, raw_y)
            print(f"[DEBUG][SETUP] Touch at x={x}, y={y}")
            handle_setup_touch(x, y)

# ==== DASHBOARD <--> SETUP MODE SWITCH ====
def switch_to_setup():
    print(">>> Switching to SETUP mode!")
    ui_mode['dashboard'] = False

def switch_to_dashboard():
    print(">>> Returning to DASHBOARD mode!")
    ui_mode['dashboard'] = True

# ==== DOUBLE-TAP DETECTOR THREAD ====
def double_tap_detector(trigger_callback):
    device = evdev.InputDevice(TOUCH_DEVICE)
    last_tap_time = 0
    DOUBLE_TAP_MAX_INTERVAL = 0.4  # seconds
    raw_x, raw_y = 0, 0
    for event in device.read_loop():
        if event.type == evdev.ecodes.EV_ABS:
            if event.code == evdev.ecodes.ABS_X:
                raw_x = event.value
            elif event.code == evdev.ecodes.ABS_Y:
                raw_y = event.value
        elif event.type == evdev.ecodes.EV_KEY and event.code == evdev.ecodes.BTN_TOUCH and event.value == 1:
            x, y = scale_touch(raw_x, raw_y)
            print(f"[DEBUG] Touch at x={x}, y={y}")
            now = time.time()
            if is_in_clock_area(x, y):
                if last_tap_time and (now - last_tap_time < DOUBLE_TAP_MAX_INTERVAL):
                    print("[TOUCH] Double tap detected in clock area!")
                    trigger_callback()
                    last_tap_time = 0
                else:
                    last_tap_time = now

# ==== MAIN PROGRAM ====
def main():
    clear_framebuffer()
    coins = load_coins()
    btc_coin = next(c for c in coins if c["id"] == "btc")
    btc_color = hex_to_rgb(btc_coin["color"])

    # Start background price updater
    t_price = threading.Thread(target=price_updater, args=(coins,), daemon=True)
    t_price.start()

    # Start double-tap detector for switching to setup
    t_touch = threading.Thread(target=double_tap_detector, args=(switch_to_setup,), daemon=True)
    t_touch.start()

    last_rot_time = 0
    coin_index = 0

    while True:
        if ui_mode['dashboard']:
            now = time.time()
            if now - last_rot_time >= ROTATE_SECS:
                coin_index = (coin_index + 1) % len(coins)
                last_rot_time = now
            show_coin = coins[coin_index]
            btc_price = get_cached_price(btc_coin)
            show_coin_price = get_cached_price(show_coin) if show_coin["id"] != "btc" else None
            draw_dashboard(btc_price, btc_color, show_coin, show_coin_price)
            time.sleep(0.95)
        else:
            # Setup/Search mode
            draw_setup_screen()
            setup_touch_listener()
            time.sleep(0.1)  # Small sleep to avoid tight loop

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
