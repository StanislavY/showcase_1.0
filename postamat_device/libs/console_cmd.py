import logging
import sys

from libs import requests_srv, serial_ports_mng

def console_loop():
    try:

        while True:
            pass
            if len(sys.argv) > 1:
                if sys.argv[1] == 'console':
                    console(input())
    except KeyboardInterrupt:
        exit()

def console(command: str):
    answer = command.split(':')

    try:
        if 'cell' == answer[0]:
            if serial_ports_mng._ARDUINO.is_connected():
                serial_ports_mng._ARDUINO.open_cell(answer[1])
                return
            else:
                logging.exception("Arduino is not connected")
                return
        elif 'check' == answer[0]:
            serial_ports_mng.process_request(answer[1])
            return
        elif 'switch' == answer[0]:
            req = requests_srv.switch_cell(int(answer[1]), True)
            logging.debug(f"receive from Server: {req.json()}")
            return
    except Exception as e1:
        logging.info("error command argument: " + str(e1))
    logging.info("Command list:")
    logging.info("cell:{number of cell} => opening cell ")
    logging.info("check:{bar code} => checking bar code on server")
    logging.info("switch:{number of cell} => switch cell status on server")
