import requests


def get_external_ip():
    response = requests.get('https://api.ipify.org')
    if response.status_code == 200:
        return response.text
    else:
        raise RuntimeError("Unable to get external ip, This should NOT happens. Try again in few moments")
