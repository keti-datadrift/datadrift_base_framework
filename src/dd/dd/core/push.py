import os
import json
import requests

#---------------------------------------------------------------------------
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "config.json")
try:
    with open(CONFIG_FILE, "r") as f:
        json_info = json.load(f)
        DD_HUB_URL = json_info['version']
except FileNotFoundError:
    DD_HUB_URL = "http://127.0.0.1:8000"
#---------------------------------------------------------------------------

def run(filepath):
    if not os.path.exists(filepath):
        print("❌ 파일이 존재하지 않습니다.")
        return

    files = {"file": open(filepath, "rb")}
    if filepath.startswith("data/"):
        response = requests.post(f"{DD_HUB_URL}/upload/data/", files=files)
    else:
        response = requests.post(f"{DD_HUB_URL}/upload/model/", files=files)

    print(response.json())