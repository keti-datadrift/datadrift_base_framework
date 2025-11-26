import os
import uuid
import pandas as pd
from sqlalchemy.orm import Session
from PIL import Image
import cv2

from app.models import Dataset
from app.services.dvc_service import dvc_add_file
from app.services.utils.json_sanitize import clean_json_value

# -----------------------------------------------
# 이미지 & 비디오 썸네일 생성기
# -----------------------------------------------
def create_thumbnail(dtype: str, file_path: str) -> str | None:
    """이미지/비디오 타입에 대해 128x128 썸네일을 생성"""
    try:
        # ----- Image -----
        if dtype == "image":
            img = Image.open(file_path).convert("RGB")
            img.thumbnail((128, 128))
            thumb_path = f"{file_path}_thumbnail.jpg"
            img.save(thumb_path)
            return thumb_path

        # ----- Video -----
        if dtype == "video":
            cap = cv2.VideoCapture(file_path)
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

            ok, frame = cap.read()
            cap.release()

            if ok:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                img.thumbnail((128, 128))
                thumb_path = f"{file_path}_thumbnail.jpg"
                img.save(thumb_path)
                return thumb_path

        return None

    except Exception:
        return None


# -----------------------------------------------
# Dataset 생성 서비스
# -----------------------------------------------
def create_dataset(db: Session, uploaded_file) -> Dataset:
    """
    파일을 data/에 저장 → DVC add → 메타DB 저장까지 처리하는 핵심 서비스
    """

    # -----------------------------
    # 1) 파일 로컬저장 + DVC 등록
    # -----------------------------
    file_path, version_info = dvc_add_file(uploaded_file)

    # 파일 확장자 판별
    filename = uploaded_file.filename
    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    # -----------------------------
    # 2) 데이터 타입 분류
    # -----------------------------
    if ext in [".csv"]:
        dtype = "csv"
    elif ext in [".txt", ".md", ".json"]:
        dtype = "text"
    elif ext in [".png", ".jpg", ".jpeg", ".bmp"]:
        dtype = "image"
    elif ext in [".mp4", ".mov", ".avi", ".mkv"]:
        dtype = "video"
    else:
        dtype = "unknown"

    # -----------------------------
    # 3) CSV면 pandas EDA 일부 수행
    # -----------------------------
    rows = 0
    cols = 0
    missing_rate = {}
    preview = {}

    if dtype == "csv":
        df = pd.read_csv(file_path)

        # NaN → safe JSON
        try:
            df = df.replace([float("inf"), float("-inf")], None)
            df = df.fillna(None)
        except:
            pass
            
        rows, cols = df.shape

        missing_dict = df.isna().mean().to_dict()
        missing_rate = clean_json_value(missing_dict)

        preview_head = df.head(5).to_dict(orient="records")
        preview = clean_json_value({"head": preview_head})

    elif dtype == "text":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            preview = {"first_lines": lines[:5]}
            rows = len(lines)
            cols = 1

    elif dtype == "image":
        img = Image.open(file_path)
        rows = img.height
        cols = img.width
        preview = {"info": f"{cols}x{rows}"}

    elif dtype == "video":
        cap = cv2.VideoCapture(file_path)
        rows = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cols = int(cap.get(cv2.CAP_PROP_FPS))
        preview = {"frames": rows, "fps": cols}
        cap.release()

    # -----------------------------
    # 4) 썸네일 생성 (image/video)
    # -----------------------------
    thumbnail = create_thumbnail(dtype, file_path)
    if thumbnail:
        if isinstance(preview, dict):
            preview["thumbnail"] = thumbnail
        else:
            preview = {"thumbnail": thumbnail}

    # -----------------------------
    # 5) Dataset 엔티티 구성
    # -----------------------------
    dataset = Dataset(
        id=str(uuid.uuid4()),
        name=filename,
        type=dtype,
        size=os.path.getsize(file_path),
        rows=rows,
        cols=cols,
        missing_rate=missing_rate,
        preview=preview,
        dvc_path=file_path,
        version="v1",
    )

    # -----------------------------
    # 6) DB 저장
    # -----------------------------
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return dataset