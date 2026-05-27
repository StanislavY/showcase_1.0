import logging
import serial.tools.list_ports
import libs.requests_srv as requests_srv
import libs.settings as settings
from time import sleep
import json
import time

import main
from libs.Globals import Globals


class SerialDevice:
    __serial = None
    __vid = None
    __pid = None
    __connection_params = None

    def __init__(self, vid, pid, connection_params=None):
        self.__vid = vid
        self.__pid = pid
        self.__connection_params = connection_params

    def _get_serial(self):
        if self.__serial is None:
            port_name = None
            for port in serial.tools.list_ports.comports():
                logging.info(f"VID = {port.vid} :PID {port.pid}")
                if port.vid == self.__vid and port.pid == self.__pid:
                    port_name = port.name
            if port_name is not None:
                cp = self.__connection_params if self.__connection_params is not None else {}
                self.__serial = serial.Serial(f"/dev/{port_name}", **cp)
            else:
                return None
        return self.__serial

    def is_connected(self):
        return self._get_serial() is not None


class Arduino(SerialDevice):
    def __init__(self):
        vid, pid = settings.data['arduino_vid_pid'].split(":")
        vid, pid = int(vid, 16), int(pid, 16)
        super().__init__(vid, pid)

    def open_cell(self, cell_number):
        logging.info(f'Open cell:{cell_number}')
        self._get_serial().write(bytes(cell_number, 'utf-8'))


_ARDUINO = Arduino()


class Scanner(SerialDevice):
    __callback = None

    def __init__(self, callback):
        vid, pid = settings.data['scanner_vid_pid'].split(":")
        vid, pid = int(vid, 16), int(pid, 16)
        super().__init__(vid, pid, {
            'baudrate': 9600,
            'bytesize': serial.SEVENBITS,
            'parity': serial.PARITY_SPACE,
            'stopbits': serial.STOPBITS_ONE
        })
        self.__callback = callback

    def listen(self):
        while True:
            if self.is_connected():
                try:
                    while True:
                        line = (self._get_serial().readline()
                                .decode('utf-8')
                                .replace(settings.data['eol_symbol'], ''))
                        logging.debug(f"received from scanner: {line}")

                        self.__callback(line)

                except Exception as e:
                    logging.info("error communicating...: " + str(e))
            sleep(10)


def process_request(line):
    test_cells(line)
    resp = requests_srv.check_code(line).json()
    logging.debug(f"received from Server: {resp}")

    if resp['open_cell'] is not None:
        if _ARDUINO.is_connected():
            _ARDUINO.open_cell(str(resp['open_cell']))
        else:
            logging.exception("Arduino is not connected")
    else:
        logging.info("Open cell is null")

def process_opening_by_button(line):
    data=line

    Globals.cells_list_for_display=data

    print(Globals.cells_list_for_display)
    try:
        #Преобразуем строку в словарь с помощью json.loads()
        data = json.loads(line)

    except Exception as e1:
        logging.info(str(e1))
    if data['cell_numbers'] is not None:
        if _ARDUINO.is_connected():


                # Извлекаем значение списка из ключа 'cell_numbers'
            array = data['cell_numbers']
            #main.cells_list_for_display=array
            #print(array)  # Выводим полученный массив
            #print(array[0])
            for item in array:
                _ARDUINO.open_cell(str(item))
                time.sleep(1)
        else:
            logging.exception("Arduino is not connected")
    else:
        logging.info("Open cell is null")


SCANNER = Scanner(callback=process_request)


def connect_new(vid, pid, name):
    if _ARDUINO.is_connected():
        logging.info("Arduino is connected on start")
    if SCANNER.is_connected():
        logging.info("Scanner is connected on start")
    SCANNER.listen()



def test_cells(line):

    if settings.data['testing_mode']=="1":


        logging.debug(f"opening cell: {line}")

        if line is not None:
            if _ARDUINO.is_connected():
                _ARDUINO.open_cell(str(line))
            else:
                logging.exception("Arduino is not connected")
        else:
            logging.info("Open cell is null")

