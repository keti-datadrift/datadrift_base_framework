#------------------------------------------------------------------------------
# data drift (dd) management module
# jpark @ KETI
#------------------------------------------------------------------------------

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

def run(filename):
    response = requests.get(f"{DD_HUB_URL}/download/data/{filename}")
    if response.status_code == 200:
        print(f"✅ 다운로드 링크: {response.json()['download_url']}")
    else:
        print("❌ 파일을 찾을 수 없습니다.")