import fiftyone as fo
import fiftyone.zoo as foz

# Fiftyone dataset 로드 (샘플 데이터셋 사용)
dataset = foz.load_zoo_dataset("quickstart")

# Fiftyone 앱 실행
session = fo.launch_app(dataset, remote=True, address="0.0.0.0")

# 앱을 계속 실행 상태로 유지
session.wait()