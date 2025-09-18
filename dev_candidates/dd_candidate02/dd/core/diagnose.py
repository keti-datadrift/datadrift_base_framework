#------------------------------------------------------------------------------
# data drift (dd) management module
# jpark @ KETI
#------------------------------------------------------------------------------

import os
import json
import pandas as pd
import numpy as np

DD_DIR = ".dd"
DATA_LOG_FILE = os.path.join(DD_DIR, "data_log.json")

def load_data_log():
    """ data_log.json을 로드하거나 새로 생성 """
    if not os.path.exists(DATA_LOG_FILE):
        return {}
    with open(DATA_LOG_FILE, "r") as f:
        return json.load(f)

def save_data_log(data_log):
    """ data_log.json 저장 """
    with open(DATA_LOG_FILE, "w") as f:
        json.dump(data_log, f, indent=4)

def run(filepath):
    df = pd.read_csv(filepath)

    report = {
        "missing_values": int(df.isnull().sum().sum()),
        "duplicates": int(df.duplicated().sum()),
        "outliers": int((np.abs(df - df.mean()) > (2 * df.std())).sum().sum()),
        "quality_score": round(1 - (df.isnull().sum().sum() / (df.shape[0] * df.shape[1])), 2)
    }

    data_log = load_data_log()
    data_log[filepath] = report
    save_data_log(data_log)

    print(f"✅ 데이터 품질 로그 업데이트 완료: {DATA_LOG_FILE}")
    print(json.dumps(report, indent=4))


#------------------------------------------------------------------------------
# End of this file
#------------------------------------------------------------------------------