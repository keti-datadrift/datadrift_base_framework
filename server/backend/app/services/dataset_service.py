import os
import uuid
import pandas as pd
from sqlalchemy.orm import Session
from PIL import Image

from app.models import Dataset
from app.services.dvc_service import dvc_add_file
from app.utils.json_sanitize import clean_json_value
from app.services.zip_resolver import analyze_zip_dataset


# -----------------------------
# 썸네일 생성 유틸 (이미지 전용)
# -----------------------------
def create_image_thumbnail(src_path: str, max_size=(128, 128)) -> str | None:
    """
    단일 이미지 파일에서 썸네일 생성.
    src_path_thumbnail.jpg 형태로 저장 후 그 경로를 반환.
    """
    try:
        if not os.path.exists(src_path):
            return None

        img = Image.open(src_path).convert("RGB")
        img.thumbnail(max_size)
        thumb_path = f"{src_path}_thumbnail.jpg"
        img.save(thumb_path)
        return thumb_path
    except Exception:
        return None


# -----------------------------
# Dataset 생성 서비스 (핵심)
# -----------------------------
def create_dataset(db: Session, uploaded_file) -> Dataset:
    """
    파일을 data/에 저장 → DVC add → 타입별 메타 + 썸네일 생성 → SQLite에 저장
    지원 포맷:
      - csv
      - text (.txt, .md, .json)
      - image (.png, .jpg, .jpeg, .bmp)
      - video (.mp4, .mov, .avi, .mkv)  → 메타만
      - zip (YOLO/VOC/COCO/기타 번들)
    """

    # 1) DVC를 통해 파일을 data/ 아래에 저장
    file_path, version_info = dvc_add_file(uploaded_file)

    filename = uploaded_file.filename
    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    # 2) 타입 분류
    if ext == ".csv":
        dtype = "csv"
    elif ext in [".txt", ".md", ".json"]:
        dtype = "text"
    elif ext in [".png", ".jpg", ".jpeg", ".bmp"]:
        dtype = "image"
    elif ext in [".mp4", ".mov", ".avi", ".mkv"]:
        dtype = "video"
    elif ext == ".zip":
        dtype = "zip"
    else:
        dtype = "unknown"

    rows = 0
    cols = 0
    missing_rate: dict | None = {}
    preview: dict | None = {}

    # 3) 타입별 메타 계산 및 preview 생성
    if dtype == "csv":
        # ---- CSV: 기본적인 EDA 메타 ----
        df = pd.read_csv(file_path)

        # NaN / inf 제거 (JSON safe)
        df = df.replace([float("inf"), float("-inf")], None)
        df = df.fillna(None)

        rows, cols = df.shape

        missing_dict = df.isna().mean().to_dict()
        missing_rate = clean_json_value(missing_dict)

        preview_head = df.head(5).to_dict(orient="records")
        preview = clean_json_value({"head": preview_head})

    elif dtype == "text":
        # ---- Text: 라인 수 + 처음 몇 줄 ----
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            rows = len(lines)
            cols = 1
            preview = {"first_lines": [line.strip() for line in lines[:5]]}
        except Exception:
            preview = {"first_lines": []}

    elif dtype == "image":
        # ---- Image: 해상도 + 썸네일 ----
        try:
            img = Image.open(file_path)
            rows = img.height
            cols = img.width
            preview = {"info": f"{cols}x{rows}"}
        except Exception:
            preview = {"info": "image"}

        thumb = create_image_thumbnail(file_path)
        if thumb:
            if isinstance(preview, dict):
                preview["thumbnail"] = thumb
            else:
                preview = {"thumbnail": thumb}

    elif dtype == "video":
        # ---- Video: 가벼운 메타만 (fps, frame 수 등은 추후 확장) ----
        # 여기서는 파일 크기/타입 정도만 기록
        preview = {"info": "video file"}
        rows = 0
        cols = 0
        # 비디오 썸네일은 OpenCV 의존성이 생기므로
        # 향후 선택적으로 추가 (지금은 생략하여 안전성을 우선)

    elif dtype == "zip":
        # ---- ZIP: 내부 구조 분석 (YOLO/VOC/COCO/Bundle 탐지) ----
        info = analyze_zip_dataset(file_path)

        # zip dataset은 "전체 파일 수"를 rows로 사용
        stats = info.get("stats", {})
        rows = stats.get("total_files", 0)
        cols = 0

        preview = {
            "zip_type": info.get("zip_type", "unknown_zip"),
            "stats": stats,
        }

        # 내부에서 뽑은 대표 이미지(sample_image)로 썸네일 생성
        sample_image = info.get("sample_image")
        if sample_image:
            thumb = create_image_thumbnail(sample_image)
            if thumb:
                preview["thumbnail"] = thumb

    else:
        # 알 수 없는 타입: 그냥 파일 크기 정도만 기록
        preview = {"info": "unknown file type"}

    # JSON 직렬화 안전 처리
    preview = clean_json_value(preview)
    missing_rate = clean_json_value(missing_rate)

    # 4) Dataset 엔티티 구성
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
        version="v1",  # 버전 관리 고도화는 나중에
    )

    # 5) DB 저장
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return dataset