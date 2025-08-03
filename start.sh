#!/bin/bash

# 1. Install needed APT packages
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-pil python3-requests fonts-dejavu-core fonts-dejavu-extra wget

# 2. Install needed pip packages
pip3 install --upgrade pillow requests

# 3. Download background PNG if missing
if [ ! -f btc_bg_cropped.png ]; then
    echo "Downloading default background..."
    wget -O btc_bg_cropped.png "https://files.oaiusercontent.com/file-CzCD5LkiHfiLaaGQngKeNE?se=2024-08-03T17%3A37%3A54Z&sp=r&sv=2021-08-06&sr=b&rscd=inline&rsct=image/png&skoid=181926c6-e55e-44eb-ada2-8824c7e37e54&sktid=7038a684-2c2a-496c-b6ee-4a98f9812e7c&skt=2024-08-03T17%3A00%3A00Z&ske=2024-08-04T17%3A00%3A00Z&sks=b&skv=2021-08-06&sig=something"
fi

# 4. Start the app
echo "Starting BTC dashboard..."
sudo python3 btc_lcd_dashboard.py
