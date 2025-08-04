import threading
import time
import sys
import termios
import tty
from calibration import load_calibration
from dashboard import draw_dashboard, update_clock_area, draw_text_overlay_box, textbox_offset
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

def load_coins(config_file="coins.json"):
    with open(config_file, "r") as f:
        cfg = json.load(f)
    coins = [coin for coin in cfg.get("coins", [])]
    return coins

def main():
    calib = load_calibration()
    clear_framebuffer()
    coins = load_coins()
    btc_coin = next(c for c in coins if c["id"] == "btc")
    btc_color = hex_to_rgb(btc_coin["color"])

    t_price = threading.Thread(target=price_updater, args=(coins,), daemon=True)
    t_price.start()
    t_touch = threading.Thread(target=double_tap_detector, args=(switch_to_setup,), daemon=True)
    t_touch.start()

    last_rot_time = time.time()
    coin_index = 0
    last_clock_str = ""

    global _prev_btc_box, _prev_coin_box
    _prev_btc_box = None
    _prev_coin_box = None

    # On first run, always draw dashboard:
    redraw_full = True

    while True:
        if ui_mode['dashboard']:
            now = time.time()
            t_struct = time.localtime(now)
            now_str = time.strftime("%H:%M:%S", t_struct)

            btc_price = get_cached_price(btc_coin)
            show_coin = coins[coin_index]
            show_coin_price = get_cached_price(show_coin)
            coin_symbol = show_coin["symbol"]
            coin_color = hex_to_rgb(show_coin["color"])

            # Detect coin switch for rotation
            if now - last_rot_time >= 20:
                coin_index = (coin_index + 1) % len(coins)
                last_rot_time = now
                redraw_full = True

            if redraw_full or _prev_btc_box is None or _prev_coin_box is None:
                draw_dashboard(btc_price, btc_color, show_coin, show_coin_price)
                last_clock_str = ""
                _prev_btc_box = None
                _prev_coin_box = None
                redraw_full = False  # <-- BELANGRIJK: direct na redraw terug op False!
                # Geen overlays tekenen deze iteratie
            else:
                # --- Overlay BTC box ---
                btc_top = "BTC"
                btc_value = "$" + (str(btc_price) if btc_price is not None else "N/A")
                btc_y = _btc_label_y
                btc_color = hex_to_rgb(btc_coin["color"])
                _prev_btc_box = draw_text_overlay_box(
                    btc_top, btc_value, btc_color, textbox_offset, btc_y, prev_box=_prev_btc_box
                )
                print("[DEBUG] BTC overlay: top:", btc_top, "value:", btc_value, "y:", btc_y)
                print("[DEBUG] COIN overlay: top:", coin_top, "value:", coin_value, "y:", coin_y, "color:", coin_color)

                # --- Overlay coin box onder BTC ---
                coin_top = show_coin["symbol"].upper()
                coin_value = "$" + (str(show_coin_price) if show_coin_price is not None else "N/A")
                coin_color = hex_to_rgb(show_coin["color"])
                coin_y = _prev_btc_box[1] + _prev_btc_box[3] + 20 if _prev_btc_box else (_btc_price_y + _btc_price_h + 20)
                _prev_coin_box = draw_text_overlay_box(
                    coin_top, coin_value, coin_color, textbox_offset, coin_y, prev_box=_prev_coin_box
                )

            if now_str != last_clock_str:
                update_clock_area(btc_color)
                last_clock_str = now_str

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
        wait_for_keypress()
        clear_framebuffer()
        time.sleep(1)
