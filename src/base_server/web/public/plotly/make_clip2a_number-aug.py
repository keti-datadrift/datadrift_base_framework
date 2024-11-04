
data_dir = "/home/jpark/www/01_testseq/number-aug"  # 이미지가 있는 디렉토리

import os
import torch
from PIL import Image
import clip
import pandas as pd

# CLIP 모델 및 처리기 로드
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# 데이터 디렉토리 설정
subfolders = [f for f in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, f))]  # 서브폴더 리스트

# 이미지 임베딩을 저장할 리스트
embeddings = []
labels = []
image_paths = []

# 모든 서브폴더를 순회하며 이미지 임베딩 처리
for label in subfolders:
    folder_path = os.path.join(data_dir, label)
    image_files = [f for f in os.listdir(folder_path) if f.endswith(('png', 'jpg', 'jpeg'))]  # 이미지 파일 필터링

    for image_file in image_files:
        try:
            # 이미지 로드 및 전처리
            image_path = os.path.join(folder_path, image_file)
            image = Image.open(image_path)
            image = preprocess(image).unsqueeze(0).to(device)

            # CLIP 모델을 사용하여 임베딩 벡터 생성
            with torch.no_grad():
                image_features = model.encode_image(image)

            # 임베딩을 CPU로 이동 및 numpy 배열로 변환
            embedding_vector = image_features.cpu().numpy().flatten()

            # 임베딩 벡터, 레이블(서브폴더 이름), 이미지 경로 저장
            embeddings.append(embedding_vector)
            labels.append(label)  # 서브폴더 이름을 레이블로 저장
            image_paths.append(image_path)

            print(f"Processed {image_file} in {label}")

        except Exception as e:
            print(f"Error processing {image_file} in {label}: {e}")

# 임베딩 벡터를 데이터프레임으로 변환
df = pd.DataFrame(embeddings)
df['label'] = labels  # 레이블 컬럼 추가
df['image_path'] = image_paths  # 이미지 경로 컬럼 추가

# CSV 파일로 저장
output_csv = "number-aug.csv"
df.to_csv(output_csv, index=False)

print(f"Embedding vectors with labels saved to {output_csv}")