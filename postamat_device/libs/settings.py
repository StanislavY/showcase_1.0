import json
import logging
import sys
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"

data = None
cell = None
arduino_connect = None


def init():
    global data, cell, arduino_connect
    logging.basicConfig(
        level=10,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[

            logging.FileHandler("postStore.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info("Start application")
    logging.info(f"Loading config from {CONFIG_PATH}")
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(
            f"config.json not found at expected location: {CONFIG_PATH}. "
            f"Make sure the file exists in the postamat_device project root."
        )
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    logging.info(f"Config {data}")
    arduino_connect = False


init()
