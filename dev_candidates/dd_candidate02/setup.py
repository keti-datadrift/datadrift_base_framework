#------------------------------------------------------------------------------
# data drift (dd) management module
# jpark @ KETI
#------------------------------------------------------------------------------

import json
import os
from setuptools import setup, find_packages

# 🔹 `config.json` 경로를 설정하고 읽기
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
print('-'*55)
print('BASE_DIR = ', BASE_DIR)
print('-'*55)
CONFIG_FILE = os.path.join(BASE_DIR, "dd/config/config.json")
print('-'*55)
print('CONFIG_FILE = ', CONFIG_FILE)
print('-'*55)

with open(CONFIG_FILE, "r") as f:
    config_info = json.load(f)

setup(
    name="keti-datadrift",
    version=config_info["version"],  # 🔹 버전 정보 설정
    packages=find_packages(include=["dd", "dd.*"]),
    package_data={"dd": ["fonts/NanumGothicCoding-Bold.ttf",
                         "fonts/NanumGothicCoding-Regular.ttf", 
                         "config/config.json", ]}, 
    include_package_data=True,
    license="Apache2.0",
    install_requires=[
        "fastapi",
        "uvicorn",
        "requests",
        "pandas",
        "numpy",
        "scikit-learn",
        "pyyaml",
        "fpdf",
        "weasyprint"
    ],
    entry_points={
        "console_scripts": [
            "dd = dd.cli:main",
        ],
    },
)

#------------------------------------------------------------------------------
# End of this file
#------------------------------------------------------------------------------
