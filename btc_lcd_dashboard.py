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
CALIBRATION_FILE = "touch_calibration.json"
DEBUG = False  # Set to True for debug prints/crosshair

# ==== Fonts ====
FONT_BIG = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SMALL = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
font_main = ImageFont.truetype(FONT_BIG, 36)
font_value = ImageFont.truetype(FONT_BIG, 48)
font_time = ImageFont.truetype(FONT_BIG, 28)
font_date = ImageFont.truetype(FONT_SMALL, 20)

# ==== UI MODE ====
ui_mode = {'dashboard': True}  # Shared between threads

def clear_framebuffer():
    with open(FRAMEBUFFER, 'wb') as f:
        f.write(bytearray([0x00, 0x00] * WIDTH * HEIGHT))

# ==== Touchscreen Calibration ====
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

def draw_crosshair(x, y, msg=""):
    image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    size = 20
    draw.line([(x-size, y), (x+size, y)], fill=(0,255,0), width=3)
    draw.line([(x, y-size), (x, y+size)], fill=(0,255,0), width=3)
    font = ImageFont.truetype(FONT_SMALL, 24)
    draw.text((WIDTH//2 - 80, HEIGHT-40), msg, fill=(255,255,255), font=font)
    # Rotate for LCD!
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
    # Unpack
    screen_points = calib["screen_points"]
    raw_points = calib["raw_points"]

    # We'll use top-left (idx 0) and bottom-right (idx 2)
    (sx0, sy0), (sx1, sy1) = screen_points[0], screen_points[2]
    (rx0, ry0), (rx1, ry1) = raw_points[0], raw_points[2]

    # x axis: map raw y to screen x (due to 90deg rotation)
    # y axis: map raw x to screen y (due to 90deg rotation)
    # And flip if needed (if calibration shows min > max)
    if rx1 == rx0: rx1 += 1
    if ry1 == ry0: ry1 += 1
    if sx1 == sx0: sx1 += 1
    if sy1 == sy0: sy1 += 1

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
PRICE_UPDATE_SECS = 60  # Cache verversen

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
                    print(f"[INFO] Updated {coin['symbol']} price: {price}")
                else:
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

    # ---- BTC altijd zichtbaar als hoofdcoin ----
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

def draw_coin_toggle_list(coins, scroll=0, search_text="", search_focused=False):
    # Filter coins using search_text
    matches = []
    st = search_text.strip().lower()
    for coin in coins:
        if st == "" or st in coin['symbol'].lower() or st in coin['name'].lower():
            matches.append(coin)
    visible = matches[scroll:scroll+6]
    image = Image.new("RGB", (WIDTH, HEIGHT), (30,30,60))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(FONT_SMALL, 26)
    font_search = ImageFont.truetype(FONT_SMALL, 24)
    
    # Title
    draw.rectangle([0, 0, WIDTH, 55], fill=(50,50,90))
    draw.text((20, 10), "SETUP: Toggle/Search", fill=(255,255,255), font=font)
    
    # Search bar
    draw.rectangle([20, 55, WIDTH-20, 95], fill=(60,60,100))
    draw.text((30, 65), f"Search: {search_text}", fill=(255,255,255), font=font_search)
    if search_focused:
        draw.rectangle([18, 53, WIDTH-18, 97], outline=(80,255,80), width=2)
    
    # Coin list (max 6 on screen, scrolling)
    for i, coin in enumerate(visible):
        y = 105 + i*40
        toggle_box = [30, y, 70, y+30]
        fill = (90,230,90) if coin.get("show", True) else (130,130,130)
        draw.rectangle(toggle_box, fill=fill)
        text = f"{coin['symbol']} - {coin['name']}"
        draw.text((80, y), text, fill=(255,255,255), font=font)

    # Up scroll arrow (top right, above coin list)
    scroll_up_x = WIDTH - 60
    scroll_up_y = 105
    draw.polygon([(scroll_up_x, scroll_up_y), (scroll_up_x+30, scroll_up_y), (scroll_up_x+15, scroll_up_y-20)], fill=(255,255,255))
    # Down scroll arrow (bottom right, below coin list)
    scroll_down_x = WIDTH - 60
    scroll_down_y = 105 + 6*40
    draw.polygon([(scroll_down_x, scroll_down_y), (scroll_down_x+30, scroll_down_y), (scroll_down_x+15, scroll_down_y+20)], fill=(255,255,255))

    # Save button at bottom right
    save_left = WIDTH - 180
    save_right = WIDTH - 50
    save_top = HEIGHT - 70
    save_bottom = HEIGHT - 20
    draw.rectangle([save_left, save_top, save_right, save_bottom], fill=(60,130,60))
    draw.text((save_left+15, save_top+12), "SAVE", fill=(255,255,255), font=font_search)
    # Keyboard only if search bar focused
    if search_focused:
        keys = [
            "QWERTYUIOP",
            "ASDFGHJKL",
            "ZXCVBNM<-"
        ]
        key_w = 38
        total_key_row_width = 10 * key_w + 9 * 4  # 10 keys, 9 spaces, per row
        key_start_x = (WIDTH - total_key_row_width) // 2
        key_h = 38
        key_start_y = HEIGHT-160
        for row_idx, row in enumerate(keys):
            yk = key_start_y + row_idx * (key_h + 4)
            for col_idx, char in enumerate(row):
                xk = key_start_x + col_idx * (key_w + 4)
                draw.rectangle([xk, yk, xk+key_w, yk+key_h], fill=(80,80,80))
                draw.text((xk+10, yk+8), char, font=font_search, fill=(255,255,255))

    
    # Scroll buttons
    if scroll > 0:
        draw.polygon([(WIDTH-60,110), (WIDTH-30,110), (WIDTH-45,90)], fill=(255,255,255))
    if scroll+6 < len(matches):
        draw.polygon([(WIDTH-60,340), (WIDTH-30,340), (WIDTH-45,360)], fill=(255,255,255))
    
    # Rotate for LCD
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
    return matches, font

def handle_setup_touch(x, y, coins, scroll, search_text, search_focused, matches, font):
    # 1. SAVE button is always on top!
    save_left = WIDTH - 180
    save_right = WIDTH - 50
    save_top = HEIGHT - 70
    save_bottom = HEIGHT - 20
    if save_left <= x <= save_right and save_top <= y <= save_bottom:
        print("[SETUP] SAVE button touched! Saving coins.json and returning to dashboard.")
        with open(CONFIG_FILE, "w") as f:
            json.dump({"coins": coins}, f, indent=2)
        switch_to_dashboard()
        return True, scroll, search_text, False

    # 2. Search bar focus
    if 20 <= x <= WIDTH-20 and 55 <= y <= 95:
        return False, scroll, search_text, True

    # 3. Keyboard keys (only if search focused)
    if search_focused:
        key_w = 38
        key_h = 38
        key_start_y = HEIGHT-160
        for row_idx, row in enumerate(["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM<-"]):
            yk = key_start_y + row_idx * (key_h + 4)
            for col_idx, char in enumerate(row):
                xk = 200 + col_idx * (key_w + 4)
                if xk <= x <= xk+key_w and yk <= y <= yk+key_h:
                    if char == "<":
                        search_text = search_text[:-1]
                    else:
                        search_text += char
                    return False, scroll, search_text, True

    # 4. Coin toggles (hitbox is name text or box, not row)
    for i in range(6):
        y_coin = 105 + i*40
        if i < len(matches):
            coin = matches[scroll+i]
            text = f"{coin['symbol']} - {coin['name']}"
            text_w, _ = font.getsize(text)
            x_name_start = 80
            x_name_end = x_name_start + text_w
            toggle_box_x1 = 30
            toggle_box_x2 = 70
            # If touch is on toggle box OR on coin text (plus margin)
            if ((toggle_box_x1 <= x <= toggle_box_x2) or
                (x_name_start - 8 <= x <= x_name_end + 8)) and y_coin <= y <= y_coin+30:
                orig_idx = coins.index(coin)
                coins[orig_idx]["show"] = not coins[orig_idx].get("show", True)
                print(f"[SETUP] Toggled {coin['symbol']}, now show={coins[orig_idx]['show']}")
                return False, scroll, search_text, False

    # 5. Scroll up button
    if (WIDTH - 60) <= x <= (WIDTH - 30) and (105-20) <= y <= (105+10):
        if scroll > 0:
            return False, scroll-1, search_text, search_focused

    # 6. Scroll down button
    if (WIDTH - 60) <= x <= (WIDTH - 30) and (105+6*40) <= y <= (105+6*40+20):
        if (scroll+6) < len(matches):
            return False, scroll+1, search_text, search_focused


    # 7. Click anywhere else: remove focus from search
    return False, scroll, search_text, False

def setup_touch_listener(coins):
    device = evdev.InputDevice(TOUCH_DEVICE)
    raw_x, raw_y = 0, 0
    finger_down = False
    scroll = 0
    search_text = ""
    search_focused = False
    while not ui_mode['dashboard']:
        matches, font = draw_coin_toggle_list(coins, scroll=scroll, search_text=search_text, search_focused=search_focused)
        for event in device.read_loop():
            if ui_mode['dashboard']:
                return
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
                    if DEBUG:
                        draw_debug_crosshair(x, y, f"({x}, {y})")
                        print(f"[DEBUG][SETUP] Touch at x={x}, y={y} (on finger UP)")
                    should_exit, scroll, search_text, search_focused = handle_setup_touch(
                        x, y, coins, scroll, search_text, search_focused, matches, font)
                    if should_exit:
                        return
                    break  # redraw after every tap

def switch_to_setup():
    if not ui_mode['dashboard']:
        return
    print(">>> Switching to SETUP mode!")
    ui_mode['dashboard'] = False

def switch_to_dashboard():
    print(">>> Returning to DASHBOARD mode!")
    ui_mode['dashboard'] = True

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
            if DEBUG:
                print(f"[DEBUG] Touch at x={x}, y={y}")
            now = time.time()
            if is_in_clock_area(x, y):
                if last_tap_time and (now - last_tap_time < DOUBLE_TAP_MAX_INTERVAL):
                    print("[TOUCH] Double tap detected in clock area!")
                    trigger_callback()
                    last_tap_time = 0
                else:
                    last_tap_time = now

def main():
    # ---- Touch Calibration (runs before anything else) ----
    global calib
    calib = load_calibration()  # This will block and calibrate if not done yet

    # ---- Only now do the rest of your setup ----
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
            time.sleep(0.95)  # Tight 1-second update
        else:
            # Setup/Search mode
            setup_touch_listener(coins)
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
        import traceback
        print("Error:", e)
        traceback.print_exc()
        clear_framebuffer()
        time.sleep(1)
