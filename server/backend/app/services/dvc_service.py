import os
import uuid
import subprocess

DATA_DIR = "data"

def dvc_add_file(uploaded_file):
    dataset_id = str(uuid.uuid4())

    save_path = f"{DATA_DIR}/{dataset_id}_{uploaded_file.filename}"
    with open(save_path, "wb") as f:
        f.write(uploaded_file.file.read())

    # DVC add
    subprocess.run(["dvc", "add", save_path])

    # Git is optional → no commit required for DVC local
    # Get DVC hash
    dvc_hash_file = save_path + ".dvc"
    with open(dvc_hash_file, "r") as f:
        dvc_content = f.read()

    return save_path, dvc_content