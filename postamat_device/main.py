import logging
import threading
import time

from libs import serial_ports_mng
from libs import settings  # noqa: F401  -- triggers config + logging init on import


if __name__ == "__main__":
    vp_scanner = settings.data['scanner_vid_pid'].split(":")

    try:
        scanner_thread = threading.Thread(
            target=serial_ports_mng.connect_new,
            args=(int(vp_scanner[0], 16), int(vp_scanner[1], 16), 'scanner'),
        )
        scanner_thread.daemon = True
        scanner_thread.start()
    except Exception as exc:
        logging.info("Error: unable to start scanner thread: " + str(exc))

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        logging.info("Shutting down")
