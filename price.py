# price.py
"""
Prijs-updates & API-logica voor het dashboard.
"""

import threading
import time
import requests

price_cache = {}
price_cache_lock = threading.Lock()

def price_updater(coins, update_interval=60):
    """
    Haalt periodiek (standaard elke 60s) de prijzen op voor de opgegeven coins.
    Updatet een thread-safe cache.
    """
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
                    # Fallback: probeer Binance
                    try:
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
        time.sleep(update_interval)

def get_cached_price(coin):
    """
    Haalt de laatst bekende prijs op voor de coin (of None).
    """
    coingecko_id = coin.get("coingecko_id", coin.get("id"))
    with price_cache_lock:
        return price_cache.get(coingecko_id)
