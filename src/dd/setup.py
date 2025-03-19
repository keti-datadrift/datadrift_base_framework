import json
import os
from setuptools import setup, find_packages

# 🔹 `version.json` 경로를 설정하고 읽기
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(BASE_DIR, "version.json")

with open(VERSION_FILE, "r") as f:
    version_info = json.load(f)

setup(
    name="dd",
    version=version_info["version"],  # 🔹 버전 정보 설정
    packages=find_packages(include=["dd", "dd.*"]),
    package_data={"dd": ["../version.json"]},  # 🔹 version.json 포함
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