#!/bin/bash
echo "Start install"

sudo mkdir -p /postamat/src
echo "Make virtual environment"
sudo chmod -R 777 /postamat
sudo python3 -m venv /postamat/venv
sudo chmod -R 777 /postamat

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
echo "Copy files..$SCRIPT_DIR"
cp -r "$SCRIPT_DIR"/* /postamat/src

echo "Install library..."
source /postamat/venv/bin/activate
pip install -r /postamat/src/requirements.txt

echo "SystemD settings..."
sudo cp /postamat/src/poststore.service /etc/systemd/system/poststore.service
sudo chmod 644 /etc/systemd/system/poststore.service
sudo systemctl daemon-reload
sudo systemctl start poststore
sudo systemctl enable poststore

echo "Install complete"
