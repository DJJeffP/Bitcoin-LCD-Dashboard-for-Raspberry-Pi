# BTC LCD Dashboard for Raspberry Pi

Een Python dashboard voor het tonen van Bitcoin en andere coin-prijzen op een Raspberry Pi met 480x320 LCD + touchscreen.

## Features

* Kalibratie van de touchscreen bij eerste opstart
* Live prijsupdates via CoinGecko (en fallback Binance)
* Dashboard met klok, datum en (optioneel) meerdere coins in rotatie
* Setup/search-modus via double-tap op de klok (rechtsboven):

  * Coins aan/uit zetten via touchscreen
  * Scrollen door de lijst
  * Coins zoeken via touchscreen keyboard
  * Save-knop om instellingen op te slaan
* Efficiënte (deel)refresh: alleen klok- of prijsgebied wordt elke seconde vernieuwd voor minimale belasting

## Installatie

1. **Clone deze repo of kopieer de bestanden naar je Pi.**
2. Installeer dependencies:

   ```bash
   pip3 install -r requirements.txt
   ```
3. Zet de juiste rechten op de framebuffer en touchscreen:

   ```bash
   sudo chmod a+rw /dev/fb1
   sudo chmod a+rw /dev/input/event0
   ```
4. Pas indien gewenst `coins.json` aan voor jouw eigen coins.

## Gebruik

Start het dashboard:

```bash
python3 main.py
```

* **Kalibratie:** bij eerste start, raak de aangegeven kruizen aan.
* **Setup/search-modus:** double-tap op de klok (rechtsboven).
  Toggle coins, zoek met keyboard, scroll, sla op met SAVE.
* **Dashboard:** draait automatisch, wisselt elke 20 seconden naar de volgende coin.

## Bestandsstructuur

```
btc_lcd_dashboard/
├── main.py
├── calibration.py
├── dashboard.py
├── setup_screen.py
├── touchscreen.py
├── price.py
├── utils.py
├── coins.json
├── requirements.txt
└── README.md
```

## Configuratie

### coins.json voorbeeld

```json
{
  "coins": [
    {
      "id": "btc",
      "symbol": "BTC",
      "name": "Bitcoin",
      "color": "#F7931A",
      "coingecko_id": "bitcoin",
      "show": true
    },
    {
      "id": "xtm",
      "symbol": "XTM",
      "name": "Tari",
      "color": "#36b0d2",
      "coingecko_id": "tari",
      "show": true
    }
    // Voeg meer coins toe zoals gewenst
  ]
}
```

## Vragen of hulp nodig?

Open een issue, of stuur een bericht naar DJJeffP / FrenziezHosting!

---

*BTC LCD Dashboard is ontwikkeld als open-source hobbyproject voor gebruik op de Raspberry Pi. Gebruik op eigen risico!*
