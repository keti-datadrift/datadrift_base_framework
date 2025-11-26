import os
import uuid
import subprocess

DATA_DIR = "data"

def dvc_add_file(uploaded_file) -> tuple[str, str]:
    """
    업로드된 파일을 data/에 저장하고 DVC로 관리.
    return: (파일 경로, dvc version-like info)
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    unique_id = str(uuid.uuid4())
    filename = f"{unique_id}_{uploaded_file.filename}"
    save_path = os.path.join(DATA_DIR, filename)

    with open(save_path, "wb") as f:
        content = uploaded_file.file.read()
        f.write(content)

    # DVC로 트래킹
    subprocess.run(["dvc", "add", save_path], check=True)

    # 간단히 dvc 파일 내용을 버전 정보로 활용
    dvc_file = save_path + ".dvc"
    version_info = ""
    if os.path.exists(dvc_file):
        with open(dvc_file, "r") as f:
            version_info = f.read()

    return save_path, version_info or "v1"