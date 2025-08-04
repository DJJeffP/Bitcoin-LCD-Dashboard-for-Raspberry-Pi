import threading
import time
import sys
import termios
import tty
from calibration import load_calibration
from dashboard import draw_dashboard, update_clock_area, update_coin_value_area
from setup_screen import setup_touch_listener
from touchscreen import double_tap_detector
from price import price_updater, get_cached_price
from utils import clear_framebuffer, hex_to_rgb
import json

# UI-modus (shared state)
ui_mode = {'dashboard': True}

def wait_for_keypress():
    print("\nPress any key to exit...")
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def switch_to_setup():
    if not ui_mode['dashboard']:
        return
    print(">>> Switching to SETUP mode!")
    ui_mode['dashboard'] = False

def switch_to_dashboard():
    print(">>> Returning to DASHBOARD mode!")
    ui_mode['dashboard'] = True

def load_coins(config_file="coins.json"):
    with open(config_file, "r") as f:
        cfg = json.load(f)
    coins = [coin for coin in cfg.get("coins", [])]
    return coins

def main():
    calib = load_calibration()  # Kalibratie altijd eerst
    clear_framebuffer()
    coins = load_coins()
    btc_coin = next(c for c in coins if c["id"] == "btc")
    btc_color = hex_to_rgb(btc_coin["color"])

    # Start prijs-thread
    t_price = threading.Thread(target=price_updater, args=(coins,), daemon=True)
    t_price.start()
    # Start double-tap detector thread
    t_touch = threading.Thread(target=double_tap_detector, args=(switch_to_setup,), daemon=True)
    t_touch.start()

    last_rot_time = time.time()
    coin_index = 0
    last_clock_str = ""
    last_coin_val_str = ""

    while True:
        if ui_mode['dashboard']:
            now = time.time()
            t_struct = time.localtime(now)
            now_str = time.strftime("%H:%M:%S", t_struct)
            date_str = time.strftime("%a %d %b %Y", t_struct)
            btc_price = get_cached_price(btc_coin)
            show_coin = coins[coin_index]
            show_coin_price = get_cached_price(show_coin) if show_coin["id"] != "btc" else None
            coin_label = show_coin["symbol"]
            coin_val_str = "$" + (str(show_coin_price) if show_coin_price is not None else "N/A")

            redraw_full = False
            if now - last_rot_time >= 20:
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
            setup_touch_listener(coins, switch_to_dashboard)
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
        wait_for_keypress()  # <-- Wacht hier op toets voordat verder
        clear_framebuffer()
        time.sleep(1)

