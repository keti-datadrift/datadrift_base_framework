import os
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel
import umap.umap_ as umap
import numpy as np
import pandas as pd # pandas 임포트

# --- 설정 ---
IMAGE_FOLDER = './imgs' # 이미지가 있는 폴더 경로
DINOV2_MODEL_NAME = "facebook/dinov2-base"
OUTPUT_CSV_FILE = './tmp/dinov2_embeddings.csv' # CSV 파일 이름
TARGET_DIMENSIONS = 3 # 임베딩을 3D로 축소하여 시각화

# --- 디바이스 설정 ---
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

# --- 1. DINOv2 모델 및 프로세서 로드 ---
print(f"Loading DINOv2 model: {DINOV2_MODEL_NAME}...")
processor = AutoImageProcessor.from_pretrained(DINOV2_MODEL_NAME)
model = AutoModel.from_pretrained(DINOV2_MODEL_NAME).to(device)
model.eval()
print("DINOv2 model loaded.")

# --- 2. 이미지 로드 및 임베딩 추출 ---
image_paths = []
embeddings_list = []
image_filenames = []

print(f"Reading images from {IMAGE_FOLDER} and generating embeddings...")
# 이미지 폴더가 없다면 더미 이미지 생성 (예시를 위해)
if not os.path.exists(IMAGE_FOLDER):
    print(f"Warning: Image folder '{IMAGE_FOLDER}' not found. Creating a dummy folder.")
    os.makedirs(IMAGE_FOLDER)
    from PIL import ImageDraw
    for i in range(5):
        dummy_img = Image.new('RGB', (224, 224), color = (i*50, i*30, i*70))
        d = ImageDraw.Draw(dummy_img)
        d.text((10,10), f"Dummy {i}", fill=(255,255,255))
        dummy_img.save(os.path.join(IMAGE_FOLDER, f'dummy_image_{i}.png'))
    print(f"Created {5} dummy images in '{IMAGE_FOLDER}'. Please replace them with your actual images.")

for filename in os.listdir(IMAGE_FOLDER):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
        img_path = os.path.join(IMAGE_FOLDER, filename)
        try:
            image = Image.open(img_path).convert("RGB")
            inputs = processor(images=image, return_tensors="pt").to(device)

            with torch.no_grad():
                outputs = model(**inputs)
                embedding = outputs.last_hidden_state[:, 0, :].squeeze().cpu().numpy()

            embeddings_list.append(embedding)
            image_paths.append(img_path)
            image_filenames.append(filename) # 파이썬 문자열 그대로 유지
        except Exception as e:
            print(f"Error processing {img_path}: {e}")

if not embeddings_list:
    print("No images processed. Exiting.")
    exit()

all_embeddings = np.array(embeddings_list)
print(f"Extracted {len(all_embeddings)} embeddings, each with shape {all_embeddings.shape[1]}.")

# --- 3. 차원 축소 (UMAP 사용 권장) ---
print(f"Reducing dimensions to {TARGET_DIMENSIONS}D using UMAP...")
reducer = umap.UMAP(n_components=TARGET_DIMENSIONS, random_state=42)
reduced_embeddings = reducer.fit_transform(all_embeddings)
print(f"Reduced embeddings shape: {reduced_embeddings.shape}")

# --- 4. 데이터프레임 생성 및 CSV 파일로 저장 ---
print(f"Saving embeddings to {OUTPUT_CSV_FILE} as CSV...")

# DataFrame 생성
# X, Y, Z 컬럼을 reduced_embeddings에서 가져옵니다.
df_data = {
    'X': reduced_embeddings[:, 0],
    'Y': reduced_embeddings[:, 1],
    'Z': reduced_embeddings[:, 2]
}
df = pd.DataFrame(df_data)

# 파일명 컬럼 추가
df['Filename'] = image_filenames

# CSV 파일로 저장
df.to_csv(OUTPUT_CSV_FILE, index=False) # 인덱스를 파일에 포함하지 않음

print(f"DINOv2 embeddings saved as CSV to '{OUTPUT_CSV_FILE}'.")
print("이제 ParaView GUI 또는 pvpython 스크립트를 사용하여 이 파일을 시각화할 수 있습니다.")