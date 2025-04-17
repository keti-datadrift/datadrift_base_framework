#------------------------------------------------------------------------------
# data drift (dd) management module
# jpark @ KETI
#------------------------------------------------------------------------------

import json

def run(filepath):
    try:
        with open(".dd/metadata.yaml", "r") as f:
            metadata = json.load(f)
        print(f"🔗 {filepath}의 lineage 정보:")
        print(json.dumps(metadata.get("domains", {}), indent=4))
    except FileNotFoundError:
        print("❌ lineage 정보를 찾을 수 없습니다.")
