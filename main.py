import threading
import time
import sys
import termios
import tty
from calibration import load_calibration
from dashboard import draw_dashboard, update_clock_area, update_coin_value_area_variable, textbox_offset
from setup_screen import setup_touch_listener
from touchscreen import double_tap_detector
from price import price_updater, get_cached_price
from utils import clear_framebuffer, hex_to_rgb
import json

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

def reload_coins(config_file="coins.json", show_all=False):
    with open(config_file, "r") as f:
        cfg = json.load(f)
    if show_all:
        return cfg.get("coins", [])
    coins = [coin for coin in cfg.get("coins", []) if coin.get("show", True)]
    if not coins:
        coins = [{"id": "btc", "symbol": "BTC", "color": "#f7931a", "show": True}]
    return coins


def main():
    calib = load_calibration()
    clear_framebuffer()
    coins = reload_coins()
    btc_coin = next(c for c in coins if c["id"] == "btc")
    btc_color = hex_to_rgb(btc_coin["color"])

    t_price = threading.Thread(target=price_updater, args=(coins,), daemon=True)
    t_price.start()
    t_touch = threading.Thread(target=double_tap_detector, args=(switch_to_setup,), daemon=True)
    t_touch.start()

    last_rot_time = time.time()
    coin_index = 0
    last_clock_str = ""
    _prev_coin_box = None

    btc_price = get_cached_price(btc_coin)
    show_coin = coins[coin_index]
    show_coin_price = get_cached_price(show_coin)
    draw_dashboard(btc_price, btc_color, show_coin, show_coin_price)

    while True:
        if ui_mode['dashboard']:
            now = time.time()
            t_struct = time.localtime(now)
            now_str = time.strftime("%H:%M:%S", t_struct)

            btc_price = get_cached_price(btc_coin)

            # Live reload na elke rotatie
            if now - last_rot_time >= 20:
                coins = reload_coins()
                coin_index = (coin_index + 1) % len(coins)
                last_rot_time = now
                show_coin = coins[coin_index]
                show_coin_price = get_cached_price(show_coin)
                draw_dashboard(btc_price, btc_color, show_coin, show_coin_price)
                last_clock_str = ""
                _prev_coin_box = None
            else:
                show_coin = coins[coin_index]
                show_coin_price = get_cached_price(show_coin)

            update_coin_value_area_variable(show_coin["symbol"], show_coin_price, hex_to_rgb(show_coin["color"]), textbox_offset)

            if now_str != last_clock_str:
                update_clock_area(btc_color)
                last_clock_str = now_str

            time.sleep(0.1)
        else:
            # LET OP: laadt altijd ALLE coins in setup, niet gefilterd!
            setup_touch_listener(reload_coins(config_file="coins.json", show_all=True), switch_to_dashboard)
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
        wait_for_keypress()
        clear_framebuffer()
        time.sleep(1)
