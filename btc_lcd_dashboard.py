import time
import requests
from PIL import Image, ImageDraw, ImageFont

FRAMEBUFFER = "/dev/fb1"
WIDTH, HEIGHT = 480, 320

# Font paths
FONT_BIG = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SMALL = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

font_btc = ImageFont.truetype(FONT_BIG, 60)     # For BTC price
font_time = ImageFont.truetype(FONT_BIG, 28)    # For time
font_date = ImageFont.truetype(FONT_SMALL, 20)  # For date

BTC_ORANGE = (247, 147, 26)

def clear_framebuffer():
    with open(FRAMEBUFFER, 'wb') as f:
        f.write(bytearray([0x00, 0x00] * WIDTH * HEIGHT))

def get_btc_price():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
        price = r.json()["bitcoin"]["usd"]
        return float(price)
    except Exception:
        try:
            r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
            price = r.json()["price"]
            return float(price)
        except Exception:
            return None

def draw_dashboard(price, t):
    # Use your custom PNG background
    image = Image.open("btc_bg_cropped.png").convert("RGB").resize((WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)

    # ---- Draw Time (top right) ----
    now_str = time.strftime("%H:%M:%S", t)
    date_str = time.strftime("%a %d %b %Y", t)
    # Get width of both time and date for right alignment
    time_w, time_h = draw.textbbox((0, 0), now_str, font=font_time)[2:]
    date_w, date_h = draw.textbbox((0, 0), date_str, font=font_date)[2:]

    # Right-aligned at 20px from the right, 16px from the top
    draw.text((WIDTH - time_w - 20, 16), now_str, font=font_time, fill=(255,255,255))
    draw.text((WIDTH - date_w - 20, 16 + time_h + 2), date_str, font=font_date, fill=BTC_ORANGE)

    # ---- Draw BTC Price (centered) ----
    price_text = "BTC $" + (f"{price:,.2f}" if price is not None else "N/A")
    price_w, price_h = draw.textbbox((0, 0), price_text, font=font_btc)[2:]
    # Centered
    center_x = (WIDTH - price_w) // 2
    center_y = (HEIGHT - price_h) // 2
    draw.text((center_x, center_y), price_text, font=font_btc, fill=BTC_ORANGE)

    # ---- Rotate for display ----
    image = image.rotate(180)

    # ---- RGB565 (little endian) ----
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
    last_price = None
    while True:
        now = time.localtime()
        if (last_price is None) or (time.time() % 30 < 1):
            last_price = get_btc_price()
        draw_dashboard(last_price, now)
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
