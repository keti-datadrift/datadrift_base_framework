#------------------------------------------------------------------------------
# data drift (dd) management module
# jpark @ KETI
#------------------------------------------------------------------------------

import os
import json
import re
import numpy as np
import torch
from PIL import Image
from tqdm import tqdm
import hashlib
import clip  # OpenAI CLIP model


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def compute_folder_hash(folder_path):
    """폴더 내 이미지들의 이름, 수정 시간, 크기 기반 해시 계산"""
    hash_obj = hashlib.sha256()

    if folder_path is None:
        return ''
        
    for fname in sorted(os.listdir(folder_path)):
        if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
            fpath = os.path.join(folder_path, fname)
            try:
                stat = os.stat(fpath)
                hash_obj.update(fname.encode())
                hash_obj.update(str(stat.st_mtime).encode())
                hash_obj.update(str(stat.st_size).encode())
            except Exception as e:
                print(f"[WARN] 해시 생성 실패: {fname}, {e}")

    return hash_obj.hexdigest()


def get_embedder(name="clip"):
    if name == "clip":
        model, preprocess = clip.load("ViT-B/32", device=DEVICE)

        def embed(images):
            embs = []
            for img in images:
                img_tensor = preprocess(img).unsqueeze(0).to(DEVICE)
                with torch.no_grad():
                    feat = model.encode_image(img_tensor).cpu().numpy().flatten()
                embs.append(feat)
            return np.array(embs)

        return embed
    else:
        raise ValueError(f"Unsupported embedder: {name}")


def embed_images_with_cache(folder_path, embedder_name="clip"):
    embedder = get_embedder(embedder_name)
    folder_hash = compute_folder_hash(folder_path)
    
    # 🔐 경로 구조: {folder_path}/dd_cache/{embedder_name}/{folder_hash}.npz
    cache_dir = os.path.join(folder_path, "dd_cache", embedder_name)
    os.makedirs(cache_dir, exist_ok=True)

    cache_file = os.path.join(cache_dir, f"{folder_hash}.npz")
    hash_record_path = os.path.join(cache_dir, "hash_records.json")

    # 🧠 기존 캐시 확인    
    if os.path.exists(cache_file):
        # st.info(f"✅ 임베딩 캐시 로딩: {cache_file}")
        print(f"✅ [임베딩 캐시 로딩]: {cache_file}")
        data = np.load(cache_file, allow_pickle=True)
        return data["embeddings"], list(data["filenames"])

    # 이미지 로딩
    images, paths = [], []
    for fname in sorted(os.listdir(folder_path)):
        if fname.lower().endswith((".jpg", ".jpeg", ".png")):
            try:
                img_path = os.path.join(folder_path, fname)
                img = Image.open(img_path).convert("RGB")
                images.append(img)
                paths.append(img_path)
            except Exception as e:
                st.error(f"❌ {fname} 로딩 실패: {e}")

    # 임베딩
    st.write("🔄 임베딩 중...")
    embeddings = []
    for i in range(0, len(images), 16):
        batch = images[i:i+16]
        embs = embedder(batch)
        embeddings.append(embs)
    embeddings = np.vstack(embeddings)

    # 저장
    np.savez(cache_file, embeddings=embeddings, filenames=np.array(paths))

    # 🔑 해시 기록 저장
    hash_records = {}
    if os.path.exists(hash_record_path):
        try:
            with open(hash_record_path, "r", encoding="utf-8") as f:
                hash_records = json.load(f)
        except json.JSONDecodeError:
            pass
    hash_records[f"{embedder_name}_{folder_hash}"] = {"folder": folder_path}
    with open(hash_record_path, "w", encoding="utf-8") as f:
        json.dump(hash_records, f, indent=2, ensure_ascii=False)

    st.success(f"📦 캐시에 저장 완료: {cache_file}")
    return embeddings, paths


def run(folder_paths, embedder_name="clip"):
    if isinstance(folder_paths, str):
        folder_paths = re.split(r'[,\s]+', folder_paths.strip())
        folder_paths = [f for f in folder_paths if f]

    all_results = {}
    for folder in folder_paths:
        emb, fnames = embed_images_with_cache(folder, embedder_name=embedder_name)
        all_results[folder] = {
            "embeddings": emb,
            "filenames": fnames
        }

    return all_results


if __name__ == "__main__":
    folders = "data/processed/train1/images data/processed/train2/images"
    results = run(folders)
    for folder, content in results.items():
        print(f"{folder}: {len(content['embeddings'])} embeddings")

#------------------------------------------------------------------------------
# End of this file
#------------------------------------------------------------------------------