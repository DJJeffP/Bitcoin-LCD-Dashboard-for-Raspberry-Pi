#!/bin/bash

# Fix locale if needed
export LC_ALL=C

# 1. Dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pil python3-requests fonts-dejavu-core fonts-dejavu-extra wget

# 2. Maak backgrounds-map aan als die nog niet bestaat
mkdir -p backgrounds

# 3. Download de BTC background als default (je kunt hier meer downloadregels toevoegen voor andere coins)
if [ ! -f backgrounds/btc-bg.png ]; then
    echo "Downloading default BTC background..."
    wget -O backgrounds/btc-bg.png "https://files.oaiusercontent.com/file-CzCD5LkiHfiLaaGQngKeNE?se=2024-08-03T17%3A37%3A54Z&sp=r&sv=2021-08-06&sr=b&rscd=inline&rsct=image/png&skoid=181926c6-e55e-44eb-ada2-8824c7e37e54&sktid=7038a684-2c2a-496c-b6ee-4a98f9812e7c&skt=2024-08-03T17%3A00%3A00Z&ske=2024-08-04T17%3A00%3A00Z&sks=b&skv=2021-08-06&sig=something"
fi

echo "Installatie klaar. Gebruik ./start.sh om te starten!"
