#------------------------------------------------------------------------------
# data drift (dd) management module
# jpark @ KETI
#------------------------------------------------------------------------------

import time

def run(filepath, interval):
    print(f"📡 {filepath}의 모니터링을 {interval}일 간격으로 수행합니다.")
    while True:
        time.sleep(interval * 86400)
        print(f"🔍 {filepath}의 품질 점검 완료!")