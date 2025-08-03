# Bitcoin & Crypto LCD Dashboard for Raspberry Pi

A modern, touch-friendly cryptocurrency dashboard for small LCD screens (like the 3.5" XPT2046 Pi display). Rotates live prices and info for your favorite coins, with custom backgrounds per coin. Supports CoinGecko (default) and automatic Binance fallback for price data.

---

## Features

* Touchscreen-ready for Raspberry Pi with 3.5" (480x320) LCD (framebuffer `/dev/fb1`)
* Modern, customizable look
* Shows **BTC** always on screen as main, rotates other coins (configurable)
* Custom PNG backgrounds for each coin (auto fallback if not found)
* Periodic background price caching (default: every 60 sec, all coins in 1 API call)
* CoinGecko as main source, **Binance fallback** for extra reliability
* Easy config: `coins.json` (enable/disable coins, pick display color, add Binance symbol)
* Auto-clears screen on exit

---

## Requirements

* Python 3 (tested 3.7+)
* Raspberry Pi OS (Lite of Desktop)
* Pillow, requests
* 3.5" XPT2046 Touch LCD or compatible (framebuffer `/dev/fb1`)

---

## Installation

**1. Clone repo & enter folder:**

```sh
git clone https://github.com/DJJeffP/Bitcoin-LCD-Dashboard-for-Raspberry-Pi.git
cd Bitcoin-LCD-Dashboard-for-Raspberry-Pi
```

**2. Install requirements:**

```sh
sudo apt update && sudo apt install -y python3-pip python3-pil fonts-dejavu-core
pip3 install --user requests pillow
```

**3. Check or update your framebuffer device:**

* Default is `/dev/fb1`. For HDMI or other screens: set `FRAMEBUFFER` in the script.

**4. (Optional) Put your PNG backgrounds in `backgrounds/`**

* Name like: `btc-bg.png`, `xmr-bg.png`, etc. (see coins.json)
* No PNG? Fallback to `btc-bg.png`.

**5. Configure coins:**

* Edit `coins.json` to choose which coins to show and their colors.
* Add `binance_symbol` for Binance fallback (see template)

---

## Usage

Start the dashboard:

```sh
python3 btc_lcd_dashboard.py
```

Or make a `start.sh`:

```sh
echo 'python3 btc_lcd_dashboard.py' > start.sh
chmod +x start.sh
./start.sh
```

Stop with **CTRL+C** (clears the screen automatically).

---

## Example coins.json

```json
{
  "coins": [
    {
      "id": "btc",
      "name": "Bitcoin",
      "symbol": "BTC",
      "color": "#F7931A",
      "coingecko_id": "bitcoin",
      "binance_symbol": "BTCUSDT",
      "show": true
    },
    {
      "id": "xmr",
      "name": "Monero",
      "symbol": "XMR",
      "color": "#FF6600",
      "coingecko_id": "monero",
      "binance_symbol": "XMRUSDT",
      "show": true
    }
    // ... (see full template in code)
  ]
}
```

---

## Notes

* All coins with `"show": true` are shown in the rotation.
* Add/remove coins by editing `coins.json` (restart script after changes)
* For Binance fallback: only works for coins/trading pairs available on Binance. Use exact Binance API symbol (e.g. `XMRUSDT`)
* For fastest display, keep background PNGs simple (480x320 px)

---

## Troubleshooting

* **Screen blank/white?**

  * Check your framebuffer (default `/dev/fb1`) and that LCD drivers are loaded.
* **Font errors?**

  * Make sure fonts-dejavu-core is installed (`sudo apt install fonts-dejavu-core`)
* **API errors or 'N/A'?**

  * Coin ID may not exist on CoinGecko or Binance, or network issue.

---

## Credits

* Code, config and concept: DJJeffP & ChatGPT

---

## License

MIT (see LICENSE)
