"""
Setup-/zoek-scherm: coin toggles, search, keyboard, scroll, save.
"""

from PIL import Image, ImageDraw, ImageFont
import json

WIDTH, HEIGHT = 480, 320
FONT_SMALL = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
CONFIG_FILE = "coins.json"

def draw_coin_toggle_list(coins, scroll=0, search_text="", search_focused=False):
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
    draw.rectangle([0, 0, WIDTH, 55], fill=(50,50,90))
    draw.text((20, 10), "SETUP: Toggle/Search", fill=(255,255,255), font=font)
    draw.rectangle([20, 55, WIDTH-20, 95], fill=(60,60,100))
    draw.text((30, 65), f"Search: {search_text}", fill=(255,255,255), font=font_search)
    if search_focused:
        draw.rectangle([18, 53, WIDTH-18, 97], outline=(80,255,80), width=2)
    for i, coin in enumerate(visible):
        y = 105 + i*40
        toggle_box = [30, y, 70, y+30]
        fill = (90,230,90) if coin.get("show", True) else (130,130,130)
        draw.rectangle(toggle_box, fill=fill)
        text = f"{coin['symbol']} - {coin['name']}"
        draw.text((80, y), text, fill=(255,255,255), font=font)
    scroll_up_x = WIDTH - 60
    scroll_up_y = 105
    scroll_down_x = WIDTH - 60
    scroll_down_y = 105 + 6*40
    draw.polygon([(scroll_up_x, scroll_up_y), (scroll_up_x+30, scroll_up_y), (scroll_up_x+15, scroll_up_y-20)], fill=(255,255,255))
    draw.polygon([(scroll_down_x, scroll_down_y), (scroll_down_x+30, scroll_down_y), (scroll_down_x+15, scroll_down_y+20)], fill=(255,255,255))
    save_left = WIDTH - 180
    save_right = WIDTH - 50
    save_top = HEIGHT - 70
    save_bottom = HEIGHT - 20
    draw.rectangle([save_left, save_top, save_right, save_bottom], fill=(60,130,60))
    draw.text((save_left+15, save_top+12), "SAVE", fill=(255,255,255), font=font_search)
    keys = [
        "QWERTYUIOP",
        "ASDFGHJKL",
        "ZXCVBNM<-"
    ]
    key_w = 38
    key_h = 38
    key_rows = 3
    key_gap = 4
    keyboard_height = key_rows * key_h + (key_rows - 1) * key_gap
    save_button_top = HEIGHT - 70
    key_start_y = save_button_top - keyboard_height - 10
    total_key_row_width = 10 * key_w + 9 * key_gap
    key_start_x = (WIDTH - total_key_row_width) // 2
    if search_focused:
        for row_idx, row in enumerate(keys):
            yk = key_start_y + row_idx * (key_h + key_gap)
            for col_idx, char in enumerate(row):
                xk = key_start_x + col_idx * (key_w + key_gap)
                draw.rectangle([xk, yk, xk+key_w, yk+key_h], fill=(80,80,80))
                draw.text((xk+10, yk+8), char, font=font_search, fill=(255,255,255))
    image = image.rotate(180)
    rgb565 = bytearray()
    for pixel in image.getdata():
        r = pixel[0] >> 3
        g = pixel[1] >> 2
        b = pixel[2] >> 3
        value = (r << 11) | (g << 5) | b
        rgb565.append(value & 0xFF)
        rgb565.append((value >> 8) & 0xFF)
    with open("/dev/fb1", 'wb') as f:
        f.write(rgb565)
    return matches, font, keys, key_start_x, key_start_y, key_w, key_h, key_gap

def handle_setup_touch(x, y, coins, scroll, search_text, search_focused, matches, font, keys, key_start_x, key_start_y, key_w, key_h, key_gap, switch_to_dashboard):
    save_left = WIDTH - 180
    save_right = WIDTH - 50
    save_top = HEIGHT - 70
    save_bottom = HEIGHT - 20
    if save_left <= x <= save_right and save_top <= y <= save_bottom:
        save_settings(coins)
        switch_to_dashboard()
        return True, scroll, search_text, False
    scroll_up_x = WIDTH - 60
    scroll_up_y = 105
    if scroll_up_x <= x <= scroll_up_x+30 and scroll_up_y-20 <= y <= scroll_up_y+10 and scroll > 0:
        return False, scroll-1, search_text, search_focused
    scroll_down_x = WIDTH - 60
    scroll_down_y = 105 + 6*40
    if scroll_down_x <= x <= scroll_down_x+30 and scroll_down_y <= y <= scroll_down_y+20 and (scroll+6) < len(matches):
        return False, scroll+1, search_text, search_focused
    if 20 <= x <= WIDTH-20 and 55 <= y <= 95:
        return False, scroll, search_text, True
    if search_focused:
        for row_idx, row in enumerate(keys):
            yk = key_start_y + row_idx * (key_h + key_gap)
            for col_idx, char in enumerate(row):
                xk = key_start_x + col_idx * (key_w + key_gap)
                if xk <= x <= xk+key_w and yk <= y <= yk+key_h:
                    if char == "<":
                        search_text = search_text[:-1]
                    else:
                        search_text += char
                    return False, scroll, search_text, True
    for i in range(6):
        y_coin = 105 + i*40
        if i < len(matches):
            coin = matches[scroll+i]
            text = f"{coin['symbol']} - {coin['name']}"
            text_bbox = font.getbbox(text)
            text_w = text_bbox[2] - text_bbox[0]
            x_name_start = 80
            x_name_end = x_name_start + text_w
            toggle_box_x1 = 30
            toggle_box_x2 = 70
            if ((toggle_box_x1 <= x <= toggle_box_x2) or
                (x_name_start - 8 <= x <= x_name_end + 8)) and y_coin <= y <= y_coin+30:
                orig_idx = coins.index(coin)
                coins[orig_idx]["show"] = not coins[orig_idx].get("show", True)
                return False, scroll, search_text, False
    return False, scroll, search_text, False

def setup_touch_listener(coins, switch_to_dashboard):
    import evdev
    device = evdev.InputDevice('/dev/input/event0')
    raw_x, raw_y = 0, 0
    finger_down = False
    scroll = 0
    search_text = ""
    search_focused = False
    while True:
        matches, font, keys, key_start_x, key_start_y, key_w, key_h, key_gap = draw_coin_toggle_list(
            coins, scroll=scroll, search_text=search_text, search_focused=search_focused)
        for event in device.read_loop():
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
                    from calibration import scale_touch
                    x, y = scale_touch(raw_x, raw_y)
                    should_exit, scroll, search_text, search_focused = handle_setup_touch(
                        x, y, coins, scroll, search_text, search_focused,
                        matches, font, keys, key_start_x, key_start_y, key_w, key_h, key_gap, switch_to_dashboard)
                    if should_exit:
                        return
                    break

def save_settings(coins):
    with open("coins.json", "w") as f:
        json.dump({"coins": coins}, f, indent=2)
    print("Coins settings saved.")
