import logging
import requests

import main
from libs import settings


def check_code(code: str):
    url = f"{settings.data['backend']}api/v1/product/check_code/"
    headers = {
        "Authorization": f"Bearer {settings.data['device_token']}"
    }
    data = {
        "code": code
    }
    logging.debug(f"Request to url :{url}")
    logging.debug(f"Headers :{headers}")
    logging.debug(f"Data :{data}")
    response = requests.post(url, headers=headers, json=data)
    logging.debug(f"received from Server: {response}")

    return response

def request_to_open_all_sold_sells_by_button(code: str):
    url = f"{settings.data['backend']}api/v1/cells-with-sell-goods"
    headers = {
        "Authorization": f"Bearer {settings.data['device_token']}"
    }
    data = {

    }
    logging.debug(f"Request to url :{url}")
    logging.debug(f"Headers :{headers}")
    logging.debug(f"Data :{data}")
    response = requests.post(url, headers=headers, json=data)
    logging.debug(f"received from Server: {response.json()}")




    return response.text


def switch_cell(cell: int, opened: bool):
    url = f"{settings.data['backend']}api/v1/product/switch_cell/"
    headers = {
        "Authorization": f"Bearer {settings.data['device_token']}"
    }
    data = {
        "cell": cell,
        "opened": opened
    }
    logging.debug(f"Request to url :{url}")
    logging.debug(f"Headers :{headers}")
    logging.debug(f"Data :{data}")
    response = requests.post(url, headers=headers, json=data)
    return response


