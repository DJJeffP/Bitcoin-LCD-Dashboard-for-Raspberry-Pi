# Bitcoin LCD Dashboard for Raspberry Pi

A modern, minimal Bitcoin price dashboard for Raspberry Pi with a 3.5" LCD touchscreen, designed for miner displays and always-on nerdy info panels.\
It features a bold BTC price, real-time clock, and date, all overlayed on a beautiful custom Bitcoin-themed background.

---

## Features

- Live BTC price (CoinGecko, auto-fallback to Binance)
- Clock and date in the top right
- Clean, modern black/white/orange theme (matches the Bitcoin palette)
- Supports 480x320 Pi LCD (XPT2046, ILI9486, etc.)
- Auto-clears screen on exit for a professional finish

---

## Requirements

- Raspberry Pi with Raspberry Pi OS (Lite or Desktop)
- 3.5" LCD display with `/dev/fb1` framebuffer (XPT2046 or compatible)
- Python 3 (pre-installed on most Pi images)

---

## Installation

### 1. **Clone this repository**

```sh
git clone https://github.com/DJJeffP/Bitcoin-LCD-Dashboard-for-Raspberry-Pi.git
cd Bitcoin-LCD-Dashboard-for-Raspberry-Pi
```

### 2. **Make the startup script executable**

```sh
chmod +x install.sh start.sh
./install.sh       # Doe je 1x voor setup
```

---

## Usage

### **Run the dashboard**

```sh
./start.sh         # Om altijd te starten
```

- The script will:
  - Install any missing dependencies (`python3`, Pillow, requests, DejaVu fonts, etc.)
  - Download the default background if missing
  - Start the dashboard app on your LCD

**Stop the dashboard** at any time with CTRL+C.\
The screen will automatically blank for a clean shutdown.

---

## Customization

- **Background:**\
  Replace `btc_bg_cropped.png` with your own 480x320 PNG for a custom look.

- **Startup at boot:**\
  To auto-start on boot, add this to your `/etc/rc.local` (before `exit 0`):

  ```sh
  cd /path/to/btc-lcd-dashboard && ./start.sh &
  ```

- **Screen orientation:**\
  Script includes a 180° rotation by default for typical Pi LCD orientation. Remove or change `.rotate(180)` if not desired.

---

## Troubleshooting

- If you see color glitches (e.g., yellow appears purple), your hardware expects **RGB565 little-endian**. This script is already fixed for that!
- If nothing shows, check:
  - The Pi LCD is correctly set up and mapped to `/dev/fb1`
  - Your user has permissions, or run with `sudo`
- For further debugging, run the Python script directly:
  ```sh
  sudo python3 btc_lcd_dashboard.py
  ```

---

## License

MIT License

---

## Credits

- Powered by Python, Pillow, and open crypto APIs

---

### Enjoy your nerdy Bitcoin dashboard! 🚀

