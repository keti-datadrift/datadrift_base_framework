#------------------------------------------------------------------------------
# data drift (dd) management module
# jpark @ KETI
#------------------------------------------------------------------------------

import os
import pickle
from PIL import Image
from tqdm import tqdm
import numpy as np
import torch
import clip  # OpenAI CLIP model

CACHE_NAME = "clip_cache.pkl"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def load_or_compute_clip_embeddings(folder_path):
    cache_path = os.path.join(folder_path, CACHE_NAME)
    image_paths = sorted([os.path.join(folder_path, f) for f in os.listdir(folder_path)
                          if f.lower().endswith(('.png', '.jpg', '.jpeg'))])

    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            cache = pickle.load(f)
        if cache.get('image_paths') == image_paths:
            print(f"[CACHE] Using cached embeddings for {folder_path}")
            return cache['embeddings'], cache['filenames']

    print(f"[CLIP] Computing embeddings for {folder_path}")
    model, preprocess = clip.load("ViT-B/32", device=DEVICE)
    embeddings = []
    filenames = []

    for path in tqdm(image_paths):
        try:
            image = preprocess(Image.open(path).convert("RGB")).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                embedding = model.encode_image(image).cpu().numpy().flatten()
            embeddings.append(embedding)
            filenames.append(os.path.basename(path))
        except Exception as e:
            print(f"[ERROR] Skipping {path}: {e}")

    embeddings = np.array(embeddings)

    with open(cache_path, 'wb') as f:
        pickle.dump({'embeddings': embeddings, 'image_paths': image_paths, 'filenames': filenames}, f)

    return embeddings, filenames

import re
def run(folder_paths):
    # 문자열인 경우: 쉼표, 공백, 탭 등을 기준으로 분리
    if isinstance(folder_paths, str):
        folder_paths = re.split(r'[,\s]+', folder_paths.strip())
        folder_paths = [f for f in folder_paths if f]  # 빈 문자열 제거

    all_embeddings = {}
    for folder in folder_paths:
        embeddings, filenames = load_or_compute_clip_embeddings(folder)
        all_embeddings[folder] = {
            "embeddings": embeddings,
            "filenames": filenames
        }
    return all_embeddings

#------------------------------------------------------------------------------
# End of this file
#------------------------------------------------------------------------------