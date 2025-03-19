import json
import os
from setuptools import setup, find_packages

# 🔹 `config.json` 경로를 설정하고 읽기
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

with open(CONFIG_FILE, "r") as f:
    config_info = json.load(f)

setup(
    name="dd",
    version=config_info["version"],  # 🔹 버전 정보 설정
    packages=find_packages(include=["dd", "dd.*"]),
    package_data={"dd": ["../config.json"]},  # 🔹 version.json 포함
    include_package_data=True,
    install_requires=[
        "fastapi",
        "uvicorn",
        "requests",
        "pandas",
        "numpy",
        "scikit-learn",
        "pyyaml"
    ],
    entry_points={
        "console_scripts": [
            "dd = dd.cli:main",
        ],
    },
)